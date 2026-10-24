"""Hero Rating Engine v1: deterministic, evidence-based, never random.

Scores only exist when a dimension has matching evidence in official skill text.
The score is a normalized heuristic, not an in-game statistic or win rate.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from statistics import mean


METHOD_VERSION = "hero-rating-v3"

# Priors are only used when official skill text has no direct keyword evidence.
# They are deliberately conservative and are persisted with explicit provenance.
ROLE_PRIORS: dict[str, dict[str, float]] = {
    "Đỡ đòn": {"damage": 42, "durability": 82, "mobility": 38, "crowd_control": 70, "sustain": 52, "burst": 35, "teamfight": 78, "split_push": 38, "pickoff": 50, "protection": 72, "objective_control": 58},
    "Trợ thủ": {"damage": 35, "durability": 64, "mobility": 48, "crowd_control": 72, "sustain": 58, "burst": 32, "teamfight": 80, "split_push": 28, "pickoff": 52, "protection": 82, "objective_control": 54},
    "Đấu sĩ": {"damage": 68, "durability": 66, "mobility": 55, "crowd_control": 48, "sustain": 58, "burst": 58, "teamfight": 61, "split_push": 70, "pickoff": 58, "protection": 35, "objective_control": 64},
    "Sát thủ": {"damage": 78, "durability": 36, "mobility": 82, "crowd_control": 38, "sustain": 35, "burst": 84, "teamfight": 45, "split_push": 66, "pickoff": 86, "protection": 24, "objective_control": 60},
    "Pháp sư": {"damage": 76, "durability": 34, "mobility": 42, "crowd_control": 62, "sustain": 34, "burst": 76, "teamfight": 74, "split_push": 42, "pickoff": 58, "protection": 40, "objective_control": 55},
    "Xạ thủ": {"damage": 84, "durability": 30, "mobility": 48, "crowd_control": 32, "sustain": 42, "burst": 65, "teamfight": 68, "split_push": 78, "pickoff": 44, "protection": 24, "objective_control": 84},
}


def normalize(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "D")
    value = value.replace("đ", "d").replace("Đ", "D")
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(char) != "Mn")


@dataclass(frozen=True)
class Rule:
    pattern: str
    weight: float
    label: str


RULES: dict[str, list[Rule]] = {
    "damage": [Rule("gay sat thuong", 18, "gây sát thương"), Rule("sat thuong chuan", 20, "sát thương chuẩn"), Rule("chi mang", 14, "chí mạng"), Rule("cong vat ly", 10, "tỷ lệ công vật lý"), Rule("cong phep", 10, "tỷ lệ công phép")],
    "durability": [Rule("la chan", 19, "lá chắn"), Rule("mien thuong", 20, "miễn thương"), Rule("giam sat thuong", 18, "giảm sát thương"), Rule("mien tu", 22, "miễn tử"), Rule("tang giap", 15, "tăng giáp")],
    "mobility": [Rule("luot", 18, "lướt"), Rule("dich chuyen", 20, "dịch chuyển"), Rule("tang toc chay", 14, "tăng tốc chạy"), Rule("nhay", 15, "nhảy"), Rule("xuyen dia hinh", 20, "xuyên địa hình")],
    "crowd_control": [Rule("lam choang", 20, "làm choáng"), Rule("hat tung", 20, "hất tung"), Rule("lam cham", 12, "làm chậm"), Rule("troi", 20, "trói"), Rule("day lui", 18, "đẩy lùi"), Rule("cam lang", 18, "câm lặng"), Rule("khong che", 14, "khống chế")],
    "sustain": [Rule("hoi mau", 20, "hồi máu"), Rule("hoi phuc", 18, "hồi phục"), Rule("hut mau", 18, "hút máu"), Rule("hoi sinh", 22, "hồi sinh")],
    "burst": [Rule("sat thuong chuan", 16, "sát thương chuẩn"), Rule("chi mang", 15, "chí mạng"), Rule("cuong hoa", 13, "cường hóa"), Rule("no", 10, "kích nổ")],
    "teamfight": [Rule("pham vi", 13, "hiệu ứng phạm vi"), Rule("xung quanh", 13, "ảnh hưởng xung quanh"), Rule("tat ca", 12, "ảnh hưởng nhiều mục tiêu"), Rule("moi tuong dich", 12, "tương tác nhiều tướng địch")],
    "split_push": [Rule("tru", 20, "tương tác công trình"), Rule("don danh", 10, "đòn đánh"), Rule("toc danh", 12, "tốc đánh")],
    "pickoff": [Rule("khoa", 18, "khóa mục tiêu"), Rule("lam choang", 14, "làm choáng"), Rule("troi", 17, "trói"), Rule("danh dau", 12, "đánh dấu")],
    "protection": [Rule("dong doi", 15, "tác động đồng đội"), Rule("la chan", 12, "lá chắn"), Rule("hoi mau", 14, "hồi máu"), Rule("bao ve", 18, "bảo vệ")],
    "objective_control": [Rule("quai", 18, "tương tác quái"), Rule("tru", 15, "tương tác trụ"), Rule("sat thuong chuan", 10, "sát thương chuẩn")],
}

TITLES = {
    "damage": "Khả năng gây sát thương", "durability": "Khả năng chống chịu",
    "mobility": "Khả năng cơ động", "crowd_control": "Khả năng khống chế",
    "sustain": "Khả năng hồi phục", "burst": "Khả năng dồn sát thương",
    "teamfight": "Khả năng giao tranh tổng", "split_push": "Khả năng đẩy lẻ",
    "pickoff": "Khả năng bắt lẻ", "protection": "Khả năng bảo vệ đồng đội",
    "objective_control": "Khả năng kiểm soát mục tiêu",
}


def score_dimension(text: str, rules: list[Rule]) -> tuple[float | None, list[str]]:
    normalized = normalize(text)
    evidence = []
    total = 0.0
    for rule in rules:
        count = len(re.findall(re.escape(rule.pattern), normalized))
        if count:
            total += rule.weight * min(count, 3)
            evidence.append(rule.label)
    if not evidence:
        return None, []
    # 20 điểm nền chỉ được áp dụng khi đã có bằng chứng; lặp cơ chế tăng điểm
    # nhưng lợi ích giảm dần và luôn giới hạn 100.
    return round(min(100.0, 20.0 + total), 1), list(dict.fromkeys(evidence))


def detect_damage_type(text: str) -> str | None:
    normalized = normalize(text)
    physical = normalized.count("sat thuong vat ly")
    magic = normalized.count("sat thuong phep")
    true_damage = normalized.count("sat thuong chuan")
    if not any((physical, magic, true_damage)):
        return None
    present = sum(value > 0 for value in (physical, magic, true_damage))
    if present > 1:
        return "mixed"
    return "physical" if physical else "magic" if magic else "true"


def derive_difficulty_and_phases(text: str, skill_count: int) -> tuple[float, dict[str, float], dict[str, list[str]]]:
    """Derive comparable tactical scores from official skill descriptions."""
    normalized = normalize(text)
    complexity_terms = {
        "luot": "lướt", "dich chuyen": "dịch chuyển", "danh dau": "đánh dấu",
        "cong don": "cộng dồn", "tai kich hoat": "tái kích hoạt", "lan nua": "tung lần nữa",
        "bien hinh": "biến hình", "cuong hoa": "cường hóa", "huong chi dinh": "định hướng",
        "xuyen dia hinh": "xuyên địa hình", "hoi chieu": "quản lý hồi chiêu", "noi tai": "nội tại",
    }
    matched_complexity = [label for term, label in complexity_terms.items() if term in normalized]
    word_count = len(normalized.split())
    difficulty = 24 + max(0, skill_count - 3) * 5 + min(24, word_count / 32 * 4) + min(38, len(matched_complexity) * 4.5)
    difficulty = round(max(25.0, min(95.0, difficulty)), 1)

    def hits(*terms: str) -> int:
        return sum(min(normalized.count(term), 3) for term in terms)

    early_cues = hits("lam choang", "lam cham", "la chan", "hoi mau", "tang toc chay", "day lui")
    mid_cues = hits("luot", "dich chuyen", "sat thuong chuan", "lam choang", "hat tung", "pham vi", "xung quanh")
    late_cues = hits("toc danh", "chi mang", "don danh", "cong don", "phan tram mau", "mau da mat", "cuong hoa")
    phases = {
        "early_game": round(min(92.0, 48 + min(28, early_cues * 4) + min(12, skill_count * 2)), 1),
        "mid_game": round(min(94.0, 52 + min(30, mid_cues * 3.5) + min(10, len(matched_complexity) * 1.5)), 1),
        "late_game": round(min(92.0, 48 + min(32, late_cues * 4) + min(10, word_count / 55)), 1),
    }
    evidence = {
        "difficulty": matched_complexity or ["độ dài và số lượng mô tả kỹ năng"],
        "early_game": [f"{early_cues} tín hiệu khống chế, phòng thủ hoặc hồi phục đầu trận"],
        "mid_game": [f"{mid_cues} tín hiệu cơ động, dồn sát thương hoặc giao tranh"],
        "late_game": [f"{late_cues} tín hiệu tăng tiến từ đòn đánh, chí mạng hoặc cộng dồn"],
    }
    return difficulty, phases, evidence


def analyze_skill_text(skills: list[dict], expert_difficulty: int | None = None, expert_phase: str | None = None, roles: list[str] | None = None) -> dict:
    text = " ".join(skill.get("description", "") for skill in skills)
    ratings: dict[str, float | None] = {}
    evidence: dict[str, list[str]] = {}
    explanations: dict[str, str] = {}
    for key, rules in RULES.items():
        rating, matched = score_dimension(text, rules)
        ratings[key] = rating
        evidence[key] = matched
        explanations[key] = (
            f"Điểm suy ra từ mô tả kỹ năng chính thức: {', '.join(matched)}."
            if matched else "Chưa đủ dữ liệu trong mô tả kỹ năng chính thức để chấm điểm."
        )
    role_priors = [ROLE_PRIORS[role] for role in (roles or []) if role in ROLE_PRIORS]
    for key in RULES:
        if ratings[key] is None and role_priors:
            ratings[key] = round(mean(prior[key] for prior in role_priors), 1)
            role_names = [role for role in (roles or []) if role in ROLE_PRIORS]
            evidence[key] = [f"vai trò chính thức: {', '.join(role_names)}"]
            explanations[key] = "Điểm nền chiến thuật suy ra từ vai trò chính thức vì mô tả kỹ năng không có từ khóa trực tiếp; không phải chỉ số Garena công bố."
    derived_difficulty, derived_phases, derived_evidence = derive_difficulty_and_phases(text, len(skills))
    ratings.update({**derived_phases, "difficulty": derived_difficulty})
    for key in ("early_game", "mid_game", "late_game", "difficulty"):
        evidence[key] = derived_evidence[key]
        explanations[key] = "Điểm thuật toán suy ra từ cơ chế trong mô tả kỹ năng chính thức; không phải thống kê do Garena công bố."
    if expert_difficulty and expert_difficulty > 0:
        ratings["difficulty"] = float(expert_difficulty * 10)
        evidence["difficulty"] = ["đánh giá chuyên gia khởi tạo"]
        explanations["difficulty"] = "Điểm chuyên gia thủ công; không phải chỉ số Garena."
    if expert_phase in {"early", "mid", "late"}:
        phase_key = {"early": "early_game", "mid": "mid_game", "late": "late_game"}[expert_phase]
        ratings[phase_key] = max(78.0, ratings[phase_key])
        evidence[phase_key] = ["giai đoạn sức mạnh do chuyên gia gắn nhãn"]
        explanations[phase_key] = "Điểm định hướng từ nhãn chuyên gia, cần quản trị viên duyệt lại."
    known = sum(value is not None for value in ratings.values())
    confidence = round(min(0.85, 0.25 + known / len(ratings) * 0.6), 2)
    mechanics = sorted({label for values in evidence.values() for label in values if "chuyên gia" not in label})
    return {
        "ratings": ratings,
        "evidence": evidence,
        "explanations": explanations,
        "damage_type": detect_damage_type(text),
        "special_mechanics": mechanics,
        "confidence": confidence,
        "known_dimensions": known,
        "total_dimensions": len(ratings),
        "method_version": METHOD_VERSION,
    }


def matchup_from_ratings(hero: dict, opponent: dict) -> dict:
    comparisons = (
        ("khống chế so với cơ động", "crowd_control", "mobility"),
        ("cơ động so với khống chế", "mobility", "crowd_control"),
        ("dồn sát thương so với chống chịu", "burst", "durability"),
        ("chống chịu so với bắt lẻ", "durability", "pickoff"),
        ("bắt lẻ so với hồi phục", "pickoff", "sustain"),
        ("hồi phục so với dồn sát thương", "sustain", "burst"),
    )
    usable = {
        label: float(hero[hero_key]) - float(opponent[opponent_key])
        for label, hero_key, opponent_key in comparisons
        if hero.get(hero_key) is not None and opponent.get(opponent_key) is not None
    }
    if len(usable) < 3:
        return {
            "advantage_score": None,
            "data_status": "insufficient",
            "confidence": 0.0,
            "coverage": round(len(usable) / len(comparisons), 2),
            "reasons": [],
            "conditions": ["Cần ít nhất ba cặp thuộc tính đối ứng có bằng chứng."],
        }
    score = 50 + mean(usable.values()) * 0.35
    reasons = [
        f"{label}: {'có lợi' if delta > 0 else 'bất lợi' if delta < 0 else 'cân bằng'} ({delta:+.0f})"
        for label, delta in sorted(usable.items(), key=lambda item: abs(item[1]), reverse=True)[:3]
    ]
    return {
        "advantage_score": round(max(0, min(100, score)), 1),
        "data_status": "derived_partial",
        "confidence": round(min(0.75, len(usable) / len(comparisons) * 0.75), 2),
        "coverage": round(len(usable) / len(comparisons), 2),
        "reasons": reasons,
        "conditions": ["Kết quả thay đổi theo vị trí, tài nguyên, cấp độ và thời điểm kỹ năng."],
    }
