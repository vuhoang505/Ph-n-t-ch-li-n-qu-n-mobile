import { AlertTriangle, Check, Copy, Crosshair, Download, Flag, Map, Pause, Pencil, Play, Radar, Route, Shield, Sparkles, Swords, Target, Trash2, Undo2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { HeroSearchSelect } from "../components/HeroSearchSelect";
import { Button, Card, EmptyState } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { post } from "../services/api";
import type { Hero } from "../types";

const PHASES = [
  { value: "01:30", title: "Khai cuộc", note: "Vòng rừng" },
  { value: "03:00", title: "Mục tiêu đầu", note: "Rồng / Caesar" },
  { value: "08:00", title: "Kiểm soát", note: "Rừng / bắt lẻ" },
  { value: "12:00+", title: "Cuối trận", note: "Caesar / đẩy đường" },
] as const;
type Phase = typeof PHASES[number]["value"];
type Role = "Caesar" | "Rừng" | "Giữa" | "Rồng" | "Trợ thủ";
type Lineup = Record<Role, number>;
type StartBuff = "auto" | "blue" | "red";
type TeamSide = "blue" | "red";
type DrawTool = "off" | "draw" | "flag" | "danger" | "attack" | "defend";
type DrawMark = { id: number; tool: Exclude<DrawTool, "off">; points: [number, number][] };
type MapPoint = { x: number; y: number; label: string };
type WarRoomResult = {
  timeline_phase: Phase;
  power_balance: { ally_power: number; enemy_power: number; advantage: "ally" | "enemy" | "balanced"; metrics: string[]; status: string; confidence: number };
  jungle_prediction: { jungler: string; start_buff: string; gank_target_lane: string; gank_window: string; path_coordinates: MapPoint[]; status: string; prediction_mode: "automatic" | "manual" };
  objective_call: { target: string; action: string; controlled_by: "ally" | "enemy" | "balanced" };
  tactical_orders: { role: string; action: string }[];
  ambush_zones: { id: string; x: number; y: number; danger_level: "low" | "medium" | "high"; warning: string }[];
  invade_alert: { active: boolean; heroes: string[]; time: string; target_buff: string; message: string; path_coordinates: { x: number; y: number }[] };
  ally_side: TeamSide;
  lineups: { ally: { role: string; hero: Hero }[]; enemy: { role: string; hero: Hero }[] };
};

const MAP_HEIGHT = 56.25;
export const orientPoint = (x: number, y: number, side: TeamSide): [number, number] => [
  side === "red" ? 100 - x : x,
  (side === "red" ? 100 - y : y) * MAP_HEIGHT / 100,
];

const ROLES: Role[] = ["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"];
const emptyLineup = (): Lineup => ({ Caesar: 0, Rừng: 0, Giữa: 0, Rồng: 0, "Trợ thủ": 0 });
const PHASE_POINTS: Record<Phase, { ally: Record<Role, [number, number]>; enemy: Record<Role, [number, number]> }> = {
  "01:30": {
    ally: { Caesar: [26, 29], Rừng: [38, 61], Giữa: [43, 56], Rồng: [52, 84], "Trợ thủ": [45, 79] },
    enemy: { Caesar: [58, 15], Rừng: [63, 39], Giữa: [57, 44], Rồng: [82, 58], "Trợ thủ": [76, 51] },
  },
  "03:00": {
    ally: { Caesar: [36, 24], Rừng: [61, 68], Giữa: [56, 61], Rồng: [63, 82], "Trợ thủ": [58, 76] },
    enemy: { Caesar: [52, 16], Rừng: [76, 61], Giữa: [65, 56], Rồng: [83, 64], "Trợ thủ": [76, 57] },
  },
  "08:00": {
    ally: { Caesar: [43, 19], Rừng: [47, 56], Giữa: [48, 51], Rồng: [42, 69], "Trợ thủ": [52, 58] },
    enemy: { Caesar: [49, 18], Rừng: [57, 43], Giữa: [55, 47], Rồng: [66, 65], "Trợ thủ": [60, 50] },
  },
  "12:00+": {
    ally: { Caesar: [42, 27], Rừng: [38, 35], Giữa: [31, 38], Rồng: [68, 78], "Trợ thủ": [27, 32] },
    enemy: { Caesar: [47, 24], Rừng: [46, 29], Giữa: [43, 35], Rồng: [76, 76], "Trợ thủ": [35, 22] },
  },
};

const SIM_KEYFRAMES: { second: number; phase: Phase }[] = [
  { second: 0, phase: "01:30" }, { second: 90, phase: "01:30" },
  { second: 180, phase: "03:00" }, { second: 480, phase: "08:00" },
  { second: 720, phase: "12:00+" }, { second: 900, phase: "12:00+" },
];

function simulatedPoint(side: "ally" | "enemy", role: Role, second: number): [number, number] {
  if (second < 90) {
    const base: [number, number] = side === "ally" ? [18, 79] : [82, 17];
    const laneTarget = PHASE_POINTS["01:30"][side][role];
    if (role !== "Rừng") {
      const progress = Math.min(1, second / 32);
      return [base[0] + (laneTarget[0] - base[0]) * progress, base[1] + (laneTarget[1] - base[1]) * progress];
    }
    const jungleRoute: [number, [number, number]][] = side === "ally"
      ? [[0, base], [12, [37, 41]], [43, [45, 54]], [68, [52, 66]], [90, laneTarget]]
      : [[0, base], [12, [67, 43]], [43, [60, 35]], [68, [49, 25]], [90, laneTarget]];
    const nextIndex = Math.max(1, jungleRoute.findIndex(([time]) => time >= second));
    const [startTime, startPoint] = jungleRoute[nextIndex - 1], [endTime, endPoint] = jungleRoute[nextIndex];
    const progress = (second - startTime) / (endTime - startTime);
    return [startPoint[0] + (endPoint[0] - startPoint[0]) * progress, startPoint[1] + (endPoint[1] - startPoint[1]) * progress];
  }
  let left = SIM_KEYFRAMES[0], right = SIM_KEYFRAMES[SIM_KEYFRAMES.length - 1];
  for (let index = 1; index < SIM_KEYFRAMES.length; index += 1) {
    if (second <= SIM_KEYFRAMES[index].second) { left = SIM_KEYFRAMES[index - 1]; right = SIM_KEYFRAMES[index]; break; }
  }
  const start = PHASE_POINTS[left.phase][side][role], end = PHASE_POINTS[right.phase][side][role];
  const progress = right.second === left.second ? 0 : (second - left.second) / (right.second - left.second);
  return [start[0] + (end[0] - start[0]) * progress, start[1] + (end[1] - start[1]) * progress];
}

const formatClock = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

export function warRoomShareText(result: WarRoomResult): string {
  return [
    `TACTICAL WAR ROOM · ${result.timeline_phase}`,
    `Tương quan: Đội ta ${result.power_balance.ally_power}% — ${result.power_balance.enemy_power}% Đội địch`,
    `Rừng địch: ${result.jungle_prediction.jungler} · ${result.jungle_prediction.start_buff === "blue" ? "Bùa Xanh" : "Bùa Đỏ"} → ${result.jungle_prediction.gank_target_lane} (${result.jungle_prediction.gank_window})`,
    `Mục tiêu: ${result.objective_call.target} — ${result.objective_call.action}`,
    ...result.tactical_orders.map(order => `${order.role}: ${order.action}`),
    "AOV Strategy · Vũ Huy Hoàng",
  ].join("\n");
}

function fallbackCopy(text: string) {
  const field = document.createElement("textarea"); field.value = text; document.body.appendChild(field); field.select(); document.execCommand("copy"); field.remove();
}

function exportWarRoomMap(result: WarRoomResult, marks: DrawMark[] = []) {
  const canvas = document.createElement("canvas"); canvas.width = 1200; canvas.height = 760;
  const context = canvas.getContext("2d"); if (!context) return;
  const gradient = context.createLinearGradient(0, 0, 1200, 760); gradient.addColorStop(0, "#061323"); gradient.addColorStop(.55, "#10193b"); gradient.addColorStop(1, "#301640");
  context.fillStyle = gradient; context.fillRect(0, 0, 1200, 760);
  context.strokeStyle = "rgba(92,232,255,.18)"; context.lineWidth = 2;
  for (let offset = 0; offset <= 600; offset += 60) { context.beginPath(); context.moveTo(50 + offset, 650); context.lineTo(650 + offset, 50); context.stroke(); }
  context.strokeStyle = "rgba(255,255,255,.2)"; context.lineWidth = 12; context.beginPath(); context.moveTo(90, 650); context.lineTo(650, 90); context.lineTo(1110, 90); context.stroke(); context.beginPath(); context.moveTo(90,650); context.lineTo(1110,90); context.stroke(); context.beginPath(); context.moveTo(90,650); context.lineTo(550,650); context.lineTo(1110,90); context.stroke();
  context.setLineDash([14, 11]); context.strokeStyle = "#ff6fae"; context.lineWidth = 5; context.beginPath();
  result.jungle_prediction.path_coordinates.forEach((point, index) => { const x = 80 + point.x * 7.2; const y = 30 + point.y * 6.2; index ? context.lineTo(x,y) : context.moveTo(x,y); }); context.stroke(); context.setLineDash([]);
  for (const zone of result.ambush_zones) { context.beginPath(); context.fillStyle = zone.danger_level === "high" ? "rgba(255,70,110,.55)" : "rgba(255,180,70,.38)"; context.arc(80 + zone.x * 7.2, 30 + zone.y * 6.2, zone.danger_level === "high" ? 28 : 20, 0, Math.PI * 2); context.fill(); }
  for (const mark of marks) {
    context.strokeStyle = "#ffd45c"; context.fillStyle = "#ffd45c"; context.lineWidth = 6; context.lineCap = "round"; context.lineJoin = "round";
    const points = mark.points.map(([x,y]) => [x * 12, y / MAP_HEIGHT * 760]);
    if (mark.tool === "draw") { context.beginPath(); points.forEach(([x,y], index) => index ? context.lineTo(x,y) : context.moveTo(x,y)); context.stroke(); }
    else { context.font = "bold 36px Segoe UI"; context.fillText(mark.tool === "flag" ? "⚑" : mark.tool === "danger" ? "!" : mark.tool === "attack" ? "⚔" : "◆", points[0][0], points[0][1]); }
  }
  context.fillStyle = "#5ce8ff"; context.font = "700 20px Segoe UI"; context.fillText(`TACTICAL WAR ROOM · ${result.timeline_phase}`, 55, 45);
  context.fillStyle = "#f2f6ff"; context.font = "700 34px Segoe UI"; context.fillText(`ĐỘI TA ${result.power_balance.ally_power}%`, 55, 710);
  context.textAlign = "right"; context.fillStyle = "#ff7aa8"; context.fillText(`${result.power_balance.enemy_power}% ĐỘI ĐỊCH`, 1145, 710); context.textAlign = "left";
  context.fillStyle = "#8999b7"; context.font = "500 15px Segoe UI"; context.fillText("© Vũ Huy Hoàng · Chỉ dành cho nghiên cứu và học tập", 55, 742);
  canvas.toBlob(blob => { if (!blob) return; const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.download = `war-room-${result.timeline_phase.replace(":", "-").replace("+", "plus")}.png`; link.href = url; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }, "image/png");
}

function HeroMarker({ hero, role, side, phase, allySide, second, selected, onSelect }: { hero: Hero; role: Role; side: "ally" | "enemy"; phase: Phase; allySide: TeamSide; second: number; selected: boolean; onSelect: () => void }) {
  const [rawX, rawY] = simulatedPoint(side, role, second);
  const [x, y] = orientPoint(rawX, rawY, allySide);
  const clipId = `hero-${side}-${hero.id}`;
  return <motion.g className={`war-hero-marker ${selected ? "selected" : ""}`} role="button" tabIndex={0} aria-label={`Xem kế hoạch ${hero.name} - ${role}`} onClick={onSelect} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") onSelect(); }} initial={{ opacity: 0, scale: .6 }} animate={{ opacity: 1, scale: 1, x, y }} transition={{ type: "spring", stiffness: 110, damping: 22 }}>
    <defs><clipPath id={clipId}><circle r="3.8" /></clipPath></defs>
    <circle r="5.2" className={`war-hero-ring ${side}`} />
    {hero.image_url ? <image href={hero.image_url} x="-3.8" y="-3.8" width="7.6" height="7.6" clipPath={`url(#${clipId})`} preserveAspectRatio="xMidYMid slice" /> : <circle r="3.8" className={`war-hero-fallback ${side}`} />}
    <text y="7.8" textAnchor="middle" className="war-hero-label">{role}</text>
  </motion.g>;
}

function MinionWaves({ second, allySide }: { second: number; allySide: TeamSide }) {
  const progress = (second % 30) / 30;
  const lanes = [
    { start: [18, 79], meet: [48, 20] }, { start: [18, 79], meet: [50, 49] }, { start: [18, 79], meet: [68, 78] },
  ];
  const point = (start: number[], end: number[], value: number) => orientPoint(start[0] + (end[0] - start[0]) * value, start[1] + (end[1] - start[1]) * value, allySide);
  return <g className="war-minions">{lanes.flatMap((lane, laneIndex) => ["ally", "enemy"].flatMap(team => Array.from({ length: 3 }, (_, index) => {
    const delay = index * .045;
    const waveProgress = Math.max(0, Math.min(1, progress - delay));
    const start = team === "ally" ? lane.start : [82, 17];
    const [x,y] = point(start, lane.meet, waveProgress);
    return <circle key={`${laneIndex}-${team}-${index}`} cx={x} cy={y} r=".48" className={team} />;
  })))}</g>;
}

function objectiveCountdown(second: number, spawn: number) {
  if (second >= spawn) return "LIVE";
  return formatClock(spawn - second);
}

function TacticalMap({ result, second, selectedHeroId, onSelectHero, drawTool, marks, setMarks }: { result: WarRoomResult; second: number; selectedHeroId: number | null; onSelectHero: (hero: Hero, role: Role, side: "ally" | "enemy") => void; drawTool: DrawTool; marks: DrawMark[]; setMarks: React.Dispatch<React.SetStateAction<DrawMark[]>> }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const activeMark = useRef<number | null>(null);
  const objectiveClass = result.objective_call.controlled_by;
  const oriented = (point: { x: number; y: number }) => orientPoint(point.x, point.y, result.ally_side);
  const pathPoints = result.jungle_prediction.path_coordinates.map(oriented);
  const path = pathPoints.map(point => point.join(",")).join(" ");
  const pathD = pathPoints.map((point, index) => `${index ? "L" : "M"}${point[0]} ${point[1]}`).join(" ");
  const invadePoints = result.invade_alert.path_coordinates.map(oriented);
  const invadePath = invadePoints.map(point => point.join(",")).join(" ");
  const [caesarX, caesarY] = oriented({ x: 42, y: 27 });
  const [dragonX, dragonY] = oriented({ x: 63, y: 62 });
  const caesarSpawn = second < 120 ? 120 : second < 480 ? 480 : 900;
  const caesarLabel = second < 120 ? `Caesar ${objectiveCountdown(second, 120)}` : second < 480 ? `Caesar Bóng Tối ${objectiveCountdown(second, 480)}` : second < 900 ? `Caesar Bạo Chúa ${objectiveCountdown(second, 900)}` : "Caesar Bạo Chúa · LIVE";
  const buffAnchors = [{ x: 37, y: 41, kind: "blue" }, { x: 52, y: 66, kind: "red" }, { x: 67, y: 43, kind: "blue" }, { x: 49, y: 25, kind: "red" }];
  const selectedRow = [...result.lineups.ally.map(row => ({ ...row, side: "ally" as const })), ...result.lineups.enemy.map(row => ({ ...row, side: "enemy" as const }))].find(row => row.hero.id === selectedHeroId);
  const selectedPosition = selectedRow ? orientPoint(...simulatedPoint(selectedRow.side, selectedRow.role as Role, second), result.ally_side) : null;
  const safeFarmPath = selectedPosition ? `${selectedPosition[0]},${selectedPosition[1]} ${selectedPosition[0] + (result.ally_side === "blue" ? 8 : -8)},${selectedPosition[1] - 3} ${selectedPosition[0] + (result.ally_side === "blue" ? 14 : -14)},${selectedPosition[1] - 1}` : "";
  const pointerPoint = (event: React.PointerEvent<SVGSVGElement>): [number, number] => {
    const rect = event.currentTarget.getBoundingClientRect();
    return [(event.clientX - rect.left) / rect.width * 100, (event.clientY - rect.top) / rect.height * MAP_HEIGHT];
  };
  const pointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (drawTool === "off") return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const mark: DrawMark = { id: Date.now(), tool: drawTool, points: [pointerPoint(event)] };
    setMarks(previous => [...previous, mark]); activeMark.current = mark.id;
  };
  const pointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (drawTool !== "draw" || activeMark.current === null) return;
    const point = pointerPoint(event);
    setMarks(previous => previous.map(mark => mark.id === activeMark.current ? { ...mark, points: [...mark.points, point] } : mark));
  };
  const pointerUp = () => { activeMark.current = null; };
  return <Card className="war-map-card"><div className="war-map-head"><div><Radar /><span><b>LIVE MACRO MAP</b><small>{result.timeline_phase} · {result.jungle_prediction.status.replace("_", " ")} · {result.jungle_prediction.prediction_mode === "manual" ? "bùa chọn thủ công" : "vòng rừng tự động"}</small></span></div><i><span /> TACTICAL MODEL ACTIVE</i></div>
    {result.invade_alert.active && <div className="war-invade-banner"><AlertTriangle /><div><b>{result.invade_alert.message}</b><span>{result.invade_alert.heroes.join(", ")} có khả năng xâm lăng cấp 1</span></div></div>}
    <div className={`war-map-wrap ${drawTool !== "off" ? "drawing" : ""}`}><svg ref={svgRef} className="war-map" viewBox={`0 0 100 ${MAP_HEIGHT}`} role="img" aria-label="Bản đồ chiến thuật Bình Nguyên Vô Tận" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp}>
      <defs>
        <linearGradient id="map-ground" x1="0" y1="1" x2="1" y2="0"><stop stopColor="#071f2c" /><stop offset=".52" stopColor="#101d36" /><stop offset="1" stopColor="#27152f" /></linearGradient>
        <filter id="war-glow"><feGaussianBlur stdDeviation="1.5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        <pattern id="war-grid" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M5 0H0V5" fill="none" stroke="rgba(112,210,255,.06)" strokeWidth=".2" /></pattern>
      </defs>
      <image href="/assets/aov-battlefield-map.png" x="0" y="0" width="100" height={MAP_HEIGHT} preserveAspectRatio="none" className={result.ally_side === "red" ? "war-map-image flipped" : "war-map-image"} />
      <rect x="0" y="0" width="100" height={MAP_HEIGHT} rx="2" className="war-map-tint" />
      <g className={`war-objective caesar ${objectiveClass} ${caesarSpawn - second <= 30 && caesarSpawn > second ? "spawning" : ""}`} transform={`translate(${caesarX} ${caesarY})`}><circle r="3.2" /><text y=".7">C</text><title>Hang Caesar</title></g>
      <g className={`war-objective dragon ${objectiveClass} ${second < 120 && second >= 90 ? "spawning" : ""}`} transform={`translate(${dragonX} ${dragonY})`}><circle r="3.2" /><text y=".7">R</text><title>Hang Rồng</title></g>
      <g className="war-buffs">{buffAnchors.map((buff, index) => { const [x,y] = oriented(buff); return <circle key={index} cx={x} cy={y} r="1.65" className={buff.kind} />; })}</g>
      <MinionWaves second={second} allySide={result.ally_side} />
      <g className="war-objective-timers"><text x={caesarX} y={caesarY + 5.2}>{caesarLabel}</text><text x={dragonX} y={dragonY + 5.2}>Rồng {objectiveCountdown(second, 120)}</text></g>
      {!selectedRow && <><polyline className="war-jungle-path-glow" points={path} /><polyline className="war-jungle-path" points={path} filter="url(#war-glow)" />{pathD && <circle r="1.15" className="war-energy-head"><animateMotion dur="2.4s" repeatCount="indefinite" path={pathD} /></circle>}</>}
      {selectedPosition && <g className="war-inspector-overlay"><circle cx={selectedPosition[0]} cy={selectedPosition[1]} r={selectedRow?.role === "Rồng" ? 8 : 6.5} /><polyline points={safeFarmPath} /><text x={selectedPosition[0]} y={selectedPosition[1] - 9}>TẦM ĐÁNH · LỘ TRÌNH AN TOÀN</text></g>}
      {result.invade_alert.active && <polyline className="war-invade-path" points={invadePath} />}
      {result.jungle_prediction.path_coordinates.map((point, index) => { const [x,y] = oriented(point); return <motion.g key={point.label} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: index * .12 }} transform={`translate(${x} ${y})`}><circle r="1.1" className="war-path-node" /><text x="1.8" y="-1" className="war-path-label">{point.label}</text></motion.g>; })}
      {result.ambush_zones.map(zone => { const [x,y] = oriented(zone); return <g key={zone.id} transform={`translate(${x} ${y})`}><circle r={zone.danger_level === "high" ? 3.5 : 2.8} className={`war-danger-wave ${zone.danger_level}`} /><circle r="1.1" className={`war-danger-core ${zone.danger_level}`} /><title>{zone.warning}</title></g>; })}
      {result.lineups.ally.map(row => <HeroMarker key={`a-${row.hero.id}`} hero={row.hero} role={row.role as Role} side="ally" phase={result.timeline_phase} allySide={result.ally_side} second={second} selected={selectedHeroId === row.hero.id} onSelect={() => onSelectHero(row.hero, row.role as Role, "ally")} />)}
      {result.lineups.enemy.map(row => <HeroMarker key={`e-${row.hero.id}`} hero={row.hero} role={row.role as Role} side="enemy" phase={result.timeline_phase} allySide={result.ally_side} second={second} selected={selectedHeroId === row.hero.id} onSelect={() => onSelectHero(row.hero, row.role as Role, "enemy")} />)}
      <g className="war-draw-layer">{marks.map(mark => mark.tool === "draw" ? <polyline key={mark.id} points={mark.points.map(point => point.join(",")).join(" ")} /> : <g key={mark.id} transform={`translate(${mark.points[0][0]} ${mark.points[0][1]})`} className={`war-map-ping ${mark.tool}`}><circle r="2.6" /><text y=".9">{mark.tool === "flag" ? "⚑" : mark.tool === "danger" ? "!" : mark.tool === "attack" ? "⚔" : "◆"}</text></g>)}</g>
    </svg></div>
    <div className="war-map-legend"><span><i className="ally" />Đội ta</span><span><i className="enemy" />Đội địch</span><span><i className="route" />Vòng rừng dự đoán</span><span><i className="danger" />Vùng nguy hiểm</span></div>
  </Card>;
}

function LineupSelector({ side, heroes, lineup, onChange, blockedIds }: { side: "ally" | "enemy"; heroes: Hero[]; lineup: Lineup; onChange: (lineup: Lineup) => void; blockedIds: number[] }) {
  const selectedIds = ROLES.map(role => lineup[role]).filter(Boolean);
  return <div className={`war-picker ${side}`}><h3>{side === "ally" ? <Shield /> : <Crosshair />} {side === "ally" ? "ĐỘI TA" : "ĐỘI ĐỊCH"}</h3><div className="war-lane-slots">{ROLES.map((role, index) => <div className="war-lane-slot" key={role}><span><i>{index + 1}</i>{role}</span><HeroSearchSelect heroes={heroes} value={lineup[role]} onChange={heroId => onChange({ ...lineup, [role]: heroId })} excludeIds={[...blockedIds, ...selectedIds.filter(id => id !== lineup[role])]} placeholder={`Chọn tướng ${role}...`} inputLabel={`${side === "ally" ? "Đội ta" : "Đội địch"} · ${role}`} module="strategy" /></div>)}</div></div>;
}

export function WarRoomPage() {
  const heroes = useHeroes().data?.items ?? [];
  const [allies, setAllies] = useState<Lineup>(emptyLineup);
  const [enemies, setEnemies] = useState<Lineup>(emptyLineup);
  const [phase, setPhase] = useState<Phase>("01:30");
  const [startBuff, setStartBuff] = useState<StartBuff>("auto");
  const [allySide, setAllySide] = useState<TeamSide>("blue");
  const [copied, setCopied] = useState(false);
  const [second, setSecond] = useState(90);
  const [playing, setPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState<0.5 | 1 | 2>(1);
  const [selectedHero, setSelectedHero] = useState<{ hero: Hero; role: Role; side: "ally" | "enemy" } | null>(null);
  const [drawTool, setDrawTool] = useState<DrawTool>("off");
  const [marks, setMarks] = useState<DrawMark[]>([]);
  const allyIds = useMemo(() => ROLES.map(role => allies[role]).filter(Boolean), [allies]);
  const enemyIds = useMemo(() => ROLES.map(role => enemies[role]).filter(Boolean), [enemies]);
  const complete = allyIds.length === 5 && enemyIds.length === 5;
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setSecond(value => value >= 900 ? (setPlaying(false), 900) : value + 1), 1000 / playbackRate);
    return () => window.clearInterval(timer);
  }, [playing, playbackRate]);
  const mutation = useMutation({ mutationFn: ({ nextPhase, buff, side }: { nextPhase: Phase; buff: StartBuff; side: TeamSide }) => post<WarRoomResult>("/strategy/macro-timeline", { ally_ids: allyIds, enemy_ids: enemyIds, ally_positions: allies, enemy_positions: enemies, enemy_start_buff: buff, ally_side: side, timeline_phase: nextPhase }) });
  useEffect(() => {
    const nextPhase: Phase = second < 180 ? "01:30" : second < 480 ? "03:00" : second < 720 ? "08:00" : "12:00+";
    if (nextPhase === phase) return;
    setPhase(nextPhase);
    setCopied(false);
    if (complete && mutation.data) mutation.mutate({ nextPhase, buff: startBuff, side: allySide });
  }, [second, phase, complete, startBuff, allySide, mutation]);
  const runPhase = (nextPhase: Phase) => { setPhase(nextPhase); setCopied(false); if (complete) mutation.mutate({ nextPhase, buff: startBuff, side: allySide }); };
  const changeStartBuff = (buff: StartBuff) => { setStartBuff(buff); setCopied(false); if (complete && mutation.data) mutation.mutate({ nextPhase: phase, buff, side: allySide }); };
  const changeSide = (side: TeamSide) => { setAllySide(side); setCopied(false); if (complete && mutation.data) mutation.mutate({ nextPhase: phase, buff: startBuff, side }); };
  const scrubTo = (value: number) => {
    setSecond(value);
    const nextPhase: Phase = value < 180 ? "01:30" : value < 480 ? "03:00" : value < 720 ? "08:00" : "12:00+";
    if (nextPhase !== phase) runPhase(nextPhase);
  };
  const copyPlan = async () => { if (!mutation.data) return; const text = warRoomShareText(mutation.data); try { if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text); else fallbackCopy(text); } catch { fallbackCopy(text); } setCopied(true); };
  return <div className="page war-room-page">
    <div className="page-intro war-intro"><div><span>TACTICAL WAR ROOM</span><h2>Bản đồ chiến thuật Macro</h2><p>Mô phỏng nhịp di chuyển, cửa sổ gank, tương quan sức mạnh và mệnh lệnh cho từng vị trí theo timeline trận đấu.</p></div><div className="war-live-chip"><i /> MACRO ENGINE ONLINE</div></div>
    <Card className="war-lineup-builder"><LineupSelector side="ally" heroes={heroes} lineup={allies} onChange={setAllies} blockedIds={enemyIds} /><div className="war-builder-core"><Swords /><b>VS</b><small>{allyIds.length + enemyIds.length}/10 READY</small></div><LineupSelector side="enemy" heroes={heroes} lineup={enemies} onChange={setEnemies} blockedIds={allyIds} /><div className="war-launch-controls"><div className="war-buff-choice"><span>GÓC NHÌN ĐỘI TA</span><div className="war-side-buttons">{(["blue", "red"] as TeamSide[]).map(side => <button type="button" key={side} className={allySide === side ? "active" : ""} onClick={() => changeSide(side)}>Ta bên {side === "blue" ? "Xanh" : "Đỏ"}</button>)}</div></div><div className="war-buff-choice"><span>ĐỊCH KHỞI ĐẦU BÙA</span><div>{(["auto", "blue", "red"] as StartBuff[]).map(buff => <button type="button" key={buff} className={startBuff === buff ? "active" : ""} onClick={() => changeStartBuff(buff)}>{buff === "auto" ? "Tự động" : buff === "blue" ? "Xanh" : "Đỏ"}</button>)}</div></div><Button disabled={!complete || mutation.isPending} onClick={() => mutation.mutate({ nextPhase: phase, buff: startBuff, side: allySide })}><Sparkles /> {mutation.isPending ? "Đang dựng bản đồ…" : "Khởi chạy War Room"}</Button></div></Card>
    {mutation.error && <div className="error-banner">{mutation.error.message}</div>}
    {mutation.data ? <div className="war-workspace"><div className="war-map-stage"><div className="war-drawing-tools"><button type="button" className={drawTool === "off" ? "active" : ""} onClick={() => setDrawTool("off")}><Target /> Chọn tướng</button><button type="button" className={drawTool === "draw" ? "active" : ""} onClick={() => setDrawTool("draw")}><Pencil /> Bút vẽ</button>{(["flag", "danger", "attack", "defend"] as DrawTool[]).map(tool => <button type="button" key={tool} className={drawTool === tool ? "active" : ""} onClick={() => setDrawTool(tool)}>{tool === "flag" ? <Flag /> : <AlertTriangle />}{tool}</button>)}<button type="button" disabled={!marks.length} onClick={() => setMarks(items => items.slice(0,-1))}><Undo2 /> Hoàn tác</button><button type="button" disabled={!marks.length} onClick={() => setMarks([])}><Trash2 /> Xóa</button></div><TacticalMap result={mutation.data} second={second} selectedHeroId={selectedHero?.hero.id ?? null} onSelectHero={(hero, role, side) => { if (drawTool === "off") setSelectedHero({ hero, role, side }); }} drawTool={drawTool} marks={marks} setMarks={setMarks} /></div><aside className="war-control-panel">
      <Card className="war-timeline"><header><button type="button" className="war-play-button" onClick={() => { if (second >= 900) setSecond(0); setPlaying(value => !value); }}>{playing ? <Pause /> : <Play />}</button><div><span>REAL-TIME SIMULATION</span><b>{formatClock(second)}</b></div><div className="war-speed-buttons">{([0.5,1,2] as const).map(rate => <button type="button" key={rate} className={playbackRate === rate ? "active" : ""} onClick={() => setPlaybackRate(rate)}>{rate}x</button>)}</div></header><input type="range" min="0" max="900" step="1" value={second} onChange={event => scrubTo(Number(event.target.value))} aria-label="Kéo thời gian mô phỏng từ 00:00 đến 15:00" /><div className="war-timeline-ticks"><span>00:00</span><span>02:00</span><span>08:00</span><span>15:00</span></div><div className="war-phase-buttons">{PHASES.map(item => <button type="button" key={item.value} className={phase === item.value ? "active" : ""} onClick={() => { const value = item.value === "01:30" ? 90 : item.value === "03:00" ? 180 : item.value === "08:00" ? 480 : 720; scrubTo(value); }}><b>{item.value}</b><span>{item.title}</span><small>{item.note}</small></button>)}</div></Card>
      {selectedHero && <Card className="war-hero-inspector"><button type="button" onClick={() => setSelectedHero(null)}>×</button><div className="war-inspector-title">{selectedHero.hero.image_url && <img src={selectedHero.hero.image_url} alt="" />}<div><span>HERO INSPECTOR · {selectedHero.role}</span><b>{selectedHero.hero.name}</b></div></div><div className="war-range-stat"><i /><span>Tầm đánh chiến thuật</span><b>{selectedHero.role === "Rồng" ? "Tối đa · 8m" : "Tiêu chuẩn · 6.5m"}</b></div><p><AlertTriangle /> Trong 15 giây tới, bạn có <strong>{selectedHero.role === "Rồng" ? "70%" : "48%"}</strong> nguy cơ bị {mutation.data.jungle_prediction.jungler} tiếp cận từ bụi gần nhất.</p><small>Bản đồ đang cô lập lộ trình farm an toàn của tướng này. Bấm × để xem lại toàn đội.</small></Card>}
      <Card className="war-networth"><div className="war-panel-title"><span><Swords /> NET WORTH CURVE</span><small>Dự kiến @ {formatClock(second)}</small></div><svg viewBox="0 0 300 105" role="img" aria-label="Biểu đồ dự đoán chênh lệch vàng"><path className="grid" d="M20 15H290M20 50H290M20 85H290"/><path className="ally" d={`M20 84 C90 ${78 - mutation.data.power_balance.ally_power/8},180 ${55 - mutation.data.power_balance.ally_power/12},290 ${35 - mutation.data.power_balance.ally_power/15}`} /><path className="enemy" d={`M20 84 C90 ${78 - mutation.data.power_balance.enemy_power/8},180 ${55 - mutation.data.power_balance.enemy_power/12},290 ${35 - mutation.data.power_balance.enemy_power/15}`} /><line x1={20 + second/900*270} y1="10" x2={20 + second/900*270} y2="91" /><text x="20" y="102">00:00</text><text x="155" y="102">08:00 · POWER SPIKE</text><text x="270" y="102">15:00</text></svg><div><span>Đội ta <b>{Math.round(3000 + second * 31 * mutation.data.power_balance.ally_power / 50).toLocaleString("vi-VN")}v</b></span><span>Đội địch <b>{Math.round(3000 + second * 31 * mutation.data.power_balance.enemy_power / 50).toLocaleString("vi-VN")}v</b></span></div></Card>
      <Card className="war-balance"><div className="war-panel-title"><span><Swords /> TƯƠNG QUAN LỰC LƯỢNG</span><small>{Math.round(mutation.data.power_balance.confidence * 100)}% tin cậy</small></div><div className="war-balance-numbers"><b>{mutation.data.power_balance.ally_power}%<small>ĐỘI TA</small></b><i>VS</i><b>{mutation.data.power_balance.enemy_power}%<small>ĐỘI ĐỊCH</small></b></div><div className="war-power-track"><motion.i initial={{ width: 0 }} animate={{ width: `${mutation.data.power_balance.ally_power}%` }} /></div><p>{mutation.data.power_balance.advantage === "ally" ? "Đội ta đang có cửa chủ động trên bản đồ." : mutation.data.power_balance.advantage === "enemy" ? "Đội địch đang mạnh hơn tại mốc này — ưu tiên đổi mục tiêu." : "Hai đội cân bằng — quyền ưu tiên đường sẽ quyết định nhịp đánh."}</p></Card>
      <Card className="war-objective-call"><Map /><div><span>OBJECTIVE CALL</span><b>{mutation.data.objective_call.target}</b><p>{mutation.data.objective_call.action}</p></div></Card>
      <Card className="war-orders"><div className="war-panel-title"><span><Radar /> CHỈ ĐẠO TÁC CHIẾN</span><small>{mutation.data.timeline_phase}</small></div>{mutation.data.tactical_orders.map((order, index) => <motion.article key={order.role} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * .06 }}><i>{index + 1}</i><div><b>{order.role}</b><p>{order.action}</p></div></motion.article>)}</Card>
      <Card className="war-alerts"><div className="war-panel-title"><span><AlertTriangle /> VÙNG TỬ THẦN</span><small>{mutation.data.ambush_zones.length} cảnh báo</small></div>{mutation.data.ambush_zones.map(zone => <article key={zone.id} className={zone.danger_level}><i /><span><b>{zone.danger_level.toUpperCase()}</b>{zone.warning}</span></article>)}</Card>
      <div className="war-share"><button type="button" onClick={copyPlan}>{copied ? <Check /> : <Copy />}{copied ? "Đã sao chép" : "Sao chép chỉ đạo"}</button><button type="button" onClick={() => exportWarRoomMap(mutation.data!, marks)}><Download /> Xuất ảnh + nét vẽ</button></div>
    </aside></div> : <Card className="war-empty"><EmptyState title="Phòng chiến thuật đang chờ đội hình" description="Chọn đủ 5 tướng mỗi bên rồi khởi chạy để dựng bản đồ macro theo timeline." /></Card>}
  </div>;
}
