from uuid import uuid4
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.main import app
from app.models import HeroPowerSpike, HeroRating


def test_health_and_heroes():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["heroes"] > 0
        heroes = client.get("/api/heroes")
        assert heroes.status_code == 200
        assert heroes.json()["total"] >= 100
        assert all(item["image_url"] for item in heroes.json()["items"])


def test_duplicate_draft_selection_is_rejected():
    with TestClient(app) as client:
        response = client.post("/api/draft/recommend", json={"ally_ids": [1], "enemy_ids": [1]})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


def test_banned_hero_cannot_be_selected():
    with TestClient(app) as client:
        response = client.post("/api/draft/recommend", json={"ally_ids": [1], "banned_ids": [1]})
        assert response.status_code == 422


def test_draft_recommendations_never_include_banned_heroes():
    with TestClient(app) as client:
        banned_ids = [2, 4, 5, 6, 7]
        response = client.post("/api/draft/recommend", json={
            "ally_ids": [1],
            "enemy_ids": [3],
            "banned_ids": banned_ids,
            "strategy": "giao tranh tổng",
        })
        assert response.status_code == 200
        recommended = {row["hero"]["id"] for row in response.json()["recommendations"]}
        assert recommended.isdisjoint(banned_ids)


def test_team_generation_never_returns_banned_heroes():
    with TestClient(app) as client:
        response = client.post("/api/team/generate", json={
            "strategy": "giao tranh tổng",
            "locked_hero_ids": [1],
            "enemy_ids": [3],
            "banned_ids": [2, 4, 5, 6, 7],
        })
        assert response.status_code == 200
        returned = {hero["id"] for hero in response.json()["team"]}
        assert returned.isdisjoint({2, 4, 5, 6, 7})


def test_team_rejects_a_locked_hero_that_is_also_banned():
    with TestClient(app) as client:
        response = client.post("/api/team/generate", json={
            "locked_hero_ids": [1],
            "banned_ids": [1],
        })
        assert response.status_code == 422


def test_auth_register_login_and_wrong_password():
    email = f"tester-{uuid4()}@example.com"
    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json={"email": email, "display_name": "Tester", "password": "a-secure-password"})
        assert registered.status_code == 201
        assert registered.json()["access_token"]
        login = client.post("/api/auth/login", json={"email": email, "password": "a-secure-password"})
        assert login.status_code == 200
        denied = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
        assert denied.status_code == 401


def test_meta_uses_sourced_public_match_snapshot():
    with TestClient(app) as client:
        response = client.get("/api/meta/heroes")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "public_match_data"
        assert payload["sample_games"] == 172
        assert payload["source"]["url"].startswith("https://liquipedia.net/")
        assert len(payload["items"]) == 129
        assert payload["heroes_with_matches"] == 84
        assert payload["heroes_without_matches"] == 45
        assert any(item["picks"] + item["bans"] > 0 for item in payload["items"])
        assert any(not item["played"] and item["win_rate"] is None for item in payload["items"])
        assert all(item["sample_games"] == payload["sample_games"] for item in payload["items"])


def test_primary_analysis_flows_return_explainable_results():
    with TestClient(app) as client:
        draft = client.post("/api/draft/recommend", json={
            "ally_ids": [1], "enemy_ids": [3], "banned_ids": [],
            "desired_position": "Giữa", "strategy": "giao tranh tổng",
        })
        assert draft.status_code == 200
        assert len(draft.json()["recommendations"]) == 5
        assert draft.json()["score_kind"] == "algorithmic"

        team = client.post("/api/team/generate", json={"strategy": "cấu rỉa", "locked_hero_ids": [1]})
        assert team.status_code == 200
        assert len(team.json()["team"]) == 5

        counter = client.post("/api/counter/analyze", json={"hero_id": 1, "opponent_id": 3})
        assert counter.status_code == 200
        assert counter.json()["score_kind"] == "algorithmic"

        build = client.post("/api/build/recommend", json={
            "hero_id": 3, "position": "Rừng", "enemy_ids": [1, 2],
            "ally_ids": [], "phase": "giữa trận", "playstyle": "cân bằng",
        })
        assert build.status_code == 200
        assert len(build.json()["items"]) == 6
        assert build.json()["score_kind"] == "algorithmic"
        assert len(build.json()["loadout"]["arcana"]) == 3
        assert all(rune["level"] == "Cấp III" for rune in build.json()["loadout"]["arcana"])
        assert [row["level"] for row in build.json()["loadout"]["enchantment"]["entries"]] == ["Bậc 1", "Bậc 2", "Bậc 3"]
        assert build.json()["loadout"]["talent"]["name"] == "TRỪNG TRỊ"

        strategy = client.post("/api/strategy/analyze", json={
            "ally_ids": [1, 2], "enemy_ids": [3, 4], "phase": "giữa trận",
        })
        assert strategy.status_code == 200
        assert strategy.json()["win_condition"]


def test_removed_ai_chat_is_not_exposed():
    with TestClient(app) as client:
        response = client.post("/api/ai/chat", json={"message": "Đội hình này thiếu gì?", "hero_ids": [1, 3]})
        assert response.status_code == 404


def test_macro_timeline_returns_map_orders_and_power_balance():
    with TestClient(app) as client:
        response = client.post("/api/strategy/macro-timeline", json={
            "ally_ids": [1, 2, 3, 4, 5],
            "enemy_ids": [6, 7, 8, 9, 10],
            "ally_positions": {"Caesar": 1, "Rừng": 2, "Giữa": 3, "Rồng": 4, "Trợ thủ": 5},
            "enemy_positions": {"Caesar": 6, "Rừng": 7, "Giữa": 8, "Rồng": 9, "Trợ thủ": 10},
            "enemy_start_buff": "red",
            "timeline_phase": "08:00",
        })
        assert response.status_code == 200
        payload = response.json()
        assert payload["timeline_phase"] == "08:00"
        assert round(payload["power_balance"]["ally_power"] + payload["power_balance"]["enemy_power"], 1) == 100
        assert len(payload["tactical_orders"]) == 5
        assert payload["jungle_prediction"]["path_coordinates"]
        assert payload["ambush_zones"]
        assert len(payload["lineups"]["ally"]) == 5
        assert next(row for row in payload["lineups"]["enemy"] if row["role"] == "Rừng")["hero"]["id"] == 7
        assert payload["jungle_prediction"]["start_buff"] == "red"
        assert payload["jungle_prediction"]["prediction_mode"] == "manual"


def test_macro_timeline_rejects_duplicate_heroes():
    with TestClient(app) as client:
        response = client.post("/api/strategy/macro-timeline", json={
            "ally_ids": [1, 2, 3, 4, 5],
            "enemy_ids": [5, 6, 7, 8, 9],
            "timeline_phase": "01:30",
        })
        assert response.status_code == 422


def test_vision_upload_reads_and_analyzes_a_real_image():
    image = Image.new("RGB", (1280, 720), color=(18, 42, 76))
    stream = BytesIO()
    image.save(stream, format="PNG")
    with TestClient(app) as client:
        response = client.post("/api/vision/analyze", files={"file": ("match.png", stream.getvalue(), "image/png")})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "analyzed"
        assert payload["image"]["width"] == 1280
        assert payload["image"]["height"] == 720
        assert payload["recommendations"]


def test_vision_upload_rejects_fake_image_content():
    with TestClient(app) as client:
        response = client.post("/api/vision/analyze", files={"file": ("fake.png", b"not-an-image", "image/png")})
        assert response.status_code == 422


def test_official_hero_has_complete_role_informed_tactical_profile():
    with TestClient(app) as client:
        roster = client.get("/api/heroes", params={"search": "Airi"}).json()["items"]
        hero = next(item for item in roster if item["name"] == "Airi")
        assert hero["profile_status"] == "complete"
        assert hero["difficulty"] > 0
        assert hero["power_phase"] in {"early", "mid", "late"}
        assert hero["strengths"] and hero["weaknesses"]
        detail = client.get(f"/api/heroes/{hero['id']}/analysis")
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["skills"]
        assert payload["ratings"]["score_kind"] == "algorithmic"
        assert all(value is not None for value in payload["ratings"]["scores"].values())
        assert payload["analysis"]["range_type"] in {"melee", "ranged"}
        assert "sources" not in payload
        assert payload["tier"]["tier"] in {"S", "A", "B", "C"}
        assert payload["tier"]["kind"] == "algorithmic"
        assert len(payload["skill_priority"]["levels"]) == 15
        assert [row["level"] for row in payload["skill_priority"]["levels"] if row["skill_order"] == payload["skill_priority"]["ultimate"]["order"]] == [4, 8, 12]
        assert len(payload["combos"]) >= 2
        assert payload["base_stats"]["kind"] == "estimated_role_model"
        assert len(payload["base_stats"]["rows"]) == 6
        assert [row["phase"] for row in payload["gameplay_tips"]] == ["early", "mid", "late"]
        counters = client.get(f"/api/heroes/{hero['id']}/counters")
        assert counters.status_code == 200
        assert counters.json()["status"] in {"ok", "insufficient"}


def test_search_is_accent_insensitive_and_supports_aliases():
    with TestClient(app) as client:
        no_accent = client.get("/api/heroes/search", params={"q": "dieu thuyen"})
        assert no_accent.status_code == 200
        assert any(item["name"] == "Điêu Thuyền" for item in no_accent.json()["items"])
        alias = client.get("/api/heroes/search", params={"q": "nak"})
        assert alias.status_code == 200
        assert any(item["name"] == "Nakroth" for item in alias.json()["items"])


def test_full_official_roster_has_stable_ids_and_analysis_sources():
    with TestClient(app) as client:
        roster = client.get("/api/heroes").json()["items"]
        assert len(roster) == 129
        assert len({item["id"] for item in roster}) == 129
        by_name = {item["name"]: item for item in roster}
        assert by_name["Thane"]["id"] == 1
        assert by_name["Alice"]["id"] == 2
        assert by_name["Nakroth"]["id"] == 3
        assert all(1 <= item["difficulty"] <= 10 for item in roster)
        assert all(item["power_phase"] in {"early", "mid", "late"} for item in roster)


def test_every_hero_has_difficulty_and_three_power_phase_scores():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
    with SessionLocal() as db:
        complete_ratings = db.scalar(select(func.count()).select_from(HeroRating).where(
            HeroRating.method_version == "hero-rating-v2",
            HeroRating.difficulty.is_not(None),
            HeroRating.early_game.is_not(None),
            HeroRating.mid_game.is_not(None),
            HeroRating.late_game.is_not(None),
        ))
        phase_rows = db.scalar(select(func.count()).select_from(HeroPowerSpike).where(HeroPowerSpike.score.is_not(None)))
        assert complete_ratings == 129
        assert phase_rows == 129 * 3


def test_admin_analysis_routes_are_protected():
    with TestClient(app) as client:
        assert client.post("/api/admin/heroes/analyze").status_code == 401
        assert client.get("/api/admin/heroes/report").status_code == 401

