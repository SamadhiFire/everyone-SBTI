<div align="center">

<br />
<br />
<br />

<h1>测所有人SBTI.Skill</h1>

<p>
  <strong>闺蜜，我想测前任、现任、Crush、导师、老板、同事的 SBTI。</strong>
</p>

<p>
  大家之前蒸出来的人别落灰了，统统可以再交给 <code>测所有人SBTI.Skill</code>。<br />
  它会直接生成一份<strong>能看、能发、还能导出分享</strong>的 SBTI 报告。
</p>

<br />

![Codex Compatible](https://img.shields.io/badge/Codex-Compatible-black)
![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-7c3aed)
![Single File HTML](https://img.shields.io/badge/Output-Single%20File%20HTML-0f766e)
![Official Images](https://img.shields.io/badge/Poster-Official%20Images-2e7d32)
![License MIT](https://img.shields.io/badge/License-MIT-f5b301)

<br />
<br />

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

`测所有人SBTI.Skill` 是一个下游报告 skill。

不负责蒸馏人物，
肯定也不负责替你采访或让你自己填问卷。  
它只做一件事：读取已经蒸馏好的人物目录，复用原版 SBTI 题库，生成 `sbti-report.html` 和 `sbti-report.json`。

> [!IMPORTANT]
> 先用别的人物蒸馏 skill 把人蒸出来，再用这个 skill 给 TA 出一份完整的 SBTI 报告。

## 2. 亮点

- **原版题库代理测评**：不是随手贴几句性格标签。
- **直接生成报告文件**：输出单文件 `HTML` 和 `JSON` 结果。
- **尽量还原原站观感**：复用原版风格和官方配图。
- **支持导出分享**：右上角保留 `导出长图`。

你也可以直接生成一份完整的 SBTI 报告，效果可以点开看：

<p align="center">
  <a href="https://htmlpreview.github.io/?https://raw.githubusercontent.com/SamadhiFire/everyone-s-SBTI/main/fixtures/exes/demo-ex/sbti-report.html">
    <img alt="在线查看 SBTI 示例报告" src="https://img.shields.io/badge/在线查看-SBTI%20示例报告-b8842c?style=for-the-badge&logo=html5&logoColor=white" />
  </a>
  
</p>

## 3. 核心技术

| 模块 | 怎么做 | 带来的结果 |
| --- | --- | --- |
| 目标识别 | 自动识别 `SKILL.md` / `persona.md` / `memory.md` / `meta.json` | 少手动传参，直接锁定人物目录 |
| 代理测评 | 优先 `conversation-first`，失败时走 `file-fallback` | 能对话就对话，不能对话也能兜底生成 |
| 原版资源复用 | 读取原版题库、类型映射和官方图片 | 结果更贴近原站，不像临时拼装页 |
| 单文件输出 | 内嵌样式和图片，直接写回目标目录 | 双击可开，右上角可导出长图 |

## 4. 适配的上游 Skills

你可以先用这些人物蒸馏 skill，把你想蒸馏的人物做出来，再把结果交给本 skill 生成 SBTI 报告。
在这里表示对各位原作的感谢：

<p align="center">
  <a href="https://github.com/NatalieCao323/crush-skill">crush.skill</a> ·
  <a href="https://github.com/therealXiaomanChu/ex-skill">前任.skill</a> ·
  <a href="https://github.com/jiangziyan-693/MamaSkill">妈妈.skill</a> ·
  <a href="https://github.com/notdog1998/yourself-skill">自己.skill</a> ·
  <a href="https://github.com/titanwings/colleague-skill">同事.skill</a> ·
  <a href="https://github.com/ybq22/supervisor">导师.skill</a> ·
  <a href="https://github.com/xiaoheizi8/crush-skills">crush.skill（扩展版）</a> ·
  <a href="https://github.com/Janlaywss/hu-chenfeng-skill">户晨风.skill</a>
</p>

一句话理解它们的关系：

- 上游人物 skill 负责**把人蒸出来**
- `测所有人SBTI.Skill` 负责**把这个人写成一份 SBTI 报告**

> [!NOTE]
> 这里说的“适配”，是适配这些 skill 产出的人物目录。  
> 不是把仓库链接直接丢给它，它就能凭空开始测。

## 5. 怎么使用

### Claude Code

Claude Code 会从项目里的 `.claude/skills/`，或全局的 `~/.claude/skills/` 读取 skill。

```bash
# 装到当前项目
mkdir -p .claude/skills
git clone https://github.com/SamadhiFire/everyone-s-SBTI.git .claude/skills/everyone-s-sbti

# 或装到全局
git clone https://github.com/SamadhiFire/everyone-s-SBTI.git ~/.claude/skills/everyone-s-sbti
```

### Codex

如果你在用 Codex，一般放进 `$CODEX_HOME/skills/` 或 `~/.codex/skills/` 就行。

```bash
git clone https://github.com/SamadhiFire/everyone-s-SBTI.git ~/.codex/skills/everyone-s-sbti
```

### 其他平台

不是每个平台都叫 skill，但多数 Agent 都支持“自定义提示词 / 自定义技能目录 / 项目规则”。

```text
请帮我接入这个 skill：
https://github.com/SamadhiFire/everyone-s-SBTI

按 README 安装；如果当前平台不支持 skill，就转成等价的自定义规则。
```

### 调取指令

```text
调用 everyone-s-SBTI，给刚蒸馏好的 crush 生成一份 SBTI 报告。
```

```text
请用 everyone-s-SBTI 读取这个人物目录里的 SKILL.md、persona.md、memory.md、meta.json，并输出 sbti-report.html 和 sbti-report.json。
```

### 命令行

如果你的 Agent 支持直接跑命令，也可以这样执行：

```bash
python scripts/generate_sbti_report.py --target "<target-dir>"
```

> [!TIP]
> Python 侧不用额外装第三方依赖，标准库就能跑。  
> 如果你还想让仓库在生成报告时顺手产出 `sbti-report.png`，记得保留 `scripts/capture_report_png.mjs`，并准备好 `Node.js + Chromium/Edge`。

生成结果会写回目标人物目录本身：

- `<target-dir>/sbti-report.html`
- `<target-dir>/sbti-report.json`

## 6. 仓库结构

```text
.
├─ SKILL.md
├─ README.md
├─ scripts/
│  ├─ generate_sbti_report.py
│  ├─ capture_report_png.mjs
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
      ├─ SKILL.md
      ├─ persona.md
      ├─ memory.md
      ├─ meta.json
      ├─ sbti-report.html
      └─ sbti-report.json
```

## 7. 致谢

感谢原始创意、镜像与开源项目，让这个 skill 能站在前人的肩膀上认真胡闹：

- 原作者主页：[Q肉儿串儿](https://space.bilibili.com/417038183/dynamic?spm_id_from=333.1368.list.card_avatar.click)
- 开源项目：[pingfanfan/SBTI](https://github.com/pingfanfan/SBTI?tab=MIT-1-ov-file)
- 镜像仓库：[UnluckyNinja/SBTI-test](https://github.com/UnluckyNinja/SBTI-test)

如果你喜欢这个项目，也请顺手尊重原作者、尊重原始创意来源、尊重开源边界。  
可以二创，可以继续适配，也可以继续整活，但别把别人的东西换个壳就当成自己从零写的。
