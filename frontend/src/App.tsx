import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { QueryErrorResetBoundary } from "@tanstack/react-query";
import {
  Bell,
  ChartCandlestick,
  Coins,
  LogIn,
  LayoutDashboard,
  LogOut,
  Settings,
  WalletCards
} from "lucide-react";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import TradesPage from "./pages/TradesPage";
import AlertsPage from "./pages/AlertsPage";
import SettingsPage from "./pages/SettingsPage";
import { useAuthStore } from "./store";
import clsx from "clsx";

const navItems = [
  { path: "/dashboard", label: "行情看板", icon: LayoutDashboard },
  { path: "/trades", label: "交易记录", icon: WalletCards },
  { path: "/alerts", label: "提醒规则", icon: Bell },
  { path: "/settings", label: "系统设置", icon: Settings }
];

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthed = useAuthStore((state) => state.isAuthed);
  const signOut = useAuthStore((state) => state.signOut);
  const visibleNavItems = isAuthed ? navItems : navItems.filter((item) => item.path === "/dashboard");

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Coins size={20} />
          </div>
          <div>
            <strong>金价守望</strong>
            <span>积存金监控台</span>
          </div>
        </div>
        <nav className="nav">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                className={clsx("nav-item", location.pathname === item.path && "active")}
                onClick={() => navigate(item.path)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="market-chip">
            <ChartCandlestick size={15} />
            最近 48 小时
          </div>
          <button
            className="ghost-button full"
            onClick={() => {
              if (isAuthed) {
                signOut();
                navigate("/dashboard");
              } else {
                navigate("/login");
              }
            }}
          >
            {isAuthed ? <LogOut size={16} /> : <LogIn size={16} />}
            {isAuthed ? "退出登录" : "登录"}
          </button>
        </div>
      </aside>
      <main className="main">
        <QueryErrorResetBoundary>
          {() => (
            <Routes>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/trades" element={isAuthed ? <TradesPage /> : <Navigate to="/dashboard" replace />} />
              <Route path="/alerts" element={isAuthed ? <AlertsPage /> : <Navigate to="/dashboard" replace />} />
              <Route path="/settings" element={isAuthed ? <SettingsPage /> : <Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          )}
        </QueryErrorResetBoundary>
      </main>
    </div>
  );
}

export default function App() {
  const isAuthed = useAuthStore((state) => state.isAuthed);
  return (
    <Routes>
      <Route path="/login" element={isAuthed ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/*" element={<Shell />} />
    </Routes>
  );
}
