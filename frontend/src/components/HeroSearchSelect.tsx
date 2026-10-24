import { Search, X } from "lucide-react";
import { memo, useDeferredValue, useEffect, useId, useMemo, useRef, useState } from "react";
import type { Hero, HeroEngineModule } from "../types";
import { heroModuleReady, heroModuleStatus, normalizeHeroSearch } from "../utils/hero";
import { HeroVisual } from "./HeroVisual";

type Props = {
  heroes: Hero[];
  value?: number;
  onChange: (heroId: number) => void;
  placeholder?: string;
  excludeIds?: number[];
  allowClear?: boolean;
  inputLabel?: string;
  module?: HeroEngineModule;
};

const EMPTY_IDS: number[] = [];

function HeroSearchSelectComponent({ heroes, value = 0, onChange, placeholder = "Tìm tướng theo tên hoặc biệt danh...", excludeIds = EMPTY_IDS, allowClear = true, inputLabel = "Tìm tướng", module }: Props) {
  const selected = useMemo(() => heroes.find(hero => hero.id === value), [heroes, value]);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  const matches = useMemo(() => {
    const needle = normalizeHeroSearch(deferredQuery);
    const excluded = new Set(excludeIds);
    return heroes
      .filter(hero => !excluded.has(hero.id) && hero.id !== value)
      .filter(hero => !needle || [hero.name, hero.slug, ...hero.aliases].some(item => normalizeHeroSearch(item).includes(needle)))
      .sort((left, right) => {
        if (!needle) return left.name.localeCompare(right.name, "vi");
        const leftName = normalizeHeroSearch(left.name);
        const rightName = normalizeHeroSearch(right.name);
        const leftRank = leftName === needle ? 0 : leftName.startsWith(needle) ? 1 : 2;
        const rightRank = rightName === needle ? 0 : rightName.startsWith(needle) ? 1 : 2;
        return leftRank - rightRank || left.name.localeCompare(right.name, "vi");
      })
      .slice(0, 12);
  }, [deferredQuery, excludeIds, heroes, value]);

  const firstAvailable = useMemo(() => {
    const index = matches.findIndex(hero => heroModuleReady(hero, module) !== false);
    return Math.max(index, 0);
  }, [matches, module]);
  const lastAvailable = useMemo(() => {
    for (let index = matches.length - 1; index >= 0; index -= 1) {
      if (heroModuleReady(matches[index], module) !== false) return index;
    }
    return 0;
  }, [matches, module]);

  useEffect(() => {
    setActive(current => matches[current] && heroModuleReady(matches[current], module) !== false ? current : firstAvailable);
  }, [firstAvailable, matches, module]);

  useEffect(() => {
    if (!open || !matches[active]) return;
    document.getElementById(`${listId}-option-${matches[active].id}`)?.scrollIntoView?.({ block: "nearest" });
  }, [active, listId, matches, open]);

  const moveActive = (direction: 1 | -1) => {
    if (!matches.length) return;
    setActive(current => {
      let next = current;
      for (let attempt = 0; attempt < matches.length; attempt += 1) {
        next = (next + direction + matches.length) % matches.length;
        if (heroModuleReady(matches[next], module) !== false) return next;
      }
      return current;
    });
  };

  const choose = (hero: Hero) => {
    if (heroModuleReady(hero, module) === false) return;
    onChange(hero.id);
    setQuery("");
    setOpen(false);
    setActive(0);
  };

  return <div className={`hero-search-select${selected ? " has-selection" : ""}`} ref={rootRef}>
    {selected && <div className="hero-search-selected" aria-live="polite">
      <HeroVisual hero={selected} compact />
      <span>{heroModuleStatus(selected, module)}</span>
      {allowClear && <button type="button" aria-label={`Bỏ chọn ${selected.name}`} onClick={() => { onChange(0); setQuery(""); setOpen(false); inputRef.current?.focus(); }}><X size={14} /></button>}
    </div>}
    <div className="hero-search-input">
      <Search size={16} aria-hidden="true" />
      <input
        ref={inputRef}
        className="input"
        value={query}
        placeholder={selected ? "Tìm để đổi tướng..." : placeholder}
        role="combobox"
        aria-label={inputLabel}
        aria-expanded={open}
        aria-autocomplete="list"
        aria-controls={listId}
        aria-activedescendant={open && matches[active] ? `${listId}-option-${matches[active].id}` : undefined}
        onFocus={() => setOpen(true)}
        onChange={event => { setQuery(event.target.value); setOpen(true); setActive(0); }}
        onKeyDown={event => {
          if (event.key === "ArrowDown") { event.preventDefault(); if (!open) { setOpen(true); setActive(firstAvailable); } else moveActive(1); }
          if (event.key === "ArrowUp") { event.preventDefault(); if (!open) { setOpen(true); setActive(lastAvailable); } else moveActive(-1); }
          if (event.key === "Home" && open) { event.preventDefault(); setActive(firstAvailable); }
          if (event.key === "End" && open) { event.preventDefault(); setActive(lastAvailable); }
          if (event.key === "Enter" && open && matches[active]) { event.preventDefault(); choose(matches[active]); }
          if (event.key === "Escape") { setOpen(false); setQuery(""); }
          if (event.key === "Tab") setOpen(false);
        }}
      />
      {query && <button className="hero-search-clear" type="button" aria-label="Xóa từ khóa" onClick={() => { setQuery(""); setActive(0); inputRef.current?.focus(); }}><X size={14} /></button>}
    </div>
    {open && <div className="hero-search-menu" id={listId} role="listbox">
      {matches.length ? matches.map((hero, index) => {
        const unavailable = heroModuleReady(hero, module) === false;
        return <button id={`${listId}-option-${hero.id}`} key={hero.id} type="button" role="option" aria-selected={false} aria-disabled={unavailable} disabled={unavailable} className={`${index === active ? "active" : ""}${unavailable ? " unavailable" : ""}`} onMouseEnter={() => setActive(index)} onClick={() => choose(hero)}>
          <HeroVisual hero={hero} compact /><span className="hero-search-option-meta"><small>{hero.positions.join(" • ") || "Chưa xác định vị trí"}</small><em>{heroModuleStatus(hero, module)}</em></span>
        </button>;
      }) : <div className="hero-search-empty" role="status">Không tìm thấy tướng phù hợp.</div>}
    </div>}
  </div>;
}

export const HeroSearchSelect = memo(HeroSearchSelectComponent);
