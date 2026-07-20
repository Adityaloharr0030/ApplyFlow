import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

const PLATFORM_META = {
  internshala: {
    name: 'Internshala',
    icon: '🎓',
    color: 'blue',
    method: 'Selenium full-browser',
    description: 'Full browser automation with cover letter auto-fill. Best for internships.',
    limit_note: 'CAPTCHA block rate ~30% of runs, clears after 12–24h. Circuit breaker activates at 3 blocks.',
    link: 'internshala.com',
  },
  linkedin: {
    name: 'LinkedIn',
    icon: '💼',
    color: 'sky',
    method: 'Guest API + Easy Apply',
    description: 'Uses guest search API + Easy Apply. Non-Easy Apply jobs are logged as manual.',
    limit_note: 'Guest API throttles after ~50–100 req/hour per IP.',
    link: 'linkedin.com',
  },
  indeed: {
    name: 'Indeed',
    icon: '🔍',
    color: 'indigo',
    method: 'python-jobspy + Indeed Apply',
    description: 'Scrapes via python-jobspy. External ATS redirect jobs logged as Manual.',
    limit_note: 'External company ATS redirects cannot be auto-submitted.',
    link: 'indeed.com',
  },
  unstop: {
    name: 'Unstop',
    icon: '⚡',
    color: 'purple',
    method: 'JSON API + Selenium 1-click',
    description: 'Uses Unstop\'s JSON API for discovery + 1-click apply via Selenium.',
    limit_note: 'Most applications are 1-click — fastest platform.',
    link: 'unstop.com',
  },
  naukri: {
    name: 'Naukri',
    icon: '🏢',
    color: 'orange',
    method: 'Selenium full-browser',
    description: 'Full browser automation for Naukri job applications.',
    limit_note: 'Requires session capture via Chrome extension for best reliability.',
    link: 'naukri.com',
  },
  cold_email: {
    name: 'Cold Email',
    icon: '📧',
    color: 'green',
    method: 'Gmail + ATS/HR discovery',
    description: 'Finds ATS career links or HR emails for target companies and sends personalized cold emails.',
    limit_note: 'Requires target_companies[] in your profile and Gmail app password in Settings.',
    link: null,
  },
};

const colorMap = {
  blue: { badge: 'bg-blue-900/30 text-blue-400 border border-blue-900/50', dot: 'bg-blue-400', ring: 'border-blue-700/40' },
  sky: { badge: 'bg-sky-900/30 text-sky-400 border border-sky-900/50', dot: 'bg-sky-400', ring: 'border-sky-700/40' },
  indigo: { badge: 'bg-indigo-900/30 text-indigo-400 border border-indigo-900/50', dot: 'bg-indigo-400', ring: 'border-indigo-700/40' },
  purple: { badge: 'bg-purple-900/30 text-purple-400 border border-purple-900/50', dot: 'bg-purple-400', ring: 'border-purple-700/40' },
  orange: { badge: 'bg-orange-900/30 text-orange-400 border border-orange-900/50', dot: 'bg-orange-400', ring: 'border-orange-700/40' },
  green: { badge: 'bg-green-900/30 text-green-400 border border-green-900/50', dot: 'bg-green-400', ring: 'border-green-700/40' },
  slate: { badge: 'bg-slate-800 text-slate-400 border border-slate-700', dot: 'bg-slate-400', ring: 'border-slate-700' },
};

export default function PlatformsPage() {
  const [platforms, setPlatforms] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/platforms`)
      .then(r => r.json())
      .then(d => setPlatforms(d))
      .catch(console.error);
  }, []);

  const togglePlatform = (key) => {
    setPlatforms(prev => ({
      ...prev,
      [key]: { ...prev[key], enabled: !prev[key]?.enabled },
    }));
  };

  const setMaxApplies = (key, val) => {
    setPlatforms(prev => ({
      ...prev,
      [key]: { ...prev[key], max_applies: parseInt(val) || 0 },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`${API_BASE}/api/platforms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(platforms),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert('Failed to save platforms.');
    }
    setSaving(false);
  };

  return (
    <div className="max-w-5xl pb-10">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Platforms</h1>
          <p className="text-slate-400 text-sm">Enable/disable platforms and set per-platform daily caps. These apply to every bot run.</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-5 py-2.5 rounded-lg transition-colors text-sm flex items-center gap-2"
        >
          {saved ? '✅ Saved!' : saving ? 'Saving…' : '💾 Save Changes'}
        </button>
      </div>

      {/* Disclaimer */}
      <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-4 mb-6 text-sm text-amber-400/80">
        <strong className="text-amber-300">⚠️ Independent Tool Disclaimer:</strong> ApplyFlow is an independent automation tool and is not affiliated with, endorsed by, or officially connected to Internshala, LinkedIn, Indeed, Unstop, or Naukri. Automating these platforms may violate their Terms of Service. Use responsibly with DRY_RUN enabled until you are confident.
      </div>

      {/* Chrome Extension Info */}
      <div className="bg-blue-950/30 border border-blue-800/40 rounded-xl p-5 mb-8">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🧩</span>
          <div>
            <h3 className="text-white font-semibold mb-1">Chrome Extension — Session Capture</h3>
            <p className="text-blue-300/80 text-sm leading-relaxed mb-3">
              <strong className="text-blue-200">Your password never leaves your browser.</strong> Instead of entering credentials into ApplyFlow, log in to each platform normally in Chrome, then click the ApplyFlow extension icon and hit <strong>Capture</strong>. The extension sends your existing session cookies to the bot — your login credentials are never touched.
            </p>
            <div className="flex flex-wrap gap-2 text-xs">
              {['linkedin.com', 'naukri.com', 'internshala.com', 'unstop.com'].map(d => (
                <span key={d} className="bg-blue-900/40 text-blue-300 border border-blue-800/50 px-2.5 py-1 rounded-full">{d}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Platform Cards */}
      <div className="grid gap-5">
        {Object.entries(PLATFORM_META).map(([key, meta]) => {
          const cfg = platforms[key] || { enabled: false, max_applies: 10 };
          const colors = colorMap[meta.color] || colorMap.slate;

          return (
            <div
              key={key}
              className={`bg-slate-900 border rounded-2xl p-6 transition-all duration-200 ${
                cfg.enabled ? `border-slate-700 ${colors.ring}` : 'border-slate-800 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 flex-1">
                  <div className="text-3xl">{meta.icon}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold text-white">{meta.name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors.badge}`}>
                        {meta.method}
                      </span>
                      {meta.link && (
                        <a href={`https://${meta.link}`} target="_blank" rel="noreferrer" className="text-xs text-slate-500 hover:text-slate-300">
                          {meta.link} ↗
                        </a>
                      )}
                    </div>
                    <p className="text-slate-400 text-sm mb-2">{meta.description}</p>
                    <div className="flex items-center gap-2 text-xs text-amber-500/80">
                      <span>⚠️</span>
                      <span>{meta.limit_note}</span>
                    </div>
                  </div>
                </div>

                {/* Controls */}
                <div className="flex flex-col items-end gap-4 shrink-0">
                  {/* Toggle */}
                  <button
                    onClick={() => togglePlatform(key)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none ${
                      cfg.enabled ? 'bg-blue-600' : 'bg-slate-700'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${
                        cfg.enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <span className={`text-xs font-semibold ${cfg.enabled ? 'text-green-400' : 'text-slate-500'}`}>
                    {cfg.enabled ? 'ENABLED' : 'DISABLED'}
                  </span>
                </div>
              </div>

              {/* Daily Cap Slider */}
              {cfg.enabled && (
                <div className="mt-5 pt-4 border-t border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm text-slate-400">Daily cap for {meta.name}</label>
                    <span className={`text-lg font-bold ${colors.badge.includes('text-') ? colors.badge.split(' ').find(c => c.startsWith('text-')) : 'text-blue-400'}`}>
                      {cfg.max_applies} <span className="text-slate-500 text-sm font-normal">/ day</span>
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="50"
                    value={cfg.max_applies || 10}
                    onChange={e => setMaxApplies(key, e.target.value)}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-slate-600 mt-1">
                    <span>1</span>
                    <span>25</span>
                    <span>50</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
