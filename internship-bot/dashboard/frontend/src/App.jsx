import { useState, useEffect, useRef } from 'react'
import './index.css'

function App() {
  const [stats, setStats] = useState({ total_applied: 0, platforms: {}, recent: [] })
  const [logs, setLogs] = useState([])
  const [applications, setApplications] = useState([])
  const [isRunning, setIsRunning] = useState(false)
  
  const terminalEndRef = useRef(null)

  const fetchData = async () => {
    try {
      const statsRes = await fetch('http://127.0.0.1:8000/api/stats')
      const statsData = await statsRes.json()
      setStats(statsData)

      const appsRes = await fetch('http://127.0.0.1:8000/api/applications')
      const appsData = await appsRes.json()
      setApplications(appsData)

      const logsRes = await fetch('http://127.0.0.1:8000/api/logs')
      const logsData = await logsRes.json()
      setLogs(logsData.logs)
    } catch (err) {
      console.error("Error fetching data:", err)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs])

  const handleLaunch = async () => {
    setIsRunning(true)
    try {
      await fetch('http://127.0.0.1:8000/api/start', { method: 'POST' })
    } catch (err) {
      console.error(err)
    }
    setTimeout(() => setIsRunning(false), 5000)
  }

  return (
    <div className="dashboard-container">
      <header>
        <h1>ApplyFlow Dashboard</h1>
        <button 
          className="btn-launch" 
          onClick={handleLaunch}
          disabled={isRunning}
        >
          {isRunning ? "Starting..." : "🚀 Launch Bot"}
        </button>
      </header>

      <div className="grid-top">
        <div className="glass-card">
          <div className="stat-label">Total Applied</div>
          <div className="stat-value">{stats.total_applied}</div>
        </div>
        <div className="glass-card">
          <div className="stat-label">Internshala</div>
          <div className="stat-value">{stats.platforms?.Internshala || 0}</div>
        </div>
        <div className="glass-card">
          <div className="stat-label">LinkedIn</div>
          <div className="stat-value">{stats.platforms?.LinkedIn || 0}</div>
        </div>
        <div className="glass-card">
          <div className="stat-label">LetsInternship</div>
          <div className="stat-value">{stats.platforms?.LetsInternship || 0}</div>
        </div>
      </div>

      <div className="grid-main">
        <div className="glass-card">
          <h2 style={{ marginBottom: "1rem", fontSize: "1.25rem" }}>Live Terminal Feed</h2>
          <div className="terminal-container">
            {logs.map((line, idx) => (
              <div key={idx} className="terminal-line">{line}</div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        </div>

        <div className="glass-card" style={{ height: "480px", overflowY: "auto" }}>
          <h2 style={{ marginBottom: "1rem", fontSize: "1.25rem" }}>Recent Applications</h2>
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {applications.slice(0, 15).map((app, idx) => (
                <tr key={idx}>
                  <td>{app.Company}</td>
                  <td>{app.Title}</td>
                  <td>
                    <span className={`status-badge status-${app.Status.split(' ')[0]}`}>
                      {app.Status}
                    </span>
                  </td>
                </tr>
              ))}
              {applications.length === 0 && (
                <tr>
                  <td colSpan="3" style={{ textAlign: "center", color: "var(--text-secondary)" }}>
                    No applications yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default App
