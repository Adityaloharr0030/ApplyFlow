import { Link } from 'react-router-dom';
import React, { useState } from 'react';

const faqs = [
  {
    category: 'Safety',
    q: 'What is DRY_RUN mode and how does it protect me?',
    a: 'DRY_RUN is enabled by default. In this mode the bot goes through the entire flow — login, scraping, scoring, cover letter generation — but stops before actually clicking the final Submit button. You can see exactly what would have been applied to, then flip the toggle to go live when you\'re confident.'
  },
  {
    category: 'Safety',
    q: 'Is my Internshala/LinkedIn/Unstop password stored safely?',
    a: 'Yes. Credentials are encrypted at rest using AES-GCM with a key derived from your SESSION_SECRET_KEY via PBKDF2. The raw password is never written to disk — only an encrypted session blob is stored.'
  },
  {
    category: 'Safety',
    q: 'How does the circuit breaker work?',
    a: 'If the bot hits 3 consecutive CAPTCHAs or blocks on a single platform in one run, that platform is automatically paused for the rest of the run. Other platforms keep running. This prevents account flags from repeated failed attempts.'
  },
  {
    category: 'Platforms',
    q: 'Which platforms are supported and how does each one apply?',
    a: 'Internshala (Selenium full browser), LinkedIn (Guest API search + Easy Apply), Indeed (python-jobspy scrape + Indeed Apply), Unstop (JSON API + Selenium 1-click), Naukri (Selenium). Each platform\'s flow is independent — you can enable/disable them individually.'
  },
  {
    category: 'Platforms',
    q: 'Can I set daily caps per platform?',
    a: 'Yes. Each platform has its own MAX_APPLIES setting (e.g., LINKEDIN_MAX_APPLIES=15). Once the cap is hit, the bot moves to the next platform.'
  },
  {
    category: 'Platforms',
    q: 'Can I exclude companies or keywords?',
    a: 'Yes. The avoid_companies[] list hard-blocks specific companies. The exclude_keywords[] list skips any listing whose title contains those words (e.g. "sales", "marketing", "HR").'
  },
  {
    category: 'AI',
    q: 'How does the AI scoring work?',
    a: 'Every scraped listing is scored 1–10 by Gemini against your skills, projects, education, and keywords. Only listings at or above your threshold get a cover note generated and an application submitted. Below-threshold listings are logged as "skipped".'
  },
  {
    category: 'AI',
    q: 'How does the cold-email / target-company mode work?',
    a: 'You provide a list of target_companies (e.g., google.com, stripe.com) and a Gmail app password. ApplyFlow uses generic search engines to hunt for ATS links or public HR emails associated with those domains, then dispatches a cold email with your generated cover letter.'
  },
  {
    category: 'Notifications',
    q: 'What notification channels are supported and how do I set each one up?',
    a: 'We support Telegram (needs Bot token and Chat ID from @BotFather), ntfy.sh push notifications (needs a topic string), and WhatsApp via CallMeBot (needs phone number and API key). You can toggle events like "Applied", "Platform Blocked", or "Daily Digest" for each.'
  },
];

const CATEGORIES = ['All', 'Safety', 'Platforms', 'AI', 'Notifications'];

const catColors = {
  Safety: 'bg-green-900/30 text-green-400 border-green-800/50',
  Platforms: 'bg-blue-900/30 text-blue-400 border-blue-800/50',
  AI: 'bg-violet-900/30 text-violet-400 border-violet-800/50',
  Notifications: 'bg-amber-900/30 text-amber-400 border-amber-800/50',
};

export default function FaqPage() {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');

  const filtered = faqs.filter(item => {
    const matchCat = activeCategory === 'All' || item.category === activeCategory;
    const s = search.toLowerCase();
    const matchSearch = !s || item.q.toLowerCase().includes(s) || item.a.toLowerCase().includes(s);
    return matchCat && matchSearch;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <span className="font-bold text-xl">ApplyFlow</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
            <Link to="/features" className="hover:text-white transition-colors">Features</Link>
            <Link to="/how-it-works" className="hover:text-white transition-colors">How it works</Link>
            <Link to="/pricing" className="hover:text-white transition-colors">Pricing</Link>
          </div>
          <Link to="/app/dashboard" className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-semibold transition-all">Open Dashboard</Link>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-24">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4">Frequently Asked Questions</h1>
          <p className="text-slate-400 text-xl">Everything you need to know about safety, caps, and capabilities.</p>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
          <input
            type="text"
            placeholder="Search questions…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl pl-11 pr-4 py-3 focus:outline-none focus:border-blue-500 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">✕</button>
          )}
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap gap-2 mb-8">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold border transition-all ${
                activeCategory === cat
                  ? 'bg-blue-600 text-white border-blue-500'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-500'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* FAQ List */}
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            <div className="text-4xl mb-3">🤔</div>
            <p>No matching questions found. Try a different search or category.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((item, i) => (
              <details key={i} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 group hover:border-slate-700 transition-all">
                <summary className="cursor-pointer flex justify-between items-start gap-4 list-none">
                  <div className="flex items-start gap-3 flex-1">
                    <span className={`mt-0.5 px-2 py-0.5 text-[10px] font-bold rounded border uppercase tracking-wider shrink-0 ${catColors[item.category]}`}>
                      {item.category}
                    </span>
                    <span className="font-semibold text-white text-sm leading-snug">{item.q}</span>
                  </div>
                  <span className="text-blue-400 shrink-0 mt-0.5 group-open:rotate-180 transition-transform duration-200 text-lg">▼</span>
                </summary>
                <p className="mt-4 text-slate-400 text-sm leading-relaxed border-t border-slate-800 pt-4">{item.a}</p>
              </details>
            ))}
          </div>
        )}

        <div className="mt-16 text-center border-t border-slate-800 pt-16">
          <p className="text-slate-400 mb-6">Still have questions? Check the codebase on GitHub.</p>
          <a href="https://github.com/Adityaloharr0030/ApplyFlow" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline font-semibold">View Repository →</a>
        </div>
      </div>
    </div>
  );
}
