import { Map, Sparkles, Swords } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { HeroPicker } from "../components/HeroPicker";
import { ScoreRadar } from "../components/ScoreRadar";
import { Button, Card, EmptyState, Select } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { post } from "../services/api";
import type { Composition } from "../types";

type StrategyResult = { phase: string; priority: string; map_control: string; fight_timing: string; avoid: string; win_condition: string; ally_analysis: Composition; enemy_analysis: Composition };

export function StrategyPage() {
  const heroes = useHeroes().data?.items ?? []; const [allies, setAllies] = useState<number[]>([]); const [enemies, setEnemies] = useState<number[]>([]); const [phase, setPhase] = useState("giữa trận");
  const mutation = useMutation({ mutationFn: () => post<StrategyResult>("/strategy/analyze", { ally_ids: allies, enemy_ids: enemies, phase }) });
  return <div className="page"><div className="page-intro"><div><span>PHASE STRATEGY ENGINE</span><h2>Kế hoạch theo giai đoạn</h2><p>Chuyển điểm mạnh đội hình thành mục tiêu, nhịp giao tranh và điều kiện thắng.</p></div></div><div className="two-col"><Card className="form-card"><HeroPicker heroes={heroes.filter(h => !enemies.includes(h.id))} selected={allies} onChange={setAllies} label="ĐỘI CỦA BẠN" module="strategy" /><HeroPicker heroes={heroes.filter(h => !allies.includes(h.id))} selected={enemies} onChange={setEnemies} label="ĐỘI ĐỐI PHƯƠNG" module="strategy" /><label>Giai đoạn<Select value={phase} onChange={e => setPhase(e.target.value)}>{["đầu trận", "giữa trận", "cuối trận"].map(x => <option key={x}>{x}</option>)}</Select></label><Button disabled={!allies.length || mutation.isPending} onClick={() => mutation.mutate()}><Sparkles size={16} /> Lập kế hoạch</Button></Card><div>{mutation.data ? <><div className="strategy-cards"><Card><Map /><span><small>MỤC TIÊU ƯU TIÊN</small>{mutation.data.priority}</span></Card><Card><Swords /><span><small>NHỊP GIAO TRANH</small>{mutation.data.fight_timing}</span></Card><Card><Map /><span><small>KIỂM SOÁT BẢN ĐỒ</small>{mutation.data.map_control}</span></Card><Card className="danger"><Swords /><span><small>CẦN TRÁNH</small>{mutation.data.avoid}</span></Card></div><Card><div className="card-title"><span>NĂNG LỰC ĐỘI HÌNH</span></div><ScoreRadar scores={mutation.data.ally_analysis.scores} /></Card></> : <EmptyState title="Chưa có kế hoạch" description="Nhập ít nhất một tướng đồng minh và chọn giai đoạn trận đấu." />}</div></div></div>;
}

