import { Link } from 'react-router-dom';

const plans = [
  {
    name: 'Free / Self-hosted',
    price: '₹0',
    period: 'forever',
    desc: 'Run ApplyFlow on your own machine. Full access to all features.',
    highlight: false,
    features: [
      'All 5 platforms (Internshala, LinkedIn, Indeed, Unstop, Naukri)',
      'AI scoring + cover letter generation (bring your Gemini API key)',
      'Telegram, ntfy.sh, WhatsApp notifications',
      'DRY_RUN mode + circuit breaker',
      'Daily scheduling',
      'Google Sheets tracking',
      'AES-GCM encrypted credential storage',
      'Cold email engine',
      'Open-source (MIT license)',
    ],
    cta: 'Clone & Run',
    ctaLink: 'https://github.com/Adityaloharr0030/ApplyFlow',
  },
  {
    name: 'Pro (Coming Soon)',
    price: '₹199',
    period: '/ month',
    desc: 'Hosted version — no setup, always-on cloud runner, team profiles.',
    highlight: true,
    features: [
      'Everything in Free',
      'Cloud-hosted bot runner (no Selenium setup)',
      'Always-on daily scheduling',
      'Priority Gemini API rate limits',
      'Email digest delivery',
      'Web dashboard with analytics',
      'Resume parsing from PDF',
      '5 concurrent platform sessions',
    ],
    cta: 'Star on GitHub',
    ctaLink: 'https://github.com/Adityaloharr0030/ApplyFlow',
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <span className="font-bold text-xl">ApplyFlow</span>
          </Link>
          <Link to="/app/dashboard" className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-semibold transition-all">Open Dashboard</Link>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4">Simple pricing</h1>
          <p className="text-slate-400 text-xl">Free and open-source, always. Hosted cloud version coming soon.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {plans.map(plan => (
            <div key={plan.name} className={`rounded-2xl p-8 border ${plan.highlight ? 'border-blue-600 bg-blue-950/30' : 'border-slate-700 bg-slate-800/60'} relative`}>
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-4 py-1 rounded-full">Coming Soon</span>
              )}
              <h2 className="text-xl font-bold mb-1">{plan.name}</h2>
              <div className="flex items-end gap-1 mb-2">
                <span className="text-4xl font-extrabold">{plan.price}</span>
                <span className="text-slate-400 mb-1">{plan.period}</span>
              </div>
              <p className="text-slate-400 text-sm mb-6">{plan.desc}</p>
              <ul className="space-y-3 mb-8">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <span className="text-green-400 mt-0.5 shrink-0">✓</span>
                    <span className="text-slate-300">{f}</span>
                  </li>
                ))}
              </ul>
              <a href={plan.ctaLink} target={plan.ctaLink.startsWith('http') ? '_blank' : undefined} rel="noreferrer"
                className={`block text-center py-3 rounded-xl font-bold transition-all ${plan.highlight ? 'bg-blue-600 hover:bg-blue-500 text-white' : 'border border-slate-600 hover:border-blue-600 text-slate-300 hover:text-white'}`}>
                {plan.cta}
              </a>
            </div>
          ))}
        </div>

        <div className="mt-16 bg-slate-800/40 border border-slate-700 rounded-2xl p-8 text-center">
          <h3 className="font-bold text-lg mb-2">Feature comparison</h3>
          <p className="text-slate-400 text-sm mb-6">Both plans have identical automation features. The Pro plan adds hosting, always-on scheduling, and enhanced analytics.</p>
          <Link to="/features" className="text-blue-400 hover:underline text-sm">View full feature list →</Link>
        </div>

        <p className="text-center text-xs text-slate-600 mt-8">
          ApplyFlow is an independent open-source tool not affiliated with Internshala, LinkedIn, Indeed, Unstop, or Naukri.
          Automating these platforms may violate their Terms of Service. Use responsibly.
        </p>
      </div>
    </div>
  );
}
