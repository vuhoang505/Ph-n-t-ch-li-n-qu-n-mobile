import type { HeroEngineModule, HeroReadiness } from "../types";

export function heroInitials(name: string): string {
  return name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
}

export function normalizeHeroSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .trim();
}

export function isEngineReady(hero: { difficulty: number; engine_ready?: boolean }): boolean {
  return hero.engine_ready ?? hero.difficulty > 0;
}

export function heroDataStatus(hero: { profile_status: string; difficulty: number; engine_ready?: boolean }): string {
  if (hero.engine_ready === true) return "Sẵn sàng phân tích";
  if (hero.engine_ready === false) return "Chưa đủ dữ liệu engine";
  if (["complete", "tactical_profile"].includes(hero.profile_status) || hero.difficulty > 0) return "Hồ sơ chiến thuật";
  return "Dữ liệu phân tích một phần";
}

export function heroModuleReady(hero: { readiness?: HeroReadiness }, module?: HeroEngineModule): boolean | undefined {
  return module ? hero.readiness?.modules?.[module] : undefined;
}

export function heroModuleStatus(hero: { profile_status: string; difficulty: number; engine_ready?: boolean; readiness?: HeroReadiness }, module?: HeroEngineModule): string {
  const ready = heroModuleReady(hero, module);
  if (ready === true) return "Sẵn sàng cho chức năng này";
  if (ready === false) return "Chưa đủ dữ liệu cho chức năng này";
  return heroDataStatus(hero);
}

