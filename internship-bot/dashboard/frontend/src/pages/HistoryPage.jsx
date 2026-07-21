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

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetch(`${API_BASE}/api/applications`)
      .then(r => r.json())
      .then(data => {
        const raw = Array.isArray(data) ? data : (data.applications || []);
        // Normalize CSV column names → standard keys
        const normalized = raw.map(r => ({
          date:      r.Date || r.date || r.timestamp || '',
          title:     r.Role || r.title || '',
          company:   r.Company || r.company || '',
          platform:  (r.Source || r.platform || r.source || '').toLowerCase(),
          status:    r.Status || r.status || '',
          score:     r.Score || r.score || null,
          apply_url: r['Apply URL'] || r.apply_url || r.url || '',
          location:  r.Location || r.location || '',
          cover:     r['Cover Note Preview'] || '',
        }));
        setRows(normalized);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const totalApplied = rows.filter(r => /applied|success/i.test(r.status || '')).length;
  const totalSkipped = rows.filter(r => /skipped|dry run/i.test(r.status || '')).length;
  const totalErrors  = rows.filter(r => /error|failed/i.test(r.status || '')).length;
  const platforms    = ['All', ...new Set(rows.map(r => r.platform || '').filter(Boolean))];
  const statuses     = ['All', 'Applied', 'Skipped', 'Error', 'Dry Run'];

  const matchStatus = (rowStatus, filter) => {
    if (filter === 'All') return true;
    const s = rowStatus.toLowerCase();
    if (filter === 'Applied') return /applied|success/.test(s);
    if (filter === 'Skipped') return /skipped/.test(s);
    if (filter === 'Error')   return /error|failed/.test(s);
    if (filter === 'Dry Run') return /dry run/.test(s);
    return s.includes(filter.toLowerCase());
  };

  const filtered = rows.filter(r => {
    const plat    = (r.platform || '').toLowerCase();
    const title   = (r.title || '').toLowerCase();
    const company = (r.company || '').toLowerCase();
    const s = search.toLowerCase();
    return (platformFilter === 'All' || plat === platformFilter.toLowerCase())
      && matchStatus(r.status || '', statusFilter)
      && (!s || title.includes(s) || company.includes(s) || plat.includes(s));
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleExport = () => {
    const headers = ['Date', 'Title', 'Company', 'Platform', 'Status', 'Score', 'URL'];
    const csv = [headers, ...filtered.map(r => [
      r.date || r.timestamp || '',
      `"${(r.title || '').replace(/"/g, '""')}"`,
      `"${(r.company || '').replace(/"/g, '""')}"`,
      r.platform || r.source || '',
      r.status || '',
      r.score || '',
      r.apply_url || r.url || '',
    ])].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `applyflow_history_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };

  return (
    <div className="max-w-6xl pb-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Application History</h1>
          <p className="text-slate-400 text-sm">Every application tracked across all runs.</p>
        </div>
        <button onClick={handleExport}
          className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm font-semibold px-4 py-2 rounded-xl transition-colors flex items-center gap-2">
          ⬇ Export CSV
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Tracked" value={rows.length}    color="text-white" />
        <StatCard label="Applied"       value={totalApplied}   color="text-green-400" />
        <StatCard label="Skipped"       value={totalSkipped}   color="text-amber-400" />
        <StatCard label="Errors"        value={totalErrors}    color="text-red-400" />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative flex-1 min-w-48">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">🔍</span>
          <input type="text" placeholder="Search role or company…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
        <select value={platformFilter} onChange={e => { setPlatformFilter(e.target.value); setPage(1); }}
          className="bg-slate-900 border border-slate-700 text-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none">
          {platforms.map(p => <option key={p} value={p}>{p === 'All' ? '📡 All Platforms' : p}</option>)}
        </select>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-slate-900 border border-slate-700 text-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none">
          {statuses.map(s => <option key={s} value={s}>{s === 'All' ? '🏷 All Statuses' : s}</option>)}
        </select>
        {(search || platformFilter !== 'All' || statusFilter !== 'All') && (
          <button onClick={() => { setSearch(''); setPlatformFilter('All'); setStatusFilter('All'); setPage(1); }}
            className="text-xs text-slate-500 hover:text-white transition-colors px-2">✕ Clear</button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-20 text-slate-500">
          <div className="text-4xl mb-3 animate-pulse">⏳</div>
          <p>Loading history…</p>
        </div>
      ) : paginated.length === 0 ? (
        <div className="text-center py-20 bg-slate-900 border border-slate-800 rounded-2xl">
          <div className="text-5xl mb-4">{rows.length === 0 ? '📭' : '🔍'}</div>
          <h3 className="text-white font-semibold mb-2">
            {rows.length === 0 ? 'No applications tracked yet' : 'No results match your filters'}
          </h3>
          <p className="text-slate-400 text-sm max-w-sm mx-auto">
            {rows.length === 0 ? 'Run the bot to start tracking. All applications appear here automatically.'
              : 'Try adjusting your search or filter.'}
          </p>
        </div>
      ) : (
        <>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 text-xs uppercase tracking-wider">
                  <th className="text-left px-5 py-3 font-semibold">Date</th>
                  <th className="text-left px-5 py-3 font-semibold">Role / Company</th>
                  <th className="text-left px-5 py-3 font-semibold">Platform</th>
                  <th className="text-left px-5 py-3 font-semibold">Status</th>
                  <th className="text-left px-5 py-3 font-semibold">Score</th>
                  <th className="text-left px-5 py-3 font-semibold">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {paginated.map((row, i) => {
                  const plat  = (row.platform || 'unknown').toLowerCase();
                  const status = row.status || 'Unknown';
                  const platStyle = PLATFORM_COLORS[plat] || PLATFORM_COLORS.generic_web;
                  const statusKey = /applied|success/i.test(status) ? 'Applied'
                    : /error|failed/i.test(status) ? 'Error'
                    : /skipped/i.test(status) ? 'Skipped'
                    : /dry run/i.test(status) ? 'Dry Run' : '';
                  const statusStyle = STATUS_STYLES[statusKey] || 'bg-slate-800 text-slate-400 border-slate-700';
                  const rawDate = row.date || row.timestamp;
                  const date = rawDate
                    ? new Date(rawDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })
                    : '—';
                  return (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-5 py-3 text-slate-500 whitespace-nowrap text-xs">{date}</td>
                      <td className="px-5 py-3">
                        <p className="text-white font-medium truncate max-w-xs">{row.title || '—'}</p>
                        <p className="text-slate-500 text-xs">{row.company || '—'}</p>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded border capitalize ${platStyle}`}>
                          {plat}
                        </span>
                      </td>
                      <td className="px-5 py-3 max-w-[160px]">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded border block truncate ${statusStyle}`}
                          title={status}>
                          {status.length > 24 ? status.slice(0, 24) + '…' : status}
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
          </div>
          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 text-sm text-slate-500">
            <span>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
            </span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg disabled:opacity-40 hover:bg-slate-700 transition-colors">
                ← Prev
              </button>
              <span className="px-3 py-1.5 text-slate-400 font-medium">{page} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg disabled:opacity-40 hover:bg-slate-700 transition-colors">
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
