---
name: everyone-s-sbti
description: 自动评估刚蒸馏好的人物 persona skill，复用原版 SBTI 题目生成单文件 HTML 报告，并在右上角提供“导出长图”按钮。
argument-hint: [target-slug-or-path]
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

# everyone-s-SBTI

## 什么时候触发

当用户说出以下意思时触发本 skill：

- `调用 everyone-s-SBTI`
- `测一测他的 sbti 是什么`
- `给这个人做 sbti 报告`
- `生成 sbti html`
- 任何明确表示“拿当前蒸馏出来的人物 skill，自动生成 SBTI 报告”的请求

## 这个 skill 做什么

本 skill 会自动找到当前目标 persona skill，用原版 SBTI 题目做代理测评，并在目标目录里写出：

- `sbti-report.html`
- `sbti-report.json`

注意：

- 报告会写到**目标人物 skill 的目录里**
- 不会写到本 skill 自己的目录里

## 目标发现优先级

同时兼容 Codex 风格和 Claude Code 风格的 skill 目录。

默认按以下顺序找目标：

1. 用户显式传入的路径或 slug
2. 当前上下文里已经很明确的目标 skill
3. 附近常见的人物 skill 目录，例如 `./exes/{slug}`、`./.claude/skills/*`、`./.codex/skills/*`、`./skills/*`
4. 最近修改过的、最像 persona skill 的目录

只有在多个候选目标都一样像、真的分不清的时候，才问用户选哪个。否则直接自动继续。

## 测评策略

### 优先：conversation-first

如果当前运行环境支持直接调用、追问或对话目标 persona skill：

1. 先拿问卷结构：

```bash
python scripts/generate_sbti_report.py --dump-questions
```

2. 按 [references/answer-protocol.md](references/answer-protocol.md) 里的结构化协议，让目标 skill 代答
3. 把答案收集成 JSON
4. 再生成报告：

```bash
python scripts/generate_sbti_report.py --target "<target-dir>" --answers-file "<answers.json>"
```

### 兜底：file-fallback

如果当前环境没法直接对话目标 skill，或者目标 skill 回答不稳定，就走文件推断模式：

```bash
python scripts/generate_sbti_report.py --target "<target-dir>"
```

脚本会读取这些材料来做推断：

- `SKILL.md`
- `persona.md`
- `memory.md`
- `meta.json`
- 目标目录附近的说明文档和文本材料

然后自动推断十五维倾向、合成题目答案，并生成一份**低置信度可见**的报告。

## 行为规则

- 不要让用户手动答题
- 默认跟随当前对话语言；语言不明确时优先中文
- 报告是**对蒸馏 persona 的代理测评**，不是医学、心理学或科学诊断
- 允许低置信度，但不允许伪装成高确定性
- 如果目标目录里已存在 `sbti-report.html` 和 `sbti-report.json`，直接覆盖

## 输出要求

生成的 HTML 报告必须：

- 单文件
- 可离线打开
- 自带样式
- 右上角有 `导出长图` 按钮

报告至少包含：

- 目标人物名称和生成时间
- 最终 SBTI 类型
- 总体置信等级
- 十五维总览
- 证据摘要
- 方法说明
- 代理测评免责声明

## 对 ex-skill 的兼容说明

`ex-skill` 通常把目标人物写在 `./exes/{slug}/` 下，并且常见文件包括：

- `memory.md`
- `persona.md`
- `meta.json`
- 合并后的目标 `SKILL.md`

这些文件都是本 skill 的一等兜底输入源。

