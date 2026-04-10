<div align="center">

# 测所有人SBTI.Skill

> “最近大家都在蒸馏各种人。  
> 但蒸馏完之后，总得有人把这些人做成一份像样、能看、能发、能导出长图的 SBTI 报告。”

**测所有人SBTI.Skill 不是问卷网站，不是心理学诊断工具，也不是单独可玩的成品。**  
**它只做一件事：把已经蒸馏好的人物 skill，自动转换成一份复用原版题库、原版配图、原版结果页风格的 SBTI 报告。**

![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-black)
![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-7c3aed)
![Single File HTML](https://img.shields.io/badge/Output-Single%20File%20HTML-0f766e)
![Official Images](https://img.shields.io/badge/Poster-Official%20Images-2e7d32)

不是自己答题，不是自己测自己。  
它的用途，是把**别人已经蒸馏好的人物目录**拿来做代理测评，产出 `sbti-report.html` 和 `sbti-report.json`。

<p>
  <a href="#这是什么">这是什么</a> ·
  <a href="#亮点">亮点</a> ·
  <a href="#核心技术">核心技术</a> ·
  <a href="#适配的上游-skills">适配的上游 Skills</a> ·
  <a href="#怎么使用">怎么使用</a> ·
  <a href="#仓库结构">仓库结构</a> ·
  <a href="#致谢">致谢</a>
</p>

</div>

## 这是什么

`测所有人SBTI.Skill` 是一个**配套型 skill**。

它本身不负责：

- 蒸馏人物
- 生成 persona
- 采访目标
- 替代问卷站

它负责的是：

- 接收一个已经蒸馏好的目标人物 skill 目录
- 读取其中的 `SKILL.md`、`persona.md`、`memory.md`、`meta.json` 等材料
- 复用原版 SBTI 题库做代理测评
- 生成一份单文件、可离线打开、右上角可导出长图的 HTML 报告

> [!IMPORTANT]
> 这个 skill **必须和别的人物蒸馏 skill 配合使用**。  
> **单独使用基本没用**，因为它不会凭空创造人物画像，只会消费别人已经蒸馏好的结果。

## 亮点

- **复用原版题库**：不是随便写几条“人格描述”，而是基于原版 SBTI 题目做代理测评。
- **复用原版配图**：每种人格都优先读取原版仓库里的官方图片，一一对应，不再使用自绘占位图。
- **原版结果页风格**：报告页面结构对齐原站结果页，保留右上角 `导出长图` 按钮。
- **单文件 HTML 输出**：生成后的报告可直接离线打开，不依赖外部静态资源。
- **兼容多种人物 skill 生态**：既支持 Claude 风格，也兼容 Codex 风格的人物目录。
- **支持双模式推断**：能直接对话目标 skill 时走 `conversation-first`，否则自动降级到 `file-fallback`。
- **落地而不是嘴上兼容**：最终会把报告真正写进目标人物目录，而不是只给一段解释。

## 核心技术

### 1. 目标人物目录自动发现

脚本会优先寻找像人物 skill 的目录，并对常见标记文件加权：

- `SKILL.md`
- `persona.md`
- `memory.md`
- `meta.json`

同时会优先考虑这些常见位置：

- `./exes/{slug}`
- `./.claude/skills/*`
- `./.codex/skills/*`
- `./skills/*`

如果目录结构比较特殊，也可以直接显式传入 `--target` 指定。

### 2. 双模式测评

#### `conversation-first`

如果运行环境支持直接和目标 skill 对话：

1. 先导出问卷结构
2. 按协议让目标 skill 代答
3. 生成结构化答案 JSON
4. 再合成报告

#### `file-fallback`

如果当前环境无法稳定对话目标 skill：

- 直接读取目录中的 Markdown / TXT / JSON 材料
- 做十五维关键词推断
- 结合 MBTI 线索和附加规则补全答案
- 生成可见低置信度的代理测评结果

### 3. 原版图片一一对应

本仓库会读取本地 `SBTI-test-main/index.html` 中的 `TYPE_IMAGES` 映射表，并将原版图片内嵌进生成结果。

也就是说：

- `MUM` 对应 `MUM.png`
- `DEAD` 对应 `DEAD.png`
- `OJBK` 对应 `OJBK.png`
- `WOC!` 对应 `WOC.png`

如果某种人格没有对应图片，脚本会明确说明原因，而不是偷偷画一个替代图糊弄过去。

### 4. 单文件 HTML 报告生成

输出文件包括：

- `sbti-report.html`
- `sbti-report.json`

其中 HTML 报告具备：

- 原版结果页风格布局
- 官方人格图
- 十五维评分
- 简单解读
- 友情提示
- 作者的话
- 右上角 `导出长图`

## 适配的上游 Skills

这个 skill 目前是为了和下面这些“人物蒸馏 skill / 人物生成 skill”配合使用的。

> [!NOTE]
> 这里说的“适配”，指的是**适配这些 skill 生成出来的人物目录**。  
> 不是说把这些仓库根目录单独丢进来就一定能直接跑。

已适配的上游 skills：

- [NatalieCao323/crush-skill](https://github.com/NatalieCao323/crush-skill)
- [therealXiaomanChu/ex-skill](https://github.com/therealXiaomanChu/ex-skill)
- [jiangziyan-693/MamaSkill](https://github.com/jiangziyan-693/MamaSkill)
- [notdog1998/yourself-skill](https://github.com/notdog1998/yourself-skill)
- [titanwings/colleague-skill](https://github.com/titanwings/colleague-skill)
- [ybq22/supervisor](https://github.com/ybq22/supervisor)
- [xiaoheizi8/crush-skills](https://github.com/xiaoheizi8/crush-skills)
- [Janlaywss/hu-chenfeng-skill](https://github.com/Janlaywss/hu-chenfeng-skill)

这些仓库和本 skill 的关系是：

- 上游 skill 负责**蒸馏人物**
- 本 skill 负责**给蒸馏结果做 SBTI 报告**

一句话：

**它是“人物 skill 的后处理器”，不是独立产品。**

## 怎么使用

### 使用前提

你需要先有一个已经蒸馏好的人物目录，里面最好至少包含以下文件中的若干个：

- `SKILL.md`
- `persona.md`
- `memory.md`
- `meta.json`

### 在对话里触发

可以直接说：

- `调用 everyone-s-SBTI`
- `测一测他的 sbti 是什么`
- `给这个人做 sbti 报告`
- `生成 sbti html`

### 用脚本直接生成

```bash
python scripts/generate_sbti_report.py --target "<target-dir>"
```

如果你已经准备好了结构化答案文件：

```bash
python scripts/generate_sbti_report.py --target "<target-dir>" --answers-file "<answers.json>"
```

导出问卷结构：

```bash
python scripts/generate_sbti_report.py --dump-questions
```

### 输出位置

报告会写进**目标人物目录本身**，而不是写回本仓库根目录：

- `<target-dir>/sbti-report.html`
- `<target-dir>/sbti-report.json`

## 仓库结构

```text
.
├─ SKILL.md                    # Skill 入口说明
├─ scripts/
│  ├─ generate_sbti_report.py  # 主生成脚本
│  └─ smoke_test.py            # 基础冒烟测试
├─ assets/
│  └─ sbti-data.json           # 题库、类型库、十五维说明
├─ references/
│  └─ answer-protocol.md       # conversation-first 的结构化答题协议
├─ SBTI-test-main/             # 原版镜像资源（题页/图片映射/官方配图）
└─ fixtures/
   └─ exes/demo-ex/            # 本地 demo 人物目录与示例报告
```

## 为什么必须配合别的 skill

因为这个 skill 的输入不是“一个名字”，而是“一个已经被蒸馏好的目录”。

比如：

- `crush-skill` 产出的暗恋对象目录
- `ex-skill` 产出的 ex 目录
- `yourself-skill` 产出的自己目录
- `colleague-skill` 产出的同事目录
- `supervisor` 产出的上级目录

没有这些上游材料，本 skill 就没有东西可以分析，也无法生成像样的报告。

所以请把它理解成：

**人物蒸馏 skill 的报告层，而不是人物蒸馏 skill 本体。**

## 致谢

感谢原始创意、镜像与开源工作，让这个配套 skill 有机会站在前人的肩膀上认真胡闹：

- 原作者主页：<https://space.bilibili.com/417038183/dynamic?spm_id_from=333.1368.list.card_avatar.click>
- `pingfanfan/SBTI`：<https://github.com/pingfanfan/SBTI?tab=MIT-1-ov-file>
- `UnluckyNinja/SBTI-test`：<https://github.com/UnluckyNinja/SBTI-test>

如果你喜欢这个项目，也请优先尊重原作者、尊重原始创意来源、尊重开源边界。  
可以二创，可以适配，可以继续折腾，但别把别人的东西拿来换个壳就装成从零开始。

