import {
  BarChart3, Blocks, BrainCircuit, Camera, Crosshair, Gem, History, Home, MapPinned,
  Menu, PackageOpen, Shield, Sparkles, Swords, UsersRound,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAppStore } from "../stores/useAppStore";

const nav = [
  ["/", "Tổng quan", Home], ["/heroes", "Kho tướng", Blocks], ["/draft", "Phân tích Draft", Crosshair],
  ["/team", "Đội hình", UsersRound], ["/counter", "Khắc chế", Shield], ["/build", "Lên trang bị", PackageOpen],
  ["/runes", "Ngọc & phù hiệu", Gem], ["/meta", "Meta Analytics", BarChart3], ["/coach", "Trợ lý chiến thuật", BrainCircuit],
  ["/vision", "Phân tích ảnh", Camera], ["/strategy", "Chiến thuật", Swords], ["/war-room", "Tactical War Room", MapPinned],
  ["/history", "Lịch sử", History],
] as const;

const titles: Record<string, string> = Object.fromEntries(nav.map(([path, label]) => [path, label]));

export function AppLayout() {
  const { sidebarOpen, toggleSidebar } = useAppStore();
  const location = useLocation();
  const pathRoot = location.pathname === "/" ? "/" : `/${location.pathname.split("/")[1]}`;
  return <div className="app-shell">
    <div className="ambient-world" aria-hidden="true">
      <span className="ambient-orb orb-a" /><span className="ambient-orb orb-b" /><span className="ambient-orb orb-c" />
      <span className="ambient-grid" /><span className="ambient-noise" />
    </div>
    <AnimatePresence>{sidebarOpen && <motion.button aria-label="Đóng menu" className="mobile-overlay" onClick={toggleSidebar} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />}</AnimatePresence>
    <aside className={sidebarOpen ? "sidebar open" : "sidebar"}>
      <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><div><b>AOV STRATEGY</b><span>OPEN TACTICAL SYSTEM</span></div></div>
      <nav>{nav.map(([path, label, Icon]) => <NavLink key={path} to={path} end={path === "/"} onClick={() => sidebarOpen && toggleSidebar()}>
        <Icon size={18} /><span>{label}</span>
      </NavLink>)}</nav>
      <div className="sidebar-status"><span className="status-dot" /><div><b>Engine sẵn sàng</b><small>Điểm số có giải thích</small></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar">
        <button className="menu-button" onClick={toggleSidebar} aria-label="Mở menu"><Menu size={20} /></button>
        <div><span>TRUNG TÂM CHIẾN THUẬT</span><h1>{titles[pathRoot] ?? "Phân tích tướng"}</h1></div>
        <div className="patch-pill"><span className="status-dot" /> TACTICAL CORE · LIVE</div>
      </header>
      <AnimatePresence mode="wait">
        <motion.main key={location.pathname} initial={{ opacity: 0, y: 14, scale: .992 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: .995 }} transition={{ duration: .28, ease: [0.22, 1, 0.36, 1] }}>
          <Outlet />
        </motion.main>
      </AnimatePresence>
      <footer className="site-copyright"><b>© Vũ Huy Hoàng</b><span>Chỉ dành cho mục đích nghiên cứu và học tập. Nghiêm cấm sao chép dưới mọi hình thức.</span></footer>
    </div>
  </div>;
}

