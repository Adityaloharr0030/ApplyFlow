import { Link } from 'react-router-dom';

const platforms = ['Internshala', 'LinkedIn', 'Indeed', 'Unstop', 'Naukri'];

const featureChips = [
  'AI Job Scoring', 'Auto-Generated Cover Letters', 'Multi-Platform Auto-Apply',
  'Cold Email Outreach', 'Real-Time Notifications', 'Dry-Run Safety Mode',
  'Circuit Breaker Protection', 'Daily Application Caps', 'Google Sheets Tracking'
];

const comparisonRows = [
  ['Re-typing the same cover letter each time', 'AI-generated cover note per listing from your profile'],
  ['Applying blind to irrelevant roles', 'AI relevance scoring filters listings before you apply'],
  ['No record of what was sent', 'Every application logged (CSV export / Google Sheets)'],
  ['Risk of shadow-bans from bulk clicking', 'Circuit breaker + randomized 2–5s delays + daily caps'],
  ['One platform at a time', '5 platforms searched and applied to in one run'],
];

const faqs = [
  {
    q: 'What is DRY_RUN mode and how does it protect me?',
    a: 'DRY_RUN is enabled by default. In this mode the bot goes through the entire flow — login, scraping, scoring, cover letter generation — but stops before actually clicking the final Submit button. You can see exactly what would have been applied to, then flip the toggle to go live when you\'re confident.'
  },
  {
    q: 'Which platforms are supported and how does each one apply?',
    a: 'Internshala (Selenium full browser), LinkedIn (Guest API search + Easy Apply), Indeed (python-jobspy scrape + Indeed Apply), Unstop (JSON API + Selenium 1-click), Naukri (Selenium). Each platform\'s flow is independent — you can enable/disable them individually.'
  },
  {
    q: 'How does the circuit breaker work?',
    a: 'If the bot hits 3 consecutive CAPTCHAs or blocks on a single platform in one run, that platform is automatically paused for the rest of the run. Other platforms keep running. This prevents account flags from repeated failed attempts.'
  },
  {
    q: 'Is my password stored safely?',
    a: 'Credentials are encrypted at rest using AES-GCM with a key derived from your SESSION_SECRET_KEY via PBKDF2. The raw password is never written to disk — only an encrypted session blob is stored.'
  },
  {
    q: 'Can I set daily caps per platform?',
    a: 'Yes. Each platform has its own MAX_APPLIES setting. For example INTERNSHALA_MAX_APPLIES=10, LINKEDIN_MAX_APPLIES=15. Once the cap is hit, the bot moves to the next platform.'
  },
  {
    q: 'Can I exclude companies or keywords?',
    a: 'Yes. The avoid_companies[] list hard-blocks specific companies. The exclude_keywords[] list skips any listing whose title contains those words (e.g. "sales", "marketing", "HR").'
  },
];

function FAQ() {
  return (
    <div className="space-y-3">
      {faqs.map((item, i) => (
        <details key={i} className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 group">
          <summary className="cursor-pointer font-semibold text-white flex justify-between items-center list-none">
            {item.q}
            <span className="ml-4 text-blue-400 group-open:rotate-180 transition-transform duration-200">▼</span>
          </summary>
          <p className="mt-3 text-slate-400 text-sm leading-relaxed">{item.a}</p>
        </details>
      ))}
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">

      {/* ── Navbar ─────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <span className="font-bold text-xl">ApplyFlow</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
            <Link to="/features" className="hover:text-white transition-colors">Features</Link>
            <Link to="/how-it-works" className="hover:text-white transition-colors">How it works</Link>
            <Link to="/pricing" className="hover:text-white transition-colors">Pricing</Link>
            <Link to="/faq" className="hover:text-white transition-colors">FAQ</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/app/dashboard" className="text-sm text-slate-300 hover:text-white px-4 py-2 rounded-lg border border-slate-700 hover:border-slate-600 transition-all">
              Open Dashboard
            </Link>
            <Link to="/app/dashboard" className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-semibold transition-all">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden py-24 px-6">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-950/40 via-slate-950 to-slate-950 pointer-events-none" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            {/* Left copy */}
            <div className="flex-1 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 bg-blue-950 border border-blue-800 text-blue-400 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                Open-source · Self-hosted · No signup required
              </div>
              <h1 className="text-5xl lg:text-6xl font-extrabold leading-tight mb-6 tracking-tight">
                Auto-apply to internships and jobs across{' '}
                <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">5 platforms</span>{' '}
                — you stay in control.
              </h1>
              <p className="text-xl text-slate-400 mb-8 leading-relaxed max-w-2xl">
                ApplyFlow searches Internshala, LinkedIn, Indeed, Unstop, and Naukri, scores each listing with Gemini AI, writes a personalized cover note, and applies — all while respecting your daily caps, safe-mode defaults, and exclude lists.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Link to="/app/dashboard" className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-8 py-4 rounded-xl text-lg transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30">
                  Start Free — Dry Run Mode 🛡️
                </Link>
                <Link to="/how-it-works" className="border border-slate-700 hover:border-blue-600 text-slate-300 hover:text-white font-semibold px-8 py-4 rounded-xl text-lg transition-all">
                  How it works →
                </Link>
              </div>
              <p className="mt-4 text-slate-500 text-sm">DRY_RUN=true by default. Nothing is submitted until you explicitly turn it off.</p>
            </div>

            {/* Right: Live mock card */}
            <div className="flex-1 w-full max-w-lg">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-t from-blue-900/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex items-center justify-between mb-4 relative">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse shadow-[0_0_8px_rgba(74,222,128,0.6)]" />
                    <span className="text-sm font-bold text-white">Session Active</span>
                  </div>
                  <span className="text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded font-bold border border-slate-700">DRY RUN</span>
                </div>
                <div className="space-y-3 mb-5 relative">
                  {[
                    { platform: '🎓 Internshala', applied: 12, skipped: 3, color: 'blue' },
                    { platform: '💼 LinkedIn', applied: 8, skipped: 2, color: 'indigo' },
                    { platform: '📋 Indeed', applied: 5, skipped: 7, color: 'sky' },
                  ].map((p) => (
                    <div key={p.platform} className="bg-slate-800/80 rounded-xl p-3 border border-slate-700/50">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium">{p.platform}</span>
                        <span className="text-xs text-green-400 font-semibold">{p.applied} applied / {p.skipped} skipped</span>
                      </div>
                      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full transition-all duration-1000" style={{ width: `${(p.applied / (p.applied + p.skipped)) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs space-y-2 border border-slate-800 relative">
                  <p className="text-green-400 flex gap-2"><span className="opacity-50">[10:42:01]</span> ✓ Applied: Flutter Dev @ Zoho — score 9/10</p>
                  <p className="text-yellow-400 flex gap-2"><span className="opacity-50">[10:42:05]</span> ⚠ Skipped: Sales Executive (excluded keyword)</p>
                  <p className="text-slate-400 flex gap-2"><span className="opacity-50">[10:42:08]</span> <span className="animate-pulse">→ Scoring: React Intern @ Razorpay...</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats bar ───────────────────────────────────────────────────── */}
      <section className="border-y border-slate-800 bg-slate-900/50 py-8">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { label: 'Platforms supported', value: '5' },
            { label: 'Notification channels', value: '3' },
            { label: 'Safety defaults', value: '5' },
            { label: 'Applications tracked', value: '∞' },
          ].map(s => (
            <div key={s.label}>
              <div className="text-3xl font-extrabold text-blue-400">{s.value}</div>
              <div className="text-slate-500 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Feature chips ───────────────────────────────────────────────── */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-slate-500 text-sm font-semibold uppercase tracking-widest mb-8">What ApplyFlow does</p>
          <div className="flex flex-wrap justify-center gap-3">
            {featureChips.map(chip => (
              <span key={chip} className="bg-slate-800 border border-slate-700 text-slate-300 px-4 py-2 rounded-full text-sm hover:border-blue-600 hover:text-white transition-all cursor-default">
                {chip}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Headline feature cards ──────────────────────────────────────── */}
      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Everything automated. Nothing hidden.</h2>
          <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">ApplyFlow is built on real features from a working codebase — not marketing copy. Here's what actually runs.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: '🌐',
                title: 'Multi-platform search + apply',
                desc: 'Internshala via Selenium, LinkedIn via Guest API + Easy Apply, Indeed via python-jobspy, Unstop via JSON API, Naukri — all in one run. Cold email engine finds HR contacts at your target companies.'
              },
              {
                icon: '🤖',
                title: 'AI scoring + cover notes',
                desc: 'Gemini scores each listing 1–10 against your skills, projects, and keywords. Listings below your threshold are skipped. Approved ones get a personalized cover note generated from your real resume context.'
              },
              {
                icon: '🔔',
                title: 'Live notifications + safety controls',
                desc: 'Telegram, ntfy.sh, and WhatsApp (CallMeBot) send per-application alerts and end-of-run digests. Circuit breaker pauses any platform after 3 blocks. DRY_RUN is on by default. Daily caps per platform.'
              },
            ].map(card => (
              <div key={card.title} className="bg-slate-800/60 border border-slate-700 hover:border-blue-700 rounded-2xl p-6 transition-all hover:bg-slate-800">
                <div className="text-4xl mb-4">{card.icon}</div>
                <h3 className="font-bold text-lg mb-3">{card.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Comparison table ────────────────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Stop grinding, start shipping</h2>
          <p className="text-slate-400 text-center mb-12">Here's what manual job searching looks like vs ApplyFlow.</p>
          <div className="overflow-hidden rounded-2xl border border-slate-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-4 px-6 text-slate-400 font-medium bg-slate-900">Manual applying</th>
                  <th className="text-left py-4 px-6 font-semibold text-blue-400 bg-blue-950/40">With ApplyFlow</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map(([manual, auto], i) => (
                  <tr key={i} className="border-b border-slate-800 last:border-0">
                    <td className="py-4 px-6 text-slate-500 bg-slate-900/50">
                      <span className="mr-2 text-red-400">✗</span>{manual}
                    </td>
                    <td className="py-4 px-6 text-slate-200 bg-blue-950/20">
                      <span className="mr-2 text-green-400">✓</span>{auto}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Up and running in 4 steps</h2>
          <p className="text-slate-400 text-center mb-16">From zero to auto-applying in under 10 minutes.</p>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: '01', title: 'Configure profile', desc: 'Fill in your skills, keywords, exclude list, and location preferences via the Profile form.' },
              { step: '02', title: 'Connect accounts', desc: 'Enter your Internshala, LinkedIn, Unstop, and Naukri credentials. Encrypted with AES-GCM at rest.' },
              { step: '03', title: 'Set safety limits', desc: 'Enable DRY_RUN, set per-platform daily caps, and choose headless or visible browser mode.' },
              { step: '04', title: 'Run or schedule', desc: 'Hit "Run Now" or schedule a daily time. Watch the live session log as it works.' },
            ].map((s, i) => (
              <div key={i} className="relative">
                <div className="text-5xl font-black text-slate-800 mb-3">{s.step}</div>
                <h3 className="font-bold text-lg mb-2">{s.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{s.desc}</p>
                {i < 3 && <div className="hidden md:block absolute top-8 right-0 translate-x-1/2 text-slate-700 text-2xl">→</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Platforms ───────────────────────────────────────────────────── */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-slate-500 text-sm font-semibold uppercase tracking-widest mb-6">Supported platforms</p>
          <div className="flex flex-wrap justify-center gap-4 mb-6">
            {platforms.map(p => (
              <span key={p} className="bg-slate-800 border border-slate-700 text-white font-semibold px-5 py-2.5 rounded-xl text-sm">{p}</span>
            ))}
            <span className="bg-slate-800 border border-dashed border-slate-600 text-slate-500 px-5 py-2.5 rounded-xl text-sm">+ Cold Email</span>
          </div>
          <p className="text-xs text-slate-600 max-w-xl mx-auto">ApplyFlow is an independent tool. It is not affiliated with, endorsed by, or partnered with Internshala, LinkedIn, Indeed, Unstop, or Naukri. Automating these platforms may violate their Terms of Service. Use responsibly and at your own risk.</p>
        </div>
      </section>

      {/* ── FAQ ────────────────────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Frequently asked questions</h2>
          <p className="text-slate-400 text-center mb-12">Real answers from the actual codebase.</p>
          <FAQ />
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-4xl font-extrabold mb-4">Start applying smarter today.</h2>
          <p className="text-slate-400 mb-8 text-lg">DRY_RUN mode is on by default — explore every feature before a single real application is sent.</p>
          <Link to="/app/dashboard" className="inline-block bg-blue-600 hover:bg-blue-500 text-white font-bold px-10 py-5 rounded-xl text-xl transition-all shadow-xl shadow-blue-600/20">
            Open Dashboard →
          </Link>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800 py-12 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2 text-slate-400">
            <span>⚡</span><span className="font-semibold text-white">ApplyFlow</span>
            <span className="text-slate-600">·</span>
            <span className="text-sm">Open-source auto-apply bot</span>
          </div>
          <div className="flex gap-6 text-sm text-slate-500">
            <Link to="/features" className="hover:text-white transition-colors">Features</Link>
            <Link to="/pricing" className="hover:text-white transition-colors">Pricing</Link>
            <Link to="/faq" className="hover:text-white transition-colors">FAQ</Link>
            <Link to="/privacy" className="hover:text-white transition-colors">Privacy</Link>
            <Link to="/terms" className="hover:text-white transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
