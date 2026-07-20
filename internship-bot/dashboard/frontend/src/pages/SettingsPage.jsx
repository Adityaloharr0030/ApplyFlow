import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function PasswordInput({ name, value, onChange, placeholder, className }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={`${className} pr-10`}
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-sm"
      >
        {show ? "👁️" : "👁️‍🗨️"}
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    gemini_key: '',
    gemini_model: 'gemini-1.5-flash',
    groq_key: '',
    groq_model: 'llama-3.3-70b-versatile',
    anthropic_key: '',
    dry_run: true,
    headless: true,
    internshala_max: 10,
    linkedin_max: 15,
    indeed_max: 10,
    unstop_max: 5,
    naukri_max: 10,
    telegram_token: '',
    telegram_chat_id: '',
    ntfy_topic: '',
    whatsapp_phone: '',
    whatsapp_api: '',
    notify_applied: true,
    notify_email: true,
    notify_block: true,
    notify_digest: true,
    internshala_email: '',
    internshala_password: '',
    linkedin_email: '',
    linkedin_password: '',
    naukri_email: '',
    naukri_password: '',
    unstop_email: '',
    unstop_password: '',
    gmail_address: '',
    gmail_app_password: '',
    google_sheets_name: '',
  });

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/settings`)
      .then(res => res.json())
      .then(data => {
        setSettings({
          gemini_key: data.GEMINI_API_KEY || '',
          gemini_model: data.GEMINI_MODEL || 'gemini-1.5-flash',
          groq_key: data.GROQ_API_KEY || '',
          groq_model: data.GROQ_MODEL || 'llama-3.3-70b-versatile',
          anthropic_key: data.ANTHROPIC_API_KEY || '',
          dry_run: String(data.DRY_RUN).toLowerCase() === 'true',
          headless: String(data.HEADLESS).toLowerCase() === 'true',
          internshala_max: parseInt(data.INTERNSHALA_MAX_APPLIES) || 10,
          linkedin_max: parseInt(data.LINKEDIN_MAX_APPLIES) || 15,
          indeed_max: parseInt(data.INDEED_MAX_APPLIES) || 10,
          unstop_max: parseInt(data.UNSTOP_MAX_APPLIES) || 5,
          naukri_max: parseInt(data.NAUKRI_MAX_APPLIES) || 10,
          telegram_token: data.TELEGRAM_BOT_TOKEN || '',
          telegram_chat_id: data.TELEGRAM_CHAT_ID || '',
          ntfy_topic: data.NTFY_TOPIC || '',
          whatsapp_phone: data.WHATSAPP_PHONE || '',
          whatsapp_api: data.WHATSAPP_API_KEY || '',
          notify_applied: true,
          notify_email: true,
          notify_block: true,
          notify_digest: true,
          internshala_email: data.INTERNSHALA_EMAIL || '',
          internshala_password: data.INTERNSHALA_PASSWORD || '',
          linkedin_email: data.LINKEDIN_EMAIL || '',
          linkedin_password: data.LINKEDIN_PASSWORD || '',
          naukri_email: data.NAUKRI_EMAIL || '',
          naukri_password: data.NAUKRI_PASSWORD || '',
          unstop_email: data.UNSTOP_EMAIL || '',
          unstop_password: data.UNSTOP_PASSWORD || '',
          gmail_address: data.GMAIL_ADDRESS || '',
          gmail_app_password: data.GMAIL_APP_PASSWORD || '',
          google_sheets_name: data.GOOGLE_SHEETS_NAME || '',
        });
      })
      .catch(console.error);
  }, []);

  const handleToggle = (key) => setSettings({ ...settings, [key]: !settings[key] });
  const handleChange = (e) => setSettings({ ...settings, [e.target.name]: e.target.value });

  const handleSave = async () => {
    setSaving(true);
    const payload = {
      GEMINI_API_KEY: settings.gemini_key,
      GEMINI_MODEL: settings.gemini_model,
      GROQ_API_KEY: settings.groq_key,
      GROQ_MODEL: settings.groq_model,
      ANTHROPIC_API_KEY: settings.anthropic_key,
      DRY_RUN: settings.dry_run ? 'true' : 'false',
      HEADLESS: settings.headless ? 'true' : 'false',
      INTERNSHALA_MAX_APPLIES: settings.internshala_max,
      LINKEDIN_MAX_APPLIES: settings.linkedin_max,
      INDEED_MAX_APPLIES: settings.indeed_max,
      UNSTOP_MAX_APPLIES: settings.unstop_max,
      NAUKRI_MAX_APPLIES: settings.naukri_max,
      TELEGRAM_BOT_TOKEN: settings.telegram_token,
      TELEGRAM_CHAT_ID: settings.telegram_chat_id,
      NTFY_TOPIC: settings.ntfy_topic,
      WHATSAPP_PHONE: settings.whatsapp_phone,
      WHATSAPP_API_KEY: settings.whatsapp_api,
      INTERNSHALA_EMAIL: settings.internshala_email,
      INTERNSHALA_PASSWORD: settings.internshala_password,
      LINKEDIN_EMAIL: settings.linkedin_email,
      LINKEDIN_PASSWORD: settings.linkedin_password,
      NAUKRI_EMAIL: settings.naukri_email,
      NAUKRI_PASSWORD: settings.naukri_password,
      UNSTOP_EMAIL: settings.unstop_email,
      UNSTOP_PASSWORD: settings.unstop_password,
      GMAIL_ADDRESS: settings.gmail_address,
      GMAIL_APP_PASSWORD: settings.gmail_app_password,
      GOOGLE_SHEETS_NAME: settings.google_sheets_name,
    };

    try {
      await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      alert('Settings saved successfully!');
    } catch (e) {
      alert('Failed to save settings.');
    }
    setSaving(false);
  };

  return (
    <div className="max-w-4xl pb-20">
      <h1 className="text-3xl font-bold text-white mb-2">Environment & Settings</h1>
      <p className="text-slate-400 mb-8">Configure your AI models, safety limits, and notifications.</p>
      
      <div className="space-y-8">
        
        {/* Core & AI */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">AI Configuration</h2>
          
          {/* Smart routing info banner */}
          <div className="bg-blue-950/40 border border-blue-900/40 rounded-xl p-4 mb-5 text-sm">
            <p className="text-blue-300 font-semibold mb-1">⚡ Smart AI Routing</p>
            <p className="text-blue-400/80">ApplyFlow uses <strong className="text-blue-300">Groq (Llama)</strong> first for blazing-fast cover notes &amp; form Q&amp;A, and falls back to <strong className="text-blue-300">Gemini</strong> for structured scoring. Add both keys to maximize speed and reliability.</p>
          </div>

          <div className="space-y-4">
            {/* Groq */}
            <div className="border border-slate-700/50 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">⚡</span>
                <h3 className="font-bold text-white">Groq (Llama 3.3 70B) — <span className="text-green-400 text-sm font-normal">Primary: Cover Letters, Q&amp;A</span></h3>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Groq API Key</label>
                <PasswordInput name="groq_key" value={settings.groq_key} onChange={handleChange} placeholder="gsk_..." className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 font-mono text-sm" />
                <p className="text-xs text-slate-500 mt-1">Get a free key at <a href="https://console.groq.com" target="_blank" rel="noreferrer" className="text-blue-400 underline">console.groq.com</a> — free tier is generous!</p>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Groq Model</label>
                <select name="groq_model" value={settings.groq_model} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2">
                  <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Recommended)</option>
                  <option value="llama-3.1-70b-versatile">llama-3.1-70b-versatile</option>
                  <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Fastest)</option>
                  <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
                  <option value="gemma2-9b-it">gemma2-9b-it</option>
                </select>
              </div>
            </div>

            {/* Gemini */}
            <div className="border border-slate-700/50 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">🧠</span>
                <h3 className="font-bold text-white">Gemini — <span className="text-purple-400 text-sm font-normal">Fallback + Structured Scoring</span></h3>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Gemini API Key(s) <span className="text-slate-500">(comma-separated for failover)</span></label>
                <PasswordInput name="gemini_key" value={settings.gemini_key} onChange={handleChange} placeholder="AIzaSy..." className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 font-mono text-sm" />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Gemini Model</label>
                <select name="gemini_model" value={settings.gemini_model} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2">
                  <option value="gemini-1.5-flash">gemini-1.5-flash (Recommended)</option>
                  <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                  <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                </select>
              </div>
            </div>

            {/* Anthropic */}
            <div className="border border-slate-700/50 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">🤖</span>
                <h3 className="font-bold text-white">Anthropic Claude — <span className="text-rose-400 text-sm font-normal">Final Fallback (Premium)</span></h3>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Anthropic API Key <span className="text-slate-500">(optional — used only if Groq and Gemini both fail)</span></label>
                <PasswordInput name="anthropic_key" value={settings.anthropic_key} onChange={handleChange} placeholder="sk-ant-..." className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 font-mono text-sm" />
              </div>
            </div>

            {/* AI Chain Visualizer */}
            <div className="bg-slate-800/40 border border-slate-700/30 rounded-xl p-4">
              <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3">Active AI Provider Chain</p>
              <div className="flex items-center gap-2 flex-wrap">
                <div className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 ${
                  settings.groq_key ? 'bg-green-900/40 text-green-300 border border-green-800/50' : 'bg-slate-800 text-slate-500 border border-slate-700'
                }`}>
                  ⚡ Groq {settings.groq_key ? '✓' : '(not set)'}
                </div>
                <span className="text-slate-600">→</span>
                <div className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 ${
                  settings.gemini_key ? 'bg-purple-900/40 text-purple-300 border border-purple-800/50' : 'bg-slate-800 text-slate-500 border border-slate-700'
                }`}>
                  🧠 Gemini {settings.gemini_key ? '✓' : '(not set)'}
                </div>
                <span className="text-slate-600">→</span>
                <div className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 ${
                  settings.anthropic_key ? 'bg-rose-900/40 text-rose-300 border border-rose-800/50' : 'bg-slate-800 text-slate-500 border border-slate-700'
                }`}>
                  🤖 Anthropic {settings.anthropic_key ? '✓' : '(optional)'}
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-2">Groq is tried first for speed. If rate-limited, falls back to Gemini (and Anthropic if set). For scoring tasks, Gemini is used first.</p>
            </div>
          </div>
        </div>

        {/* Safety & Execution */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Safety Limits</h2>
          
          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg mb-4">
            <div>
              <h3 className="font-bold text-white">DRY_RUN Mode 🛡️</h3>
              <p className="text-sm text-slate-400">Do not click the final submit button on any platform.</p>
            </div>
            <button onClick={() => handleToggle('dry_run')} className={`px-4 py-2 rounded font-bold ${settings.dry_run ? 'bg-yellow-600 text-white' : 'bg-slate-700 text-slate-300'}`}>
              {settings.dry_run ? 'ACTIVE' : 'OFF'}
            </button>
          </div>

          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg mb-6">
            <div>
              <h3 className="font-bold text-white">Headless Browser</h3>
              <p className="text-sm text-slate-400">Run Chrome invisibly in the background.</p>
            </div>
            <button onClick={() => handleToggle('headless')} className={`px-4 py-2 rounded font-bold ${settings.headless ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'}`}>
              {settings.headless ? 'HIDDEN' : 'VISIBLE'}
            </button>
          </div>

          <h3 className="font-bold text-slate-300 mb-3 mt-6">Daily Caps Per Platform</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {['internshala', 'linkedin', 'indeed', 'unstop', 'naukri'].map(p => (
              <div key={p}>
                <label className="block text-xs text-slate-400 uppercase mb-1">{p}</label>
                <input type="number" name={`${p}_max`} value={settings[`${p}_max`]} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
              </div>
            ))}
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Notification Channels</h2>
          
          <div className="space-y-6">
            <div>
              <h3 className="font-bold text-blue-400 mb-2">Telegram</h3>
              <div className="flex gap-4">
                <input placeholder="Bot Token" value={settings.telegram_token} onChange={handleChange} name="telegram_token" className="flex-1 bg-slate-800 border border-slate-700 text-white rounded p-2" />
                <input placeholder="Chat ID" value={settings.telegram_chat_id} onChange={handleChange} name="telegram_chat_id" className="flex-1 bg-slate-800 border border-slate-700 text-white rounded p-2" />
              </div>
            </div>
            
            <div>
              <h3 className="font-bold text-green-400 mb-2">ntfy.sh Push</h3>
              <input placeholder="Topic String (use a long random string)" value={settings.ntfy_topic} onChange={handleChange} name="ntfy_topic" className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>

            <div>
              <h3 className="font-bold text-green-500 mb-2">WhatsApp (CallMeBot)</h3>
              <div className="flex gap-4">
                <input placeholder="Phone Number" value={settings.whatsapp_phone} onChange={handleChange} name="whatsapp_phone" className="flex-1 bg-slate-800 border border-slate-700 text-white rounded p-2" />
                <input placeholder="API Key" value={settings.whatsapp_api} onChange={handleChange} name="whatsapp_api" className="flex-1 bg-slate-800 border border-slate-700 text-white rounded p-2" />
              </div>
            </div>
          </div>

          <h3 className="font-bold text-slate-300 mb-3 mt-6">Event Triggers</h3>
          <div className="grid grid-cols-2 gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={settings.notify_applied} onChange={() => handleToggle('notify_applied')} className="w-4 h-4" />
              ✅ Application Submitted
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={settings.notify_email} onChange={() => handleToggle('notify_email')} className="w-4 h-4" />
              📧 Cold Email Sent
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={settings.notify_block} onChange={() => handleToggle('notify_block')} className="w-4 h-4" />
              ⚠️ Circuit Breaker / Blocked
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={settings.notify_digest} onChange={() => handleToggle('notify_digest')} className="w-4 h-4" />
              📊 End-of-run Digest
            </label>
          </div>
        </div>

        {/* Platform Credentials */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-2">Platform Credentials</h2>
          <p className="text-slate-400 text-sm mb-4">Stored encrypted on disk. Only needed if not using the Chrome Extension for session capture.</p>
          <div className="grid md:grid-cols-2 gap-5">
            {[['Internshala', 'internshala'], ['LinkedIn', 'linkedin'], ['Naukri', 'naukri'], ['Unstop', 'unstop']].map(([label, key]) => (
              <div key={key} className="border border-slate-700/40 rounded-xl p-4 space-y-2">
                <h3 className="text-sm font-bold text-white">{label}</h3>
                <input type="email" placeholder="Email" name={`${key}_email`} value={settings[`${key}_email`] || ''} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 text-sm" />
                <PasswordInput placeholder="Password" name={`${key}_password`} value={settings[`${key}_password`] || ''} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 text-sm" />
              </div>
            ))}
          </div>
        </div>

        {/* Gmail + Google Sheets */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Cold Email & Tracking</h2>
          <div className="space-y-4">
            <div className="border border-slate-700/40 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-bold text-white">📧 Gmail (Cold Email Outreach)</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Gmail Address</label>
                  <input type="email" name="gmail_address" value={settings.gmail_address} onChange={handleChange} placeholder="you@gmail.com" className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Gmail App Password</label>
                  <PasswordInput name="gmail_app_password" value={settings.gmail_app_password} onChange={handleChange} placeholder="xxxx xxxx xxxx xxxx" className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 text-sm font-mono" />
                </div>
              </div>
              <p className="text-xs text-slate-500">Use a <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="text-blue-400 underline">Gmail App Password</a>, not your real password.</p>
            </div>

            <div className="border border-slate-700/40 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-bold text-white">📊 Google Sheets Tracking</h3>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Sheet Name</label>
                <input name="google_sheets_name" value={settings.google_sheets_name} onChange={handleChange} placeholder="ApplyFlow Applications" className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2 text-sm" />
              </div>
              <p className="text-xs text-slate-500">Add your service account JSON as <code className="bg-slate-800 px-1 rounded text-slate-300">data/google_creds.json</code> on the server.</p>
            </div>
          </div>
        </div>

        <button onClick={handleSave} disabled={saving} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg px-4 py-3 transition-colors">
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
