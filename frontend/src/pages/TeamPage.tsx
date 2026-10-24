import { LockKeyhole, Sparkles, UsersRound } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { HeroPicker } from "../components/HeroPicker";
import { HeroVisual } from "../components/HeroVisual";
import { ScoreRadar } from "../components/ScoreRadar";
import { Button, Card, EmptyState, Select } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { post } from "../services/api";
import type { Composition, Hero } from "../types";

export function TeamPage() {
  const heroes = useHeroes().data?.items ?? []; const [locked, setLocked] = useState<number[]>([]); const [enemies, setEnemies] = useState<number[]>([]); const [banned, setBanned] = useState<number[]>([]); const [strategy, setStrategy] = useState("giao tranh tổng");
  const mutation = useMutation({ mutationFn: () => post<{ team: Hero[]; analysis: Composition; complete: boolean; banned_ids: number[] }>("/team/generate", { strategy, locked_hero_ids: locked, enemy_ids: enemies, banned_ids: banned }) });
  return <div className="page"><div className="page-intro"><div><span>COMPOSITION ENGINE</span><h2>Kiến tạo đội hình 5 người</h2><p>Khóa tướng bạn muốn chơi, chọn đối thủ và danh sách cấm; hệ thống chỉ xét những tướng còn hợp lệ.</p></div></div><div className="two-col"><Card className="form-card"><h3><LockKeyhole /> Tướng khóa, đối thủ & lượt cấm</h3><HeroPicker heroes={heroes.filter(h => !enemies.includes(h.id) && !banned.includes(h.id))} selected={locked} onChange={setLocked} label="TƯỚNG ĐÃ KHÓA" module="team" /><HeroPicker heroes={heroes.filter(h => !locked.includes(h.id) && !banned.includes(h.id))} selected={enemies} onChange={setEnemies} label="ĐỘI HÌNH ĐỊCH" module="team" /><HeroPicker heroes={heroes.filter(h => !locked.includes(h.id) && !enemies.includes(h.id))} selected={banned} onChange={setBanned} max={10} label="TƯỚNG ĐÃ CẤM" /><label>Định hướng chiến thuật<Select value={strategy} onChange={e => setStrategy(e.target.value)}>{["giao tranh tổng", "bắt lẻ", "cấu rỉa", "đẩy lẻ", "kiểm soát mục tiêu", "bảo vệ chủ lực", "nhiều khống chế", "cơ động", "chống chịu cao"].map(x => <option key={x}>{x}</option>)}</Select></label><Button onClick={() => mutation.mutate()} disabled={mutation.isPending}><Sparkles size={16} /> Tạo đội hình</Button>{mutation.error && <div className="error-banner">{mutation.error.message}</div>}</Card>
      <Card className="result-card"><div className="card-title"><span><UsersRound /> ĐỘI HÌNH ĐỀ XUẤT</span></div>{mutation.data ? <><div className="lineup">{mutation.data.team.map((hero, index) => <div key={hero.id}><span>{hero.positions[0] ?? `Vị trí ${index + 1}`}</span><HeroVisual hero={hero} compact /></div>)}</div><ScoreRadar scores={mutation.data.analysis.scores} /><div className="analysis-chips"><span>Thiếu: {mutation.data.analysis.missing.join(", ") || "không có điểm yếu lớn"}</span><span>{mutation.data.analysis.damage_balance}</span><span>Đã loại {mutation.data.banned_ids.length} tướng cấm</span></div></> : <EmptyState title="Sẵn sàng xây đội hình" description="Khóa tối đa 5 tướng hoặc để hệ thống đề xuất toàn bộ." />}</Card></div></div>;
}

