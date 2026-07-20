import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

export default function ProfilePage() {
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    phone: '',
    location: '',
    degree: '',
    college: '',
    year: '',
    cgpa: '',
    resume_path: './data/resume.pdf',
    linkedin: '',
    github: '',
    skills: '',
    keywords: '',
    exclude_keywords: '',
    location_preferences: '',
    preferred_cities: '',
    job_types: '',
    countries: '',
    target_companies: '',
    avoid_companies: '',
    min_stipend: '0',
    years_of_experience: '0',
    notice_period: 'Immediate',
    current_ctc: '0',
    expected_ctc: 'As per industry standards',
    willing_to_relocate: 'Yes',
    preferred_mode: 'remote, hybrid',
    open_to_hybrid: 'Yes',
    work_authorization: 'Indian Citizen',
    projects: '',
    achievement: '',
    internshala_email: '',
    linkedin_email: '',
    naukri_email: '',
    unstop_email: ''
  });

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/profile`)
      .then(res => res.json())
      .then(data => {
        if (Object.keys(data).length === 0) return;
        setProfile({
          ...profile,
          ...data,
          skills: data.skills ? data.skills.join(', ') : '',
          keywords: data.keywords ? data.keywords.join(', ') : '',
          exclude_keywords: data.exclude_keywords ? data.exclude_keywords.join(', ') : '',
          location_preferences: data.location_preferences ? data.location_preferences.join(', ') : '',
          preferred_cities: data.preferred_cities ? data.preferred_cities.join(', ') : '',
          job_types: data.job_types ? data.job_types.join(', ') : '',
          countries: data.countries ? data.countries.join(', ') : '',
          target_companies: data.target_companies ? data.target_companies.join(', ') : '',
          avoid_companies: data.avoid_companies ? data.avoid_companies.join(', ') : '',
          preferred_mode: data.preferred_mode ? data.preferred_mode.join(', ') : '',
          projects: data.projects ? data.projects.join(', ') : '',
        });
      })
      .catch(console.error);
  }, []);

  const handleChange = (e) => setProfile({ ...profile, [e.target.name]: e.target.value });

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      ...profile,
      skills: profile.skills.split(',').map(s => s.trim()).filter(Boolean),
      keywords: profile.keywords.split(',').map(s => s.trim()).filter(Boolean),
      exclude_keywords: profile.exclude_keywords.split(',').map(s => s.trim()).filter(Boolean),
      location_preferences: profile.location_preferences.split(',').map(s => s.trim()).filter(Boolean),
      preferred_cities: profile.preferred_cities.split(',').map(s => s.trim()).filter(Boolean),
      job_types: profile.job_types.split(',').map(s => s.trim()).filter(Boolean),
      countries: profile.countries.split(',').map(s => s.trim()).filter(Boolean),
      target_companies: profile.target_companies.split(',').map(s => s.trim()).filter(Boolean),
      avoid_companies: profile.avoid_companies.split(',').map(s => s.trim()).filter(Boolean),
      preferred_mode: profile.preferred_mode.split(',').map(s => s.trim()).filter(Boolean),
      projects: profile.projects.split(',').map(s => s.trim()).filter(Boolean),
    };

    try {
      await fetch(`${API_BASE}/api/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      setSaving(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      alert('Failed to save profile.');
      setSaving(false);
    }
  };

  // Completion score
  const KEY_FIELDS = ['name','email','phone','location','degree','college','skills','keywords','resume_path','linkedin','github','projects'];
  const filled = KEY_FIELDS.filter(k => profile[k] && profile[k].toString().trim() !== '' && profile[k] !== '0').length;
  const pct = Math.round((filled / KEY_FIELDS.length) * 100);
  const pctColor = pct < 40 ? 'bg-red-500' : pct < 75 ? 'bg-amber-500' : 'bg-green-500';

  return (
    <div className="max-w-4xl">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Applicant Profile</h1>
          <p className="text-slate-400 text-sm">This data feeds into the AI scorer and cover letter generator.</p>
        </div>
        {saved && (
          <div className="bg-green-900/40 border border-green-700/50 text-green-400 text-sm font-semibold px-4 py-2 rounded-xl animate-pulse">
            ✅ Saved!
          </div>
        )}
      </div>

      {/* Completion Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-8">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-slate-400 font-medium">Profile Completeness</span>
          <span className={`text-sm font-bold ${pct < 40 ? 'text-red-400' : pct < 75 ? 'text-amber-400' : 'text-green-400'}`}>{pct}%</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div className={`h-full ${pctColor} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-slate-500 mt-2">{filled} of {KEY_FIELDS.length} key fields filled — complete your profile to improve AI scoring accuracy.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        
        {/* Basic Identity */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Basic Identity</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Full Name</label>
              <input name="name" value={profile.name} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Email</label>
              <input name="email" value={profile.email} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Phone</label>
              <input name="phone" value={profile.phone} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Location</label>
              <input name="location" value={profile.location} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
          </div>
        </div>

        {/* Education & Links */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Education & Links</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Degree</label>
              <input name="degree" value={profile.degree} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">College</label>
              <input name="college" value={profile.college} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">LinkedIn URL</label>
              <input name="linkedin" value={profile.linkedin} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">GitHub URL</label>
              <input name="github" value={profile.github} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-slate-400 mb-1">Resume Path (Server)</label>
              <input name="resume_path" value={profile.resume_path} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-slate-400 rounded p-2" />
            </div>
          </div>
        </div>

        {/* AI Matching & Keywords */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">AI Matching & Keywords (Comma separated)</h2>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Skills</label>
            <textarea name="skills" value={profile.skills} onChange={handleChange} rows="2" className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Search Keywords</label>
            <input name="keywords" value={profile.keywords} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
          </div>
          <div>
            <label className="block text-sm text-red-400 mb-1">Exclude Keywords (Skip listings with these)</label>
            <input name="exclude_keywords" value={profile.exclude_keywords} onChange={handleChange} className="w-full bg-slate-800 border border-red-900/50 text-white rounded p-2" />
          </div>
        </div>

        {/* Preferences */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Job Preferences</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Job Types (internship, full-time)</label>
              <input name="job_types" value={profile.job_types} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Min Stipend / Salary</label>
              <input type="number" name="min_stipend" value={profile.min_stipend} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-slate-400 mb-1">Preferred Cities</label>
              <input name="preferred_cities" value={profile.preferred_cities} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Years of Experience</label>
              <input type="number" name="years_of_experience" value={profile.years_of_experience} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Notice Period</label>
              <input name="notice_period" value={profile.notice_period} onChange={handleChange} className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
            </div>
          </div>
        </div>

        {/* Cold Email Targeting */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <h2 className="text-xl font-semibold text-white border-b border-slate-800 pb-2 mb-4">Cold Email Targeting</h2>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Target Companies (Domains)</label>
            <input name="target_companies" value={profile.target_companies} onChange={handleChange} placeholder="google.com, stripe.com" className="w-full bg-slate-800 border border-slate-700 text-white rounded p-2" />
          </div>
          <div>
            <label className="block text-sm text-red-400 mb-1">Avoid Companies (Domains)</label>
            <input name="avoid_companies" value={profile.avoid_companies} onChange={handleChange} className="w-full bg-slate-800 border border-red-900/50 text-white rounded p-2" />
          </div>
        </div>

        <button type="submit" disabled={saving} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg px-4 py-3 transition-colors">
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </form>
    </div>
  );
}
