import { RotateCcw, Sparkles, Target, TriangleAlert } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { HeroPicker } from "../components/HeroPicker";
import { HeroVisual } from "../components/HeroVisual";
import { Badge, Button, Card, EmptyState, Select, Skeleton } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { post } from "../services/api";
import type { Composition, DraftRecommendation } from "../types";

type DraftResult = { recommendations: DraftRecommendation[]; ally_analysis: Composition; enemy_analysis: Composition; notice: string };

export function DraftPage() {
  const { data } = useHeroes(); const heroes = data?.items ?? [];
  const [allies, setAllies] = useState<number[]>([]); const [enemies, setEnemies] = useState<number[]>([]); const [bans, setBans] = useState<number[]>([]);
  const [position, setPosition] = useState("Rừng"); const [strategy, setStrategy] = useState("cân bằng");
  const mutation = useMutation({ mutationFn: () => post<DraftResult>("/draft/recommend", { ally_ids: allies, enemy_ids: enemies, banned_ids: bans, desired_position: position, strategy }) });
  const reset = () => { setAllies([]); setEnemies([]); setBans([]); mutation.reset(); };
  return <div className="page"><div className="page-intro"><div><span>REAL-TIME DRAFT ENGINE</span><h2>Phòng cấm chọn chiến thuật</h2><p>Mỗi thay đổi đội hình tạo một phép tính mới trên bốn nhóm tiêu chí độc lập.</p></div><Button className="button-secondary" onClick={reset}><RotateCcw size={16} /> Làm lại</Button></div>
    <div className="draft-layout"><Card className="draft-board"><div className="draft-team blue"><HeroPicker heroes={heroes.filter(h => !enemies.includes(h.id) && !bans.includes(h.id))} selected={allies} onChange={setAllies} label="ĐỘI XANH" module="draft" /></div><div className="draft-vs"><span>VS</span><i /></div><div className="draft-team red"><HeroPicker heroes={heroes.filter(h => !allies.includes(h.id) && !bans.includes(h.id))} selected={enemies} onChange={setEnemies} label="ĐỘI ĐỎ" module="draft" /></div><div className="ban-zone"><HeroPicker heroes={heroes.filter(h => !allies.includes(h.id) && !enemies.includes(h.id))} selected={bans} onChange={setBans} max={10} label="TƯỚNG ĐÃ CẤM" /></div></Card>
      <Card className="draft-controls"><h3><Target /> Thiết lập lượt chọn</h3><label>Vị trí cần chơi<Select value={position} onChange={e => setPosition(e.target.value)}>{["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"].map(x => <option key={x}>{x}</option>)}</Select></label><label>Chiến thuật<Select value={strategy} onChange={e => setStrategy(e.target.value)}>{["cân bằng", "giao tranh tổng", "bắt lẻ", "cấu rỉa", "đẩy lẻ", "kiểm soát mục tiêu"].map(x => <option key={x}>{x}</option>)}</Select></label><Button disabled={mutation.isPending} onClick={() => mutation.mutate()}><Sparkles size={17} /> {mutation.isPending ? "Đang phân tích..." : "Phân tích lượt chọn"}</Button><p className="control-note"><TriangleAlert size={14} /> Không sử dụng tỷ lệ thắng giả.</p></Card></div>
    {mutation.error && <div className="error-banner">{mutation.error.message}</div>}
    <div className="section-heading"><div><span>KẾT QUẢ ENGINE</span><h3>Top lựa chọn phù hợp</h3></div>{mutation.data && <Badge>Độ tin cậy phụ thuộc dữ liệu đầu vào</Badge>}</div>
    {mutation.isPending ? <div className="recommend-list"><Skeleton className="recommend-skeleton" /><Skeleton className="recommend-skeleton" /></div> : mutation.data ? <div className="recommend-list">{mutation.data.recommendations.map((row, index) => <Card className="recommend-row" key={row.hero.id}><div className="rank">0{index + 1}</div><HeroVisual hero={row.hero} compact /><div className="recommend-bars"><span><label>Phù hợp <b>{row.fit_score}</b></label><i><em style={{ width: `${row.fit_score}%` }} /></i></span><span><label>Khắc chế <b>{row.counter_score ?? "—"}</b></label><i><em style={{ width: `${row.counter_score ?? 0}%` }} /></i></span><span><label>Phối hợp <b>{row.synergy_score ?? "—"}</b></label><i><em style={{ width: `${row.synergy_score ?? 0}%` }} /></i></span></div><div className="recommend-reason"><b>{row.advantages[0] ?? "Đề xuất dựa trên phần dữ liệu đã xác minh"}</b><span>Rủi ro: {row.risks.join(", ") || "Chưa ghi nhận"}</span></div></Card>)}</div> : <EmptyState title="Chưa có kết quả" description="Chọn đội hình hiện tại rồi chạy phân tích để nhận đề xuất." />}
  </div>;
}

