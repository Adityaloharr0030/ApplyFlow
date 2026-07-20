import { Link } from 'react-router-dom';

const steps = [
  {
    title: 'Configure profile',
    desc: 'Fill in your skills, keywords, exclude list, and location preferences via the Profile form. This is saved directly to your local `data/profile.json`.',
    code: `{
  "skills": ["React", "Python", "SQL"],
  "exclude_keywords": ["sales", "marketing"],
  "min_stipend": 10000
}`
  },
  {
    title: 'Connect accounts',
    desc: 'Enter your Internshala, LinkedIn, Unstop, and Naukri credentials. They are encrypted at rest using AES-GCM and never stored in plain text.',
    code: `export SESSION_SECRET_KEY="your-secure-key"
# Required for AES-GCM encryption`
  },
  {
    title: 'Set safety limits',
    desc: 'Toggle DRY_RUN mode, configure your daily application caps per platform, and enable headless mode to run invisibly.',
    code: `DRY_RUN=true
INTERNSHALA_MAX_APPLIES=10
LINKEDIN_MAX_APPLIES=15`
  },
  {
    title: 'Run or schedule',
    desc: 'Trigger a run instantly or set a daily schedule. ApplyFlow connects to platforms, scores listings with Gemini, writes cover letters, and applies.',
    code: `python main.py --run-now
# OR
python main.py --time 09:00`
  }
];

export default function HowItWorksPage() {
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

      <div className="max-w-4xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4">How it works</h1>
          <p className="text-slate-400 text-xl">Get your auto-apply bot up and running in 4 simple steps.</p>
        </div>

        <div className="space-y-12 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
          {steps.map((step, i) => (
            <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
              <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-slate-950 bg-slate-800 text-slate-300 font-bold shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow ml-[3px] md:ml-0 z-10">
                {i + 1}
              </div>
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-2xl bg-slate-800/60 border border-slate-700 hover:border-blue-700 transition-colors">
                <h3 className="font-bold text-xl mb-2">{step.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed mb-4">{step.desc}</p>
                <div className="bg-slate-950 rounded-lg p-4 border border-slate-800 overflow-x-auto">
                  <pre className="text-xs text-blue-300 font-mono"><code>{step.code}</code></pre>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-24 text-center">
          <Link to="/app/dashboard" className="inline-block bg-blue-600 hover:bg-blue-500 text-white font-bold px-10 py-4 rounded-xl text-lg transition-all">
            Get Started →
          </Link>
        </div>
      </div>
    </div>
  );
}
