#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "assets" / "sbti-data.json"
ORIGINAL_MIRROR_DIR = BASE_DIR / "SBTI-test-main"
ORIGINAL_INDEX_PATH = ORIGINAL_MIRROR_DIR / "index.html"
OUTPUT_STEM = "sbti-report"
PNG_CAPTURE_SCRIPT = BASE_DIR / "scripts" / "capture_report_png.mjs"
PNG_CAPTURE_VIEWPORT = (1440, 960)
IGNORED_AUTO_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    "agents",
    "assets",
    "references",
    "scripts",
    "fixtures",
    "node_modules",
    "venv",
    ".venv",
}

DIMENSION_HINTS: dict[str, dict[str, list[str]]] = {
    "S1": {
        "low": ["自卑", "敏感", "不够好", "配不上", "没安全感", "讨好", "内耗", "自我否定", "胆怯"],
        "high": ["自信", "笃定", "自尊", "松弛", "底气", "有数", "不卑不亢", "稳定"],
    },
    "S2": {
        "low": ["迷茫", "不知道自己", "摇摆", "混乱", "拧巴", "矛盾", "找不到自己"],
        "high": ["清楚自己", "清晰", "知道自己", "明确", "自知", "有追求", "目标清晰"],
    },
    "S3": {
        "low": ["躺平", "安稳", "求稳", "舒服", "及时行乐", "佛系", "摆烂"],
        "high": ["上进", "成长", "野心", "事业心", "不断变强", "往上爬", "目标感", "要赢"],
    },
    "E1": {
        "low": ["患得患失", "焦虑型", "怕被抛弃", "吃醋", "不回消息就", "试探", "缺安全感"],
        "high": ["安全感", "信任", "稳定依恋", "不乱猜", "关系稳定", "愿意相信"],
    },
    "E2": {
        "low": ["慢热", "克制", "不上头", "保留", "防备", "留后手", "不会陷太深"],
        "high": ["深情", "恋爱脑", "投入", "认真对待感情", "上头", "全情投入", "很珍惜"],
    },
    "E3": {
        "low": ["黏人", "依赖", "需要陪伴", "离不开", "想要一直在一起"],
        "high": ["独立空间", "边界感", "个人空间", "保持距离", "不喜欢太黏", "电子围栏"],
    },
    "A1": {
        "low": ["悲观", "阴暗", "不信任", "戒备", "怀疑", "人心险恶", "防御滤镜"],
        "high": ["乐观", "相信善良", "愿意相信", "温柔看世界", "好人更多", "善意"],
    },
    "A2": {
        "low": ["叛逆", "不喜欢束缚", "自由", "随性", "打破常规", "不按规矩"],
        "high": ["规则", "秩序", "自律", "按流程", "守规矩", "讨厌失控"],
    },
    "A3": {
        "low": ["虚无", "没意义", "空虚", "无意义", "摆烂", "走过场"],
        "high": ["有方向", "意义感", "使命", "目标明确", "知道往哪走"],
    },
    "Ac1": {
        "low": ["避险", "怕麻烦", "求稳", "别翻车", "风险", "保守"],
        "high": ["结果导向", "进步", "成长", "推进", "想赢", "成果"],
    },
    "Ac2": {
        "low": ["犹豫", "纠结", "反复想", "拿不定主意", "优柔寡断"],
        "high": ["果断", "决绝", "拍板", "利落", "说干就干"],
    },
    "Ac3": {
        "low": ["拖延", "死线", "最后一刻", "磨蹭", "拖到最后"],
        "high": ["执行力", "推进", "落地", "计划强", "说做就做", "高效"],
    },
    "So1": {
        "low": ["社恐", "慢热", "内向", "不主动", "怕生", "启动慢"],
        "high": ["社牛", "外向", "主动社交", "热情聊天", "会打开场子", "爱交朋友"],
    },
    "So2": {
        "low": ["熟了就很近", "亲密", "想要关系密切", "融入", "内圈"],
        "high": ["距离感", "边界感", "电子围栏", "别靠太近", "保留空间"],
    },
    "So3": {
        "low": ["有话直说", "直球", "坦率", "不爱绕", "直接表达"],
        "high": ["会表现不同自己", "看人下菜", "分场合", "戴面具", "切换模式", "不想暴露真实"],
    },
}

MBTI_HINTS: dict[str, dict[str, str]] = {
    "E": {"So1": "H"},
    "I": {"So1": "L"},
    "J": {"A2": "H", "Ac3": "H"},
    "P": {"A2": "L", "Ac3": "L"},
    "T": {"So3": "M", "Ac2": "H"},
    "F": {"E2": "H"},
}

DRINK_KEYWORDS = ["饮酒", "喝酒", "白酒", "红酒", "啤酒", "小酌", "微醺", "酒局", "夜店", "威士忌", "保温杯里泡白酒"]
HEAVY_DRINK_KEYWORDS = ["当白开水喝", "酒精令我信服", "海量", "灌白酒", "保温杯", "酗酒", "一天一瓶", "烈酒"]
FITNESS_KEYWORDS = ["健身", "跑步", "撸铁", "运动", "普拉提", "瑜伽"]
ART_KEYWORDS = ["艺术", "音乐", "电影", "摄影", "画画", "戏剧", "写作", "设计"]


def load_reference_data() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an SBTI report for a persona skill.")
    parser.add_argument("--target", help="Explicit target skill directory.")
    parser.add_argument("--answers-file", help="Optional JSON file with conversation-first structured answers.")
    parser.add_argument("--mode", choices=["auto", "file", "answers"], default="auto")
    parser.add_argument("--dump-questions", action="store_true", help="Print the questionnaire payload and exit.")
    return parser.parse_args()


def slugify(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", value.strip()).strip("-")
    return value or "unknown-target"


def display_target_path(target: Path) -> str:
    resolved = target.resolve()
    for root in (Path.cwd().resolve(), BASE_DIR):
        if is_relative_to(resolved, root):
            return resolved.relative_to(root).as_posix()
    return resolved.name


def find_screenshot_browser() -> str | None:
    env_browser = os.environ.get("EVERYONE_SBTI_BROWSER")
    if env_browser:
        return env_browser

    for name in (
        "msedge",
        "chrome",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ):
        path = shutil.which(name)
        if path:
            return path

    windows_candidates = [
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    ]
    for candidate in windows_candidates:
        if candidate.exists():
            return str(candidate)
    return None


def capture_report_png(html_path: Path) -> Path | None:
    browser = find_screenshot_browser()
    node = shutil.which("node")
    png_path = html_path.with_suffix(".png")
    if png_path.exists():
        png_path.unlink()
    if not browser or not node or not PNG_CAPTURE_SCRIPT.exists():
        return None

    temp_dir = Path(tempfile.mkdtemp(prefix="everyone-s-sbti-", dir=str(html_path.parent)))
    try:
        command = [
            node,
            str(PNG_CAPTURE_SCRIPT),
            "--input",
            str(html_path.resolve()),
            "--output",
            str(png_path.resolve()),
            "--browser",
            browser,
            "--width",
            str(PNG_CAPTURE_VIEWPORT[0]),
            "--height",
            str(PNG_CAPTURE_VIEWPORT[1]),
            "--profile-dir",
            str(temp_dir),
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=creationflags,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if completed.returncode == 0 and png_path.exists():
        return png_path
    warning = completed.stderr.strip() or completed.stdout.strip()
    if warning:
        print(f"[warn] png capture skipped: {warning}", file=sys.stderr)
    return None


def is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def is_candidate_dir(path: Path) -> bool:
    return any((path / marker).exists() for marker in ("SKILL.md", "persona.md", "memory.md", "meta.json"))


def score_candidate(path: Path) -> tuple[int, float]:
    score = 0
    if (path / "persona.md").exists():
        score += 60
    if (path / "memory.md").exists():
        score += 40
    if (path / "meta.json").exists():
        score += 20
    if (path / "SKILL.md").exists():
        score += 25
    if path.parent.name == "exes":
        score += 35
    if (path / "agents" / "openai.yaml").exists():
        score += 12
    if any(part.startswith(".codex") for part in path.parts):
        score += 8
    if any(part.startswith(".claude") for part in path.parts):
        score += 8
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        mtime = 0.0
    return score, mtime


def iter_search_roots(cwd: Path) -> list[Path]:
    candidates = [
        cwd,
        cwd / "exes",
        cwd / ".claude" / "skills",
        cwd / ".codex" / "skills",
        cwd / "skills",
        cwd.parent,
        cwd.parent / "exes",
        cwd.parent / ".claude" / "skills",
        cwd.parent / ".codex" / "skills",
        cwd.parent / "skills",
    ]
    unique: list[Path] = []
    seen: set[Path] = set()
    for item in candidates:
        resolved = item.resolve()
        if resolved not in seen and resolved.exists():
            unique.append(resolved)
            seen.add(resolved)
    return unique


def discover_target(explicit: str | None) -> Path:
    if explicit:
        target = Path(explicit).expanduser().resolve()
        if not target.exists():
            raise SystemExit(f"Target path does not exist: {target}")
        return target

    import os

    for env_key in ("SBTI_TARGET_PATH", "TARGET_SKILL_PATH", "CLAUDE_SKILL_TARGET_PATH", "CODEX_SKILL_TARGET_PATH"):
        env_raw = os.environ.get(env_key)
        if env_raw:
            target = Path(env_raw).expanduser().resolve()
            if target.exists():
                return target

    cwd = Path.cwd().resolve()
    found: list[tuple[int, float, Path]] = []
    for root in iter_search_roots(cwd):
        if is_relative_to(root, BASE_DIR / "fixtures"):
            continue
        if root.is_dir():
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                if child.name in IGNORED_AUTO_DIRS:
                    continue
                if is_relative_to(child.resolve(), BASE_DIR / "fixtures"):
                    continue
                if is_candidate_dir(child):
                    score, mtime = score_candidate(child)
                    found.append((score, mtime, child.resolve()))

    if not found:
        raise SystemExit("No persona-like target skill directory found. Pass --target explicitly.")

    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best = found[0]
    if len(found) > 1:
        runner_up = found[1]
        if best[0] == runner_up[0] and abs(best[1] - runner_up[1]) < 90:
            choices = ", ".join(str(item[2]) for item in found[:3])
            raise SystemExit(f"Target discovery is ambiguous. Top candidates: {choices}")
    return best[2]


def detect_runtime(target: Path) -> str:
    if target.parent.name == "exes" or (target / "persona.md").exists():
        return "claude-ex-skill"
    if (target / "agents" / "openai.yaml").exists() or ".codex" in target.as_posix():
        return "codex-skill"
    return "generic-skill"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def frontmatter_lookup(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip().strip('"').strip("'") if match else None


def collect_sources(target: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    sources: list[dict[str, str]] = []
    meta: dict[str, Any] = {}
    preferred = ["SKILL.md", "persona.md", "memory.md", "meta.json", "README.md"]
    seen: set[Path] = set()

    for name in preferred:
        path = target / name
        if path.exists():
            text = read_text(path)
            sources.append({"path": path.name, "text": text})
            seen.add(path.resolve())
            if name == "meta.json":
                try:
                    meta = json.loads(text)
                except json.JSONDecodeError:
                    meta = {}

    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() in seen:
            continue
        if path.name.startswith("sbti-report"):
            continue
        if path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        relative = path.relative_to(target)
        if any(part in {"versions", "__pycache__"} for part in relative.parts):
            continue
        sources.append({"path": relative.as_posix(), "text": read_text(path)})
        seen.add(path.resolve())
        if len(sources) >= 16:
            break

    return sources, meta


def choose_target_name(target: Path, sources: list[dict[str, str]], meta: dict[str, Any]) -> str:
    if isinstance(meta, dict):
        for key in ("name", "display_name", "nickname", "slug"):
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        profile = meta.get("profile")
        if isinstance(profile, dict):
            for key in ("name", "nickname"):
                value = profile.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    for source in sources:
        if source["path"] == "SKILL.md":
            for key in ("name", "description"):
                value = frontmatter_lookup(source["text"], key)
                if value:
                    return value
    return target.name


def match_keyword_hits(sources: list[dict[str, str]], keywords: list[str], max_hits: int = 3) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for keyword in keywords:
        kw_lower = keyword.lower()
        for source in sources:
            lowered = source["text"].lower()
            index = lowered.find(kw_lower)
            if index == -1:
                continue
            key = (source["path"], keyword)
            if key in seen:
                continue
            seen.add(key)
            snippet = source["text"][max(0, index - 28): index + len(keyword) + 40].replace("\n", " ").strip()
            hits.append({"keyword": keyword, "source": source["path"], "snippet": snippet})
            break
        if len(hits) >= max_hits:
            break
    return hits


def find_mbti_tokens(sources: list[dict[str, str]]) -> list[str]:
    tokens: list[str] = []
    pattern = re.compile(r"\b([EI][NS][FT][JP])\b", re.IGNORECASE)
    for source in sources:
        for match in pattern.findall(source["text"]):
            token = match.upper()
            if token not in tokens:
                tokens.append(token)
    return tokens


def level_score(level: str) -> int:
    return {"L": 1, "M": 2, "H": 3}[level]


def confidence_band(value: float) -> str:
    if value >= 0.78:
        return "高"
    if value >= 0.58:
        return "中"
    return "低"


def infer_dimensions(sources: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    mbti_tokens = find_mbti_tokens(sources)
    dimension_inference: dict[str, dict[str, Any]] = {}

    for dim, hint_set in DIMENSION_HINTS.items():
        low_hits = match_keyword_hits(sources, hint_set["low"])
        high_hits = match_keyword_hits(sources, hint_set["high"])
        delta = len(high_hits) - len(low_hits)
        mbti_notes: list[str] = []
        for token in mbti_tokens:
            for letter in token:
                hint_level = MBTI_HINTS.get(letter, {}).get(dim)
                if not hint_level:
                    continue
                mbti_notes.append(f"MBTI {token} 提示 {dim} 更接近 {hint_level}")
                delta += 1 if hint_level == "H" else -1 if hint_level == "L" else 0

        if delta >= 2:
            level = "H"
        elif delta <= -2:
            level = "L"
        else:
            level = "M"

        evidence_hits = high_hits if level == "H" else low_hits if level == "L" else (high_hits[:1] + low_hits[:1])
        evidence_lines = [f"{item['source']}：{item['snippet']}" for item in evidence_hits]
        if mbti_notes and len(evidence_lines) < 3:
            evidence_lines.extend(mbti_notes[: 3 - len(evidence_lines)])
        if not evidence_lines:
            evidence_lines = ["未找到稳定直接证据，按中位档保守处理。"]

        confidence = 0.38 + min(0.48, abs(delta) * 0.1 + (len(high_hits) + len(low_hits)) * 0.06)
        dimension_inference[dim] = {
            "level": level,
            "confidence": round(max(0.35, min(0.9, confidence)), 2),
            "evidence": evidence_lines,
        }
    return dimension_inference


def choose_special_answers(sources: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    corpus = "\n".join(source["text"] for source in sources).lower()
    hobby_value = 1
    hobby_evidence = "未发现明确兴趣偏好关键词，按默认非饮酒爱好处理。"

    if any(keyword.lower() in corpus for keyword in DRINK_KEYWORDS):
        hobby_value = 3
        hobby_evidence = "文本中多次出现饮酒相关描述。"
    elif any(keyword.lower() in corpus for keyword in FITNESS_KEYWORDS):
        hobby_value = 4
        hobby_evidence = "文本中出现健身或运动相关描述。"
    elif any(keyword.lower() in corpus for keyword in ART_KEYWORDS):
        hobby_value = 2
        hobby_evidence = "文本中出现艺术、音乐、影像或创作相关描述。"

    answers = {
        "drink_gate_q1": {
            "id": "drink_gate_q1",
            "option": hobby_value,
            "confidence": 0.62 if hobby_value != 1 else 0.42,
            "evidence": hobby_evidence,
            "fallback_used": True,
        }
    }

    if hobby_value == 3:
        heavy = any(keyword.lower() in corpus for keyword in HEAVY_DRINK_KEYWORDS)
        answers["drink_gate_q2"] = {
            "id": "drink_gate_q2",
            "option": 2 if heavy else 1,
            "confidence": 0.76 if heavy else 0.56,
            "evidence": "文本出现重度饮酒信号。" if heavy else "存在饮酒偏好，但没有强烈重度饮酒证据。",
            "fallback_used": True,
        }
    return answers


def dimension_questions(reference: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for question in reference["questions"]:
        grouped.setdefault(question["dim"], []).append(question)
    return grouped


def synthesize_answers(reference: dict[str, Any], inferred: dict[str, dict[str, Any]], sources: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    grouped = dimension_questions(reference)
    answers: dict[str, dict[str, Any]] = {}
    for dim, dim_questions in grouped.items():
        info = inferred[dim]
        level = info["level"]
        confidence = info["confidence"]
        if level == "L":
            pair = [1, 1] if confidence >= 0.68 else [1, 2]
        elif level == "H":
            pair = [3, 3] if confidence >= 0.68 else [2, 3]
        else:
            pair = [2, 2]

        for index, question in enumerate(dim_questions):
            answers[question["id"]] = {
                "id": question["id"],
                "option": pair[index],
                "confidence": confidence,
                "evidence": info["evidence"][0],
                "fallback_used": True,
            }

    answers.update(choose_special_answers(sources))
    return answers


def load_answers_file(path: str | None, reference: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_answers = payload["answers"] if isinstance(payload, dict) and "answers" in payload else payload
    question_index = {
        item["id"]: {opt["value"] for opt in item["options"]}
        for item in reference["questions"] + reference["special_questions"]
    }
    answers: dict[str, dict[str, Any]] = {}
    for item in raw_answers:
        qid = item.get("id") or item.get("question_id")
        option = item.get("option", item.get("value"))
        if qid not in question_index:
            continue
        if option not in question_index[qid]:
            continue
        answers[qid] = {
            "id": qid,
            "option": int(option),
            "confidence": round(float(item.get("confidence", 0.72)), 2),
            "evidence": str(item.get("evidence", "由目标 skill 的直接回答提供。")).strip(),
            "fallback_used": False,
        }
    return answers


def merge_answers(reference: dict[str, Any], preferred: dict[str, dict[str, Any]], fallback: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    order = [item["id"] for item in reference["questions"]] + [item["id"] for item in reference["special_questions"]]
    merged: list[dict[str, Any]] = []
    for qid in order:
        answer = preferred.get(qid) or fallback.get(qid)
        if answer:
            merged.append(answer)
    return merged


def sum_to_level(score: int) -> str:
    if score <= 3:
        return "L"
    if score == 4:
        return "M"
    return "H"


def parse_pattern(pattern: str) -> list[str]:
    return list(pattern.replace("-", ""))


def compute_result(reference: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, Any]:
    answer_map = {item["id"]: item for item in answers}
    raw_scores = {dim: 0 for dim in reference["dimension_meta"]}
    for question in reference["questions"]:
        raw_scores[question["dim"]] += int(answer_map[question["id"]]["option"])

    levels = {dim: sum_to_level(score) for dim, score in raw_scores.items()}
    user_vector = [level_score(levels[dim]) for dim in reference["dimension_order"]]
    ranked = []
    for type_item in reference["normal_types"]:
        vector = [level_score(value) for value in parse_pattern(type_item["pattern"])]
        distance = 0
        exact = 0
        for index, value in enumerate(vector):
            diff = abs(user_vector[index] - value)
            distance += diff
            if diff == 0:
                exact += 1
        similarity = max(0, round((1 - distance / 30) * 100))
        ranked.append(
            {
                **type_item,
                **reference["type_library"][type_item["code"]],
                "distance": distance,
                "exact": exact,
                "similarity": similarity,
            }
        )
    ranked.sort(key=lambda item: (item["distance"], -item["exact"], -item["similarity"]))
    best_normal = ranked[0]

    answer_confidences = [float(item["confidence"]) for item in answers if item["id"].startswith("q")]
    average_confidence = sum(answer_confidences) / len(answer_confidences)
    drunk_triggered = answer_map.get(reference["drunk_trigger_question_id"], {}).get("option") == 2

    final_type = best_normal
    mode_kicker = "你的主类型"
    badge = f"匹配度 {best_normal['similarity']}% · 精准命中 {best_normal['exact']}/15 维"
    sub = "维度命中度较高，当前结果可视为该 persona 的第一人格画像。"
    special = False
    secondary_type = None

    if drunk_triggered:
        final_type = reference["type_library"]["DRUNK"]
        secondary_type = best_normal
        mode_kicker = "隐藏人格已激活"
        badge = "匹配度 100% · 酒精异常因子已接管"
        sub = "文本或作答中出现了强烈的重度饮酒信号，系统直接切换到隐藏人格。"
        special = True
    elif best_normal["similarity"] < 60:
        final_type = reference["type_library"]["HHHH"]
        mode_kicker = "系统强制兜底"
        badge = f"标准人格库最高匹配仅 {best_normal['similarity']}%"
        sub = "标准人格库对该 persona 的匹配度偏低，因此进入 HHHH 兜底类型。"
        special = True

    report_confidence = 0.55 * (best_normal["similarity"] / 100) + 0.45 * average_confidence
    if special and final_type["code"] == "DRUNK":
        report_confidence = max(report_confidence, 0.84)

    return {
        "raw_scores": raw_scores,
        "levels": levels,
        "ranked": ranked,
        "best_normal": best_normal,
        "final_type": final_type,
        "mode_kicker": mode_kicker,
        "badge": badge,
        "sub": sub,
        "special": special,
        "secondary_type": secondary_type,
        "average_confidence": round(average_confidence, 2),
        "confidence_score": round(report_confidence, 2),
        "confidence_band": confidence_band(report_confidence),
    }


def build_payload(
    target: Path,
    reference: dict[str, Any],
    sources: list[dict[str, str]],
    meta: dict[str, Any],
    answers: list[dict[str, Any]],
    result: dict[str, Any],
    source_mode: str,
) -> dict[str, Any]:
    target_name = choose_target_name(target, sources, meta)
    target_slug = slugify(target_name)
    dimension_details = []
    answer_by_question = {item["id"]: item for item in answers}

    for dim in reference["dimension_order"]:
        items = [item for item in reference["questions"] if item["dim"] == dim]
        answer_items = [answer_by_question[item["id"]] for item in items]
        evidence = []
        for item in answer_items:
            if item["evidence"] not in evidence:
                evidence.append(item["evidence"])
        dimension_details.append(
            {
                "dim": dim,
                "name": reference["dimension_meta"][dim]["name"],
                "model": reference["dimension_meta"][dim]["model"],
                "score": result["raw_scores"][dim],
                "level": result["levels"][dim],
                "confidence": round(sum(item["confidence"] for item in answer_items) / len(answer_items), 2),
                "explanation": reference["dim_explanations"][dim][result["levels"][dim]],
                "evidence": evidence or ["未找到稳定直接证据，按中位档保守处理。"],
            }
        )

    low_confidence_questions = [
        {"id": item["id"], "confidence": item["confidence"], "evidence": item["evidence"]}
        for item in answers
        if item["id"].startswith("q") and float(item["confidence"]) < 0.55
    ]

    return {
        "target": {
            "name": target_name,
            "slug": target_slug,
            "path": display_target_path(target),
            "runtime": detect_runtime(target),
            "source_mode": source_mode,
        },
        "answers": answers,
        "scores": {
            "raw": result["raw_scores"],
            "levels": result["levels"],
            "top_matches": result["ranked"][:3],
            "average_answer_confidence": result["average_confidence"],
        },
        "result": {
            "type": result["final_type"]["code"],
            "cn": result["final_type"]["cn"],
            "intro": result["final_type"]["intro"],
            "description": result["final_type"]["desc"],
            "confidence_band": result["confidence_band"],
            "confidence_score": result["confidence_score"],
            "badge": result["badge"],
            "sub": result["sub"],
            "special": result["special"],
            "secondary_type": result["secondary_type"],
        },
        "dimension_details": dimension_details,
        "meta": {
            "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
            "question_source": "UnluckyNinja/SBTI-test mirrored questionnaire",
            "report_version": "v1",
            "method_note": "这是基于蒸馏 persona skill 的代理测评，不是用户本人手动答题，也不是心理学诊断。",
            "source_files": [item["path"] for item in sources],
            "low_confidence_questions": low_confidence_questions,
        },
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_report_html(payload: dict[str, Any]) -> str:
    result = payload["result"]
    target = payload["target"]
    meta = payload["meta"]
    top_matches = payload["scores"]["top_matches"]
    low_conf = meta["low_confidence_questions"]

    top_match_html = "".join(
        f"""
        <div class="top3-item">
          <div>
            <strong>{esc(item['code'])}（{esc(item['cn'])}）</strong>
            <span>{esc(item['intro'])}</span>
          </div>
          <div class="top3-score">{esc(item['similarity'])}%</div>
        </div>
        """
        for item in top_matches
    )

    dim_cards = "".join(
        f"""
        <article class="dim-item">
          <div class="dim-item-top">
            <div>
              <div class="dim-item-name">{esc(item['name'])}</div>
              <div class="dim-item-model">{esc(item['model'])}</div>
            </div>
            <div class="dim-item-score">{esc(item['level'])} / {esc(item['score'])}分</div>
          </div>
          <p class="dim-explanation">{esc(item['explanation'])}</p>
          <div class="meter"><span style="width:{min(100, max(16, round(item['confidence'] * 100)))}%"></span></div>
          <div class="dim-confidence">证据置信度 {esc(round(item['confidence'] * 100))}%</div>
          <ul class="evidence-list">
            {''.join(f'<li>{esc(line)}</li>' for line in item['evidence'])}
          </ul>
        </article>
        """
        for item in payload["dimension_details"]
    )

    low_conf_html = (
        "".join(
            f"<li><strong>{esc(item['id'])}</strong> · {esc(round(item['confidence'] * 100))}% · {esc(item['evidence'])}</li>"
            for item in low_conf[:8]
        )
        if low_conf
        else "<li>本次代理测评未出现明显低于 55% 的题目置信度。</li>"
    )

    method_label = "conversation-first" if target["source_mode"] == "conversation-first" else "file-fallback"
    payload_blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(target['name'])} · SBTI 报告</title>
  <style>
    :root {{
      --bg: #f6faf6;
      --panel: #ffffff;
      --text: #1e2a22;
      --muted: #6a786f;
      --line: #dbe8dd;
      --soft: #edf6ef;
      --accent: #6c8d71;
      --accent-strong: #4d6a53;
      --shadow: 0 16px 40px rgba(47, 73, 55, 0.08);
      --radius: 22px;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background: radial-gradient(circle at top left, #f8fff8 0, #f6faf6 36%, #f2f7f3 100%);
      color: var(--text);
    }}
    .shell {{ max-width: 1080px; margin: 0 auto; padding: 28px 16px 56px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }}
    .report-root {{ display: grid; gap: 18px; }}
    .hero {{ padding: 26px; position: relative; overflow: hidden; }}
    .hero::after {{
      content: "";
      position: absolute;
      right: -54px;
      top: -54px;
      width: 170px;
      height: 170px;
      border-radius: 50%;
      background: linear-gradient(180deg, rgba(127, 165, 134, 0.18), rgba(127, 165, 134, 0.02));
      pointer-events: none;
    }}
    .toolbar {{ display: flex; justify-content: flex-end; margin-bottom: 14px; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }}
    .eyebrow {{
      display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--accent-strong);
      border: 1px solid var(--line); background: var(--soft); border-radius: 999px; padding: 8px 12px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: clamp(28px, 5vw, 50px); line-height: 1.08; letter-spacing: -0.03em; max-width: 760px; }}
    .sub {{ margin-top: 14px; color: var(--muted); font-size: 15px; line-height: 1.8; max-width: 760px; }}
    .hero-grid {{ display: grid; grid-template-columns: 0.92fr 1.08fr; gap: 18px; margin-top: 24px; }}
    .type-box, .analysis-box, .note-box, .top3-box {{ border: 1px solid var(--line); border-radius: 18px; padding: 18px; background: linear-gradient(180deg, #ffffff, #fbfdfb); }}
    .type-kicker {{ font-size: 12px; color: var(--accent-strong); margin-bottom: 8px; letter-spacing: .06em; }}
    .type-name {{ font-size: clamp(30px, 5vw, 48px); line-height: 1.08; letter-spacing: -0.03em; }}
    .type-subname {{ margin-top: 10px; color: var(--muted); font-size: 14px; line-height: 1.8; }}
    .match {{
      margin-top: 18px; display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 10px 14px;
      background: var(--soft); border: 1px solid var(--line); color: var(--accent-strong); font-weight: 700; font-size: 14px;
    }}
    .analysis-box h3, .note-box h3, .top3-box h3 {{ font-size: 16px; margin-bottom: 12px; }}
    .analysis-box p, .note-box p {{ color: #304034; font-size: 15px; line-height: 1.9; white-space: pre-wrap; }}
    .top3-list {{ display: grid; gap: 10px; }}
    .top3-item {{
      border: 1px solid var(--line); border-radius: 14px; padding: 12px; background: #fff;
      display: flex; justify-content: space-between; gap: 12px; align-items: center;
    }}
    .top3-item strong {{ display: block; margin-bottom: 4px; }}
    .top3-item span {{ color: var(--muted); font-size: 13px; line-height: 1.7; }}
    .top3-score {{ color: var(--accent-strong); font-weight: 800; white-space: nowrap; }}
    .section-card {{ padding: 22px; }}
    .section-card h2 {{ font-size: 19px; margin-bottom: 14px; }}
    .dim-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .dim-item {{ border: 1px solid var(--line); border-radius: 16px; padding: 14px; background: #fff; }}
    .dim-item-top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 8px; }}
    .dim-item-name {{ font-size: 14px; font-weight: 700; }}
    .dim-item-model {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .dim-item-score {{ color: var(--accent-strong); font-weight: 800; font-size: 14px; white-space: nowrap; }}
    .dim-explanation {{ color: #304034; font-size: 13px; line-height: 1.8; margin-bottom: 10px; }}
    .meter {{ height: 8px; background: #edf3ee; border-radius: 999px; overflow: hidden; }}
    .meter span {{ display: block; height: 100%; background: linear-gradient(90deg, #97b59c, #5b7a62); border-radius: inherit; }}
    .dim-confidence {{ margin-top: 8px; color: var(--muted); font-size: 12px; }}
    .evidence-list {{ margin: 10px 0 0; padding-left: 18px; color: #304034; font-size: 13px; line-height: 1.8; }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
    .meta-item {{ border: 1px solid var(--line); border-radius: 16px; padding: 14px; background: linear-gradient(180deg, #fbfefb, #f3f8f4); }}
    .meta-label {{ color: var(--muted); font-size: 12px; margin-bottom: 8px; }}
    .meta-value {{ font-size: 17px; font-weight: 800; color: var(--accent-strong); }}
    .meta-sub {{ margin-top: 6px; color: var(--muted); font-size: 13px; line-height: 1.7; }}
    .question-warning {{ margin-top: 14px; border: 1px dashed var(--line); border-radius: 16px; padding: 14px; background: #fafdfa; }}
    .question-warning ul {{ margin: 10px 0 0; padding-left: 18px; color: #304034; line-height: 1.8; font-size: 13px; }}
    .btn-primary {{
      border: 0; cursor: pointer; background: var(--accent-strong); color: #fff; padding: 14px 20px;
      border-radius: 14px; box-shadow: 0 12px 30px rgba(77, 106, 83, 0.18); font-weight: 700; font: inherit;
    }}
    .btn-primary:disabled {{ opacity: 0.6; cursor: wait; }}
    .footer-note {{ margin-top: 16px; color: var(--muted); font-size: 12px; line-height: 1.8; }}
    @media (max-width: 900px) {{ .hero-grid, .dim-grid, .meta-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="report-root" id="reportCapture">
      <section class="card hero">
        <div class="toolbar" data-export-hide>
          <button class="btn-primary" id="exportBtn">导出长图</button>
        </div>
        <div class="badge-row">
          <div class="eyebrow">everyone-s-SBTI · {esc(method_label)}</div>
          <div class="eyebrow">报告时间 · {esc(meta['generated_at'])}</div>
          <div class="eyebrow">置信等级 · {esc(result['confidence_band'])}</div>
        </div>
        <h1>{esc(target['name'])} 的 SBTI 代理测评报告</h1>
        <p class="sub">本报告基于蒸馏 persona skill 自动推断并生成，无需用户手动答题。结果用于角色画像与娱乐分析，不等同于本人亲测或专业评估。</p>
        <div class="meta-grid">
          <div class="meta-item"><div class="meta-label">最终类型</div><div class="meta-value">{esc(result['type'])}</div><div class="meta-sub">{esc(result['cn'])}</div></div>
          <div class="meta-item"><div class="meta-label">总体置信度</div><div class="meta-value">{esc(round(result['confidence_score'] * 100))}%</div><div class="meta-sub">综合匹配度与题目证据计算</div></div>
          <div class="meta-item"><div class="meta-label">来源模式</div><div class="meta-value">{esc(target['source_mode'])}</div><div class="meta-sub">{esc(target['runtime'])}</div></div>
          <div class="meta-item"><div class="meta-label">题目来源</div><div class="meta-value">原版镜像</div><div class="meta-sub">{esc(meta['question_source'])}</div></div>
        </div>
        <div class="hero-grid">
          <div class="type-box">
            <div class="type-kicker">{esc(result['badge'])}</div>
            <div class="type-name">{esc(result['type'])}（{esc(result['cn'])}）</div>
            <div class="type-subname">{esc(result['intro'])}</div>
            <div class="match">{esc(result['sub'])}</div>
          </div>
          <div class="analysis-box">
            <h3>类型摘要</h3>
            <p>{esc(result['description'])}</p>
          </div>
        </div>
      </section>
      <section class="card section-card">
        <h2>Top 3 匹配类型</h2>
        <div class="top3-list">{top_match_html}</div>
      </section>
      <section class="card section-card">
        <h2>十五维度总览</h2>
        <div class="dim-grid">{dim_cards}</div>
      </section>
      <section class="card section-card">
        <div class="note-box">
          <h3>方法说明</h3>
          <p>{esc(meta['method_note'])}</p>
          <div class="footer-note">源文件：{esc('、'.join(meta['source_files'][:8]))}</div>
        </div>
        <div class="question-warning">
          <h3>低置信度提醒</h3>
          <ul>{low_conf_html}</ul>
        </div>
      </section>
    </div>
  </div>
  <script id="reportData" type="application/json">{payload_blob}</script>
  <script>
    function xmlEscape(value) {{
      return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }}
    async function exportLongImage() {{
      const button = document.getElementById('exportBtn');
      const report = document.getElementById('reportCapture');
      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = '导出中...';
      try {{
        const clone = report.cloneNode(true);
        clone.querySelectorAll('[data-export-hide]').forEach((node) => node.remove());
        const styles = Array.from(document.querySelectorAll('style')).map((node) => node.textContent).join('\\n');
        const width = Math.ceil(report.scrollWidth);
        const height = Math.ceil(report.scrollHeight);
        const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${{width}}" height="${{height}}">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>${{xmlEscape(styles)}}</style>
      ${{clone.outerHTML}}
    </div>
  </foreignObject>
</svg>`.trim();
        const blob = new Blob([svg], {{ type: 'image/svg+xml;charset=utf-8' }});
        const url = URL.createObjectURL(blob);
        const img = new Image();
        await new Promise((resolve, reject) => {{
          img.onload = resolve;
          img.onerror = reject;
          img.src = url;
        }});
        const scale = window.devicePixelRatio > 1 ? 2 : 1.5;
        const canvas = document.createElement('canvas');
        canvas.width = Math.ceil(width * scale);
        canvas.height = Math.ceil(height * scale);
        const ctx = canvas.getContext('2d');
        ctx.scale(scale, scale);
        ctx.drawImage(img, 0, 0, width, height);
        URL.revokeObjectURL(url);
        const png = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
        const downloadUrl = URL.createObjectURL(png);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = 'sbti-report.png';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(downloadUrl);
      }} catch (error) {{
        console.error(error);
        alert('长图导出失败，请使用 Chromium/Edge 重试。');
      }} finally {{
        button.disabled = false;
        button.textContent = originalLabel;
      }}
    }}
    document.getElementById('exportBtn').addEventListener('click', exportLongImage);
  </script>
</body>
</html>
"""


def short_dimension_name(label: str) -> str:
    parts = label.split(" ", 1)
    return parts[1] if len(parts) == 2 else label


def build_interpretation(payload: dict[str, Any]) -> str:
    result = payload["result"]
    top_matches = payload["scores"]["top_matches"]
    dimension_details = payload["dimension_details"]

    highlights = [
        short_dimension_name(item["name"])
        for item in sorted(dimension_details, key=lambda item: item["confidence"], reverse=True)[:3]
    ]
    highlight_text = "、".join(highlights) if highlights else "十五维画像"
    sentences = [
        f"从当前画像来看，你在 {highlight_text} 上的倾向更突出，整体更接近 {result['type']}（{result['cn']}）这一类人物。",
        f"{result['description']}{result['sub']}",
    ]
    alternates = [f"{item['code']}（{item['cn']}）" for item in top_matches[1:3]]
    if alternates:
        sentences.append(f"另外，你和 {'、'.join(alternates)} 也有一定相似度，但主结果仍然以 {result['type']} 为先。")
    sentences.append("把它当作一张娱乐向的人格切片来看会更合适，不必把自己锁死在单一标签里。")
    return "".join(sentences)


def load_original_type_image_map() -> dict[str, Path]:
    if not ORIGINAL_INDEX_PATH.exists():
        return {}

    text = ORIGINAL_INDEX_PATH.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"const TYPE_IMAGES = \{(.*?)\};", text, re.DOTALL)
    if not match:
        return {}

    mapping: dict[str, Path] = {}
    for code, relative_path in re.findall(r'"([^"]+)":\s*"([^"]+)"', match.group(1)):
        cleaned = relative_path.replace("./", "", 1)
        mapping[code] = ORIGINAL_MIRROR_DIR / cleaned
    return mapping


def image_path_to_data_uri(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


def resolve_official_type_image(type_code: str) -> tuple[str | None, str | None]:
    image_map = load_original_type_image_map()
    if not image_map:
        return None, f"未找到原版映射文件：{ORIGINAL_INDEX_PATH}"

    image_path = image_map.get(type_code)
    if not image_path:
        return None, f"原版 index.html 里没有 {type_code} 的图片映射。"
    if not image_path.exists():
        return None, f"原版映射指向 {image_path.name}，但本地文件不存在。"

    return image_path_to_data_uri(image_path), None


def build_fake_qr(seed: str) -> str:
    size = 21
    seed_total = sum((index + 1) * ord(char) for index, char in enumerate(seed))
    cells: list[str] = []

    def in_finder(x: int, y: int) -> bool:
        return ((0 <= x <= 6 and 0 <= y <= 6) or (14 <= x <= 20 and 0 <= y <= 6) or (0 <= x <= 6 and 14 <= y <= 20))

    def finder_value(x: int, y: int) -> bool:
        local_x = x if x <= 6 else x - 14
        local_y = y if y <= 6 else y - 14
        return local_x in {0, 6} or local_y in {0, 6} or (2 <= local_x <= 4 and 2 <= local_y <= 4)

    for y in range(size):
        for x in range(size):
            if in_finder(x, y):
                dark = finder_value(x, y)
            else:
                value = seed_total + x * 17 + y * 23 + x * y * 3 + (x + y) * 5
                dark = value % 7 in {0, 1, 3}
            cells.append(f'<span class="qr-cell{" is-dark" if dark else ""}"></span>')
    return "".join(cells)


def build_poster_scene(result: dict[str, Any]) -> str:
    code = result["type"]
    accent = "#6c8d71"
    ink = "#37413a"
    soft = "#eef4ee"
    warm = "#ead9cb"
    kind = "badge"

    if code == "DEAD":
        accent = "#6aa05e"
        ink = "#2d3036"
        soft = "#eef4ee"
        warm = "#f2e3d3"
        kind = "coffin"
    elif code == "MUM":
        accent = "#6f8f68"
        ink = "#5d685f"
        soft = "#eef4ea"
        warm = "#efddd0"
        kind = "heart"

    if kind == "coffin":
        return f"""
        <svg class="poster-scene-svg" viewBox="0 0 300 220" aria-hidden="true">
          <ellipse cx="148" cy="198" rx="86" ry="12" fill="#dbe5db" />
          <path d="M76 64 L150 52 L224 64 L224 124 L150 136 L76 124 Z" fill="{ink}" opacity="0.88" />
          <path d="M86 68 L150 58 L214 68 L214 114 L150 124 L86 114 Z" fill="#45484f" />
          <path d="M64 126 L150 118 L236 126 L212 184 L88 184 Z" fill="#2f3238" />
          <path d="M78 134 L150 128 L222 134 L204 174 L96 174 Z" fill="#3b4048" />
          <path d="M94 102 L124 76 L170 116 L148 156 L104 150 Z" fill="#76797f" />
          <path d="M116 86 L142 74 L178 104 L142 114 Z" fill="{warm}" />
          <path d="M140 114 L204 120 L190 168 L144 162 Z" fill="#81c0eb" />
          <path d="M142 114 L110 114 L100 160 L142 162 Z" fill="#d7ecfb" />
          <circle cx="126" cy="98" r="3" fill="{ink}" />
          <path d="M132 106 C128 110, 118 110, 114 104" stroke="{ink}" stroke-width="3" fill="none" stroke-linecap="round" />
          <rect x="103" y="165" width="18" height="8" rx="4" fill="#d8dde0" />
          <rect x="145" y="165" width="18" height="8" rx="4" fill="#d8dde0" />
          <rect x="186" y="165" width="18" height="8" rx="4" fill="#d8dde0" />
          <rect x="117" y="171" width="4" height="10" rx="2" fill="#c6ced0" />
          <rect x="159" y="171" width="4" height="10" rx="2" fill="#c6ced0" />
          <rect x="200" y="171" width="4" height="10" rx="2" fill="#c6ced0" />
        </svg>
        """

    if kind == "heart":
        return f"""
        <svg class="poster-scene-svg" viewBox="0 0 300 220" aria-hidden="true">
          <ellipse cx="150" cy="198" rx="84" ry="12" fill="#dbe5db" />
          <circle cx="150" cy="108" r="68" fill="{soft}" />
          <path d="M150 158 C120 138, 98 122, 98 92 C98 74, 112 60, 130 60 C142 60, 151 67, 157 77 C163 67, 172 60, 184 60 C202 60, 216 74, 216 92 C216 122, 193 138, 150 158 Z" fill="#efb9b1" />
          <path d="M100 150 C92 120, 98 92, 118 82 C122 108, 132 128, 150 140 C132 150, 114 154, 100 150 Z" fill="{accent}" opacity="0.9" />
          <path d="M200 150 C208 120, 202 92, 182 82 C178 108, 168 128, 150 140 C168 150, 186 154, 200 150 Z" fill="{accent}" opacity="0.9" />
          <circle cx="135" cy="104" r="6" fill="#ffffff" opacity="0.7" />
          <circle cx="165" cy="104" r="6" fill="#ffffff" opacity="0.7" />
          <path d="M132 126 C140 134, 160 134, 168 126" stroke="#ffffff" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.9" />
          <path d="M72 180 C104 160, 122 158, 150 166 C178 158, 196 160, 228 180" stroke="{ink}" stroke-width="8" fill="none" stroke-linecap="round" opacity="0.22" />
        </svg>
        """

    return f"""
    <svg class="poster-scene-svg" viewBox="0 0 300 220" aria-hidden="true">
      <ellipse cx="150" cy="198" rx="84" ry="12" fill="#dbe5db" />
      <circle cx="150" cy="104" r="68" fill="{soft}" />
      <circle cx="150" cy="104" r="46" fill="#ffffff" />
      <path d="M150 58 L163 89 L197 91 L171 112 L180 145 L150 127 L120 145 L129 112 L103 91 L137 89 Z" fill="{accent}" />
      <circle cx="150" cy="104" r="18" fill="#ffffff" />
      <path d="M92 174 C112 150, 128 144, 150 144 C172 144, 188 150, 208 174" stroke="{ink}" stroke-width="8" fill="none" stroke-linecap="round" opacity="0.16" />
      <rect x="108" y="156" width="84" height="12" rx="6" fill="{warm}" opacity="0.78" />
    </svg>
    """


def render_mirror_styles() -> str:
    return """
    :root {
      --page-bg: #f3faf5;
      --panel: #ffffff;
      --panel-soft: #fbfdfb;
      --text: #1f2a22;
      --muted: #647468;
      --line: #d8e6d9;
      --soft: #eef5ee;
      --accent: #6d8f72;
      --accent-strong: #547257;
      --shadow: 0 20px 48px rgba(69, 101, 74, 0.10);
      --panel-radius: 20px;
      --frame-radius: 28px;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at 12% 10%, rgba(235, 246, 238, 0.95) 0, rgba(243, 250, 245, 0.95) 30%, rgba(243, 248, 244, 0.88) 60%, #eef6f1 100%);
      color: var(--text);
    }
    button { font: inherit; }
    .page-shell {
      max-width: 1040px;
      margin: 0 auto;
      padding: 28px 16px 56px;
    }
    .report-frame {
      position: relative;
      max-width: 950px;
      margin: 0 auto;
      padding: 68px 22px 22px;
      border: 1px solid var(--line);
      border-radius: var(--frame-radius);
      background: linear-gradient(180deg, #ffffff, #fbfdfb);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .report-frame::after {
      content: "";
      position: absolute;
      top: -34px;
      right: -28px;
      width: 146px;
      height: 146px;
      border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, rgba(173, 195, 171, 0.28), rgba(173, 195, 171, 0.08) 58%, rgba(173, 195, 171, 0) 70%);
      pointer-events: none;
    }
    .toolbar {
      position: absolute;
      top: 26px;
      right: 26px;
      z-index: 2;
    }
    .export-btn {
      border: 0;
      border-radius: 14px;
      padding: 14px 20px;
      background: #5c775d;
      color: #ffffff;
      font-weight: 700;
      box-shadow: 0 14px 30px rgba(83, 109, 85, 0.22);
      cursor: pointer;
    }
    .export-btn:disabled {
      opacity: 0.65;
      cursor: wait;
    }
    .stack {
      display: grid;
      gap: 18px;
    }
    .panel {
      position: relative;
      border: 1px solid var(--line);
      border-radius: var(--panel-radius);
      background: linear-gradient(180deg, #ffffff, var(--panel-soft));
      padding: 18px;
    }
    .hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 0.98fr) minmax(0, 1.12fr);
      gap: 18px;
      align-items: stretch;
    }
    .hero-poster-wrap {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 22px;
      gap: 16px;
      padding: 0;
      background: transparent;
      border: 0;
    }
    .hero-poster {
      min-height: 390px;
      border: 1px solid var(--line);
      border-radius: var(--panel-radius);
      background: linear-gradient(180deg, #ffffff, #f8fbf8);
      padding: 16px;
    }
    .poster-window {
      position: relative;
      height: 100%;
      min-height: 356px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background:
        radial-gradient(circle at 100% 100%, rgba(222, 236, 223, 0.62), rgba(255, 255, 255, 0) 28%),
        radial-gradient(circle at 10% 0%, rgba(233, 237, 233, 0.74), rgba(255, 255, 255, 0) 24%),
        linear-gradient(180deg, #ffffff, #f7faf8);
      padding: 18px 16px 14px;
      overflow: hidden;
    }
    .poster-window::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 34px;
      background: linear-gradient(180deg, rgba(132, 137, 138, 0.52), rgba(255, 255, 255, 0));
      pointer-events: none;
    }
    .poster-kicker,
    .poster-cn,
    .poster-code {
      position: relative;
      z-index: 1;
      text-align: center;
    }
    .poster-kicker {
      color: #484f4b;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.02em;
      margin-top: 4px;
    }
    .poster-cn {
      margin-top: 10px;
      font-size: 42px;
      line-height: 1.06;
      font-weight: 800;
      color: #222a25;
    }
    .poster-code {
      margin-top: 6px;
      color: #6da05f;
      font-size: 26px;
      font-weight: 800;
      letter-spacing: 0.02em;
    }
    .poster-scene {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 190px;
      margin-top: 8px;
      padding-bottom: 40px;
    }
    .poster-image {
      width: 100%;
      max-width: 298px;
      height: auto;
      display: block;
      object-fit: contain;
    }
    .poster-image-missing {
      width: 100%;
      max-width: 280px;
      min-height: 176px;
      border: 1px dashed var(--line);
      border-radius: 16px;
      background: rgba(238, 245, 238, 0.68);
      color: #53665a;
      font-size: 13px;
      line-height: 1.8;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: left;
      padding: 14px 16px;
    }
    .poster-quote {
      position: absolute;
      left: 16px;
      right: 16px;
      bottom: 18px;
      color: #54665a;
      font-size: 13px;
      line-height: 1.5;
    }
    .poster-side-note {
      display: flex;
      align-items: center;
      justify-content: center;
      color: #75837a;
      font-size: 12px;
      letter-spacing: 0.08em;
      writing-mode: vertical-rl;
      text-orientation: mixed;
      user-select: none;
    }
    .summary-card {
      min-height: 390px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: flex-start;
      padding: 18px 18px 20px;
    }
    .summary-kicker {
      color: var(--accent-strong);
      font-size: 13px;
      margin-bottom: 10px;
    }
    .summary-title {
      font-size: clamp(34px, 6vw, 56px);
      line-height: 1.08;
      letter-spacing: -0.03em;
      font-weight: 500;
      color: #1b2520;
    }
    .summary-badge {
      margin-top: 18px;
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 10px 14px;
      background: #eef6ee;
      border: 1px solid var(--line);
      color: #47684b;
      font-size: 13px;
      font-weight: 700;
    }
    .summary-copy {
      margin-top: 16px;
      color: #415449;
      font-size: 15px;
      line-height: 1.9;
      max-width: 92%;
    }
    .panel h2 {
      margin: 0 0 12px;
      font-size: 18px;
      line-height: 1.3;
    }
    .interpretation-copy,
    .tips-copy {
      margin: 0;
      color: #2b3c32;
      font-size: 15px;
      line-height: 2;
    }
    .score-list {
      display: grid;
      gap: 14px;
    }
    .score-item {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: #ffffff;
      padding: 15px 16px;
    }
    .score-item-top {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
    }
    .score-item-name {
      font-size: 15px;
      font-weight: 800;
      color: #1f2923;
    }
    .score-item-value {
      color: #47694b;
      font-size: 14px;
      font-weight: 800;
      white-space: nowrap;
    }
    .score-item-desc {
      margin: 10px 0 0;
      color: #4f6556;
      font-size: 14px;
      line-height: 1.8;
    }
    .author-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .author-head h2 {
      margin-bottom: 0;
    }
    .author-toggle {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 14px;
      background: #eef6ee;
      color: #47684b;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }
    .author-details {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px dashed var(--line);
    }
    .author-section + .author-section {
      margin-top: 16px;
    }
    .author-copy {
      margin: 10px 0 0;
      color: #32433a;
      font-size: 14px;
      line-height: 1.9;
    }
    .author-subtitle {
      margin-top: 0;
      font-size: 13px;
      font-weight: 800;
      color: #304238;
    }
    .author-link {
      color: #47684b;
      text-decoration: none;
      border-bottom: 1px solid rgba(71, 104, 75, 0.25);
    }
    .author-link:hover {
      color: #2f4b34;
      border-bottom-color: rgba(47, 75, 52, 0.5);
    }
    @media (max-width: 900px) {
      .page-shell {
        padding: 16px 10px 40px;
      }
      .report-frame {
        padding: 76px 14px 14px;
      }
      .hero-grid {
        grid-template-columns: 1fr;
      }
      .hero-poster-wrap {
        grid-template-columns: 1fr;
      }
      .poster-side-note {
        display: none;
      }
      .summary-copy {
        max-width: 100%;
      }
      .score-item-top {
        align-items: flex-start;
        flex-direction: column;
      }
    }
    """


def render_mirror_script() -> str:
    return """
    function xmlEscape(value) {
      return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function loadImage(src) {
      return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('image-load-failed'));
        img.src = src;
      });
    }

    async function waitForImages(root) {
      const images = Array.from(root.querySelectorAll('img'));
      await Promise.all(images.map((img) => {
        if (img.complete) {
          if (typeof img.decode === 'function') {
            return img.decode().catch(() => {});
          }
          return Promise.resolve();
        }
        return new Promise((resolve) => {
          img.addEventListener('load', resolve, { once: true });
          img.addEventListener('error', resolve, { once: true });
        });
      }));
    }

    function getExportDimensions(report) {
      const rect = report.getBoundingClientRect();
      return {
        width: Math.max(Math.ceil(rect.width), Math.ceil(report.scrollWidth)),
        height: Math.max(Math.ceil(report.scrollHeight), Math.ceil(report.offsetHeight)),
      };
    }

    function serializeReportForExport(report, width) {
      const clone = report.cloneNode(true);
      clone.querySelectorAll('[data-export-hide]').forEach((node) => node.remove());
      clone.style.width = `${width}px`;
      clone.style.maxWidth = 'none';
      clone.style.margin = '0';

      const wrapper = document.createElement('div');
      wrapper.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
      wrapper.style.width = `${width}px`;
      wrapper.style.margin = '0';
      wrapper.style.padding = '0';

      const style = document.createElement('style');
      style.textContent = Array.from(document.querySelectorAll('style'))
        .map((node) => node.textContent || '')
        .join('\\n');

      wrapper.appendChild(style);
      wrapper.appendChild(clone);

      return new XMLSerializer().serializeToString(wrapper);
    }

    function getExportScale(width, height) {
      const maxEdge = 16384;
      const maxArea = 268435456;
      let scale = window.devicePixelRatio >= 2 ? 2 : 1.5;
      scale = Math.min(scale, maxEdge / Math.max(width, height));
      scale = Math.min(scale, Math.sqrt(maxArea / Math.max(width * height, 1)));
      return Math.max(scale, 1);
    }

    async function canvasToBlob(canvas) {
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (!blob) {
        throw new Error('canvas-to-blob-failed');
      }
      return blob;
    }

    function triggerDownload(href, filename) {
      const link = document.createElement('a');
      link.href = href;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    }

    function getPreRenderedImageUrl() {
      const url = new URL(window.location.href);
      url.hash = '';
      url.search = '';
      url.pathname = url.pathname.replace(/\\.html?$/i, '.png');
      return url;
    }

    async function tryDownloadPreRenderedImage() {
      const imageUrl = getPreRenderedImageUrl();
      try {
        await loadImage(imageUrl.href);
        triggerDownload(imageUrl.href, 'sbti-report.png');
        return true;
      } catch (error) {
        return false;
      }
    }

    async function exportLongImage() {
      const button = document.getElementById('exportBtn');
      const report = document.getElementById('reportCapture');
      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = '\\u5bfc\\u51fa\\u4e2d...';
      try {
        if (await tryDownloadPreRenderedImage()) {
          return;
        }
        await waitForImages(report);
        const { width, height } = getExportDimensions(report);
        const serializedReport = serializeReportForExport(report, width);
        const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <foreignObject x="0" y="0" width="${width}" height="${height}">
    ${serializedReport}
  </foreignObject>
</svg>`.trim();
        const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        try {
          const img = await loadImage(url);
          const scale = getExportScale(width, height);
          const canvas = document.createElement('canvas');
          canvas.width = Math.max(1, Math.ceil(width * scale));
          canvas.height = Math.max(1, Math.ceil(height * scale));
          const ctx = canvas.getContext('2d');
          if (!ctx) {
            throw new Error('canvas-context-unavailable');
          }
          ctx.setTransform(scale, 0, 0, scale, 0, 0);
          ctx.imageSmoothingEnabled = true;
          ctx.imageSmoothingQuality = 'high';
          ctx.drawImage(img, 0, 0, width, height);
          const png = await canvasToBlob(canvas);
          const downloadUrl = URL.createObjectURL(png);
          triggerDownload(downloadUrl, 'sbti-report.png');
          URL.revokeObjectURL(downloadUrl);
        } finally {
          URL.revokeObjectURL(url);
        }
      } catch (error) {
        console.error(error);
        alert('\\u957f\\u56fe\\u5bfc\\u51fa\\u5931\\u8d25\\uff0c\\u8bf7\\u91cd\\u65b0\\u751f\\u6210\\u9644\\u5e26 PNG \\u7684\\u62a5\\u544a\\uff0c\\u6216\\u4f7f\\u7528 Chromium/Edge \\u91cd\\u8bd5\\u3002');
      } finally {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    }

    const exportBtn = document.getElementById('exportBtn');
    const authorToggle = document.getElementById('authorToggle');
    const authorDetails = document.getElementById('authorDetails');

    exportBtn.addEventListener('click', exportLongImage);
    authorToggle.addEventListener('click', () => {
      const expanded = authorToggle.getAttribute('aria-expanded') === 'true';
      authorToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      authorToggle.textContent = expanded ? '灞曞紑' : '鏀惰捣';
      authorDetails.hidden = expanded;
    });
    """

def render_report_html(payload: dict[str, Any]) -> str:
    result = payload["result"]
    target = payload["target"]
    meta = payload["meta"]
    dimension_details = payload["dimension_details"]

    dim_cards = "".join(
        f"""
        <article class="score-item">
          <div class="score-item-top">
            <div class="score-item-name">{esc(item['name'])}</div>
            <div class="score-item-value">{esc(item['level'])} / {esc(item['score'])}分</div>
          </div>
          <p class="score-item-desc">{esc(item['explanation'])}</p>
        </article>
        """
        for item in dimension_details
    )

    poster_image_data, poster_image_reason = resolve_official_type_image(result["type"])
    if poster_image_data:
        poster_visual_html = (
            f'<img class="poster-image" src="{poster_image_data}" '
            f'alt="{esc(result["type"])} 官方人格图" />'
        )
    else:
        poster_visual_html = f'<div class="poster-image-missing">未能载入官方配图：{esc(poster_image_reason)}</div>'
    interpretation = build_interpretation(payload)
    original_author_paragraphs = [
        "本测试首发于b站up主Q肉儿串儿（UID417038183），初衷是劝诫一位爱喝酒的朋友戒酒。",
        "由于作者的人格是SHIT愤世者，所以平等的攻击了各位，在此抱歉！！不过我是一个绝世大美女，你们一定会原谅我，有B站的朋友们也可以关注我。",
        "关于这个测试，这里是在b站制作的官方初版，为了合规做了些许改动，没有很好的平衡娱乐和专业性，up主不是心理学专业，对于一些人格的阐释较为模糊或完全不准，如有冒犯非常抱歉！！",
        "再鉴于时间精力有限，就随便搞了一个先这样玩玩，后续会慢慢完善修改的，总之好玩为主，还请不要用于盈利呀（若看见贩卖的麻烦点点举报呜呜！）",
        "本测试含有人工智能合成技术，15维度的L/M/H为低/中/高，其实更多是为了做匹配用的（）",
    ]
    original_author_html = "".join(f'<p class="author-copy">{esc(item)}</p>' for item in original_author_paragraphs)
    remix_author_paragraphs = [
        "这个版本属于送钱者 ATM-er 一时手痒搞出来的胡闹二创，开源归开源，礼数还是得有，原作的图、梗、骨架和气质都该先给原作者磕一个电子响头。",
        "所以这里特别说明：现在这个页面只是基于开源版本做适配和折腾，不代表官方，也不该拿原作的东西换个壳就装成自己的丰功伟绩。真要夸，先夸原作者；真要骂，也欢迎优先骂 ATM-er，别把原创一起连坐了。",
    ]
    remix_author_html = "".join(f'<p class="author-copy">{esc(item)}</p>' for item in remix_author_paragraphs)
    payload_blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(target['name'])} · SBTI 报告</title>
  <style>{render_mirror_styles()}</style>
</head>
<body>
  <div class="page-shell">
    <div class="report-frame" id="reportCapture">
      <div class="toolbar" data-export-hide>
        <button class="export-btn" id="exportBtn">导出长图</button>
      </div>
      <div class="stack">
        <section class="hero-grid">
          <div class="hero-poster-wrap">
            <div class="hero-poster">
              <div class="poster-window">
                <div class="poster-kicker">你的人格类型是：</div>
                <div class="poster-cn">{esc(result['cn'])}</div>
                <div class="poster-code">{esc(result['type'])}</div>
                <div class="poster-scene">{poster_visual_html}</div>
                <div class="poster-quote">{esc(result['intro'])}</div>
              </div>
            </div>
            <div class="poster-side-note">SBTI 原站结果页</div>
          </div>
          <div class="panel summary-card">
            <div class="summary-kicker">你的主类型</div>
            <div class="summary-title">{esc(result['type'])}（{esc(result['cn'])}）</div>
            <div class="summary-badge">{esc(result['badge'])}</div>
            <p class="summary-copy">{esc(result['sub'])}</p>
          </div>
        </section>
        <section class="panel">
          <h2>该人格的简单解读</h2>
          <p class="interpretation-copy">{esc(interpretation)}</p>
        </section>
        <section class="panel">
          <h2>十五维评分</h2>
          <div class="score-list">{dim_cards}</div>
        </section>
        <section class="panel">
          <h2>友情提示</h2>
          <p class="tips-copy">本测试仅供娱乐，别拿它当诊断、面试、相亲、分手、招魂、算命或人生决策。你可以笑，但别太当真。</p>
        </section>
        <section class="panel">
          <div class="author-head">
            <h2>作者的话</h2>
            <button type="button" class="author-toggle" id="authorToggle" aria-controls="authorDetails" aria-expanded="false">展开</button>
          </div>
          <div class="author-details" id="authorDetails" hidden>
            <div class="author-section">
              <div class="author-subtitle">原作者的话：</div>
              {original_author_html}
            </div>
            <div class="author-section">
              <div class="author-subtitle">送钱者 ATM-er基于开源版本的胡闹：</div>
              {remix_author_html}
              <p class="author-copy">原作者主页：<a class="author-link" href="https://space.bilibili.com/417038183/dynamic?spm_id_from=333.1368.list.card_avatar.click" target="_blank" rel="noreferrer">https://space.bilibili.com/417038183/dynamic?spm_id_from=333.1368.list.card_avatar.click</a></p>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
  <script id="reportData" type="application/json">{payload_blob}</script>
  <script>{render_mirror_script()}</script>
</body>
</html>
"""


def write_report(target: Path, payload: dict[str, Any]) -> tuple[Path, Path, Path | None]:
    html_path = target / f"{OUTPUT_STEM}.html"
    json_path = target / f"{OUTPUT_STEM}.json"
    html_path.write_text(render_report_html(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    png_path = capture_report_png(html_path)
    return html_path, json_path, png_path


def build_answer_dump(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "questions": reference["questions"],
        "special_questions": reference["special_questions"],
        "answer_schema": {
            "answers": [
                {"id": "q1", "option": 2, "confidence": 0.68, "evidence": "引用目标 skill 中的稳定人格证据。"}
            ]
        },
    }


def main() -> int:
    args = parse_args()
    reference = load_reference_data()
    if args.dump_questions:
        print(json.dumps(build_answer_dump(reference), ensure_ascii=False, indent=2))
        return 0

    target = discover_target(args.target)
    sources, meta = collect_sources(target)
    fallback_inference = infer_dimensions(sources)
    fallback_answers = synthesize_answers(reference, fallback_inference, sources)

    provided_answers = load_answers_file(args.answers_file, reference)
    source_mode = "conversation-first" if provided_answers else "file-fallback"
    if args.mode == "answers" and not provided_answers:
        raise SystemExit("--mode answers requires --answers-file")
    if args.mode == "file":
        provided_answers = {}
        source_mode = "file-fallback"

    answers = merge_answers(reference, provided_answers, fallback_answers)
    result = compute_result(reference, answers)
    payload = build_payload(target, reference, sources, meta, answers, result, source_mode)
    html_path, json_path, png_path = write_report(target, payload)
    print(
        json.dumps(
            {
                "html": str(html_path),
                "json": str(json_path),
                "png": str(png_path) if png_path else None,
                "target": str(target),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

