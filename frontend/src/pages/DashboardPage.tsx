import { ArrowRight, Bot, Crosshair, Database, ShieldCheck, Sparkles, Swords, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useHeroes } from "../hooks/useHeroes";
import { Card, Skeleton } from "../components/ui";

const tools = [
  { to: "/draft", icon: Crosshair, title: "Phân tích Draft", text: "Chấm điểm lựa chọn theo đội hình hai bên và vị trí còn thiếu.", tint: "cyan" },
  { to: "/team", icon: UsersRound, title: "Kiến tạo đội hình", text: "Ghép đủ 5 vị trí theo phong cách chiến thuật bạn chọn.", tint: "violet" },
  { to: "/counter", icon: ShieldCheck, title: "Phân tích khắc chế", text: "Đối chiếu hai chiều, nêu điều kiện có lợi của từng bên.", tint: "gold" },
  { to: "/coach", icon: Bot, title: "Trợ lý chiến thuật", text: "Nhận cây trả lời trực quan theo câu hỏi và đội hình đang chọn.", tint: "blue" },
];

export function DashboardPage() {
  const heroes = useHeroes();
  return <div className="page dashboard-page">
    <section className="hero-banner">
      <div className="eyebrow"><Sparkles size={14} /> DECISION INTELLIGENCE</div>
      <h2>Đọc thế trận.<br /><em>Chọn đúng nước đi.</em></h2>
      <p>Nền tảng phân tích chiến thuật Liên Quân sử dụng engine đa tiêu chí minh bạch — không biến điểm thuật toán thành tỷ lệ thắng.</p>
      <div className="hero-actions"><Link className="button" to="/draft">Bắt đầu phân tích Draft <ArrowRight size={17} /></Link><Link className="ghost-link" to="/heroes">Khám phá kho tướng</Link></div>
      <div className="orbital"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="core"><Swords /></div></div>
    </section>
    <section className="stat-strip">
      <div><Database /><span>{heroes.isLoading ? <Skeleton className="tiny" /> : heroes.data?.total ?? 0}<small>TƯỚNG TRONG DATASET</small></span></div>
      <div><Crosshair /><span>10<small>TIÊU CHÍ CHẤM ĐIỂM</small></span></div>
      <div><ShieldCheck /><span>0<small>SỐ LIỆU META GIẢ</small></span></div>
      <div><Sparkles /><span>100%<small>GIẢI THÍCH ĐƯỢC</small></span></div>
    </section>
    <div className="section-heading"><div><span>CÔNG CỤ PHÂN TÍCH</span><h3>Mọi quyết định, một nền tảng</h3></div><Link to="/strategy">Xem chiến thuật <ArrowRight size={15} /></Link></div>
    <section className="tool-grid">{tools.map((tool, index) => <motion.div key={tool.to} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * .06 }}>
      <Link to={tool.to}><Card className={`tool-card ${tool.tint}`}><div className="tool-icon"><tool.icon /></div><h3>{tool.title}</h3><p>{tool.text}</p><span>Khởi chạy <ArrowRight size={15} /></span></Card></Link>
    </motion.div>)}</section>
    <section className="integrity-panel"><div><ShieldCheck /><span><b>Tactical Core đã sẵn sàng</b><small>Kho 129 tướng, phân tích draft, đội hình, khắc chế và meta trong cùng một không gian.</small></span></div><span className="live-chip"><i /> ONLINE</span></section>
  </div>;
}

