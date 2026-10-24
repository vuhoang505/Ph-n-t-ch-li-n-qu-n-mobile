"""Deterministic, explainable in-match playbook derived from hero roles and official skills."""
from __future__ import annotations

import re


def _text(skill) -> str:
    return f"{skill.name} {skill.description}".casefold()


def _active(skills):
    rows = [row for row in skills if row.skill_type != "passive"]
    return rows[-3:] if len(rows) >= 3 else rows


def build_skill_priority(skills) -> dict:
    active = _active(skills)
    if len(active) < 2:
        return {"primary": None, "secondary": None, "ultimate": None, "levels": [], "advice": "Chưa đủ kỹ năng chủ động để lập thứ tự nâng."}
    basic, ultimate = active[:-1], active[-1]
    damage_words = ("sát thương", "công vật lý", "công phép", "giảm hồi chiêu", "hồi máu", "lá chắn")
    utility_words = ("làm choáng", "hất tung", "câm lặng", "trói", "đóng băng", "làm chậm")
    def score(row):
        text = _text(row)
        return sum(text.count(word) * (3 if word in damage_words else 2) for word in damage_words + utility_words) + len(re.findall(r"\d+", text)) * .12
    primary, secondary = sorted(basic[:2], key=score, reverse=True)
    counts = {primary.order_index: 0, secondary.order_index: 0, ultimate.order_index: 0}
    levels = []
    for level in range(1, 16):
        if level in (4, 8, 12): chosen = ultimate
        elif level == 2 and counts[secondary.order_index] == 0: chosen = secondary
        elif counts[primary.order_index] < 6: chosen = primary
        else: chosen = secondary
        counts[chosen.order_index] += 1
        levels.append({"level": level, "skill_order": chosen.order_index, "skill_name": chosen.name, "rank": counts[chosen.order_index]})
    number = basic.index(primary) + 1
    return {
        "primary": {"order": primary.order_index, "name": primary.name, "label": f"Max Chiêu {number}"},
        "secondary": {"order": secondary.order_index, "name": secondary.name},
        "ultimate": {"order": ultimate.order_index, "name": ultimate.name, "levels": [4, 8, 12]},
        "levels": levels,
        "advice": f"Ưu tiên tối đa {primary.name} để khai thác sát thương, dọn lính hoặc trao đổi chiêu; nâng {ultimate.name} đúng cấp 4, 8 và 12.",
        "kind": "derived_from_official_skills",
    }


def build_combos(skills) -> list[dict]:
    active = _active(skills)
    if not active: return []
    cc_words = ("làm choáng", "hất tung", "trói", "đóng băng", "làm chậm", "câm lặng")
    mobility_words = ("lướt", "dịch chuyển", "lao", "nhảy")
    opener = max(active, key=lambda row: sum(word in _text(row) for word in cc_words + mobility_words))
    remaining = [row for row in active if row is not opener]
    poke = [opener, *(remaining[:1])]
    burst = [opener, *remaining]
    def step(row): return {"type": "skill", "order": row.order_index, "label": row.name}
    mechanic = "Canh hiệu ứng khống chế hoặc dấu ấn trúng mục tiêu rồi mới nối chiêu; xen đánh thường khi kỹ năng tạo cường hóa đòn đánh."
    all_text = " ".join(_text(row) for row in skills)
    if "nội tại" in all_text: mechanic = "Theo dõi và tích đủ nội tại trước nhịp dồn sát thương; không dùng liên tiếp kỹ năng khi chưa kích hoạt được hiệu ứng cộng thêm."
    return [
        {"name": "Cấu rỉa / mở giao tranh", "steps": [*(step(row) for row in poke), {"type": "attack", "label": "Đánh thường"}], "tip": "Giữ lại một kỹ năng để rút lui hoặc ngắt phản công."},
        {"name": "Dồn sát thương", "steps": [*(step(row) for row in burst), {"type": "attack", "label": "Đánh thường"}], "tip": mechanic},
    ]


def build_base_stats(hero, rating) -> dict:
    roles = {row.role for row in hero.roles}
    tank = bool(roles & {"Đỡ đòn", "Trợ thủ", "Đấu sĩ"})
    marksman = "Xạ thủ" in roles
    mage = "Pháp sư" in roles
    durability = float(getattr(rating, "durability", 50) or 50)
    mobility = float(getattr(rating, "mobility", 50) or 50)
    hp1 = round(3250 + durability * 6 + (260 if tank else 0))
    hp15 = round(hp1 + 14 * (235 + durability * 1.45))
    armor1 = round(125 + durability * 1.05 + (25 if tank else 0))
    armor15 = round(armor1 + 14 * (17 + durability * .08))
    magic1 = 80
    magic15 = 246
    speed = round(365 + mobility * .2 + (5 if marksman else 0))
    attack_speed = round(8 + (16 if marksman else 5 if mage else 10), 1)
    regen1 = round(42 + durability * .1, 1)
    regen15 = round(regen1 + 14 * 3.2, 1)
    return {
        "kind": "estimated_role_model", "label": "Ước tính tham khảo theo vai trò", "confidence": .35,
        "rows": [
            {"key": "health", "label": "Máu tối đa", "level_1": hp1, "level_15": hp15, "unit": ""},
            {"key": "armor", "label": "Giáp vật lý", "level_1": armor1, "level_15": armor15, "unit": ""},
            {"key": "magic_defense", "label": "Giáp phép", "level_1": magic1, "level_15": magic15, "unit": ""},
            {"key": "move_speed", "label": "Tốc chạy", "level_1": speed, "level_15": speed, "unit": ""},
            {"key": "attack_speed", "label": "Tốc đánh cộng thêm", "level_1": attack_speed, "level_15": round(attack_speed + (28 if marksman else 18), 1), "unit": "%"},
            {"key": "health_regen", "label": "Hồi máu / 5 giây", "level_1": regen1, "level_15": regen15, "unit": ""},
        ],
    }


def build_phase_tips(hero, rating) -> list[dict]:
    roles = {row.role for row in hero.roles}; positions = set(hero.positions or [])
    assassin = "Sát thủ" in roles or "Rừng" in positions
    carry = bool(roles & {"Xạ thủ", "Pháp sư"})
    support = bool(roles & {"Trợ thủ", "Đỡ đòn"})
    early = "Hoàn thành vòng rừng đầu, quan sát hai cánh và chỉ gank khi đồng đội có quyền đẩy lính." if assassin else "Ưu tiên dọn đợt lính đầu, giữ máu và kiểm soát bụi trước khi trao đổi chiêu."
    mid = "Di chuyển cùng chủ lực, mở tầm nhìn và giữ kỹ năng khống chế để phản công." if support else "Đẩy xong đường rồi di chuyển trước tới Rồng hoặc Caesar; tìm góc bắt mục tiêu đi lẻ." 
    late = "Đứng tuyến sau, giữ khoảng cách và chờ đối thủ dùng kỹ năng tiếp cận trước khi xả sát thương." if carry else "Đứng lệch sườn, che tầm nhìn và chỉ mở giao tranh khi đồng đội đủ gần để theo sát."
    if assassin: late = "Không lộ vị trí sớm; vòng sau đội hình và chờ chủ lực địch mất kỹ năng bảo vệ rồi mới lao vào."
    scores = {"early": getattr(rating, "early_game", None), "mid": getattr(rating, "mid_game", None), "late": getattr(rating, "late_game", None)}
    return [{"phase": phase, "score": scores[phase], "title": title, "advice": advice} for phase, title, advice in (("early", "Đầu trận", early), ("mid", "Giữa trận", mid), ("late", "Cuối trận", late))]

