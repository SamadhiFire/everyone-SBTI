#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "assets" / "sbti-data.json"
OUTPUT_STEM = "sbti-report"
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
            "path": str(target),
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


def write_report(target: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    html_path = target / f"{OUTPUT_STEM}.html"
    json_path = target / f"{OUTPUT_STEM}.json"
    html_path.write_text(render_report_html(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return html_path, json_path


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
    html_path, json_path = write_report(target, payload)
    print(json.dumps({"html": str(html_path), "json": str(json_path), "target": str(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
