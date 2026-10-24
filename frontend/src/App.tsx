import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { Skeleton } from "./components/ui";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then(m => ({ default: m.DashboardPage })));
const HeroesPage = lazy(() => import("./pages/HeroesPage").then(m => ({ default: m.HeroesPage })));
const HeroDetailPage = lazy(() => import("./pages/HeroDetailPage").then(m => ({ default: m.HeroDetailPage })));
const DraftPage = lazy(() => import("./pages/DraftPage").then(m => ({ default: m.DraftPage })));
const TeamPage = lazy(() => import("./pages/TeamPage").then(m => ({ default: m.TeamPage })));
const CounterPage = lazy(() => import("./pages/CounterPage").then(m => ({ default: m.CounterPage })));
const BuildPage = lazy(() => import("./pages/BuildPage").then(m => ({ default: m.BuildPage })));
const MetaPage = lazy(() => import("./pages/MetaPage").then(m => ({ default: m.MetaPage })));
const CoachPage = lazy(() => import("./pages/CoachPage").then(m => ({ default: m.CoachPage })));
const VisionPage = lazy(() => import("./pages/VisionPage").then(m => ({ default: m.VisionPage })));
const StrategyPage = lazy(() => import("./pages/StrategyPage").then(m => ({ default: m.StrategyPage })));
const WarRoomPage = lazy(() => import("./pages/WarRoomPage").then(m => ({ default: m.WarRoomPage })));
const RunesPage = lazy(() => import("./pages/UtilityPages").then(m => ({ default: m.RunesPage })));
const HistoryPage = lazy(() => import("./pages/UtilityPages").then(m => ({ default: m.HistoryPage })));

const page = (node: React.ReactNode) => <Suspense fallback={<div className="page"><Skeleton className="detail-skeleton" /></div>}>{node}</Suspense>;

const router = createBrowserRouter([{ path: "/", element: <AppLayout />, children: [
  { index: true, element: page(<DashboardPage />) }, { path: "heroes", element: page(<HeroesPage />) },
  { path: "heroes/:id", element: page(<HeroDetailPage />) }, { path: "draft", element: page(<DraftPage />) },
  { path: "team", element: page(<TeamPage />) }, { path: "counter", element: page(<CounterPage />) },
  { path: "build", element: page(<BuildPage />) }, { path: "runes", element: page(<RunesPage />) },
  { path: "meta", element: page(<MetaPage />) }, { path: "coach", element: page(<CoachPage />) },
  { path: "vision", element: page(<VisionPage />) }, { path: "strategy", element: page(<StrategyPage />) },
  { path: "war-room", element: page(<WarRoomPage />) },
  { path: "history", element: page(<HistoryPage />) },
]}]);

export default function App() { return <RouterProvider router={router} />; }

