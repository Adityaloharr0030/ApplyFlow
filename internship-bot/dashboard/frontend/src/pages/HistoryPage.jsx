import { useState, useEffect } from 'react';
import { apiFetch as fetch } from '../utils/apiFetch';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PLATFORM_COLORS = {
  internshala: 'bg-blue-900/40 text-blue-300 border-blue-700/50',
  linkedin:    'bg-indigo-900/40 text-indigo-300 border-indigo-700/50',
  indeed:      'bg-sky-900/40 text-sky-300 border-sky-700/50',
  unstop:      'bg-violet-900/40 text-violet-300 border-violet-700/50',
  naukri:      'bg-amber-900/40 text-amber-300 border-amber-700/50',
  generic_web: 'bg-slate-800 text-slate-300 border-slate-700',
};

const STATUS_STYLES = {
  Applied:   'bg-green-900/40 text-green-400 border-green-700/50',
  Skipped:   'bg-amber-900/40 text-amber-400 border-amber-700/50',
  Error:     'bg-red-900/40 text-red-400 border-red-700/50',
  'Dry Run': 'bg-slate-800 text-slate-400 border-slate-700',
};

function StatCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-extrabold ${color}`}>{value}</p>
    </div>
  );
}

function RunPanel({ run, index, expanded, toggle }) {
  const isExpanded = expanded;
  const { date, stats, platforms, applications, duration_mins } = run;
  
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden mb-4 shadow-sm">
      {/* Header (Clickable) */}
      <div 
        onClick={toggle}
        className="p-5 flex items-center justify-between cursor-pointer hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="bg-blue-900/30 text-blue-400 rounded-xl p-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-white mb-1">
              Run: {date}
            </h2>
            <div className="flex gap-3 text-sm text-slate-400">
              <span>⏱ {duration_mins || 0} mins</span>
              <span>•</span>
              <span>🌐 {platforms.length > 0 ? platforms.join(', ') : 'No specific platform'}</span>
            </div>
          </div>
        </div>
        
        {/* Quick Stats in Header */}
        <div className="flex items-center gap-6 text-sm mr-4 hidden md:flex">
          <div className="text-center">
            <p className="text-slate-500 font-semibold mb-1">Processed</p>
            <p className="text-white font-bold">{stats.total}</p>
          </div>
          <div className="text-center">
            <p className="text-slate-500 font-semibold mb-1">Applied</p>
            <p className="text-green-400 font-bold">{stats.applied}</p>
          </div>
          <div className="text-center">
            <p className="text-slate-500 font-semibold mb-1">Skipped</p>
            <p className="text-amber-400 font-bold">{stats.skipped}</p>
          </div>
          <div className="text-center">
            <p className="text-slate-500 font-semibold mb-1">Avg Score</p>
            <p className="text-blue-400 font-bold">{stats.avg_score || '—'}</p>
          </div>
        </div>
        
        <div className="text-slate-500 transform transition-transform duration-200" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)' }}>
          ▼
        </div>
      </div>
      
      {/* Applications Table */}
      {isExpanded && (
        <div className="border-t border-slate-800">
          {applications.length === 0 ? (
            <div className="p-8 text-center text-slate-500">
              No applications tracked during this run.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-900/50 text-slate-500 text-xs uppercase tracking-wider">
                  <th className="text-left px-5 py-3 font-semibold pl-16">Role / Company</th>
                  <th className="text-left px-5 py-3 font-semibold">Platform</th>
                  <th className="text-left px-5 py-3 font-semibold">Status</th>
                  <th className="text-left px-5 py-3 font-semibold">Score</th>
                  <th className="text-left px-5 py-3 font-semibold">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {applications.map((row, i) => {
                  const plat  = (row.platform || 'unknown').toLowerCase();
                  const status = row.status || 'Unknown';
                  const platStyle = PLATFORM_COLORS[plat] || PLATFORM_COLORS.generic_web;
                  const statusKey = /applied|success/i.test(status) ? 'Applied'
                    : /error|failed/i.test(status) ? 'Error'
                    : /skipped/i.test(status) ? 'Skipped'
                    : /dry run/i.test(status) ? 'Dry Run' : '';
                  const statusStyle = STATUS_STYLES[statusKey] || 'bg-slate-800 text-slate-400 border-slate-700';
                  
                  return (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-5 py-3 pl-16">
                        <p className="text-white font-medium truncate max-w-xs">{row.title || '—'}</p>
                        <p className="text-slate-500 text-xs">{row.company || '—'}</p>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded border capitalize ${platStyle}`}>
                          {plat}
                        </span>
                      </td>
                      <td className="px-5 py-3 max-w-[200px]">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded border block truncate ${statusStyle}`}
                          title={status}>
                          {status}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {row.score
                          ? <span className="font-bold text-blue-400">{row.score}/10</span>
                          : <span className="text-slate-600">—</span>}
                      </td>
                      <td className="px-5 py-3">
                        {(row.apply_url || row.url)
                          ? <a href={row.apply_url || row.url} target="_blank" rel="noreferrer"
                              className="text-blue-400 hover:text-blue-300 text-xs hover:underline underline-offset-2">
                              Open ↗
                            </a>
                          : <span className="text-slate-600">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

export default function HistoryPage() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedRuns, setExpandedRuns] = useState({});

  useEffect(() => {
    fetch(`${API_BASE}/api/runs`)
      .then(r => r.json())
      .then(data => {
        const raw = Array.isArray(data.runs) ? data.runs : [];
        setRuns(raw);
        
        // Auto-expand the most recent run
        if (raw.length > 0) {
          setExpandedRuns({ 0: true });
        }
        
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleRun = (index) => {
    setExpandedRuns(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleExport = () => {
    const headers = ['Run Date', 'Title', 'Company', 'Platform', 'Status', 'Score', 'URL'];
    const rows = [];
    runs.forEach(run => {
      run.applications.forEach(r => {
        rows.push([
          run.date,
          `"${(r.title || '').replace(/"/g, '""')}"`,
          `"${(r.company || '').replace(/"/g, '""')}"`,
          r.platform || r.source || '',
          r.status || '',
          r.score || '',
          r.apply_url || r.url || '',
        ].join(','));
      });
    });
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `applyflow_history_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };
  
  // Calculate globals
  let globalTotal = 0;
  let globalApplied = 0;
  let globalSkipped = 0;
  let globalErrors = 0;
  
  runs.forEach(r => {
    globalTotal += r.stats.total;
    globalApplied += r.stats.applied;
    globalSkipped += r.stats.skipped;
    globalErrors += r.stats.errors;
  });

  return (
    <div className="max-w-6xl pb-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Application History</h1>
          <p className="text-slate-400 text-sm">Every application tracked, grouped by bot run.</p>
        </div>
        <button onClick={handleExport}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm font-semibold px-4 py-2 rounded-xl transition-colors flex items-center gap-2">
          ⬇ Export CSV
        </button>
      </div>

      {/* Global Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Processed" value={globalTotal}    color="text-white" />
        <StatCard label="Successfully Applied" value={globalApplied}  color="text-green-400" />
        <StatCard label="Skipped"       value={globalSkipped}  color="text-amber-400" />
        <StatCard label="Errors / Failed" value={globalErrors}   color="text-red-400" />
      </div>

      {/* Runs List */}
      {loading ? (
        <div className="text-center py-20 text-slate-500">
          <div className="text-4xl mb-3 animate-pulse">⏳</div>
          <p>Loading run history…</p>
        </div>
      ) : runs.length === 0 ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-2xl">
          <div className="text-5xl mb-4">📭</div>
          <h3 className="text-white font-semibold mb-2">
            No runs tracked yet
          </h3>
          <p className="text-slate-400 text-sm max-w-sm mx-auto">
            Launch the bot to start tracking. Your application history will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {runs.map((run, i) => (
            <RunPanel 
              key={i} 
              run={run} 
              index={i} 
              expanded={!!expandedRuns[i]} 
              toggle={() => toggleRun(i)} 
            />
          ))}
        </div>
      )}
    </div>
  );
}
