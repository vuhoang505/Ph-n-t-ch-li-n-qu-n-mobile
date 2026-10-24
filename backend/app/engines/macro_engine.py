"""Deterministic macro timeline engine for the Tactical War Room."""
from __future__ import annotations

from statistics import mean

from .analysis_adapter import profile_for
from .hero_rating import normalize


PHASE_METRICS = {
    "01:30": ("early_game", "burst", "mobility"),
    "03:00": ("early_game", "burst", "mobility", "objective_control"),
    "08:00": ("mid_game", "crowd_control", "teamfight", "pickoff"),
    "12:00+": ("late_game", "split_push", "durability", "teamfight"),
}
ROLE_ORDER = ("Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ")
ASSIGNMENT_ORDER = ("Rừng", "Caesar", "Giữa", "Rồng", "Trợ thủ")
BLUE_JUNGLERS = {normalize(name) for name in ("Nakroth", "Keera", "Murad", "Ngộ Không", "Kriknak", "Paine", "Aoi")}
RED_JUNGLERS = {normalize(name) for name in ("Slimz", "Fennik", "Lindis", "Moren", "Hayate", "Kil'Groth", "Triệu Vân", "Lữ Bố", "Skud")}
EARLY_INVADERS = {normalize(name) for name in ("Zip", "Arum", "Mina", "Grakk", "Veres", "Gildur")}


def _assign_roles(heroes, positions: dict[str, int] | None = None) -> dict:
    if positions:
        by_id = {hero.id: hero for hero in heroes}
        return {role: by_id[positions[role]] for role in ROLE_ORDER}
    available = list(heroes)
    assigned = {}
    for position in ASSIGNMENT_ORDER:
        match = next((hero for hero in available if position in (hero.positions or [])), None)
        if match is None and position == "Rừng":
            match = next((hero for hero in available if any(role.role == "Sát thủ" for role in hero.roles)), None)
        if match is None and available:
            match = available[0]
        if match is not None:
            assigned[position] = match
            available.remove(match)
    return {role: assigned[role] for role in ROLE_ORDER if role in assigned}


def _hero_phase_score(hero, metrics: tuple[str, ...]) -> tuple[float | None, int]:
    scores = profile_for(hero).rating_scores
    known = [float(scores[key]) for key in metrics if scores.get(key) is not None]
    return (mean(known), len(known)) if known else (None, 0)


def _team_power(heroes, metrics: tuple[str, ...]) -> tuple[float | None, int]:
    values, evidence = [], 0
    for hero in heroes:
        score, known = _hero_phase_score(hero, metrics)
        if score is not None:
            values.append(score)
            evidence += known
    return (mean(values), evidence) if values else (None, 0)


def _power_balance(allies, enemies, phase: str) -> dict:
    metrics = PHASE_METRICS[phase]
    ally_raw, ally_evidence = _team_power(allies, metrics)
    enemy_raw, enemy_evidence = _team_power(enemies, metrics)
    if ally_raw is None or enemy_raw is None or ally_raw + enemy_raw == 0:
        ally_power = enemy_power = 50.0
        status = "insufficient"
    else:
        ally_power = round(ally_raw / (ally_raw + enemy_raw) * 100, 1)
        enemy_power = round(100 - ally_power, 1)
        status = "ok" if ally_evidence >= 10 and enemy_evidence >= 10 else "partial"
    delta = ally_power - enemy_power
    return {
        "ally_power": ally_power, "enemy_power": enemy_power,
        "advantage": "ally" if delta >= 3 else "enemy" if delta <= -3 else "balanced",
        "metrics": list(metrics), "status": status,
        "confidence": round(min(0.9, (ally_evidence + enemy_evidence) / (len(metrics) * 10) * 0.9), 2),
    }


def _jungle_prediction(enemy_roles: dict, phase: str, start_buff: str = "auto") -> dict:
    jungler = enemy_roles.get("Rừng")
    normalized_name = normalize(jungler.name) if jungler else ""
    if start_buff != "auto":
        blue_start = start_buff == "blue"
        prediction_mode = "manual"
    else:
        blue_start = bool(jungler and normalized_name not in RED_JUNGLERS and (
            normalized_name in BLUE_JUNGLERS
            or any(role.role == "Sát thủ" for role in jungler.roles)
            or profile_for(jungler).damage_type == "magic"
        ))
        prediction_mode = "automatic"
    if blue_start:
        path = [
            {"x": 67, "y": 43, "label": "Bùa Xanh Địch"},
            {"x": 60, "y": 35, "label": "Bãi Quái"},
            {"x": 49, "y": 25, "label": "Bùa Đỏ Địch"},
            {"x": 79, "y": 63, "label": "Hướng Gank Đường Rồng"},
        ]
        target = "Rồng"
    else:
        path = [
            {"x": 49, "y": 25, "label": "Bùa Đỏ Địch"},
            {"x": 58, "y": 35, "label": "Bãi Quái"},
            {"x": 67, "y": 43, "label": "Bùa Xanh Địch"},
            {"x": 58, "y": 15, "label": "Hướng Gank Đường Caesar"},
        ]
        target = "Caesar"
    visible = phase in {"01:30", "03:00"}
    return {
        "jungler": jungler.name if jungler else "Chưa xác định",
        "start_buff": "blue" if blue_start else "red",
        "gank_target_lane": target,
        "gank_window": "01:20 - 01:40" if phase == "01:30" else "02:40 - 03:15",
        "path_coordinates": path if visible else path[-2:],
        "status": "early_path" if visible else "rotation_estimate",
        "prediction_mode": prediction_mode,
    }


def _objective_call(power: dict, phase: str) -> dict:
    lead = power["advantage"]
    if phase in {"01:30", "03:00"}:
        target = "Rồng Kraygath" if lead != "enemy" else "Tà Thần Caesar / trụ ngoài"
        action = "Ép quyền vào sông sau khi đẩy đường Rồng." if lead == "ally" else "Không vào sông tối; đổi mục tiêu hoặc lấy tài nguyên phía đối diện."
    elif phase == "08:00":
        target = "Cụm trụ giữa và rừng đối phương" if lead == "ally" else "Rừng nhà và đường lính xa"
        action = "Bắt lẻ trước rồi mới chạm mục tiêu lớn." if lead != "enemy" else "Giữ đội hình, dọn hai đường và phản giao tranh ở cửa hẹp."
    else:
        target = "Tà Thần Caesar Bạo Chúa"
        action = "Thiết lập tầm nhìn và ép giao tranh quanh Caesar." if lead == "ally" else "Không kiểm tra bụi đơn lẻ; đẩy đường xa để kéo đối thủ khỏi Caesar."
    return {"target": target, "action": action, "controlled_by": lead}


def _ambush_zones(phase: str, jungle: dict) -> list[dict]:
    zones = [
        {"id": "river_bush_bot", "x": 69, "y": 61, "danger_level": "high" if jungle["gank_target_lane"] == "Rồng" else "medium", "warning": "Bụi ngã ba đường Rồng: nguy cơ bị rừng và trợ thủ kẹp."},
        {"id": "river_bush_top", "x": 39, "y": 30, "danger_level": "high" if jungle["gank_target_lane"] == "Caesar" else "medium", "warning": "Bụi sông Caesar: chỉ tiến vào khi đã thấy rừng địch."},
        {"id": "mid_river", "x": 52, "y": 47, "danger_level": "medium", "warning": "Cửa sông giữa: điểm giao cắt của hai hướng đảo đường."},
    ]
    if phase in {"08:00", "12:00+"}:
        zones.append({"id": "enemy_blue_gate", "x": 64, "y": 40, "danger_level": "high", "warning": "Cửa bùa xanh địch: vùng bắt lẻ nguy hiểm khi thiếu tầm nhìn."})
    return zones


def _invade_alert(enemies) -> dict:
    invaders = [hero.name for hero in enemies if normalize(hero.name) in EARLY_INVADERS]
    return {
        "active": bool(invaders),
        "heroes": invaders,
        "time": "00:30",
        "target_buff": "blue",
        "message": "Cảnh báo cướp Bùa Xanh lúc 00:30!",
        "path_coordinates": [
            {"x": 78, "y": 18}, {"x": 61, "y": 34},
            {"x": 48, "y": 47}, {"x": 37, "y": 41},
        ] if invaders else [],
    }


def _orders(phase: str, power: dict, jungle: dict) -> list[dict]:
    defensive = power["advantage"] == "enemy"
    target = jungle["gank_target_lane"]
    common = {
        "Caesar": "Giữ dịch chuyển và đẩy đường xa; chỉ rời đường sau khi lính đã chạm trụ.",
        "Rừng": f"Đọc vòng rừng địch từ bùa {jungle['start_buff']}; {'phản gank' if defensive else 'xâm lăng cùng đường có quyền ưu tiên'} tại cánh {target}.",
        "Giữa": "Dọn lính nhanh rồi di chuyển sau lớp tầm nhìn của trợ thủ, không vào sông trước.",
        "Rồng": f"{'Lùi sau nửa đường sông' if target == 'Rồng' else 'Giữ nhịp đẩy có kiểm soát'} và lưu kỹ năng thoát thân cho cửa sổ gank.",
        "Trợ thủ": f"Cắm tầm nhìn bụi ngã ba {target} trước cửa sổ {jungle['gank_window']} và ping đường lùi.",
    }
    if phase == "08:00": common["Trợ thủ"] = "Đi cùng rừng kiểm soát cửa rừng; không để chủ lực tự kiểm tra bụi."
    if phase == "12:00+": common["Caesar"] = "Quản lý đường xa đối diện Caesar; giữ vị trí có thể hội quân trước giao tranh."
    return [{"role": role, "action": common[role]} for role in ROLE_ORDER]


def analyze_macro_timeline(
    allies, enemies, phase: str, hero_payload,
    ally_positions: dict[str, int] | None = None,
    enemy_positions: dict[str, int] | None = None,
    enemy_start_buff: str = "auto",
    ally_side: str = "blue",
) -> dict:
    ally_roles = _assign_roles(allies, ally_positions)
    enemy_roles = _assign_roles(enemies, enemy_positions)
    power = _power_balance(allies, enemies, phase)
    jungle = _jungle_prediction(enemy_roles, phase, enemy_start_buff)
    return {
        "timeline_phase": phase,
        "power_balance": power,
        "jungle_prediction": jungle,
        "objective_call": _objective_call(power, phase),
        "tactical_orders": _orders(phase, power, jungle),
        "ambush_zones": _ambush_zones(phase, jungle),
        "invade_alert": _invade_alert(enemies),
        "ally_side": ally_side,
        "lineups": {
            "ally": [{"role": role, "hero": hero_payload(hero)} for role, hero in ally_roles.items()],
            "enemy": [{"role": role, "hero": hero_payload(hero)} for role, hero in enemy_roles.items()],
        },
        "score_kind": "algorithmic",
    }
