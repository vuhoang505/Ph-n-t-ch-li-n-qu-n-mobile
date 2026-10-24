import { ArrowLeftRight, Clock3, Eye, Shield, Sparkles, Swords, Zap } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { HeroSearchSelect } from "../components/HeroSearchSelect";
import { HeroVisual } from "../components/HeroVisual";
import { Button, Card, EmptyState, Select } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { post } from "../services/api";
import type { Hero } from "../types";

type CounterResult = {
  hero: Hero;
  opponent: Hero;
  hero_advantage: number;
  opponent_advantage: number;
  hero_reasons?: string[];
  opponent_reasons?: string[];
  confidence?: number;
  position?: string | null;
  conditions: string[];
};

const SOLO_DODGE_TIPS: Record<string, string> = {
  florentino: "Né Chiêu 1 ném hoa theo phương ngang; không bước vào ba đóa hoa khi chưa thấy Florentino dùng lướt.",
  omen: "Giữ kỹ năng thoát thân cho Sát Vực; lùi lại khi Omen tích đủ nội tại và chuẩn bị kéo bằng Chiêu 2.",
  hayate: "Tách khỏi đợt lính để giảm góc phi tiêu xuyên mục tiêu; giữ khống chế cho thời điểm Hayate mở Bão Phi Tiêu.",
  violet: "Đứng chéo với lính và ép Violet dùng Đạn Xuyên Thấu để farm trước khi bước lên trao đổi.",
};

export function CounterPage() {
  const heroes = useHeroes().data?.items ?? [];
  const [a, setA] = useState(0);
  const [b, setB] = useState(0);
  const [lane, setLane] = useState("");
  const [mode, setMode] = useState<"counter" | "solo">("counter");
  const laneHeroes = useMemo(() => lane ? heroes.filter(hero => hero.positions.includes(lane)) : heroes, [heroes, lane]);
  useEffect(() => {
    if (a && !laneHeroes.some(hero => hero.id === a)) setA(0);
    if (b && !laneHeroes.some(hero => hero.id === b)) setB(0);
  }, [a, b, laneHeroes]);
  const mutation = useMutation({ mutationFn: () => post<CounterResult>("/counter/analyze", { hero_id: a, opponent_id: b, position: lane || null }) });
  const heroA = heroes.find(hero => hero.id === a);
  const heroB = heroes.find(hero => hero.id === b);
  const soloLane = lane === "Rồng" ? "Đường Rồng" : "Đường Tà Thần";
  const spikeLevel = heroA?.power_phase.includes("đầu") ? "Cấp 2–4" : heroA?.power_phase.includes("cuối") ? "Cấp 12+" : "Cấp 4–8";
  const dodgeTip = heroB ? SOLO_DODGE_TIPS[heroB.name.toLocaleLowerCase("vi")] ?? heroB.weaknesses[0] ?? `Giữ khoảng cách ngoài vùng khống chế chủ lực của ${heroB.name}.` : "";
  return <div className="page">
    <div className="page-intro"><div><span>COUNTER ENGINE</span><h2>Đối đầu hai chiều</h2><p>Tìm trong đủ 129 tướng. Điểm chỉ được trả về khi hai hồ sơ có ít nhất ba cặp thuộc tính chung có bằng chứng.</p></div></div>
    <div className="counter-mode-tabs"><button type="button" className={mode === "counter" ? "active" : ""} onClick={() => setMode("counter")}><Shield /> Phân tích đối kháng</button><button type="button" className={mode === "solo" ? "active" : ""} onClick={() => { setMode("solo"); if (!['Caesar','Rồng'].includes(lane)) setLane("Caesar"); }}><Swords /> Kèo Solo Đường</button></div>
    <Card className={`versus-form ${mode === "solo" ? "solo-mode" : ""}`}>
      <div className="lane-matchup-filter"><span>KÈO ĐI ĐƯỜNG</span><Select value={lane} onChange={event => setLane(event.target.value)}>{mode === "counter" && <option value="">Tất cả vị trí</option>}{(mode === "solo" ? ["Caesar", "Rồng"] : ["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"]).map(position => <option key={position}>{position}</option>)}</Select><small>{lane ? `${laneHeroes.length} tướng phù hợp vị trí ${lane}` : "So sánh tự do toàn bộ kho tướng"}</small></div>
      <label>Tướng của bạn<HeroSearchSelect heroes={laneHeroes} value={a} onChange={setA} excludeIds={b ? [b] : []} module="counter" /></label>
      <ArrowLeftRight />
      <label>Đối thủ<HeroSearchSelect heroes={laneHeroes} value={b} onChange={setB} excludeIds={a ? [a] : []} placeholder="Tìm đối thủ..." module="counter" /></label>
      <Button disabled={!a || !b || mutation.isPending} onClick={() => mutation.mutate()}><Sparkles size={16} /> Phân tích</Button>
    </Card>
    {mutation.error && <div className="error-banner">{mutation.error.message}</div>}
    {mode === "solo" && mutation.data && heroA && heroB && <div className="solo-matchup-explorer"><header><span>LANE MATCHUP EXPLORER</span><h3>{heroA.name} <i>vs</i> {heroB.name}</h3><small>{soloLane} · Kế hoạch trao đổi chiêu theo dữ liệu sức mạnh</small></header><div><Card><Eye /><span>KỸ NĂNG CẦN NÉ</span><b>{dodgeTip}</b><p>Dùng bước ngang, giữ kỹ năng lướt và không đứng cùng hướng đợt lính khi đối thủ mở trao đổi.</p></Card><Card><Clock3 /><span>COOLDOWN PUNISH</span><b>Phản công sau kỹ năng mở giao tranh</b><p>{mutation.data.conditions[0] ?? `Chờ ${heroB.name} dùng kỹ năng áp sát rồi tận dụng cửa sổ hồi chiêu để trao đổi ngắn.`}</p></Card><Card><Zap /><span>POWER SPIKE SOLO</span><b>{spikeLevel}</b><p>{heroA.strengths[0] ?? `${heroA.name} mạnh nhất khi hoàn tất ngưỡng trang bị đầu và giữ thế lính thuận lợi.`}</p></Card></div></div>}
    {mutation.data ? <div className="counter-result">
      <Card className="fighter"><HeroVisual hero={mutation.data.hero} /><div className="big-score">{mutation.data.hero_advantage}<small>ĐIỂM ĐỐI KHÁNG</small></div><ul>{(mutation.data.hero_reasons ?? mutation.data.hero.strengths).map(x => <li key={x}>{x}</li>)}</ul></Card>
      <div className="versus-mark">VS<span>Độ tin cậy {Math.round((mutation.data.confidence ?? 0) * 100)}%</span></div>
      <Card className="fighter"><HeroVisual hero={mutation.data.opponent} /><div className="big-score">{mutation.data.opponent_advantage}<small>ĐIỂM ĐỐI KHÁNG</small></div><ul>{(mutation.data.opponent_reasons ?? mutation.data.opponent.strengths).map(x => <li key={x}>{x}</li>)}</ul></Card>
      <Card className="conditions"><h3><Shield /> Điều kiện cần nhớ</h3>{mutation.data.conditions.map(x => <p key={x}>{x}</p>)}</Card>
    </div> : <EmptyState title="Chọn một kèo đối đầu" description="Kết quả là điểm thuật toán có giải thích, không phải tỷ lệ thắng thực tế." />}
  </div>;
}
