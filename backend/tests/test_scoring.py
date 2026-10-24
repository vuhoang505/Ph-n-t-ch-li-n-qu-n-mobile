from types import SimpleNamespace

from app.engines.scoring import composition_analysis, counter_fit, rank_candidates


def hero(hero_id: int, name: str, **values):
    defaults = dict(physical_damage=50, magic_damage=50, durability=50, crowd_control=50, mobility=50, engage=50, protection=50, split_push=50, wave_clear=50, objective_control=50)
    defaults.update(values)
    return SimpleNamespace(
        id=hero_id, name=name, attributes=SimpleNamespace(**defaults), roles=[SimpleNamespace(role="Đấu sĩ")],
        positions=["Caesar"], power_phase="mid", weaknesses=[],
    )


def test_composition_identifies_missing_frontline():
    team = [hero(1, "A", durability=20, crowd_control=25, engage=20, protection=20)]
    result = composition_analysis(team)
    assert "chống chịu" in result["missing"]
    assert "khống chế" in result["missing"]
    assert result["score_kind"] == "algorithmic"


def test_counter_score_changes_with_enemy_profile():
    candidate = hero(1, "Control", crowd_control=95, durability=80)
    mobile_enemy = hero(2, "Mobile", mobility=95, physical_damage=85)
    slow_enemy = hero(3, "Slow", mobility=20, physical_damage=40)
    assert counter_fit(candidate, [mobile_enemy]) > counter_fit(candidate, [slow_enemy])


def test_draft_ranking_respects_desired_position():
    jungle = hero(1, "Jungle", mobility=90)
    jungle.positions = ["Rừng"]
    lane = hero(2, "Lane", mobility=90)
    rows = rank_candidates([lane, jungle], [], [], desired_position="Rừng")
    assert rows[0].hero.id == jungle.id


def test_missing_data_remains_unknown_without_crash():
    incomplete = hero(1, "Incomplete")
    incomplete.attributes.mobility = None
    result = composition_analysis([incomplete])
    assert result["scores"]["mobility"] is None
    assert "mobility" in result["missing_evidence"]

