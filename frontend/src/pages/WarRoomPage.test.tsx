// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { warRoomShareText } from "./WarRoomPage";

describe("warRoomShareText", () => {
  it("xuất đủ tương quan, vòng rừng, mục tiêu và chỉ đạo", () => {
    const text = warRoomShareText({
      timeline_phase: "03:00",
      power_balance: { ally_power: 54, enemy_power: 46 },
      jungle_prediction: { jungler: "Nakroth", start_buff: "blue", gank_target_lane: "Rồng", gank_window: "01:20 - 01:40" },
      objective_call: { target: "Rồng Kraygath", action: "Ép quyền vào sông." },
      tactical_orders: [{ role: "Rừng", action: "Phản gank đường Rồng." }],
    } as Parameters<typeof warRoomShareText>[0]);
    expect(text).toContain("TACTICAL WAR ROOM · 03:00");
    expect(text).toContain("Đội ta 54%");
    expect(text).toContain("Nakroth · Bùa Xanh → Rồng");
    expect(text).toContain("Rồng Kraygath");
    expect(text).toContain("Rừng: Phản gank đường Rồng.");
  });
});
