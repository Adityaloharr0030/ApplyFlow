import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiFetch as fetch } from '../utils/apiFetch';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function OverviewTab({ stats, session, runStatus, events, sessionStatus, onStart, onStop }) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-slate-900 border border-slate-800 p-6 rounded-2xl">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            Real-time Overview
            <span className={`text-xs px-3 py-1 rounded-full font-bold ${runStatus.is_running ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'}`}>
              {runStatus.is_running ? '● RUNNING' : '● IDLE'}
            </span>
          </h2>
          <p className="text-slate-400 mt-1">Monitor your bot's live activity and success rates.</p>
        </div>
        <div>
          {runStatus.is_running ? (
            <button onClick={onStop} className="bg-red-600 hover:bg-red-500 text-white font-bold px-6 py-3 rounded-lg transition-colors flex items-center gap-2">
              <span>⏹</span> Stop Bot
            </button>
          ) : (
            <button onClick={onStart} className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-6 py-3 rounded-lg transition-colors flex items-center gap-2">
              <span>🚀</span> Launch Bot
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
          <div className="text-slate-400 text-sm mb-1">Total Applied</div>
          <div className="text-3xl font-extrabold text-blue-400">{stats.total_applied || 0}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
          <div className="text-slate-400 text-sm mb-1">Today</div>
          <div className="text-3xl font-extrabold text-green-400">{stats.today_applied || 0}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
          <div className="text-slate-400 text-sm mb-1">Success Rate</div>
          <div className="text-3xl font-extrabold text-purple-400">{stats.success_rate || 0}%</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
          <div className="text-slate-400 text-sm mb-1">This Session</div>
          <div className="text-3xl font-extrabold text-amber-400">{session.applied_count || 0}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>🔴</span> Live Session</h3>
          <div className="space-y-3">
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 text-sm">Status</span>
              <span className="text-white font-medium capitalize">{session.status}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 text-sm">Platform</span>
              <span className="text-white font-medium capitalize">{session.current_platform || '—'}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 text-sm">Current Listing</span>
              <span className="text-white font-medium truncate max-w-[200px]">{session.current_listing || '—'}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400 text-sm">Step</span>
              <span className="text-white font-medium">{session.current_step || '—'}</span>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-4 pt-2">
              <div className="bg-green-900/20 border border-green-900/50 p-2 rounded-lg text-center">
                <div className="text-xl font-bold text-green-400">{session.applied_count}</div>
                <div className="text-[10px] text-green-500/70 uppercase tracking-wider">Applied</div>
              </div>
              <div className="bg-amber-900/20 border border-amber-900/50 p-2 rounded-lg text-center">
                <div className="text-xl font-bold text-amber-400">{session.skipped_count}</div>
                <div className="text-[10px] text-amber-500/70 uppercase tracking-wider">Skipped</div>
              </div>
              <div className="bg-red-900/20 border border-red-900/50 p-2 rounded-lg text-center">
                <div className="text-xl font-bold text-red-400">{session.error_count}</div>
                <div className="text-[10px] text-red-500/70 uppercase tracking-wider">Errors</div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><span>⚡</span> Activity Feed</h3>
          <div className="flex-1 overflow-y-auto max-h-[250px] space-y-2 pr-2">
            {events.length === 0 ? (
              runStatus.is_running ? (
                <div className="flex flex-col items-center justify-center mt-6 space-y-3">
                  <div className="text-3xl animate-pulse">⏳</div>
                  <div className="text-slate-300 text-sm font-semibold text-center">Bot is running…</div>
                  <div className="text-slate-500 text-xs text-center max-w-xs">
                    The bot launched in scheduler mode and is waiting for the scheduled time (09:00).
                    Activity will appear here once it starts applying.
                  </div>
                  <div className="text-xs text-blue-400/60 border border-blue-900/40 bg-blue-900/10 rounded-lg px-3 py-1.5">
                    💡 To run immediately: Stop Bot → Launch Bot (with "Run Now" mode)
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center mt-8 space-y-4">
                  <div className="text-slate-500 text-sm text-center">No activity yet — launch the bot to see output.</div>
                  <button onClick={onStart} className="bg-blue-600/20 hover:bg-blue-600/40 border border-blue-600/30 text-blue-400 font-bold px-4 py-2 rounded-lg transition-colors text-xs flex items-center gap-2">
                    <span>🚀</span> Launch Bot Now
                  </button>
                </div>
              )
            ) : (
              events.slice(-20).reverse().map((event, idx) => {
                let colorClass = 'text-slate-300';
                const msg = (event.message || event.type || '').toLowerCase();
                if (event.type === 'error' || msg.includes('fail') || msg.includes('error')) colorClass = 'text-red-400';
                else if (event.type === 'success' || msg.includes('applied to') || msg.includes('success')) colorClass = 'text-green-400';
                else if (msg.includes('skip') || msg.includes('dry run')) colorClass = 'text-amber-400';
                
                return (
                  <div key={idx} className="flex gap-3 text-sm p-2.5 rounded-lg bg-slate-800/40 border border-slate-800/60 font-mono">
                    <span className="text-slate-500 shrink-0">
                      {event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
                    </span>
                    <span className={colorClass}>
                      {event.message || event.type || 'Event'}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function HistoryTab() {
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/api/history/applications`)
      .then(res => res.json())
      .then(data => { setHistory(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = history.filter(app => {
    const search = filter.toLowerCase();
    const matchesText = !filter ||
      (app.title || '').toLowerCase().includes(search) ||
      (app.company || '').toLowerCase().includes(search) ||
      (app.platform || '').toLowerCase().includes(search);
    const matchesStatus = statusFilter === 'all' || app.status === statusFilter;
    return matchesText && matchesStatus;
  });

  const platformColor = (p) => {
    const map = { internshala: 'blue', linkedin: 'sky', indeed: 'indigo', unstop: 'purple', naukri: 'orange' };
    const c = map[p?.toLowerCase()] || 'slate';
    return `bg-${c}-900/30 text-${c}-400 border border-${c}-900/50`;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        {[['Total', history.length, 'text-blue-400'],
          ['Success', history.filter(h => h.status === 'success').length, 'text-green-400'],
          ['Dry Run', history.filter(h => h.dry_run).length, 'text-amber-400'],
          ['Failed', history.filter(h => h.status === 'failed').length, 'text-red-400']
        ].map(([label, count, color]) => (
          <div key={label} className="bg-slate-900 border border-slate-800 p-4 rounded-2xl text-center">
            <div className={`text-3xl font-extrabold ${color}`}>{count}</div>
            <div className="text-slate-400 text-sm mt-1">{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 items-center">
        <input
          type="text"
          placeholder="🔍  Search company, role, platform..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="flex-1 bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 text-sm"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm"
        >
          <option value="all">All Statuses</option>
          <option value="success">✅ Success</option>
          <option value="failed">❌ Failed</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="overflow-auto max-h-[calc(100vh-400px)]">
          <table className="w-full text-left text-sm text-slate-400">
            <thead className="text-xs text-slate-500 uppercase bg-slate-900/80 sticky top-0 border-b border-slate-800 backdrop-blur">
              <tr>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Company</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Platform</th>
                <th className="px-5 py-3">Score</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Link</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" className="text-center py-12 text-slate-500">⏳ Loading history...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="7" className="text-center py-12 text-slate-500">No applications recorded yet. Launch the bot to start applying!</td></tr>
              ) : (
                filtered.map((app, idx) => (
                  <tr key={idx} className="border-b border-slate-800/50 hover:bg-slate-800/40 transition-colors">
                    <td className="px-5 py-3 whitespace-nowrap text-slate-500 text-xs">
                      {app.applied_at ? new Date(app.applied_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                    <td className="px-5 py-3 text-slate-200 font-semibold">{app.company || '—'}</td>
                    <td className="px-5 py-3 max-w-[200px] truncate">{app.title || '—'}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold capitalize ${platformColor(app.platform)}`}>
                        {app.platform || '—'}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1">
                        <span className={`text-sm font-bold ${
                          app.score >= 7 ? 'text-green-400' : app.score >= 4 ? 'text-amber-400' : 'text-red-400'
                        }`}>{app.score ?? '—'}</span>
                        <span className="text-slate-600 text-xs">/10</span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold capitalize ${
                        app.status === 'success' ? 'bg-green-900/30 text-green-400 border border-green-900/50' :
                        app.status === 'failed' ? 'bg-red-900/30 text-red-400 border border-red-900/50' :
                        'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}>
                        {app.dry_run ? '🧪 Dry Run' : app.status === 'success' ? '✅ Applied' : '❌ Failed'}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      {app.apply_url ? (
                        <a href={app.apply_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 text-xs underline underline-offset-2">
                          View →
                        </a>
                      ) : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ApplicationsTab({ applications }) {
  const [filter, setFilter] = useState('');

  const filtered = applications.filter(app => {
    if (!filter) return true;
    const search = filter.toLowerCase();
    return (
      (app.Company || '').toLowerCase().includes(search) ||
      (app.Role || app.Title || '').toLowerCase().includes(search) ||
      (app.Source || app.Platform || '').toLowerCase().includes(search) ||
      (app.Status || '').toLowerCase().includes(search)
    );
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-180px)]">
      <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900 shrink-0">
        <h2 className="text-xl font-bold text-white">Application History ({applications.length})</h2>
        <input 
          type="text" 
          placeholder="Search company, role, platform..." 
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 w-64 focus:outline-none focus:border-blue-500 text-sm"
        />
      </div>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-sm text-slate-400">
          <thead className="text-xs text-slate-500 uppercase bg-slate-900/50 sticky top-0 border-b border-slate-800 shadow-sm backdrop-blur">
            <tr>
              <th className="px-6 py-4 font-semibold">Date</th>
              <th className="px-6 py-4 font-semibold">Company</th>
              <th className="px-6 py-4 font-semibold">Role</th>
              <th className="px-6 py-4 font-semibold">Platform</th>
              <th className="px-6 py-4 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="5" className="text-center py-10 text-slate-500">No applications found.</td>
              </tr>
            ) : (
              filtered.map((app, idx) => (
                <tr key={idx} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <td className="px-6 py-3 whitespace-nowrap">{app.Date || '—'}</td>
                  <td className="px-6 py-3 text-slate-200 font-medium">{app.Company || '—'}</td>
                  <td className="px-6 py-3">{app.Role || app.Title || '—'}</td>
                  <td className="px-6 py-3">
                    <span className="bg-slate-800 text-slate-300 px-2 py-1 rounded text-xs border border-slate-700 capitalize">
                      {app.Source || app.Platform || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold capitalize ${
                      app.Status?.toLowerCase().includes('success') ? 'bg-green-900/30 text-green-400 border border-green-900/50' :
                      app.Status?.toLowerCase().includes('error') ? 'bg-red-900/30 text-red-400 border border-red-900/50' :
                      'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}>
                      {app.Status || 'Pending'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LogsTab({ logs }) {
  const terminalRef = useRef(null);

  useEffect(() => {
    terminalRef.current?.scrollTo({ top: terminalRef.current.scrollHeight, behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="bg-[#0c0c0c] border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-180px)] font-mono text-sm shadow-2xl">
      <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex items-center gap-2 shrink-0">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
          <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
          <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
        </div>
        <span className="text-slate-500 text-xs ml-2 font-sans tracking-wide">bot-terminal</span>
      </div>
      <div className="p-4 overflow-y-auto flex-1 space-y-1" ref={terminalRef}>
        {logs.length === 0 ? (
          <div className="text-slate-600">Waiting for logs...</div>
        ) : (
          logs.map((line, idx) => {
            const lower = line.toLowerCase();
            let color = 'text-slate-300';
            if (lower.includes('error') || lower.includes('failed')) color = 'text-red-400';
            if (lower.includes('success') || lower.includes('applied')) color = 'text-green-400';
            if (lower.includes('warning') || lower.includes('skip')) color = 'text-amber-400';
            return <div key={idx} className={color}>{line}</div>;
          })
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState({ total_applied: 0, today_applied: 0, platforms: {}, success_rate: 0, recent: [], session: {} });
  const [session, setSession] = useState({ status: 'idle', applied_count: 0, skipped_count: 0, error_count: 0, events: [] });
  const [applications, setApplications] = useState([]);
  const [logs, setLogs] = useState([]);
  const [runStatus, setRunStatus] = useState({ is_running: false, started_at: null, next_run: null, schedule_enabled: false });
  const [events, setEvents] = useState([]);
  const [sessionStatus, setSessionStatus] = useState({});

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
        if (data.session) setSession(prev => ({ ...prev, ...data.session }));
      }
    } catch (err) {}
  }, []);

  const fetchApplications = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/applications`);
      if (res.ok) {
        const data = await res.json();
        setApplications(Array.isArray(data) ? data : []);
      }
    } catch (err) {}
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/logs?lines=100`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {}
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      if (res.ok) {
        const data = await res.json();
        setRunStatus(data);
      }
    } catch (err) {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchStatus();
    
    const statusInterval = setInterval(fetchStatus, 2000);
    const statsInterval = setInterval(fetchStats, 3000);
    
    return () => {
      clearInterval(statusInterval);
      clearInterval(statsInterval);
    };
  }, [fetchStats, fetchStatus]);

  useEffect(() => {
    let interval;
    if (activeTab === 'applications') {
      fetchApplications();
      interval = setInterval(fetchApplications, 5000);
    } else if (activeTab === 'logs') {
      fetchLogs();
      interval = setInterval(fetchLogs, 2000);
    }
    return () => interval && clearInterval(interval);
  }, [activeTab, fetchApplications, fetchLogs]);

  const handleStart = async () => {
    try {
      await fetch(`${API_BASE}/api/start`, { method: 'POST' });
      fetchStatus();
    } catch (err) {
      alert('Failed to start bot.');
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/api/stop`, { method: 'POST' });
      fetchStatus();
    } catch (err) {
      alert('Failed to stop bot.');
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'history', label: 'History', icon: '🕐' },
    { id: 'applications', label: 'CSV Log', icon: '📋' },
    { id: 'logs', label: 'Live Logs', icon: '🖥️' }
  ];

  return (
    <div className="max-w-6xl w-full h-full flex flex-col font-sans">
      <div className="flex gap-2 mb-6 border-b border-slate-800 pb-px">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === tab.id 
                ? 'border-blue-500 text-blue-400' 
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-600'
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1">
        {activeTab === 'overview' && (
          <OverviewTab 
            stats={stats} 
            session={session} 
            runStatus={runStatus} 
            events={events} 
            sessionStatus={sessionStatus} 
            onStart={handleStart} 
            onStop={handleStop} 
          />
        )}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'applications' && <ApplicationsTab applications={applications} />}
        {activeTab === 'logs' && <LogsTab logs={logs} />}
      </div>
    </div>
  );
}
