import { useEffect, useRef, useState } from 'react';
import {
  Briefcase,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Play,
  Activity,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

interface Metrics {
  total: number;
  applied: number;
  failed: number;
  manual: number;
  skipped: number;
  average_score: number;
}

interface Application {
  Date: string;
  Company: string;
  Role: string;
  Location: string;
  Source: string;
  Status: string;
  Score: number | string;
  'Apply URL': string;
}

// Use relative URLs — Vite proxy forwards /api/* to localhost:8000
const API = '';

function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [showBrowser, setShowBrowser] = useState(true);  // 👁 Show Chrome live
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [error, setError] = useState<string | null>(null);
  const [botStatus, setBotStatus] = useState<'idle' | 'running' | 'error'>('idle');
  const logEndRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<EventSource | null>(null);

  // Auto-scroll logs terminal
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveLogs]);

  useEffect(() => {
    fetchData();
    connectSSE();
    const dataInterval = setInterval(fetchData, 10000);
    const statusInterval = setInterval(fetchBotStatus, 3000);
    return () => {
      clearInterval(dataInterval);
      clearInterval(statusInterval);
      sseRef.current?.close();
    };
  }, []);

  // Connect to SSE log stream — auto-reconnects if dropped
  const connectSSE = () => {
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource(`${API}/api/logs/stream`);
    es.onmessage = (e) => {
      if (e.data && !e.data.startsWith(':')) {
        setLiveLogs(prev => [...prev.slice(-300), e.data]); // keep last 300 lines
      }
    };
    es.onerror = () => {
      // Reconnect after 3s on error
      es.close();
      setTimeout(connectSSE, 3000);
    };
    sseRef.current = es;
  };

  const fetchBotStatus = async () => {
    try {
      const res = await fetch(`${API}/api/status`);
      if (res.ok) {
        const data = await res.json();
        setBotStatus(data.running ? 'running' : 'idle');
      }
    } catch {
      // backend offline — keep last known state
    }
  };

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/applications`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setMetrics(data.metrics);
      setApplications(data.applications || []);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Backend unreachable: ${msg}. Make sure dashboard.py is running.`);
    } finally {
      setLoading(false);
    }
  };

  const handleRunBot = async () => {
    if (botStatus === 'running') return;
    setRunning(true);
    try {
      const res = await fetch(`${API}/api/run-bot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: dryRun, headless: !showBrowser }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      if (data.status === 'already_running') {
        alert('⚠️ Bot is already running!');
      } else {
        setBotStatus('running');
        setLiveLogs([]);
        connectSSE(); // reconnect SSE to pick up new log file
      }
    } catch {
      alert('❌ Failed to start bot. Make sure dashboard.py is running on port 8000.');
      setBotStatus('error');
    } finally {
      setTimeout(() => setRunning(false), 1500);
    }
  };


  const getStatusBadge = (status: string) => {
    if (!status) return <span className="status-badge">Unknown</span>;
    const s = status.toLowerCase();
    if (s.includes('applied') || s.includes('success')) return <span className="status-badge status-success">Applied ✓</span>;
    if (s.includes('error') || s.includes('failed')) return <span className="status-badge status-error">Failed</span>;
    if (s.includes('manual') || s.includes('pending')) return <span className="status-badge status-manual">Manual</span>;
    if (s.includes('dry run')) return <span className="status-badge status-dry">Dry Run</span>;
    if (s.includes('skipped')) return <span className="status-badge">Skipped</span>;
    return <span className="status-badge">{status}</span>;
  };

  const filteredApps = applications.filter(app => {
    const s = (app.Status || '').toLowerCase();
    if (sourceFilter !== 'All' && app.Source?.toLowerCase() !== sourceFilter.toLowerCase()) return false;
    if (statusFilter === 'Applied' && !s.includes('applied') && !s.includes('success')) return false;
    if (statusFilter === 'Failed' && !s.includes('error') && !s.includes('failed')) return false;
    if (statusFilter === 'Manual' && !s.includes('manual') && !s.includes('pending')) return false;
    if (statusFilter === 'Skipped' && !s.includes('skipped') && !s.includes('dry')) return false;
    return true;
  });

  const sources = ['linkedin', 'internshala', 'indeed', 'unstop'];
  const sourceColors = ['#0a66c2', '#10b981', '#2563eb', '#f59e0b'];
  const sourceData = {
    labels: ['LinkedIn', 'Internshala', 'Indeed', 'Unstop'],
    datasets: [{
      label: 'Applications by Source',
      data: sources.map(s => applications.filter(a => a.Source?.toLowerCase() === s).length),
      backgroundColor: sourceColors,
      borderWidth: 0,
    }],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'bottom' as const, labels: { color: '#94a3b8', padding: 20 } },
    },
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>
          <Activity className="header-icon" size={36} />
          ApplyFlow Dashboard
        </h1>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {lastUpdated && (
            <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
              Updated {lastUpdated}
            </span>
          )}
          {/* Bot status dot */}
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: botStatus === 'running' ? '#34d399' : botStatus === 'error' ? '#f87171' : '#64748b' }}>
            <span style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: botStatus === 'running' ? '#34d399' : botStatus === 'error' ? '#f87171' : '#475569',
              display: 'inline-block',
              boxShadow: botStatus === 'running' ? '0 0 8px #34d399' : 'none',
              animation: botStatus === 'running' ? 'pulse 1.5s infinite' : 'none',
            }} />
            {botStatus === 'running' ? 'Bot Running' : botStatus === 'error' ? 'Error' : 'Idle'}
          </span>
          {/* 👁 Show Browser toggle */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: showBrowser ? '#34d399' : '#94a3b8', cursor: 'pointer', userSelect: 'none', padding: '0.3rem 0.6rem', borderRadius: '6px', border: `1px solid ${showBrowser ? 'rgba(52,211,153,0.3)' : 'rgba(255,255,255,0.08)'}`, transition: 'all 0.2s' }}>
            <input
              type="checkbox"
              checked={showBrowser}
              onChange={e => setShowBrowser(e.target.checked)}
              style={{ accentColor: '#34d399', width: '13px', height: '13px' }}
            />
            👁️ Show Browser
          </label>
          {/* Dry Run toggle */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: dryRun ? '#a78bfa' : '#94a3b8', cursor: 'pointer', userSelect: 'none', padding: '0.3rem 0.6rem', borderRadius: '6px', border: `1px solid ${dryRun ? 'rgba(167,139,250,0.3)' : 'rgba(255,255,255,0.08)'}`, transition: 'all 0.2s' }}>
            <input
              type="checkbox"
              checked={dryRun}
              onChange={e => setDryRun(e.target.checked)}
              style={{ accentColor: '#a78bfa', width: '13px', height: '13px' }}
            />
            🧪 Dry Run
          </label>
          <button className="run-btn" onClick={fetchData} style={{ padding: '0.6rem 1rem' }}>
            <RefreshCw size={16} />
          </button>
          <button
            className="run-btn"
            onClick={handleRunBot}
            disabled={running || botStatus === 'running'}
            style={{
              background: dryRun
                ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                : showBrowser
                ? 'linear-gradient(135deg, #059669, #34d399)'
                : undefined,
            }}
          >
            <Play size={18} />
            {botStatus === 'running' ? 'Bot Running…' : running ? 'Starting…' : dryRun ? '🧪 Dry Run' : showBrowser ? '👁️ Run + Show' : '▶️ Run Bot'}
          </button>
        </div>
      </header>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          color: '#f87171', borderRadius: '12px', padding: '1rem 1.5rem',
          marginBottom: '2rem', fontSize: '0.9rem',
        }}>
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="metrics-grid">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="metric-card skeleton" style={{ height: '140px' }} />
          ))}
        </div>
      ) : (
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-header"><Briefcase size={18} /> Total Found</div>
            <div className="metric-value">{metrics?.total ?? 0}</div>
          </div>
          <div className="metric-card">
            <div className="metric-header"><CheckCircle2 size={18} color="#34d399" /> Applied</div>
            <div className="metric-value">{metrics?.applied ?? 0}</div>
          </div>
          <div className="metric-card">
            <div className="metric-header"><XCircle size={18} color="#f87171" /> Failed</div>
            <div className="metric-value">{metrics?.failed ?? 0}</div>
          </div>
          <div className="metric-card">
            <div className="metric-header"><AlertCircle size={18} color="#fbbf24" /> Manual</div>
            <div className="metric-value">{metrics?.manual ?? 0}</div>
          </div>
          <div className="metric-card">
            <div className="metric-header"><Activity size={18} color="#a78bfa" /> Avg Score</div>
            <div className="metric-value">{metrics?.average_score ?? 0}/10</div>
          </div>
        </div>
      )}

      <div className="main-content">
        {/* Applications table */}
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <h2 style={{ margin: 0 }}>
              Applications
              <span style={{ color: '#94a3b8', fontSize: '0.85rem', fontWeight: 400, marginLeft: '0.75rem' }}>
                ({filteredApps.length})
              </span>
            </h2>
            <div className="filters">
              <select className="filter-select" value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
                <option value="All">All Sources</option>
                <option value="linkedin">LinkedIn</option>
                <option value="internshala">Internshala</option>
                <option value="indeed">Indeed</option>
                <option value="unstop">Unstop</option>
              </select>
              <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="All">All Statuses</option>
                <option value="Applied">Applied</option>
                <option value="Failed">Failed</option>
                <option value="Manual">Manual</option>
                <option value="Skipped">Skipped</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="skeleton" style={{ height: '300px' }} />
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Company / Role</th>
                    <th>Date</th>
                    <th>Source</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Link</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredApps.slice(0, 30).map((app, idx) => (
                    <tr key={idx}>
                      <td>
                        <div className="company-cell">
                          {app.Company || 'Unknown'}
                          <span className="role-cell">{app.Role || 'Role not specified'}</span>
                        </div>
                      </td>
                      <td style={{ whiteSpace: 'nowrap', color: '#94a3b8', fontSize: '0.85rem' }}>
                        {app.Date ? app.Date.split(' ')[0] : 'N/A'}
                      </td>
                      <td style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>{app.Source || '—'}</td>
                      <td style={{ fontSize: '0.9rem' }}>
                        {app.Score ? (
                          <span style={{ color: Number(app.Score) >= 7 ? '#34d399' : Number(app.Score) >= 5 ? '#fbbf24' : '#f87171' }}>
                            {app.Score}/10
                          </span>
                        ) : '—'}
                      </td>
                      <td>{getStatusBadge(app.Status)}</td>
                      <td>
                        {app['Apply URL'] && (
                          <a href={app['Apply URL']} target="_blank" rel="noreferrer" className="apply-btn">
                            Open <ExternalLink size={13} />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                  {filteredApps.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                        {error ? 'Backend offline — start dashboard.py' : 'No applications yet. Run the bot!'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Chart panel */}
        <div className="panel">
          <h2>Application Sources</h2>
          {loading ? (
            <div className="skeleton" style={{ height: '300px' }} />
          ) : applications.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
              No data yet
            </div>
          ) : (
            <div style={{ padding: '1rem' }}>
              <Doughnut data={sourceData} options={chartOptions} />
            </div>
          )}

          {/* Mini stats below chart */}
          {!loading && metrics && (
            <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {[
                { label: 'Applied', value: metrics.applied, color: '#34d399' },
                { label: 'Manual', value: metrics.manual, color: '#fbbf24' },
                { label: 'Failed', value: metrics.failed, color: '#f87171' },
                { label: 'Skipped', value: metrics.skipped, color: '#94a3b8' },
              ].map(item => (
                <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{item.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                      width: `${metrics.total ? (item.value / metrics.total) * 120 : 0}px`,
                      height: '6px', borderRadius: '3px',
                      background: item.color, minWidth: '4px', maxWidth: '120px',
                      transition: 'width 0.5s ease',
                    }} />
                    <span style={{ color: item.color, fontWeight: 600, fontSize: '0.9rem', minWidth: '28px', textAlign: 'right' }}>
                      {item.value}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 📺 Live Log Terminal */}
      <div className="panel" style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>
            📺 Live Bot Terminal
            {botStatus === 'running' && (
              <span style={{ marginLeft: '0.75rem', fontSize: '0.75rem', color: '#34d399', fontWeight: 400 }}>
                ● streaming
              </span>
            )}
          </h2>
          <button
            onClick={() => setLiveLogs([])}
            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: '#64748b', borderRadius: '6px', padding: '0.3rem 0.7rem', cursor: 'pointer', fontSize: '0.75rem' }}
          >
            Clear
          </button>
        </div>
        <div style={{
          background: '#0d1117',
          borderRadius: '10px',
          padding: '1rem 1.25rem',
          height: '320px',
          overflowY: 'auto',
          fontFamily: '"Cascadia Code", "Fira Code", monospace',
          fontSize: '0.78rem',
          lineHeight: '1.6',
          border: '1px solid rgba(255,255,255,0.06)',
        }}>
          {liveLogs.length === 0 ? (
            <span style={{ color: '#475569' }}>Waiting for bot logs… Click "👁️ Run + Show" to start.</span>
          ) : (
            liveLogs.map((line, i) => {
              const isError = line.includes('ERROR') || line.includes('❌');
              const isWarn  = line.includes('WARNING') || line.includes('⚠️');
              const isOk    = line.includes('[YES]') || line.includes('✅') || line.includes('Applied');
              const isSkip  = line.includes('[SKIP]') || line.includes('[DUP]');
              const color = isError ? '#f87171' : isWarn ? '#fbbf24' : isOk ? '#34d399' : isSkip ? '#64748b' : '#94a3b8';
              return (
                <div key={i} style={{ color, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {line}
                </div>
              );
            })
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}

export default App;
