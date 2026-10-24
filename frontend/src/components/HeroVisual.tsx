import { Heart } from "lucide-react";
import { useState } from "react";
import type { Hero } from "../types";
import { useAppStore } from "../stores/useAppStore";
import { heroInitials } from "../utils/hero";
import { Badge } from "./ui";

export function HeroVisual({ hero, compact = false }: { hero: Hero; compact?: boolean }) {
  const { favoriteHeroIds, toggleFavorite } = useAppStore();
  const [imageFailed, setImageFailed] = useState(false);
  const partial = !["complete", "tactical_profile"].includes(hero.profile_status);
  return <div className={`hero-visual ${compact ? "compact" : ""}`}>
    {hero.image_url && !imageFailed
      ? <img className="hero-portrait" src={hero.image_url} alt={hero.name} loading="lazy" onError={() => setImageFailed(true)} />
      : <div className="hero-monogram" aria-hidden="true">{heroInitials(hero.name)}</div>}
    <div className="hero-copy">
      <strong>{hero.name}</strong>
      <span>{hero.roles.join(" • ")}</span>
      {!compact && <div className="badge-row">{partial && <Badge className="pending">Phân tích một phần</Badge>}{hero.positions.map(position => <Badge key={position}>{position}</Badge>)}</div>}
    </div>
    {!compact && <button className="icon-button" onClick={(event) => { event.preventDefault(); toggleFavorite(hero.id); }} aria-label="Yêu thích"><Heart size={17} fill={favoriteHeroIds.includes(hero.id) ? "currentColor" : "none"} /></button>}
  </div>;
}
