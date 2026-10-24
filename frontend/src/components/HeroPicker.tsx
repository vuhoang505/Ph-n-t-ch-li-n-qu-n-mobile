import { memo, useMemo } from "react";
import { X } from "lucide-react";
import type { Hero, HeroEngineModule } from "../types";
import { HeroSearchSelect } from "./HeroSearchSelect";
import { HeroVisual } from "./HeroVisual";

function HeroPickerComponent({ heroes, selected, onChange, max = 5, label, module }: { heroes: Hero[]; selected: number[]; onChange: (ids: number[]) => void; max?: number; label: string; module?: HeroEngineModule }) {
  const chosen = useMemo(() => {
    const byId = new Map(heroes.map(hero => [hero.id, hero]));
    return selected.map(id => byId.get(id)).filter(Boolean) as Hero[];
  }, [heroes, selected]);
  return <div className="picker">
    <div className="picker-head"><b>{label}</b><span>{selected.length}/{max}</span></div>
    <div className="picked-list">
      {chosen.map(hero => <div className="picked" key={hero.id}><HeroVisual hero={hero} compact /><button type="button" onClick={() => onChange(selected.filter(id => id !== hero.id))} aria-label={`Bỏ ${hero.name}`}><X size={14} /></button></div>)}
      {selected.length < max && <HeroSearchSelect heroes={heroes} excludeIds={selected} onChange={(id) => { if (id && !selected.includes(id)) onChange([...selected, id]); }} placeholder="Thêm tướng..." inputLabel={`Thêm tướng vào ${label.toLocaleLowerCase("vi")}`} allowClear={false} module={module} />}
    </div>
  </div>;
}

export const HeroPicker = memo(HeroPickerComponent);
