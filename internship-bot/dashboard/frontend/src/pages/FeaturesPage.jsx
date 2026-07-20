import { Link } from 'react-router-dom';

const platforms = [
  {
    name: 'Internshala',
    icon: '🎓',
    search: 'Requests + BeautifulSoup',
    apply: 'Selenium (full browser)',
    extra: 'Auto-fills cover letter field per listing',
    color: 'blue'
  },
  {
    name: 'LinkedIn',
    icon: '💼',
    search: 'Guest API (no login required)',
    apply: 'Easy Apply only (non-Easy Apply logged as manual)',
    extra: 'AI cover note injected into About field',
    color: 'indigo'
  },
  {
    name: 'Indeed',
    icon: '📋',
    search: 'python-jobspy library',
    apply: 'Indeed Apply flow (external ATS redirects logged as manual)',
    extra: 'Captures stipend + duration metadata',
    color: 'sky'
  },
  {
    name: 'Unstop',
    icon: '🏆',
    search: 'JSON API',
    apply: 'Selenium + 1-click apply',
    extra: 'Handles competition-style applications',
    color: 'violet'
  },
  {
    name: 'Naukri',
    icon: '💡',
    search: 'Selenium-based scrape',
    apply: 'Selenium',
    extra: 'Supports resume update + apply flow',
    color: 'amber'
  },
  {
    name: 'Cold Email',
    icon: '📧',
    search: 'Target company domain list → ATS link or HR email discovery',
    apply: 'Gmail send via App Password',
    extra: 'Fully automated cold outreach engine',
    color: 'emerald'
  },
];

const aiFeatures = [
  {
    title: 'Gemini-Powered Job Scoring',
    icon: '🧠',
    desc: 'Each listing is scored 1–10 against your actual resume context — skills, projects, and past application outcomes. Listings below your threshold are skipped. AI scoring uses failover across multiple Gemini API keys to avoid rate limits.'
  },
  {
    title: 'AI Cover Letter Generation',
    icon: '✍️',
    desc: 'A personalized cover note or "About Me" blurb is generated per listing using Gemini, pulling from your real skills and project descriptions. No template repetition — every cover note is listing-specific.'
  },
  {
    title: 'Outcome Learning',
    icon: '📊',
    desc: 'The outcome tracker records what worked across all past applications, feeding good title keywords and bad companies back into the AI scorer for improved accuracy over time.'
  },
  {
    title: 'Resume Brain',
    icon: '📄',
    desc: 'Your resume PDF is parsed into structured context (skills, tech stacks, achievements, projects) and injected into each Gemini prompt — making AI scoring resume-aware, not just keyword-aware.'
  },
];

const safetyFeatures = [
  { icon: '🛡️', title: 'DRY_RUN default', desc: 'Bot runs the full pipeline but stops before clicking Submit. Enable explicit confirmation to go live.' },
  { icon: '⚡', title: 'Circuit breaker', desc: '3 CAPTCHAs or blocks in one run automatically pauses that platform. Other platforms keep running.' },
  { icon: '🎯', title: 'Daily caps per platform', desc: 'INTERNSHALA_MAX_APPLIES, LINKEDIN_MAX_APPLIES, etc. Cap hits → platform gracefully exits.' },
  { icon: '⏱️', title: 'Randomized delays', desc: '2–5 second random waits between requests mimic human behavior and reduce detection risk.' },
  { icon: '🔒', title: 'Encrypted credential storage', desc: 'AES-GCM encryption with PBKDF2-derived key. Raw passwords never written to disk.' },
  { icon: '🚫', title: 'Exclude keyword & company lists', desc: 'Blocklist entire job categories (sales, HR) and specific companies from ever being applied to.' },
];

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <span className="font-bold text-xl">ApplyFlow</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/app/dashboard" className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-semibold transition-all">Open Dashboard</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-6 py-20">
        {/* Hero */}
        <div className="text-center mb-20">
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4">Every feature, documented</h1>
          <p className="text-slate-400 text-xl max-w-2xl mx-auto">ApplyFlow is built on a working Python automation engine. Every feature listed here exists in the codebase.</p>
        </div>

        {/* Platform Cards */}
        <section className="mb-20">
          <h2 className="text-2xl font-bold mb-3">Supported platforms</h2>
          <p className="text-slate-400 mb-8">Each platform has its own module in <code className="text-blue-400 bg-slate-800 px-1 rounded">platforms/</code> with independent search and apply logic.</p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {platforms.map(p => (
              <div key={p.name} className="bg-slate-800/60 border border-slate-700 hover:border-blue-700 rounded-2xl p-5 transition-all">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{p.icon}</span>
                  <h3 className="font-bold text-lg">{p.name}</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex gap-2">
                    <span className="text-slate-500 w-16 shrink-0">Search:</span>
                    <span className="text-slate-300">{p.search}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-slate-500 w-16 shrink-0">Apply:</span>
                    <span className="text-slate-300">{p.apply}</span>
                  </div>
                  <div className="mt-3 bg-blue-950/40 border border-blue-900 rounded-lg px-3 py-2 text-blue-300 text-xs">{p.extra}</div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-600 mt-4">Independent tool — not affiliated with or endorsed by any listed platform. Automation may violate platform ToS.</p>
        </section>

        {/* AI Features */}
        <section className="mb-20">
          <h2 className="text-2xl font-bold mb-3">AI capabilities (Gemini)</h2>
          <p className="text-slate-400 mb-8">All AI features use Google Gemini with configurable models and API key failover.</p>
          <div className="grid md:grid-cols-2 gap-5">
            {aiFeatures.map(f => (
              <div key={f.title} className="bg-slate-800/60 border border-slate-700 rounded-2xl p-5">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-bold mb-2">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Safety */}
        <section className="mb-20">
          <h2 className="text-2xl font-bold mb-3">Safety & protection</h2>
          <p className="text-slate-400 mb-8">Built-in safeguards that protect your accounts and give you full control.</p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {safetyFeatures.map(f => (
              <div key={f.title} className="bg-slate-800/60 border border-slate-700 rounded-2xl p-5">
                <span className="text-3xl block mb-3">{f.icon}</span>
                <h3 className="font-bold mb-2">{f.title}</h3>
                <p className="text-slate-400 text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <div className="text-center py-12 border-t border-slate-800">
          <Link to="/app/dashboard" className="inline-block bg-blue-600 hover:bg-blue-500 text-white font-bold px-10 py-4 rounded-xl text-lg transition-all">
            Open Dashboard →
          </Link>
        </div>
      </div>
    </div>
  );
}
