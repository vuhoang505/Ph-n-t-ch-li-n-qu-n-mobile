import { ArrowLeft, BookOpen, Gauge, PackageOpen, ShieldCheck, Sparkles, Swords, UsersRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { HeroSearchSelect } from "../components/HeroSearchSelect";
import { HeroVisual } from "../components/HeroVisual";
import { ScoreRadar } from "../components/ScoreRadar";
import { Card, EmptyState, Skeleton } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { api } from "../services/api";
import type { HeroAnalysisDetail } from "../types";

const STAT_LABELS: Record<string, string> = {
  damage: "Sát thương", durability: "Chống chịu", mobility: "Cơ động",
  crowd_control: "Khống chế", sustain: "Hồi phục", burst: "Dồn sát thương",
  teamfight: "Giao tranh tổng", split_push: "Đẩy lẻ", pickoff: "Bắt lẻ",
  protection: "Bảo vệ", objective_control: "Kiểm soát mục tiêu",
  early_game: "Đầu trận", mid_game: "Giữa trận", late_game: "Cuối trận", difficulty: "Độ khó",
};

const DAMAGE_LABELS: Record<string, string> = { physical: "Vật lý", magic: "Phép", mixed: "Hỗn hợp", true: "Sát thương chuẩn" };
const RANGE_LABELS: Record<string, string> = { melee: "Cận chiến", ranged: "Đánh xa", hybrid: "Linh hoạt" };
const PHASE_LABELS: Record<string, string> = { early: "Đầu trận", mid: "Giữa trận", late: "Cuối trận" };

export function HeroDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const heroes = useHeroes().data?.items ?? [];
  const query = useQuery({ queryKey: ["hero-analysis", id], queryFn: () => api<HeroAnalysisDetail>(`/heroes/${id}/analysis`) });
  type RelatedData = {
    counters: { counters: { hero: HeroAnalysisDetail["hero"]; algorithmic_score: number; confidence: number; reasons: string[]; conditions: string[] }[] };
    synergies: { items: { partner_id: number; score: number; confidence: number; reason: string }[] };
    builds: { items: { position: string; items: { id: number; name: string; image_url: string | null; category: string }[]; talent: string | null; explanation: string; confidence: number }[] };
  };
  const related = useQuery({ queryKey: ["hero-related", id], queryFn: async (): Promise<RelatedData> => {
    const [counters, synergies, builds] = await Promise.all([
      api<RelatedData["counters"]>(`/heroes/${id}/counters`),
      api<RelatedData["synergies"]>(`/heroes/${id}/synergies`),
      api<RelatedData["builds"]>(`/heroes/${id}/builds`),
    ]);
    return { counters, synergies, builds };
  }});
  if (query.isLoading) return <div className="page"><Skeleton className="detail-skeleton" /></div>;
  if (query.error || !query.data) return <div className="page"><div className="error-banner">{query.error?.message ?? "Không tìm thấy tướng"}</div></div>;
  const { hero, analysis, ratings, tier, skills, skill_priority: priority, combos, base_stats: baseStats, gameplay_tips: gameplayTips, strengths, weaknesses, power_spikes: spikes } = query.data;
  const radar = ratings ? Object.fromEntries(Object.entries(ratings.scores).filter(([key, value]) => value !== null && !["early_game", "mid_game", "late_game", "difficulty"].includes(key))) : {};
  return <div className="page">
    <div className="detail-toolbar"><Link className="back-link" to="/heroes"><ArrowLeft size={16} /> Trở lại kho tướng</Link><HeroSearchSelect heroes={heroes} value={hero.id} onChange={heroId => heroId && navigate(`/heroes/${heroId}`)} placeholder="Chuyển sang tướng khác..." /></div>
    <Card className="detail-hero"><HeroVisual hero={hero} />{tier && <div className={`hero-tier tier-${tier.tier.toLowerCase()}`}><small>{tier.label}</small><b>{tier.tier}</b><span>{tier.score}/100</span></div>}<div className="detail-score"><Gauge /><span><b>{ratings?.scores.difficulty != null ? `${ratings.scores.difficulty}/100` : "—"}</b><small>ĐỘ KHÓ · {Math.round((ratings?.confidence ?? 0) * 100)}% TIN CẬY</small></span></div></Card>
    <Card className="hero-profile-facts">
      <div><small>VAI TRÒ</small><b>{hero.roles.join(" / ") || "Đang cập nhật"}</b></div>
      <div><small>VỊ TRÍ</small><b>{hero.positions.join(" / ") || "Đang cập nhật"}</b></div>
      <div><small>SÁT THƯƠNG</small><b>{DAMAGE_LABELS[analysis?.damage_type ?? ""] ?? analysis?.damage_type ?? "Đang cập nhật"}</b></div>
      <div><small>TẦM ĐÁNH</small><b>{RANGE_LABELS[analysis?.range_type ?? ""] ?? analysis?.range_type ?? "Đang cập nhật"}</b></div>
      <div><small>MẠNH NHẤT</small><b>{PHASE_LABELS[hero.power_phase] ?? hero.power_phase}</b></div>
      <div><small>ĐỘ KHÓ</small><b>{hero.difficulty}/10</b></div>
    </Card>
    {!!analysis?.special_mechanics?.length && <Card className="hero-mechanics"><div className="card-title"><span><Sparkles /> CƠ CHẾ NỔI BẬT</span></div><div>{analysis.special_mechanics.slice(0, 8).map(item => <span key={item}>{item}</span>)}</div></Card>}
    <div className="detail-grid detail-grid-radar"><Card className="ability-map-card"><div className="card-title ability-map-title"><span><ShieldCheck /> BẢN ĐỒ NĂNG LỰC</span><small>Điểm thuật toán 0–100 · kỹ năng + vai trò chính thức</small></div>{Object.keys(radar).length >= 3 ? <ScoreRadar scores={radar} /> : <EmptyState title="Chưa đủ dữ liệu để vẽ biểu đồ" description="Hồ sơ đang chờ đồng bộ lại dữ liệu chiến thuật." />}</Card><div className="stack">
      <Card><h3>Điểm mạnh có bằng chứng</h3>{strengths.length ? <ul className="evidence-list">{strengths.slice(0, 6).map(item => <li key={item.title}><b>{item.title}</b><span>{item.explanation}</span><small>{Math.round(item.confidence * 100)}% · {item.provenance}</small></li>)}</ul> : <p className="muted">Chưa có thuộc tính vượt ngưỡng bằng chứng.</p>}</Card>
      <Card><h3>Điểm cần lưu ý</h3>{weaknesses.length ? <ul className="evidence-list risk">{weaknesses.map(item => <li key={item.title}><b>{item.title}</b><span>{item.explanation}</span></li>)}</ul> : <p className="muted">Chưa có điểm yếu đủ căn cứ; cần quản trị viên phân tích.</p>}</Card>
    </div></div>
    <div className="detail-sections">
      {ratings && <Card><div className="card-title"><span><Gauge /> THÔNG SỐ CHIẾN THUẬT ĐẦY ĐỦ</span><small>15 chỉ số · thang 0–100</small></div><div className="hero-stat-grid">{Object.entries(ratings.scores).map(([key,value]) => <div key={key}><span>{STAT_LABELS[key] ?? key}</span><b>{value == null ? "—" : Math.round(value)}</b><i><em style={{ width: `${value ?? 0}%` }} /></i></div>)}</div></Card>}
      <div className="hero-related-grid">
        <Card><div className="card-title"><span><Swords /> CÁCH KHẮC CHẾ TƯỚNG NÀY</span></div><div className="related-list counter-guides">{related.data?.counters.counters.slice(0, 3).map(row => <Link to={`/heroes/${row.hero.id}`} key={row.hero.id}><b>{row.hero.name}<em>{row.algorithmic_score} điểm</em></b><span>{row.reasons[0] ?? "Có bộ chỉ số phù hợp để đối đầu."}</span><small>{row.conditions[0] ?? "Hiệu quả phụ thuộc thời điểm kỹ năng và tài nguyên."}</small></Link>) ?? <p className="muted">Đang tải dữ liệu đối đầu…</p>}</div></Card>
        <Card><div className="card-title"><span><UsersRound /> ĐỒNG ĐỘI PHÙ HỢP</span></div><div className="related-list">{related.data?.synergies.items.slice(0, 3).map(row => { const partner = heroes.find(item => item.id === row.partner_id); return <Link to={`/heroes/${row.partner_id}`} key={row.partner_id}><b>{partner?.name ?? `Tướng #${row.partner_id}`}</b><span>{row.reason} · {row.score} điểm</span></Link>; }) ?? <p className="muted">Đang tải dữ liệu phối hợp…</p>}</div></Card>
      </div>
      <Card><div className="card-title"><span><PackageOpen /> BUILD THEO VỊ TRÍ</span></div><div className="hero-builds">{related.data?.builds.items.map(build => <article key={build.position}><header><b>{build.position}</b><span>{build.talent ?? "Chưa có phép bổ trợ"}</span></header><div>{build.items.map(item => <span key={item.id}>{item.image_url && <img src={item.image_url} alt="" />}<em>{item.name}</em></span>)}</div><p>{build.explanation}</p></article>) ?? <p className="muted">Đang tải bộ trang bị…</p>}</div></Card>
      <div className="hero-playbook-grid">
        <Card className="skill-priority-card"><div className="card-title"><span><Gauge /> THỨ TỰ NÂNG CHIÊU</span>{priority.primary && <strong>{priority.primary.label}</strong>}</div><p>{priority.advice}</p><div className="skill-level-timeline">{priority.levels.map(row => <div key={row.level} title={`${row.skill_name} · bậc ${row.rank}`}><small>{row.level}</small><b>{row.skill_order}</b><span>{row.skill_name}</span></div>)}</div></Card>
        <Card><div className="card-title"><span><Swords /> COMBO KỸ NĂNG</span></div><div className="combo-list">{combos.map(combo => <article key={combo.name}><h3>{combo.name}</h3><div>{combo.steps.map((step, index) => <span key={`${step.label}-${index}`}><b className={step.type}>{step.type === "attack" ? "AA" : step.order}</b><em>{step.label}</em>{index < combo.steps.length - 1 && <i>➜</i>}</span>)}</div><p>{combo.tip}</p></article>)}</div></Card>
      </div>
      <div className="hero-playbook-grid">
        <Card><div className="card-title"><span><ShieldCheck /> CHỈ SỐ GỐC CẤP 1–15</span><small>{baseStats.label}</small></div><div className="base-stat-table"><header><span>Thuộc tính</span><b>Cấp 1</b><b>Cấp 15</b></header>{baseStats.rows.map(row => <div key={row.key}><span>{row.label}</span><b>{row.level_1.toLocaleString("vi-VN")}{row.unit}</b><strong>{row.level_15.toLocaleString("vi-VN")}{row.unit}</strong></div>)}</div></Card>
        <Card><div className="card-title"><span><Sparkles /> MẸO TÁC CHIẾN THEO GIAI ĐOẠN</span></div><div className="gameplay-tip-list">{gameplayTips.map(tip => <article key={tip.phase}><span>{tip.title}<b>{tip.score ?? "—"}</b></span><p>{tip.advice}</p></article>)}</div></Card>
      </div>
      <Card><div className="card-title"><span><BookOpen /> KỸ NĂNG CHÍNH THỨC</span><small>{skills.length} kỹ năng</small></div><div className="skill-list">{skills.map(skill => <article key={skill.id}><span>{skill.order + 1}</span><div><h3>{skill.name}</h3><small>{skill.type}</small><p>{skill.description}</p></div></article>)}</div></Card>
      <Card><div className="card-title"><span><Sparkles /> GIAI ĐOẠN SỨC MẠNH</span></div><div className="phase-grid">{spikes.map(spike => <div key={spike.phase}><b>{spike.phase === "early" ? "Đầu trận" : spike.phase === "mid" ? "Giữa trận" : "Cuối trận"}</b><strong>{spike.score ?? "—"}</strong><span>{spike.analysis.explanation ?? "Chưa đủ dữ liệu."}</span></div>)}</div></Card>
    </div>
  </div>;
}
