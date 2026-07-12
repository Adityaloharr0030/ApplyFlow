import { useState, useEffect, useRef, useCallback } from 'react'
import './index.css'

const API_BASE = '' // Same origin (proxied via vite config)

// ── Sidebar Navigation ──────────────────────────────────────────────────────
function Sidebar({ activePage, setActivePage, session }) {
  const navItems = [
    { id: 'overview', icon: '📊', label: 'Overview' },
    { id: 'applications', icon: '📋', label: 'Applications' },
    { id: 'schedule', icon: '📅', label: 'Schedules' },
    { id: 'logs', icon: '🖥️', label: 'Live Logs' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">⚡</div>
        <h1>ApplyFlow</h1>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <div
            key={item.id}
            className={`nav-item ${activePage === item.id ? 'active' : ''}`}
            onClick={() => setActivePage(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar-session">
        <div className="session-status">
          <span className={`status-dot ${session.status}`} />
          <span>{session.status === 'running' ? 'Session Active' : session.status === 'paused' ? 'Paused' : 'Idle'}</span>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {session.status === 'running' ? `${session.applied_count} applied this session` : 'No active session'}
        </div>
      </div>
    </aside>
  )
}

// ── Overview Page ───────────────────────────────────────────────────────────
function OverviewPage({ stats, session, events, onStart, onPause, onResume }) {
  return (
    <>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p className="subtitle">Real-time overview of your automated applications</p>
        </div>
        <div className="header-actions">
          {session.status === 'running' ? (
            <button className="btn btn-warning" onClick={onPause}>⏸ Pause</button>
          ) : session.status === 'paused' ? (
            <button className="btn btn-success" onClick={onResume}>▶ Resume</button>
          ) : (
            <button className="btn btn-primary" onClick={onStart}>🚀 Launch Bot</button>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="glass-card stat-card">
          <div className="card-title">Total Applied</div>
          <div className="stat-value accent">{stats.total_applied || 0}</div>
        </div>
        <div className="glass-card stat-card">
          <div className="card-title">Today</div>
          <div className="stat-value success">{stats.today_applied || 0}</div>
        </div>
        <div className="glass-card stat-card">
          <div className="card-title">Success Rate</div>
          <div className="stat-value info">{stats.success_rate || 0}%</div>
        </div>
        <div className="glass-card stat-card">
          <div className="card-title">This Session</div>
          <div className="stat-value warning">{session.applied_count || 0}</div>
        </div>
        <div className="glass-card stat-card">
          <div className="card-title">Platforms</div>
          <div className="stat-value" style={{ color: 'var(--text-primary)' }}>
            {Object.keys(stats.platforms || {}).length}
          </div>
        </div>
      </div>

      {/* Live Session + Activity Feed */}
      <div className="live-session-card">
        <div className="glass-card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            🔴 Live Session
          </h3>
          <div className="session-monitor">
            <div className="session-info">
              <div className={`status-indicator ${session.status}`} />
              <span className="status-text">{session.status}</span>
            </div>
            <div className="session-detail">
              <span className="label">Platform</span>
              <span className="value">{session.current_platform || '—'}</span>
            </div>
            <div className="session-detail">
              <span className="label">Current Listing</span>
              <span className="value" style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {session.current_listing || '—'}
              </span>
            </div>
            <div className="session-detail">
              <span className="label">Step</span>
              <span className="value">{session.current_step || '—'}</span>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
              <div style={{ flex: 1, textAlign: 'center', padding: '0.5rem', background: 'var(--success-bg)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--success)' }}>{session.applied_count}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Applied</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center', padding: '0.5rem', background: 'var(--warning-bg)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--warning)' }}>{session.skipped_count}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Skipped</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center', padding: '0.5rem', background: 'var(--danger-bg)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--danger)' }}>{session.error_count}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Errors</div>
              </div>
            </div>
          </div>
        </div>

        <div className="glass-card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            ⚡ Activity Feed
          </h3>
          <div className="activity-feed">
            {events.length === 0 ? (
              <div className="empty-state">
                <div className="icon">📭</div>
                <div className="desc">No activity yet. Launch the bot to get started.</div>
              </div>
            ) : (
              events.slice(-20).reverse().map((event, idx) => (
                <div key={idx} className={`activity-item ${event.type || 'info'}`}>
                  <span className="time">
                    {event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                  </span>
                  <span className="message">{event.message || event.type || 'Event'}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Platform Breakdown + Recent */}
      <div className="live-session-card">
        <div className="glass-card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            🏢 Platform Breakdown
          </h3>
          {Object.keys(stats.platforms || {}).length === 0 ? (
            <div className="empty-state">
              <div className="desc">No applications recorded yet.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {Object.entries(stats.platforms || {}).map(([platform, count]) => (
                <div key={platform} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className={`platform-badge platform-${platform.toLowerCase()}`}>{platform}</span>
                  <div style={{ flex: 1, margin: '0 1rem', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, (count / (stats.total_applied || 1)) * 100)}%`,
                      background: `var(--${platform.toLowerCase()}, var(--accent))`,
                      borderRadius: '3px',
                      transition: 'width 0.5s ease'
                    }} />
                  </div>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', minWidth: '2rem', textAlign: 'right' }}>{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="glass-card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            🕐 Recent Applications
          </h3>
          {(stats.recent || []).length === 0 ? (
            <div className="empty-state">
              <div className="desc">No recent applications.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {(stats.recent || []).slice(0, 8).map((app, idx) => (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.5rem 0.75rem',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.8rem'
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{app.Company || app.company || '—'}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{app.Role || app.Title || app.title || '—'}</div>
                  </div>
                  <span className={`status-badge status-${(app.Status || 'pending').split(' ')[0]}`}>
                    {app.Status || 'Pending'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ── Applications Page ───────────────────────────────────────────────────────
function ApplicationsPage({ applications }) {
  const [filter, setFilter] = useState('')

  const filtered = applications.filter(app => {
    if (!filter) return true
    const search = filter.toLowerCase()
    return (
      (app.Company || '').toLowerCase().includes(search) ||
      (app.Role || app.Title || '').toLowerCase().includes(search) ||
      (app.Source || app.Platform || '').toLowerCase().includes(search) ||
      (app.Status || '').toLowerCase().includes(search)
    )
  })

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Applications</h2>
          <p className="subtitle">{applications.length} total applications tracked</p>
        </div>
        <div className="header-actions">
          <input
            type="text"
            placeholder="🔍 Search company, role, platform..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--card-border)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.6rem 1rem',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              width: '280px',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />
        </div>
      </div>

      <div className="glass-card" style={{ overflow: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Company</th>
              <th>Role</th>
              <th>Platform</th>
              <th>Score</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem' }}>
                  {filter ? 'No matching applications found.' : 'No applications yet. Launch the bot to get started!'}
                </td>
              </tr>
            ) : (
              filtered.slice(0, 100).map((app, idx) => (
                <tr key={idx}>
                  <td style={{ whiteSpace: 'nowrap' }}>{app.Date || '—'}</td>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{app.Company || '—'}</td>
                  <td>{app.Role || app.Title || '—'}</td>
                  <td>
                    <span className={`platform-badge platform-${(app.Source || app.Platform || 'unknown').toLowerCase()}`}>
                      {app.Source || app.Platform || '—'}
                    </span>
                  </td>
                  <td>{app.Score || '—'}</td>
                  <td>
                    <span className={`status-badge status-${(app.Status || 'pending').split(' ')[0]}`}>
                      {app.Status || 'Pending'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}

// ── Schedule Page ───────────────────────────────────────────────────────────
function SchedulePage({ schedules }) {
  return (
    <>
      <div className="page-header">
        <div>
          <h2>Schedules</h2>
          <p className="subtitle">Configure automated recurring sessions</p>
        </div>
      </div>

      {schedules.length === 0 ? (
        <div className="glass-card">
          <div className="empty-state">
            <div className="icon">📅</div>
            <div className="title">No Schedules Configured</div>
            <div className="desc">Edit <code>data/schedules.json</code> to add platform schedules.</div>
          </div>
        </div>
      ) : (
        <div className="schedule-grid">
          {schedules.map((s, idx) => (
            <div key={idx} className="glass-card schedule-card">
              <div className="schedule-header">
                <span className={`platform-badge platform-${s.platform}`}>
                  {s.platform}
                </span>
                <div className={`toggle-switch ${s.enabled !== false ? 'active' : ''}`} />
              </div>
              <div className="schedule-time">{s.time}</div>
              <div className="schedule-meta">
                <div>📆 {s.days || 'daily'}</div>
                <div>⏱ {s.runtime_minutes || 30} min runtime</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

// ── Logs Page ───────────────────────────────────────────────────────────────
function LogsPage({ logs }) {
  const terminalRef = useRef(null)

  useEffect(() => {
    terminalRef.current?.scrollTo({ top: terminalRef.current.scrollHeight, behavior: 'smooth' })
  }, [logs])

  const getLineClass = (line) => {
    const lower = line.toLowerCase()
    if (lower.includes('error') || lower.includes('✗') || lower.includes('failed')) return 'error'
    if (lower.includes('warning') || lower.includes('⚠')) return 'warning'
    if (lower.includes('✓') || lower.includes('✅') || lower.includes('success')) return 'success'
    return ''
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Live Logs</h2>
          <p className="subtitle">Real-time terminal output from the bot</p>
        </div>
      </div>

      <div className="glass-card">
        <div className="terminal-container" ref={terminalRef}>
          {logs.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '8rem' }}>
              No logs available. Start a session to see output here.
            </div>
          ) : (
            logs.map((line, idx) => (
              <div key={idx} className={`terminal-line ${getLineClass(line)}`}>{line}</div>
            ))
          )}
        </div>
      </div>
    </>
  )
}

// ── Main App ────────────────────────────────────────────────────────────────
function App() {
  const [activePage, setActivePage] = useState('overview')
  const [stats, setStats] = useState({ total_applied: 0, today_applied: 0, platforms: {}, success_rate: 0, recent: [], session: {} })
  const [session, setSession] = useState({ status: 'idle', applied_count: 0, skipped_count: 0, error_count: 0, events: [] })
  const [applications, setApplications] = useState([])
  const [logs, setLogs] = useState([])
  const [schedules, setSchedules] = useState([])
  const [events, setEvents] = useState([])
  const wsRef = useRef(null)

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
        if (data.session) setSession(prev => ({ ...prev, ...data.session }))
      }
    } catch (err) { console.debug('Stats fetch failed:', err) }
  }, [])

  const fetchApplications = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/applications`)
      if (res.ok) {
        const data = await res.json()
        setApplications(Array.isArray(data) ? data : [])
      }
    } catch (err) { console.debug('Applications fetch failed:', err) }
  }, [])

  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/logs?lines=200`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
      }
    } catch (err) { console.debug('Logs fetch failed:', err) }
  }, [])

  const fetchSchedules = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/schedule`)
      if (res.ok) {
        const data = await res.json()
        setSchedules(Array.isArray(data) ? data : [])
      }
    } catch (err) { console.debug('Schedules fetch failed:', err) }
  }, [])

  const fetchSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/session/live`)
      if (res.ok) {
        const data = await res.json()
        setSession(data)
        if (data.events) setEvents(data.events)
      }
    } catch (err) { console.debug('Session fetch failed:', err) }
  }, [])

  // WebSocket connection for real-time events
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/live`

    const connectWs = () => {
      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => console.log('WebSocket connected')
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'session_state') {
              setSession(data.data)
              if (data.data.events) setEvents(data.data.events)
            } else {
              setEvents(prev => [...prev.slice(-99), data])
            }
          } catch (e) { /* ignore parse errors */ }
        }
        ws.onclose = () => setTimeout(connectWs, 3000)
        ws.onerror = () => ws.close()
      } catch (e) { /* WebSocket not available, fallback to polling */ }
    }

    connectWs()
    return () => wsRef.current?.close()
  }, [])

  // Polling fallback
  useEffect(() => {
    fetchStats()
    fetchSession()
    fetchSchedules()

    const statsInterval = setInterval(fetchStats, 3000)
    const sessionInterval = setInterval(fetchSession, 2000)

    return () => {
      clearInterval(statsInterval)
      clearInterval(sessionInterval)
    }
  }, [fetchStats, fetchSession, fetchSchedules])

  // Fetch page-specific data when page changes
  useEffect(() => {
    if (activePage === 'applications') fetchApplications()
    if (activePage === 'logs') fetchLogs()
    if (activePage === 'schedule') fetchSchedules()

    let interval
    if (activePage === 'logs') {
      interval = setInterval(fetchLogs, 2000)
    } else if (activePage === 'applications') {
      interval = setInterval(fetchApplications, 5000)
    }

    return () => interval && clearInterval(interval)
  }, [activePage, fetchApplications, fetchLogs, fetchSchedules])

  const handleStart = async (platform) => {
    try {
      const url = platform ? `${API_BASE}/api/start?platform=${platform}` : `${API_BASE}/api/start`
      const res = await fetch(url, { method: 'POST' })
      const data = await res.json()
      if (data.message?.includes('already')) {
        alert('⚠️ Bot is already running!')
      } else {
        setSession(prev => ({ ...prev, status: 'running' }))
        fetchSession()
      }
    } catch (err) {
      alert('❌ Failed to start bot. Is the dashboard API running?')
    }
  }

  const handlePause = async () => {
    try {
      await fetch(`${API_BASE}/api/session/pause`, { method: 'POST' })
      setSession(prev => ({ ...prev, status: 'paused' }))
    } catch (err) { console.error('Pause failed:', err) }
  }

  const handleResume = async () => {
    try {
      await fetch(`${API_BASE}/api/session/resume`, { method: 'POST' })
      setSession(prev => ({ ...prev, status: 'running' }))
    } catch (err) { console.error('Resume failed:', err) }
  }

  return (
    <div className="dashboard-layout">
      <Sidebar activePage={activePage} setActivePage={setActivePage} session={session} />

      <main className="main-content">
        {activePage === 'overview' && (
          <OverviewPage
            stats={stats}
            session={session}
            events={events}
            onStart={() => handleStart()}
            onPause={handlePause}
            onResume={handleResume}
          />
        )}
        {activePage === 'applications' && <ApplicationsPage applications={applications} />}
        {activePage === 'schedule' && <SchedulePage schedules={schedules} />}
        {activePage === 'logs' && <LogsPage logs={logs} />}
      </main>
    </div>
  )
}

export default App
