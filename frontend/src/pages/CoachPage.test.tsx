// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { buildAnswerTree } from "./CoachPage";

describe("buildAnswerTree", () => {
  it("tạo cây trả lời ngay trong web", () => {
    const answer = buildAnswerTree("Nên cấm chọn thế nào?", []);
    expect(answer.nodes).toHaveLength(3);
    expect(answer.nodes[1].children.some(item => item.includes("tướng đã cấm"))).toBe(true);
    expect(answer.nodes[2].title).toBe("Kế hoạch hành động");
    expect(answer).not.toHaveProperty("googleUrl");
  });
});
