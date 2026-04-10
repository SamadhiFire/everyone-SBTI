<div align="center">

<br />

# 测所有人SBTI.Skill

**把已经蒸馏好的人物 skill，自动变成一份能看、能发、能导出长图的 SBTI 报告。**

不是问卷网站，不是心理学诊断，也不是单独可玩的成品。  
它只负责一件事：**读取现成的人物 skill，复用原版题库、原版配图、原版结果页风格，生成 `sbti-report.html` 和 `sbti-report.json`。**

![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-black)
![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-7c3aed)
![Single File HTML](https://img.shields.io/badge/Output-Single%20File%20HTML-0f766e)
![Official Images](https://img.shields.io/badge/Poster-Official%20Images-2e7d32)

<br />

不是自己答题，不是自己测自己。  
它的用途，是把**别人已经蒸馏好的人物目录**拿来做代理测评，产出一份像样的 SBTI 报告。

<p>
  <a href="#1-项目定位">项目定位</a> ·
  <a href="#2-亮点">亮点</a> ·
  <a href="#3-核心技术">核心技术</a> ·
  <a href="#4-适配的上游-skills">适配的上游 Skills</a> ·
  <a href="#5-怎么使用">怎么使用</a> ·
  <a href="#6-仓库结构">仓库结构</a> ·
  <a href="#7-致谢">致谢</a>
</p>

</div>

## 1. 项目定位

`测所有人SBTI.Skill` 是一个**配套型 skill**。

它不负责：

- 蒸馏人物
- 生成 persona
- 采访目标
- 替代问卷站

它负责：

- 接收一个已经蒸馏好的人物 skill 目录
- 读取其中的 `SKILL.md`、`persona.md`、`memory.md`、`meta.json` 等材料
- 复用原版 SBTI 题库做代理测评
- 生成一份单文件、可离线打开、右上角可导出长图的 HTML 报告

> [!IMPORTANT]
> 这个 skill **必须和别的人物蒸馏 skill 配合使用**。  
> **单独使用基本没用**，因为它不会凭空创造人物画像，只会消费别人已经蒸馏好的结果。

## 2. 亮点

- **原版题库复用**：不是随手写几条人格描述，而是基于原版 SBTI 题目做代理测评。
- **原版配图复用**：每种人格优先读取官方图片，一一对应，不再用自绘占位图糊弄。
- **原版结果页风格**：生成结果尽量贴近原站排版，并保留右上角 `导出长图` 按钮。
- **单文件 HTML**：输出后的报告可以直接离线打开，不依赖外部静态资源。
- **兼容多种人物目录**：同时兼容 Claude Code 风格和 Codex 风格的人物 skill 目录。
- **真正落地到目标目录**：不是只输出一段分析，而是会把报告写回目标人物目录。

## 3. 核心技术

这里不讲复杂词，直接说它现在靠什么工作：

### 3.1 自动找目标人物目录

脚本会优先寻找像人物 skill 的目录，并重点识别这些文件：

- `SKILL.md`
- `persona.md`
- `memory.md`
- `meta.json`

如果目录结构比较特殊，也可以直接用 `--target` 显式指定。

### 3.2 两种测评模式

- `conversation-first`：能直接和目标 skill 对话时，就让它按结构化协议代答。
- `file-fallback`：不能稳定对话时，就读取目录里的 Markdown / TXT / JSON 材料做推断。

### 3.3 官方图片映射

本仓库会读取本地 `SBTI-test-main/index.html` 中的 `TYPE_IMAGES` 映射，把官方图片直接嵌进生成结果。

也就是说：

- `MUM` 对应 `MUM.png`
- `DEAD` 对应 `DEAD.png`
- `OJBK` 对应 `OJBK.png`
- `WOC!` 对应 `WOC.png`

如果没有对应图片，脚本会明确说明原因，不会偷偷生成一张假的替代图。

### 3.4 单文件报告输出

最终输出：

- `sbti-report.html`
- `sbti-report.json`

其中 HTML 报告默认包含：

- 官方人格图
- 简单解读
- 十五维评分
- 友情提示
- 作者的话
- 导出长图按钮

## 4. 适配的上游 Skills

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

这些上游 skill 和本 skill 的关系很简单：

- 上游 skill 负责**蒸馏人物**
- 本 skill 负责**给蒸馏结果生成 SBTI 报告**

一句话总结：

**它是“人物 skill 的报告层”，不是人物 skill 本体。**

## 5. 怎么使用

### 5.1 使用前提

你需要先有一个已经蒸馏好的人物目录，里面最好至少包含以下文件中的若干个：

- `SKILL.md`
- `persona.md`
- `memory.md`
- `meta.json`

### 5.2 在对话里触发

可以直接说：

- `调用 everyone-s-SBTI`
- `测一测他的 sbti 是什么`
- `给这个人做 sbti 报告`
- `生成 sbti html`

### 5.3 用脚本直接生成

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

### 5.4 输出位置

报告会写进**目标人物目录本身**：

- `<target-dir>/sbti-report.html`
- `<target-dir>/sbti-report.json`

## 6. 仓库结构

```text
.
├─ SKILL.md
├─ README.md
├─ scripts/
│  ├─ generate_sbti_report.py
│  └─ smoke_test.py
├─ assets/
│  └─ sbti-data.json
├─ references/
│  └─ answer-protocol.md
├─ SBTI-test-main/
│  ├─ index.html
│  └─ image/
└─ fixtures/
   └─ exes/demo-ex/
```

### 6.1 关键目录说明

- `scripts/`：主生成逻辑和测试脚本
- `assets/`：题库、类型库、十五维说明
- `references/`：conversation-first 的答题协议
- `SBTI-test-main/`：原版镜像资源，包括官方图片映射
- `fixtures/`：本地 demo 和示例输出

## 7. 致谢

感谢原始创意、镜像与开源工作，让这个配套 skill 有机会站在前人的肩膀上认真胡闹：

- 原作者主页：<https://space.bilibili.com/417038183/dynamic?spm_id_from=333.1368.list.card_avatar.click>
- `pingfanfan/SBTI`：<https://github.com/pingfanfan/SBTI?tab=MIT-1-ov-file>
- `UnluckyNinja/SBTI-test`：<https://github.com/UnluckyNinja/SBTI-test>

如果你喜欢这个项目，也请优先尊重原作者、尊重原始创意来源、尊重开源边界。  
可以二创，可以适配，可以继续折腾，但别把别人的东西换个壳就装成自己从零开始。

