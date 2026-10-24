import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import type { Attributes } from "../types";

const labels: Record<string, string> = {
  physical_damage: "Vật lý", magic_damage: "Phép", damage: "Sát thương",
  durability: "Chống chịu", crowd_control: "Khống chế", mobility: "Cơ động",
  engage: "Mở giao tranh", sustain: "Hồi phục", burst: "Dồn sát thương",
  teamfight: "Giao tranh", pickoff: "Bắt lẻ", protection: "Bảo vệ",
  split_push: "Đẩy lẻ", wave_clear: "Dọn lính", objective_control: "Mục tiêu",
  early_game: "Đầu trận", mid_game: "Giữa trận", late_game: "Cuối trận", difficulty: "Độ khó",
};

export function ScoreRadar({ scores }: { scores: Record<string, number | null> | Attributes }) {
  const data = Object.entries(scores).filter(([, value]) => value !== null).map(([key, value]) => ({ metric: labels[key] ?? key, value }));
  const strongest = [...data].sort((a, b) => Number(b.value) - Number(a.value)).slice(0, 4);
  return <div className="radar-panel">
    <div className="radar-wrap"><ResponsiveContainer width="100%" height="100%">
      <RadarChart data={data} outerRadius="76%" margin={{ top: 34, right: 76, bottom: 34, left: 76 }}>
        <defs>
          <radialGradient id="radarFill" cx="50%" cy="50%" r="62%"><stop offset="0%" stopColor="#8b5cf6" stopOpacity=".7"/><stop offset="55%" stopColor="#22d3ee" stopOpacity=".4"/><stop offset="100%" stopColor="#06b6d4" stopOpacity=".14"/></radialGradient>
          <filter id="radarGlow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        <PolarGrid gridType="polygon" stroke="rgba(103,232,249,.18)" radialLines />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} tickCount={6} />
        <PolarAngleAxis dataKey="metric" tick={{ fill: "#b9cbe0", fontSize: 12, fontWeight: 650 }} />
        <Radar dataKey="value" stroke="#67e8f9" strokeWidth={2.5} fill="url(#radarFill)" fillOpacity={1} dot={{ r: 4, fill: "#e0f2fe", stroke: "#22d3ee", strokeWidth: 2 }} filter="url(#radarGlow)" isAnimationActive animationDuration={900} />
        <Tooltip formatter={(value) => [`${value}/100`, "Điểm năng lực"]} contentStyle={{ background: "rgba(5,14,29,.96)", border: "1px solid rgba(103,232,249,.35)", borderRadius: 14, boxShadow: "0 18px 50px rgba(0,0,0,.45)" }} labelStyle={{ color: "#e0f2fe", fontWeight: 700 }} />
      </RadarChart>
    </ResponsiveContainer></div>
    <div className="radar-highlights">{strongest.map((item, index) => <div key={item.metric}><small>TOP {index + 1}</small><span>{item.metric}</span><b>{Math.round(Number(item.value))}</b><i><em style={{ width: `${item.value}%` }} /></i></div>)}</div>
  </div>;
}
