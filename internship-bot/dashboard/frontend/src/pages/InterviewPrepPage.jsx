import React, { useState, useEffect } from 'react';
import { apiFetch as fetch } from '../utils/apiFetch';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function PrepGuideCard({ file, onOpen }) {
  const name = file.filename.replace('.txt', '').replace(/_/g, ' ');
  const date = file.modified
    ? new Date(file.modified).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })
    : '—';
  const sizeKb = (file.size / 1024).toFixed(1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-violet-700/50 transition-all duration-200 group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-violet-900/40 border border-violet-800/50 flex items-center justify-center text-xl shrink-0">
            📝
          </div>
          <div className="min-w-0">
            <h3 className="text-white font-semibold text-sm capitalize truncate group-hover:text-violet-300 transition-colors">
              {name}
            </h3>
            <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
              <span>🗓️ {date}</span>
              <span>📄 {sizeKb} KB</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => onOpen(file.filename)}
          className="bg-violet-700 hover:bg-violet-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-colors shrink-0"
        >
          View Guide →
        </button>
      </div>
    </div>
  );
}

function GuideModal({ filename, content, onClose }) {
  // Simple markdown-ish renderer: bold headings
  const lines = content.split('\n');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
          <div>
            <h3 className="text-white font-bold">📝 Interview Prep Guide</h3>
            <p className="text-slate-400 text-xs mt-0.5 capitalize">{filename.replace(/_/g, ' ').replace('.txt', '')}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const blob = new Blob([content], { type: 'text/plain' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                a.click();
              }}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-blue-400 border border-slate-700 px-3 py-1.5 rounded-lg transition-colors"
            >
              ⬇ Download
            </button>
            <button onClick={onClose} className="text-slate-400 hover:text-white text-xl transition-colors">✕</button>
          </div>
        </div>
        <div className="overflow-y-auto flex-1 p-6 prose prose-invert prose-sm max-w-none">
          {lines.map((line, i) => {
            if (line.startsWith('## ')) return <h2 key={i} className="text-violet-300 font-bold text-base mt-4 mb-1">{line.slice(3)}</h2>;
            if (line.startsWith('# ')) return <h1 key={i} className="text-white font-bold text-lg mt-2 mb-2">{line.slice(2)}</h1>;
            if (line.startsWith('### ')) return <h3 key={i} className="text-slate-300 font-semibold text-sm mt-3 mb-1">{line.slice(4)}</h3>;
            if (line.startsWith('- ') || line.startsWith('* ')) return <li key={i} className="text-slate-300 text-sm ml-4 list-disc">{line.slice(2)}</li>;
            if (line.trim() === '') return <div key={i} className="h-2" />;
            return <p key={i} className="text-slate-300 text-sm leading-relaxed">{line}</p>;
          })}
        </div>
      </div>
    </div>
  );
}

function GeneratePanel({ onGenerated }) {
  const [role, setRole] = useState('');
  const [jobDesc, setJobDesc] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!role.trim() || !jobDesc.trim()) { setError('Both role and job description are required.'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/prep/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: role.trim(), job_description: jobDesc.trim() }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Generation failed'); }
      const data = await res.json();
      onGenerated(data);
      setRole(''); setJobDesc('');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xl">⚡</span>
        <h2 className="text-white font-bold">Generate Prep Guide on Demand</h2>
        <span className="text-xs bg-blue-900/40 border border-blue-800/40 text-blue-400 px-2 py-0.5 rounded-full">AI-Powered</span>
      </div>
      <p className="text-slate-400 text-sm mb-4 leading-relaxed">
        Paste any job description and role — the AI will instantly create a tailored interview prep guide with likely questions, key skills, and talking points.
      </p>
      <div className="space-y-3">
        <input
          type="text"
          placeholder="Role / Job title (e.g. Frontend Engineer Intern)"
          value={role}
          onChange={e => setRole(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-violet-500 transition-colors"
        />
        <textarea
          placeholder="Paste the full job description here…"
          value={jobDesc}
          onChange={e => setJobDesc(e.target.value)}
          rows={6}
          className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2.5 text-sm font-mono focus:outline-none focus:border-violet-500 transition-colors resize-none"
        />
        {error && <p className="text-red-400 text-xs">{error}</p>}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="bg-violet-700 hover:bg-violet-600 disabled:opacity-50 disabled:cursor-wait text-white font-bold px-6 py-2.5 rounded-lg transition-colors flex items-center gap-2"
        >
          {loading ? <><span className="animate-spin">⏳</span> Generating…</> : <><span>🤖</span> Generate Prep Guide</>}
        </button>
      </div>
    </div>
  );
}

export default function InterviewPrepPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openGuide, setOpenGuide] = useState(null);

  const loadFiles = () => {
    setLoading(true);
    fetch(`${API_BASE}/api/prep`)
      .then(r => r.json())
      .then(data => { setFiles(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadFiles(); }, []);

  const handleOpen = async (filename) => {
    try {
      const res = await fetch(`${API_BASE}/api/prep/${encodeURIComponent(filename)}`);
      const data = await res.json();
      setOpenGuide({ filename: data.filename, content: data.content });
    } catch {
      alert('Failed to load guide.');
    }
  };

  const handleGenerated = (data) => {
    setOpenGuide({ filename: data.filename, content: data.content });
    loadFiles();
  };

  return (
    <div className="max-w-3xl pb-10">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-1">Interview Prep</h1>
        <p className="text-slate-400 text-sm">AI-generated prep guides — created automatically after each successful application, or generate one on demand.</p>
      </div>

      {/* Generate Panel */}
      <GeneratePanel onGenerated={handleGenerated} />

      {/* How it works */}
      <div className="bg-violet-950/30 border border-violet-800/40 rounded-xl p-5 mb-8">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🤖</span>
          <div>
            <h3 className="text-white font-semibold mb-1">Automatic Guides</h3>
            <p className="text-violet-300/80 text-sm leading-relaxed">
              After the bot successfully applies to a role, ApplyFlow automatically generates a personalized interview prep guide based on the job description, your profile, and resume. Guides cover likely topics, common questions, and key points to highlight.
            </p>
          </div>
        </div>
      </div>

      {/* Guide List */}
      {loading ? (
        <div className="text-center py-16 text-slate-500">
          <div className="text-4xl mb-3 animate-pulse">⏳</div>
          <p>Loading prep guides…</p>
        </div>
      ) : files.length === 0 ? (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl">
          <div className="text-5xl mb-4">📂</div>
          <h3 className="text-white font-semibold mb-2">No saved guides yet</h3>
          <p className="text-slate-400 text-sm max-w-sm mx-auto leading-relaxed">
            Generate a guide above, or run the bot — it creates guides automatically after successful applications.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-semibold">{files.length} prep guide{files.length !== 1 ? 's' : ''} saved</h2>
            <button onClick={loadFiles} className="text-xs text-slate-500 hover:text-white transition-colors">↻ Refresh</button>
          </div>
          {files.map(file => (
            <PrepGuideCard key={file.filename} file={file} onOpen={handleOpen} />
          ))}
        </div>
      )}

      {/* Guide Modal */}
      {openGuide && (
        <GuideModal
          filename={openGuide.filename}
          content={openGuide.content}
          onClose={() => setOpenGuide(null)}
        />
      )}
    </div>
  );
}
