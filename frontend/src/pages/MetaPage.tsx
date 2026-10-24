import { ChevronLeft, ChevronRight, Search, Trophy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card, EmptyState, Input, Select, Skeleton } from "../components/ui";
import { api } from "../services/api";

type MetaItem = {
  hero: { id: number; name: string; slug: string; image_url: string | null; roles: string[] };
  source_rank: number | null; picks: number; wins: number; losses: number; win_rate: number | null;
  pick_rate: number; bans: number; ban_rate: number; presence: number; meta_score: number;
  sample_games: number; played: boolean;
};
type MetaResponse = {
  status: string; message: string; items: MetaItem[]; policy: string;
  tournament?: string; stage?: string; sample_games?: number; captured_at?: string;
  total_heroes?: number; heroes_with_matches?: number; heroes_without_matches?: number;
};

const PAGE_SIZE = 10;
const normalizeText = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase();

export function MetaPage() {
  const query = useQuery({ queryKey: ["meta"], queryFn: () => api<MetaResponse>("/meta/heroes") });
  const [role, setRole] = useState("");
  const [sort, setSort] = useState<"meta_score" | "presence" | "win_rate">("meta_score");
  const [status, setStatus] = useState<"all" | "played" | "unplayed">("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [role, sort, status, search]);

  const items = useMemo(() => [...(query.data?.items ?? [])]
    .filter(item => !role || item.hero.roles.includes(role))
    .filter(item => status === "all" || (status === "played" ? item.played : !item.played))
    .filter(item => !search.trim() || normalizeText(item.hero.name).includes(normalizeText(search.trim())))
    .sort((left, right) => (right[sort] ?? -1) - (left[sort] ?? -1) || left.hero.name.localeCompare(right.hero.name, "vi")), [query.data, role, sort, status, search]);
  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const visible = items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return <div className="page">
    <div className="page-intro"><div><span>TOURNAMENT MATCH DATA</span><h2>Meta Analytics</h2><p>Xếp hạng đủ 129 tướng. Mỗi trang hiển thị 10 tướng; tướng chưa xuất hiện được tách riêng để bạn lọc nhanh.</p></div></div>
    <Card className="meta-filter-bar">
      <label><Search size={16} /><Input value={search} onChange={event => setSearch(event.target.value)} placeholder="Tìm tướng trong bảng meta..." /></label>
      <Select value={sort} onChange={event => setSort(event.target.value as typeof sort)}><option value="meta_score">Điểm meta</option><option value="presence">Mức hiện diện</option><option value="win_rate">Tỷ lệ thắng</option></Select>
      <Select value={role} onChange={event => setRole(event.target.value)}><option value="">Tất cả vai trò</option>{["Đỡ đòn", "Đấu sĩ", "Sát thủ", "Pháp sư", "Xạ thủ", "Trợ thủ"].map(item => <option key={item}>{item}</option>)}</Select>
      <Select value={status} onChange={event => setStatus(event.target.value as typeof status)}><option value="all">Toàn bộ 129 tướng</option><option value="played">Có dữ liệu trận</option><option value="unplayed">Chưa xuất hiện</option></Select>
    </Card>
    {query.isLoading ? <Skeleton className="meta-skeleton" /> : query.data?.status === "unavailable" ? <Card className="meta-empty"><EmptyState title="Chưa có dữ liệu trận đấu" description={query.data.message} /></Card> : <>
      <Card className="meta-source-card meta-overview"><Trophy /><div><b>TOURNAMENT PULSE</b><span>{query.data?.sample_games} ván đã phân tích · {query.data?.heroes_with_matches} tướng đã xuất hiện · {query.data?.heroes_without_matches} tướng đang chờ dữ liệu</span></div></Card>
      <div className="meta-page-summary"><span>Đang hiển thị <b>{items.length ? (page - 1) * PAGE_SIZE + 1 : 0}–{Math.min(page * PAGE_SIZE, items.length)}</b> trong {items.length} tướng</span><span>Trang <b>{page}/{totalPages}</b></span></div>
      <div className="meta-ranking">{visible.map((item, index) => <Link to={`/heroes/${item.hero.id}`} key={item.hero.id}><Card className={`meta-row ${item.played ? "" : "no-match"}`}>
        <strong>#{(page - 1) * PAGE_SIZE + index + 1}</strong>{item.hero.image_url ? <img src={item.hero.image_url} alt={item.hero.name} /> : <div className="meta-avatar">{item.hero.name.slice(0, 1)}</div>}
        <div className="meta-hero"><b>{item.hero.name}</b><span>{item.played ? item.hero.roles.join(" · ") : "Chưa xuất hiện tại APL 2026"}</span><i><em style={{ width: `${item.meta_score}%` }} /></i></div>
        <div><small>ĐIỂM META</small><b>{item.played ? item.meta_score : "—"}</b></div><div><small>THẮNG</small><b>{item.win_rate == null ? "—" : `${item.win_rate}%`}</b><span>{item.played ? `${item.wins}–${item.losses}` : "Chưa có trận"}</span></div><div><small>CHỌN</small><b>{item.picks}</b><span>{item.pick_rate}%</span></div><div><small>CẤM</small><b>{item.bans}</b><span>{item.ban_rate}%</span></div><div><small>HIỆN DIỆN</small><b>{item.presence}%</b></div>
      </Card></Link>)}</div>
      {items.length > 0 && <nav className="pagination" aria-label="Phân trang Meta Analytics"><button onClick={() => setPage(current => Math.max(1, current - 1))} disabled={page === 1} aria-label="Trang trước"><ChevronLeft /></button>{Array.from({ length: totalPages }, (_, index) => index + 1).map(number => <button key={number} className={number === page ? "active" : ""} onClick={() => setPage(number)}>{number}</button>)}<button onClick={() => setPage(current => Math.min(totalPages, current + 1))} disabled={page === totalPages} aria-label="Trang sau"><ChevronRight /></button></nav>}
    </>}
  </div>;
}
