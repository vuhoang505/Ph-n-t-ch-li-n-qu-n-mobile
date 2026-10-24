from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


Position = Literal["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"]
POSITIONS = {"Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"}


class HeroAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    physical_damage: float
    magic_damage: float
    durability: float
    crowd_control: float
    mobility: float
    engage: float
    protection: float
    split_push: float
    wave_clear: float
    objective_control: float


class HeroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    image_url: str | None
    damage_type: str
    positions: list[str]
    power_phase: str
    difficulty: int
    strengths: list[str]
    weaknesses: list[str]
    patch_version: str
    roles: list[str]
    attributes: HeroAttributeOut


class DraftRequest(BaseModel):
    ally_ids: list[int] = Field(default_factory=list, max_length=5)
    enemy_ids: list[int] = Field(default_factory=list, max_length=5)
    banned_ids: list[int] = Field(default_factory=list, max_length=10)
    desired_position: Position | None = None
    strategy: str = "cân bằng"
    mastered_hero_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique(self):
        all_selected = self.ally_ids + self.enemy_ids
        if len(all_selected) != len(set(all_selected)):
            raise ValueError("Một tướng không thể xuất hiện ở cả hai đội hoặc được chọn hai lần")
        if set(all_selected) & set(self.banned_ids):
            raise ValueError("Tướng đã cấm không thể được chọn")
        return self


class TeamGenerateRequest(BaseModel):
    strategy: str = "giao tranh tổng"
    locked_hero_ids: list[int] = Field(default_factory=list, max_length=5)
    enemy_ids: list[int] = Field(default_factory=list, max_length=5)
    banned_ids: list[int] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_unique(self):
        selected = self.locked_hero_ids + self.enemy_ids
        if len(selected) != len(set(selected)):
            raise ValueError("Một tướng không thể vừa thuộc đội đề xuất vừa thuộc đội đối phương")
        if set(selected) & set(self.banned_ids):
            raise ValueError("Tướng đã cấm không thể được khóa hoặc nằm trong đội đối phương")
        if len(self.banned_ids) != len(set(self.banned_ids)):
            raise ValueError("Danh sách cấm không được chứa tướng trùng nhau")
        return self


class TeamCompareRequest(BaseModel):
    team_a_ids: list[int] = Field(min_length=1, max_length=5)
    team_b_ids: list[int] = Field(min_length=1, max_length=5)


class BuildRequest(BaseModel):
    hero_id: int
    position: Position
    enemy_ids: list[int] = Field(default_factory=list, max_length=5)
    ally_ids: list[int] = Field(default_factory=list, max_length=4)
    phase: Literal["đầu trận", "giữa trận", "cuối trận"] = "giữa trận"
    playstyle: str = "cân bằng"


class CounterRequest(BaseModel):
    hero_id: int
    opponent_id: int | None = None
    position: Position | None = None


class StrategyRequest(BaseModel):
    ally_ids: list[int] = Field(min_length=1, max_length=5)
    enemy_ids: list[int] = Field(default_factory=list, max_length=5)
    phase: Literal["đầu trận", "giữa trận", "cuối trận"]


class MacroTimelineRequest(BaseModel):
    ally_ids: list[int] = Field(min_length=5, max_length=5)
    enemy_ids: list[int] = Field(min_length=5, max_length=5)
    ally_positions: dict[Position, int] | None = None
    enemy_positions: dict[Position, int] | None = None
    enemy_start_buff: Literal["auto", "blue", "red"] = "auto"
    ally_side: Literal["blue", "red"] = "blue"
    timeline_phase: Literal["01:30", "03:00", "08:00", "12:00+"] = "01:30"

    @model_validator(mode="after")
    def validate_lineups(self):
        selected = self.ally_ids + self.enemy_ids
        if len(selected) != len(set(selected)):
            raise ValueError("Mỗi tướng chỉ được xuất hiện một lần trong War Room")
        for label, lineup, hero_ids in (
            ("đội ta", self.ally_positions, self.ally_ids),
            ("đội địch", self.enemy_positions, self.enemy_ids),
        ):
            if lineup is not None and (set(lineup) != POSITIONS or set(lineup.values()) != set(hero_ids)):
                raise ValueError(f"Phân công {label} phải có đúng 5 vị trí và khớp danh sách tướng")
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)
    hero_ids: list[int] = Field(default_factory=list, max_length=10)


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

