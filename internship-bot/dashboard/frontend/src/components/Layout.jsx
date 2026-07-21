import { useState, useEffect } from 'react';
import { apiFetch as fetch } from '../utils/apiFetch';
import { Outlet, Link, useLocation } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const navSections = [
  {
    label: 'App',
    items: [
      { to: '/app/dashboard', icon: '📊', label: 'Dashboard' },
      { to: '/app/history',   icon: '📋', label: 'History' },
      { to: '/app/platforms', icon: '🔌', label: 'Platforms' },
      { to: '/app/schedules', icon: '🗓️', label: 'Schedules' },
      { to: '/app/prep',      icon: '📝', label: 'Interview Prep' },
    ]
  },
  {
    label: 'Config',
    items: [
      { to: '/app/profile',  icon: '👤', label: 'Profile' },
      { to: '/app/settings', icon: '⚙️', label: 'Settings' },
    ]
  }
];

export default function Layout() {
  const location = useLocation();
  const [botStatus, setBotStatus] = useState({ is_running: false });

  useEffect(() => {
    const fetchStatus = () => {
      fetch(`${API_BASE}/api/status`)
        .then(r => r.json())
        .then(d => setBotStatus(d))
        .catch(() => {});
    };
    fetchStatus();
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex min-h-screen bg-[#0a0f1e]">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900/80 border-r border-slate-800 flex flex-col shrink-0">
        {/* Brand */}
        <div className="px-5 py-5 border-b border-slate-800">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm shadow-lg">
              AF
            </div>
            <span className="font-bold text-white text-lg tracking-tight">ApplyFlow</span>
          </Link>
          {/* Bot status pill */}
          <div className={`mt-2 ml-10 flex items-center gap-1.5 text-[11px] font-semibold ${
            botStatus.is_running ? 'text-green-400' : 'text-slate-500'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${botStatus.is_running ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} />
            {botStatus.is_running ? 'Bot Running' : 'Bot Idle'}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
          {navSections.map(section => (
            <div key={section.label}>
              <p className="text-[10px] uppercase tracking-widest text-slate-600 font-semibold px-2 mb-2">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map(item => {
                  const isActive = location.pathname === item.to ||
                    (item.to !== '/app/dashboard' && location.pathname.startsWith(item.to));
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                        isActive
                          ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                      }`}
                    >
                      <span className="text-base">{item.icon}</span>
                      {item.label}
                      {isActive && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-slate-800 space-y-3">
          <button
            onClick={() => {
              localStorage.removeItem('token');
              window.location.href = '/login';
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-slate-400 hover:text-white hover:bg-red-500/10 hover:text-red-400 rounded-lg transition-all duration-150"
          >
            Logout
          </button>
          
          <div>
            <Link to="/" className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition-colors">
              <span>←</span> Back to site
            </Link>
            <div className="mt-2 text-[10px] text-slate-600">ApplyFlow v2.0 • SaaS Mode</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
