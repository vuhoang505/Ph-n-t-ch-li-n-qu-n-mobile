import { CheckCircle2, Gem, Heart, History, ShieldCheck } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { HeroSearchSelect } from "../components/HeroSearchSelect";
import { HeroVisual } from "../components/HeroVisual";
import { Card, EmptyState, Select } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { get } from "../services/api";
import { useAppStore } from "../stores/useAppStore";

export function RunesPage() {
  const heroes = useHeroes().data?.items ?? [];
  const [heroId, setHeroId] = useState(0);
  const [position, setPosition] = useState("Rừng");
  const hero = heroes.find(item => item.id === heroId);
  type BuildSetup = { position: string; arcana: Record<string, { name: string }>; enchantments: { family?: string; entries?: { name: string }[] }; talent: string | null; explanation: string; data_status: string };
  const builds = useQuery<{ items: BuildSetup[] }>({
    queryKey: ["hero-builds", heroId],
    queryFn: () => get(`/heroes/${heroId}/builds`),
    enabled: heroId > 0,
    staleTime: 10 * 60_000,
  });
  const setup = builds.data?.items.find(item => item.position === position) ?? builds.data?.items[0];
  const arcana = setup ? Object.entries(setup.arcana).map(([color, row]) => `${color}: ${row.name}`).join(" · ") : "";
  const enchantments = setup ? [setup.enchantments.family, ...(setup.enchantments.entries?.map(item => item.name) ?? [])].filter(Boolean).join(" · ") : "";
  return <div className="page"><div className="page-intro"><div><span>LOADOUT LAB</span><h2>Ngọc, phù hiệu & phép bổ trợ</h2><p>Tạo cấu hình theo tướng và vị trí để chuẩn bị nhanh trước mỗi trận đấu.</p></div></div><div className="two-col"><Card className="form-card"><label>Chọn tướng<HeroSearchSelect heroes={heroes} value={heroId} onChange={setHeroId} module="build" /></label><label>Vị trí<Select value={position} onChange={event => setPosition(event.target.value)}>{["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"].map(item => <option key={item}>{item}</option>)}</Select></label></Card><Card>{builds.isLoading ? <p className="muted">Đang tải cấu hình…</p> : builds.isError ? <div className="error-banner">Không tải được dữ liệu ngọc và phù hiệu.</div> : hero && setup ? <div className="loadout"><HeroVisual hero={hero} /><div><Gem /><span><small>BẢNG NGỌC</small>{arcana || "Chưa đủ dữ liệu"}</span></div><div><ShieldCheck /><span><small>PHÙ HIỆU CHÍNH</small>{enchantments || "Chưa đủ dữ liệu"}</span></div><div><CheckCircle2 /><span><small>PHÉP BỔ TRỢ</small>{setup.talent ?? "Chưa đủ dữ liệu"}</span></div><p>Cấu hình được tối ưu theo vai trò và vị trí đã chọn.</p></div> : <EmptyState title="Chọn tướng để xem thiết lập" description="Gợi ý sẽ thay đổi theo vị trí bạn chọn." />}</Card></div></div>;
}

export function HistoryPage() {
  const { favoriteHeroIds } = useAppStore();
  const heroes = useHeroes().data?.items ?? [];
  const favorites = heroes.filter(hero => favoriteHeroIds.includes(hero.id));
  return <div className="page"><div className="page-intro"><div><span>LOCAL WORKSPACE</span><h2>Nội dung đã lưu trên thiết bị</h2><p>Không cần tài khoản. Tướng yêu thích được lưu cục bộ trong trình duyệt và không gửi lên máy chủ.</p></div></div><div className="two-col"><Card><div className="card-title"><span><Heart /> TƯỚNG YÊU THÍCH</span></div>{favorites.length ? <div className="lineup">{favorites.map(hero => <HeroVisual key={hero.id} hero={hero} compact />)}</div> : <EmptyState title="Chưa có tướng yêu thích" description="Nhấn biểu tượng trái tim tại kho tướng." />}</Card><Card><div className="card-title"><span><History /> QUYỀN RIÊNG TƯ</span></div><EmptyState title="Dữ liệu chỉ ở trình duyệt này" description="Không đăng nhập, không đồng bộ tài khoản và không thu thập lịch sử cá nhân." /></Card></div></div>;
}
