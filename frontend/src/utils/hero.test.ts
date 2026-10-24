import { describe, expect, it } from "vitest";
import { heroInitials, heroModuleReady, heroModuleStatus, normalizeHeroSearch } from "./hero";

describe("heroInitials", () => {
  it("tạo ký hiệu ổn định từ tên tướng", () => {
    expect(heroInitials("Huyết Kiếm")).toBe("HK");
    expect(heroInitials("  Alice ")).toBe("A");
  });
});

describe("normalizeHeroSearch", () => {
  it("tìm tiếng Việt không phân biệt dấu và hoa thường", () => {
    expect(normalizeHeroSearch("Điêu Thuyền")).toBe("dieu thuyen");
    expect(normalizeHeroSearch("ĐỠ ĐÒN")).toBe("do don");
  });
});

describe("hero module readiness", () => {
  const partialHero = {
    profile_status: "official_partial_analysis",
    difficulty: 0,
    readiness: { modules: { counter: true, build: false } },
  };

  it("chỉ kết luận khi backend cung cấp trạng thái cho đúng module", () => {
    expect(heroModuleReady(partialHero, "counter")).toBe(true);
    expect(heroModuleReady(partialHero, "build")).toBe(false);
    expect(heroModuleReady(partialHero, "strategy")).toBeUndefined();
    expect(heroModuleStatus(partialHero, "build")).toBe("Chưa đủ dữ liệu cho chức năng này");
  });
});

