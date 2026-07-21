import { useState, useEffect, useRef } from 'react';
import { apiFetch as fetch } from '../utils/apiFetch';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
const DAY_LABELS = { mon: 'M', tue: 'T', wed: 'W', thu: 'Th', fri: 'F', sat: 'Sa', sun: 'Su' };

export default function SchedulesPage() {
  const [schedule, setSchedule] = useState({
    enabled: false,
    days: ['mon', 'tue', 'wed', 'thu', 'fri'],
    time: '09:00',
    dry_run: true,
  });
  const [status, setStatus] = useState({ is_running: false, next_run: null });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [logs, setLogs] = useState([]);
  const logRef = useRef(null);

  const fetchStatus = () => {
    fetch(`${API_BASE}/api/status`).then(r => r.json()).then(d => setStatus(d)).catch(() => {});
  };

  const fetchLogs = () => {
    fetch(`${API_BASE}/api/logs?lines=12`).then(r => r.json()).then(d => {
      if (Array.isArray(d)) setLogs(d);
      else if (d.lines) setLogs(d.lines);
    }).catch(() => {});
  };

  useEffect(() => {
    fetch(`${API_BASE}/api/schedule`)
      .then(r => r.json())
      .then(d => setSchedule(prev => ({ ...prev, ...d })))
      .catch(console.error);
    fetchStatus();
    fetchLogs();
  }, []);

  // Poll status + logs every 3s when running
  useEffect(() => {
    if (!status.is_running) return;
    const id = setInterval(() => { fetchStatus(); fetchLogs(); }, 3000);
    return () => clearInterval(id);
  }, [status.is_running]);

  // Auto-scroll log panel to bottom
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);


  const toggleDay = (day) => {
    setSchedule(prev => ({
      ...prev,
      days: prev.days.includes(day)
        ? prev.days.filter(d => d !== day)
        : [...prev.days, day],
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`${API_BASE}/api/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schedule),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      alert('Failed to save schedule.');
    }
    setSaving(false);
  };

  const handleRunNow = async (dryRun = false) => {
    try {
      const res = await fetch(`${API_BASE}/api/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: dryRun }),
      });
      const data = await res.json();
      if (data.already_running) {
        alert('Bot is already running!');
      } else {
        alert(dryRun ? '🧪 Dry run started! Check the Dashboard.' : '🚀 Bot launched! Check the Dashboard.');
      }
      fetch(`${API_BASE}/api/status`).then(r => r.json()).then(d => setStatus(d));
    } catch {
      alert('Failed to start bot.');
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/api/stop`, { method: 'POST' });
      fetch(`${API_BASE}/api/status`).then(r => r.json()).then(d => setStatus(d));
    } catch {
      alert('Failed to stop bot.');
    }
  };

  return (
    <div className="max-w-3xl pb-10">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-1">Schedules</h1>
        <p className="text-slate-400 text-sm">Set a recurring schedule or launch the bot manually for an instant run.</p>
      </div>

      {/* Current Status */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span>🔴</span> Bot Status
        </h2>
        <div className="flex items-center justify-between">
          <div>
            <span className={`text-sm font-bold px-3 py-1 rounded-full ${
              status.is_running
                ? 'bg-green-900/30 text-green-400 border border-green-800/50'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}>
              {status.is_running ? '● RUNNING' : '● IDLE'}
            </span>
            {status.next_run && (
              <p className="text-xs text-slate-500 mt-2">Next scheduled run: {status.next_run}</p>
            )}
          </div>
          {status.is_running && (
            <button
              onClick={handleStop}
              className="bg-red-600 hover:bg-red-500 text-white font-bold px-4 py-2 rounded-lg text-sm transition-colors"
            >
              ⏹ Stop Bot
            </button>
          )}
        </div>
      </div>

      {/* Manual Run Buttons */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-6">
        <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
          <span>🚀</span> Manual Run
        </h2>
        <p className="text-slate-400 text-sm mb-4">Launch a one-shot run immediately. DRY_RUN mode goes through the full flow but stops before submitting.</p>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => handleRunNow(false)}
            disabled={status.is_running}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white font-bold px-5 py-2.5 rounded-lg text-sm transition-colors flex items-center gap-2"
          >
            🚀 Run Now (Live)
          </button>
          <button
            onClick={() => handleRunNow(true)}
            disabled={status.is_running}
            className="bg-amber-700 hover:bg-amber-600 disabled:opacity-40 text-white font-bold px-5 py-2.5 rounded-lg text-sm transition-colors flex items-center gap-2"
          >
            🧪 Run Now (Dry Run)
          </button>
        </div>
      </div>

      {/* Scheduler Config */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <span>🗓️</span> Recurring Schedule
            </h2>
            <p className="text-slate-400 text-sm mt-0.5">Run the bot automatically on selected days at a fixed time.</p>
          </div>
          <button
            onClick={() => setSchedule(prev => ({ ...prev, enabled: !prev.enabled }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${
              schedule.enabled ? 'bg-blue-600' : 'bg-slate-700'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${
              schedule.enabled ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>

        <div className={`space-y-6 transition-opacity duration-200 ${!schedule.enabled ? 'opacity-40 pointer-events-none' : ''}`}>
          {/* Day Picker */}
          <div>
            <label className="block text-sm text-slate-400 mb-3">Run on these days</label>
            <div className="flex gap-2 flex-wrap">
              {DAYS.map(day => (
                <button
                  key={day}
                  onClick={() => toggleDay(day)}
                  className={`w-10 h-10 rounded-full text-sm font-bold transition-all ${
                    schedule.days?.includes(day)
                      ? 'bg-blue-600 text-white border-2 border-blue-400'
                      : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-500'
                  }`}
                >
                  {DAY_LABELS[day]}
                </button>
              ))}
            </div>
          </div>

          {/* Time Picker */}
          <div>
            <label className="block text-sm text-slate-400 mb-2">Start time</label>
            <input
              type="time"
              value={schedule.time || '09:00'}
              onChange={e => setSchedule(prev => ({ ...prev, time: e.target.value }))}
              className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 w-40"
            />
          </div>

          {/* Dry Run Override */}
          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl">
            <div>
              <h3 className="font-semibold text-white text-sm">🛡️ Dry Run for scheduled runs</h3>
              <p className="text-slate-400 text-xs mt-0.5">Override DRY_RUN specifically for scheduled runs, independent of the global setting.</p>
            </div>
            <button
              onClick={() => setSchedule(prev => ({ ...prev, dry_run: !prev.dry_run }))}
              className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-colors ${
                schedule.dry_run ? 'bg-amber-700 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              {schedule.dry_run ? 'ACTIVE' : 'OFF'}
            </button>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white font-bold py-3 rounded-xl transition-colors"
        >
          {saved ? '✅ Schedule Saved!' : saving ? 'Saving…' : '💾 Save Schedule'}
        </button>
      </div>

      {/* Mini Live Log Panel */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-bold flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${status.is_running ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} />
            Live Log
          </h2>
          <button onClick={fetchLogs} className="text-xs text-slate-500 hover:text-white transition-colors">↻ Refresh</button>
        </div>
        <div
          ref={logRef}
          className="bg-slate-950 border border-slate-800 rounded-xl p-4 h-40 overflow-y-auto font-mono text-xs space-y-1"
        >
          {logs.length === 0 ? (
            <p className="text-slate-600">No log output yet. Run the bot to see live output.</p>
          ) : (
            logs.map((line, i) => {
              let color = 'text-slate-400';
              if (line.includes('ERROR') || line.includes('error') || line.includes('FAILED')) color = 'text-red-400';
              else if (line.includes('Applied') || line.includes('SUCCESS') || line.includes('✓')) color = 'text-green-400';
              else if (line.includes('Skipped') || line.includes('DRY') || line.includes('⚠')) color = 'text-amber-400';
              return <p key={i} className={color}>{line}</p>;
            })
          )}
        </div>
        {status.is_running && (
          <p className="text-xs text-green-500 mt-2 animate-pulse">● Auto-refreshing every 3 seconds…</p>
        )}
      </div>
    </div>
  );
}

