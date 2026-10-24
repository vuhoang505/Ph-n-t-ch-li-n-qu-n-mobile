// @vitest-environment jsdom
import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { Hero } from "../types";
import { HeroSearchSelect } from "./HeroSearchSelect";

const attributes = {
  physical_damage: 50, magic_damage: 0, durability: 40, crowd_control: 20,
  mobility: 60, engage: 40, protection: 10, split_push: 30,
  wave_clear: 50, objective_control: 30,
};

const heroes: Hero[] = [
  {
    id: 1, slug: "alice", name: "Alice", image_url: null, damage_type: "magic",
    positions: ["Trợ thủ"], power_phase: "mid", difficulty: 4, strengths: [], weaknesses: [],
    patch_version: "test", roles: ["Trợ thủ"], attributes, profile_status: "complete",
    aliases: ["ali"], data_confidence: 1, engine_ready: true,
    readiness: { modules: { counter: true, build: true } },
  },
  {
    id: 2, slug: "dieu-thuyen", name: "Điêu Thuyền", image_url: null, damage_type: "magic",
    positions: ["Giữa"], power_phase: "mid", difficulty: 0, strengths: [], weaknesses: [],
    patch_version: "test", roles: ["Pháp sư"], attributes, profile_status: "official_partial_analysis",
    aliases: ["dieu"], data_confidence: .7,
    readiness: { modules: { counter: true, build: false } },
  },
];

describe("HeroSearchSelect", () => {
  let host: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  it("xóa từ khóa sau khi chọn nhưng vẫn hiển thị tướng đã chọn riêng", async () => {
    function Harness() {
      const [value, setValue] = useState(0);
      return <HeroSearchSelect heroes={heroes} value={value} onChange={setValue} />;
    }

    await act(async () => root.render(<Harness />));
    const input = host.querySelector("input") as HTMLInputElement;
    await act(async () => {
      input.focus();
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      setter?.call(input, "ali");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const alice = Array.from(host.querySelectorAll<HTMLButtonElement>('[role="option"]')).find(option => option.textContent?.includes("Alice"));
    expect(alice).toBeTruthy();
    await act(async () => alice?.click());

    expect(input.value).toBe("");
    expect(host.querySelector(".hero-search-selected")?.textContent).toContain("Alice");
    expect(input.placeholder).toBe("Tìm để đổi tướng...");
  });

  it("hiển thị đủ lựa chọn nhưng khóa đúng module backend đánh dấu thiếu dữ liệu", async () => {
    await act(async () => root.render(<HeroSearchSelect heroes={heroes} onChange={() => undefined} module="build" />));
    const input = host.querySelector("input") as HTMLInputElement;
    await act(async () => input.focus());
    const options = Array.from(host.querySelectorAll<HTMLButtonElement>('[role="option"]'));
    const alice = options.find(option => option.textContent?.includes("Alice"));
    const dieuThuyen = options.find(option => option.textContent?.includes("Điêu Thuyền"));

    expect(alice?.disabled).toBe(false);
    expect(dieuThuyen?.disabled).toBe(true);
    expect(dieuThuyen?.textContent).toContain("Chưa đủ dữ liệu");
  });

  it("hỗ trợ chọn bằng bàn phím", async () => {
    function Harness() {
      const [value, setValue] = useState(0);
      return <HeroSearchSelect heroes={heroes} value={value} onChange={setValue} module="counter" />;
    }

    await act(async () => root.render(<Harness />));
    const input = host.querySelector("input") as HTMLInputElement;
    await act(async () => input.focus());
    await act(async () => {
      input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });

    expect(input.value).toBe("");
    expect(host.querySelector(".hero-search-selected")?.textContent).toContain("Alice");
  });
});
