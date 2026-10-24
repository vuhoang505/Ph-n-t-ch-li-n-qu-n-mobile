// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { buildToShareText } from "./BuildPage";

describe("buildToShareText", () => {
  it("xuất đủ trang bị, ngọc, phù hiệu và bổ trợ", () => {
    const text = buildToShareText({
      hero: "Nakroth", position: "Rừng", phase: "giữa trận",
      items: [{ name: "Kiếm truy hồn" }, { name: "Giày kiên cường" }],
      loadout: {
        arcana: [{ color: "Đỏ", count: 10, name: "Đỏ III Công vật lý" }],
        enchantment: { family: "Vực hỗn mang", entries: [{ name: "Ma hỏa" }, { name: "Cường công" }, { name: "Ma tính" }] },
        talent: { name: "TRỪNG TRỊ" },
      },
    } as Parameters<typeof buildToShareText>[0]);
    expect(text).toContain("BUILD NAKROTH · Rừng · giữa trận");
    expect(text).toContain("Kiếm truy hồn");
    expect(text).toContain("10× Đỏ III Công vật lý");
    expect(text).toContain("Vực hỗn mang");
    expect(text).toContain("TRỪNG TRỊ");
  });
});
