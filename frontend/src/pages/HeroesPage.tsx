import { Filter, RotateCcw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { HeroVisual } from "../components/HeroVisual";
import { Card, EmptyState, Input, Select, Skeleton } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { normalizeHeroSearch } from "../utils/hero";

const phaseLabel: Record<string, string> = { early: "Mạnh đầu trận", mid: "Mạnh giữa trận", late: "Mạnh cuối trận" };

export function HeroesPage() {
  const { data, isLoading, error } = useHeroes();
  const [search, setSearch] = useState(""); const [role, setRole] = useState(""); const [position, setPosition] = useState(""); const [damage, setDamage] = useState(""); const [difficulty, setDifficulty] = useState(""); const [sort, setSort] = useState("name");
  const filtered = useMemo(() => {
    const needle = normalizeHeroSearch(search);
    return (data?.items ?? []).filter(hero => {
      const searchable = [hero.name, hero.slug, ...hero.aliases].map(normalizeHeroSearch);
      return (!needle || searchable.some(value => value.includes(needle)))
        && (!role || hero.roles.includes(role))
        && (!position || hero.positions.includes(position))
        && (!damage || hero.damage_type === damage)
        && (!difficulty || (difficulty === "rated" ? hero.difficulty > 0 : hero.difficulty === 0));
    }).sort((left, right) => {
      if (sort === "confidence") return right.data_confidence - left.data_confidence;
      if (sort === "difficulty") return right.difficulty - left.difficulty;
      if (sort === "mobility") return (right.attributes.mobility ?? -1) - (left.attributes.mobility ?? -1);
      return left.name.localeCompare(right.name, "vi");
    });
  }, [data, search, role, position, damage, difficulty, sort]);
  const reset = () => { setSearch(""); setRole(""); setPosition(""); setDamage(""); setDifficulty(""); setSort("name"); };
  return <div className="page">
    <div className="page-intro"><div><span>KHO DỮ LIỆU CHIẾN THUẬT</span><h2>Danh sách 129 tướng</h2><p>Tìm không dấu, theo tên, biệt danh, vai trò, vị trí và trạng thái đánh giá.</p></div><div className="count-chip">{filtered.length} / {data?.total ?? 0} tướng</div></div>
    <Card className="filter-bar"><label><Search size={17} /><Input value={search} onChange={event => setSearch(event.target.value)} placeholder="Ví dụ: dieu thuyen, nak, van..." /></label><Select value={role} onChange={event => setRole(event.target.value)}><option value="">Tất cả vai trò</option>{["Đỡ đòn", "Đấu sĩ", "Sát thủ", "Pháp sư", "Xạ thủ", "Trợ thủ"].map(item => <option key={item}>{item}</option>)}</Select><Select value={position} onChange={event => setPosition(event.target.value)}><option value="">Tất cả vị trí</option>{["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"].map(item => <option key={item}>{item}</option>)}</Select><Select value={damage} onChange={event => setDamage(event.target.value)}><option value="">Mọi loại sát thương</option><option value="physical">Vật lý</option><option value="magic">Phép</option><option value="mixed">Hỗn hợp</option><option value="true">Chuẩn</option></Select><Select value={difficulty} onChange={event => setDifficulty(event.target.value)}><option value="">Mọi trạng thái</option><option value="rated">Đã có độ khó</option><option value="unrated">Chưa có độ khó</option></Select><Select value={sort} onChange={event => setSort(event.target.value)}><option value="name">Tên A–Z</option><option value="confidence">Độ tin cậy</option><option value="difficulty">Độ khó</option><option value="mobility">Cơ động</option></Select><button className="filter-reset" type="button" onClick={reset} aria-label="Xóa tất cả bộ lọc"><RotateCcw size={16} /></button><Filter size={18} /></Card>
    {error && <div className="error-banner">{error.message}</div>}
    {isLoading ? <div className="hero-grid">{Array.from({ length: 10 }).map((_, index) => <Skeleton key={index} className="hero-skeleton" />)}</div> : filtered.length ? <div className="hero-grid">{filtered.map(hero => <Link to={`/heroes/${hero.id}`} key={hero.id}><Card className="hero-card"><HeroVisual hero={hero} />{hero.attributes.mobility != null || hero.attributes.crowd_control != null ? <div className="mini-stats"><span><i style={{ width: `${hero.attributes.mobility ?? 0}%` }} />Cơ động {hero.attributes.mobility ?? "—"}</span><span><i style={{ width: `${hero.attributes.crowd_control ?? 0}%` }} />Khống chế {hero.attributes.crowd_control ?? "—"}</span></div> : <div className="profile-pending">Đã có kỹ năng từ hồ sơ chính thức<br />Mở chi tiết để xem điểm giai đoạn</div>}<div className="hero-card-footer"><span>Độ khó {hero.difficulty}/10</span><span>{phaseLabel[hero.power_phase] ?? "Đang phân tích giai đoạn"}</span></div></Card></Link>)}</div> : <EmptyState title="Không tìm thấy tướng" description="Hãy đổi từ khóa hoặc bộ lọc." />}
  </div>;
}
