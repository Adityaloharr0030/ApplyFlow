import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

SCORER_DATA = [
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Flutter Developer Intern at Groww | Remote | 3 months | ₹15,000/month",
        "output": '{"score": 10, "reason": "Perfect match — Flutter is Aditya\'s primary skill, remote, strong stipend, top fintech company", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: React Frontend Intern at Razorpay | Bengaluru (hybrid) | 2 months | ₹12,000/month",
        "output": '{"score": 9, "reason": "React is core skill, Razorpay is top brand, hybrid in Bengaluru acceptable, strong stipend", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Full Stack Developer Intern at Startup | Remote | 6 months | ₹8,000/month",
        "output": '{"score": 8, "reason": "Full stack matches MERN skills, remote ideal, stipend acceptable for startup", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Mobile App Developer Intern at Zepto | Mumbai (hybrid) | 3 months | ₹10,000/month",
        "output": '{"score": 8, "reason": "Mobile dev matches Flutter, Zepto is good brand, Mumbai hybrid manageable", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Next.js Frontend Intern at Agency | Remote | 3 months | ₹6,000/month",
        "output": '{"score": 7, "reason": "Next.js is direct skill match, remote is ideal mode, stipend is low but acceptable", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Node.js Backend Intern at Fintech Startup | Pune | 3 months | ₹8,000/month",
        "output": '{"score": 7, "reason": "Node.js and Express match backend skills, Pune is target city, decent stipend", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: MERN Stack Intern at EdTech Company | Hyderabad | 2 months | ₹5,000/month",
        "output": '{"score": 6, "reason": "MERN is exact stack, Hyderabad acceptable, stipend is low but role is strong match", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Web Developer Intern at Digital Agency | Remote | 3 months | ₹3,000/month",
        "output": '{"score": 6, "reason": "Web dev is broad match, remote is ideal, but stipend is very low — borderline", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Python Developer Intern at Data Firm | Remote | 3 months | ₹5,000/month",
        "output": '{"score": 5, "reason": "Python is secondary skill, data firm may not fit web/mobile profile, skip unless no better options", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Android Developer Intern at Gaming Company | Chennai | 2 months | ₹4,000/month",
        "output": '{"score": 4, "reason": "Android (Kotlin/Java) not in skillset — Flutter covers cross-platform but not native Android; Chennai is far from preferred cities", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Java Backend Intern at IT Services Company | Noida | 6 months | ₹8,000/month",
        "output": '{"score": 3, "reason": "Java not in skillset, IT services company is commodity work, Noida not in preferred cities, 6 months too long for final year student", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Content Writing Intern at Marketing Agency | Remote | 3 months | Unpaid",
        "output": '{"score": 1, "reason": "Content writing is completely unrelated to any technical skill; unpaid; waste of time for a developer", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: HR Intern at Corporate Company | Delhi | 3 months | ₹5,000/month",
        "output": '{"score": 1, "reason": "HR role has zero technical overlap; completely wrong domain for a software developer", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Data Science Intern at Analytics Firm | Remote | 3 months | ₹10,000/month",
        "output": '{"score": 4, "reason": "Data science uses Python but requires ML/pandas/sklearn skills not in core profile; good stipend but mismatched domain", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: UI/UX Design Intern at Product Startup | Remote | 2 months | ₹6,000/month",
        "output": '{"score": 3, "reason": "Design role, not development — Aditya is a developer not a designer; skills don't match even though it's remote", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Flutter + Firebase Developer Intern at HealthTech Startup | Remote | 3 months | ₹12,000/month",
        "output": '{"score": 10, "reason": "Flutter AND Firebase are both in Aditya\'s core skillset, remote, strong stipend, HealthTech is growing sector", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: AI/ML Intern at Deep Learning Lab | Remote | 6 months | ₹15,000/month",
        "output": '{"score": 3, "reason": "AI/ML requires TensorFlow/PyTorch skills not in profile; Gemini API experience is integration, not ML research; 6 months conflicts with final year academics", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: DevOps Intern at SaaS Company | Bengaluru | 3 months | ₹10,000/month",
        "output": '{"score": 3, "reason": "DevOps requires Docker/Kubernetes/CI-CD skills not in current profile; Bengaluru is preferred city but wrong tech domain", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: React Native Developer Intern at Travel App | Remote | 3 months | ₹8,000/month",
        "output": '{"score": 8, "reason": "React Native closely relates to both React and Flutter experience, remote, decent stipend, mobile domain matches profile", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Generative AI Integration Intern at SaaS Startup | Remote | 2 months | ₹10,000/month",
        "output": '{"score": 9, "reason": "Gemini API and Claude API are explicitly in Aditya\'s skills; AI integration is emerging high-value niche; remote; strong stipend", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Frontend Intern at E-Commerce Platform | Remote | 3 months | ₹0 (certificate only)",
        "output": '{"score": 2, "reason": "Frontend matches skills but unpaid internship is exploitative; certificate-only offers should be avoided; remote doesn\'t compensate for zero stipend", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Software Developer Intern at MNC (TCS/Infosys/Wipro) | Pune | 6 months | ₹10,000/month",
        "output": '{"score": 4, "reason": "MNC service companies offer low learning value for a product-focused developer; 6 months too long for final year; Pune is good city but not worth it", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Open Source Contributor Intern at Linux Foundation | Remote | 3 months | ₹20,000/month (stipend)",
        "output": '{"score": 7, "reason": "Open source contribution is excellent resume value, remote, strong stipend — but requires unfamiliar C/systems skills; worth applying for portfolio value", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Backend Engineer Intern at Fintech Unicorn | Bengaluru | 3 months | ₹25,000/month",
        "output": '{"score": 8, "reason": "High stipend, top-tier company, backend with Node.js matches profile, Bengaluru is target city — strong brand value even if not perfect tech match", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Flutter Developer Intern at EdTech Startup | Jalgaon (on-site) | 3 months | ₹5,000/month",
        "output": '{"score": 6, "reason": "Flutter matches primary skill, local Jalgaon means no relocation cost, but on-site only and low stipend; acceptable if no remote options available", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Full Stack MERN Intern at Product Company | Remote | 3 months | ₹15,000/month",
        "output": '{"score": 10, "reason": "MERN (MongoDB Express React Node) is Aditya\'s exact stack, product company means real work, remote, excellent stipend — apply immediately", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Cybersecurity Intern at Defense PSU | Delhi | 6 months | ₹12,000/month",
        "output": '{"score": 1, "reason": "Cybersecurity is completely different domain, PSU has slow environment, Delhi is far, 6 months blocks final year — strong skip", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Blockchain Developer Intern at Web3 Startup | Remote | 2 months | ₹8,000/month",
        "output": '{"score": 3, "reason": "Blockchain/Solidity not in skillset; Web3 is high-risk domain for a short internship; not worth learning curve unless already interested in crypto", "apply": false}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: TypeScript + React Intern at SaaS Product | Remote | 3 months | ₹10,000/month",
        "output": '{"score": 9, "reason": "TypeScript extends React skills, SaaS product company = real product experience, remote, solid stipend — excellent match", "apply": true}'
    },
    {
        "text_input": "Score this internship for Aditya Lohar (B.Tech CSE, DBATU 2027, skills: Flutter React Next.js Node.js MongoDB Python). INTERNSHIP: Software Testing/QA Intern at IT Company | Remote | 3 months | ₹4,000/month",
        "output": '{"score": 2, "reason": "QA/Testing is not development work, low stipend, does not advance Aditya\'s developer career trajectory", "apply": false}'
    }
]

COVER_LETTER_DATA = [
    {
        "text_input": "Write a cover letter for: Flutter Developer Intern at Groww | Remote. Candidate: Aditya Lohar, B.Tech CSE DBATU 2027, skills Flutter React Node.js MongoDB Python, projects: CrazyXAni (anime streaming), Krushi Mitra (AI farming app), achievement: Top 800/31000+ Meta PyTorch Hackathon",
        "output": "Dear Hiring Team,\n\nI'm Aditya Lohar, a final-year B.Tech Computer Engineering student at KBSCOE Jalgaon (DBATU, 2027), applying for the Flutter Developer Intern role at Groww.\n\nFlutter is my primary framework — I've used it to build production-grade mobile applications with Riverpod for state management and Firebase for backend. My project Krushi Mitra, an AI-powered farming app, was built in Flutter and presented at the FAR AWAY Hackathon 2026.\n\nI also ranked in the top 800 of 31,000+ participants at the Meta PyTorch OpenEnv Hackathon, which reflects my ability to perform under competitive conditions.\n\nI'm available immediately and excited to contribute to Groww's mission.\n\nRegards,\nAditya Lohar\nGitHub: github.com/Adityaloharaa0030"
    },
    {
        "text_input": "Write a cover letter for: React Frontend Intern at Razorpay | Bengaluru. Candidate: Aditya Lohar, B.Tech CSE DBATU 2027, skills Flutter React Next.js Node.js MongoDB Python, projects: CrazyXAni (anime streaming), Neural Protocol (portfolio in Next.js)",
        "output": "Dear Hiring Team,\n\nI'm Aditya Lohar, a final-year B.Tech Computer Engineering student (DBATU, 2027), writing for the React Frontend Intern position at Razorpay.\n\nReact is one of my core skills. I built CrazyXAni, an anime streaming platform using Next.js and React that integrates multiple live APIs (Anilist, Gogoanime, Zoro) — giving me real experience with performance optimization, dynamic routing, and scalable frontend architecture.\n\nRazorpay's product-first culture is exactly the environment I want to grow in as a developer. I'm ready to contribute from day one.\n\nRegards,\nAditya Lohar\nGitHub: github.com/Adityaloharaa0030"
    },
    {
        "text_input": "Write a cover letter for: Full Stack MERN Intern at Startup | Remote. Candidate: Aditya Lohar, B.Tech CSE DBATU 2027, skills Flutter React Next.js Node.js MongoDB Python, projects: CrazyXAni (anime streaming with Node.js + MongoDB backend)",
        "output": "Dear Hiring Manager,\n\nI'm Aditya Lohar, a B.Tech Computer Engineering student at KBSCOE Jalgaon (DBATU, 2027), applying for the Full Stack MERN Intern role.\n\nMERN is my primary stack. My project CrazyXAni — an anime streaming platform — is built entirely on Next.js, Node.js, Express, and MongoDB, handling real API integrations and serving live users. This gave me hands-on experience with REST API design, database schema optimization, and frontend-backend integration.\n\nI work best in async, remote environments and am available to start immediately.\n\nRegards,\nAditya Lohar\nGitHub: github.com/Adityaloharaa0030"
    },
    {
        "text_input": "Write a cover letter for: Generative AI Integration Intern at SaaS Startup | Remote. Candidate: Aditya Lohar, B.Tech CSE DBATU 2027, skills Gemini API Claude API Flutter React Node.js, projects: ApplyFlow (AI internship bot using Gemini), Krushi Mitra (AI farming app)",
        "output": "Dear Hiring Team,\n\nI'm Aditya Lohar, a final-year B.Tech CSE student (DBATU, 2027), excited to apply for the Generative AI Integration Intern role.\n\nI have direct, production-level experience integrating Gemini API and Claude API into real applications. ApplyFlow, my internship automation bot, uses Gemini for intelligent listing scoring and cover letter generation. Krushi Mitra, presented at FAR AWAY Hackathon 2026, uses AI for crop disease detection and farmer advisories.\n\nI understand the practical challenges of AI integration — prompt engineering, rate limiting, fallback handling, and cost optimization — not just the theory.\n\nRegards,\nAditya Lohar\nGitHub: github.com/Adityaloharaa0030"
    },
    {
        "text_input": "Write a cover letter for: Node.js Backend Intern at Fintech Startup | Pune. Candidate: Aditya Lohar, B.Tech CSE DBATU 2027, skills Node.js Express MongoDB REST API Firebase, projects: CrazyXAni backend (Node.js + MongoDB + Express)",
        "output": "Dear Hiring Team,\n\nI'm Aditya Lohar, a B.Tech Computer Engineering student at KBSCOE Jalgaon (DBATU, 2027), applying for the Node.js Backend Intern role.\n\nI've designed and deployed REST APIs using Node.js and Express with MongoDB for real projects. CrazyXAni's backend handles multi-source API aggregation, authentication, and caching — built solo and serving live users.\n\nI'm comfortable with async patterns, middleware design, and debugging production issues. Pune is my preferred city and I can join immediately.\n\nRegards,\nAditya Lohar\nGitHub: github.com/Adityaloharaa0030"
    },
    {
        "text_input": "Write a cover letter for: Mobile App Developer Intern at E-Commerce App | Remote. Candidate: Aditya Lohar, B.Tech CSE DBATU 2027, skills Flutter Riverpod Firebase Dart, projects: Krushi Mitra (Flutter mobile app, AI-powered)",
        "output": "Dear Hiring Team,\n\nI'm Aditya Lohar, a final-year B.Tech CSE student (DBATU, 2027), applying for the Mobile App Developer Intern position.\n\nI build Flutter apps with Riverpod for state management and Firebase for real-time backend — the same stack used in production-grade apps. Krushi Mitra, my AI-powered farming app built for a national hackathon, demonstrates my ability to ship a complete, polished mobile product under pressure.\n\nI'm available immediately for a remote role and excited to ship features that real users interact with.\n\nRegards,\nAditya Lohar\nGitHub: github.com/Adityaloharaa0030"
    }
]

def write_jsonl(filename: Path, data: list):
    with open(filename, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"✅ Created {filename} with {len(data)} records")

def validate_jsonl(filename: Path):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            try:
                obj = json.loads(line)
                if "text_input" not in obj or "output" not in obj:
                    print(f"❌ Validation failed on line {i}: Missing 'text_input' or 'output' key")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ Validation failed on line {i}: Invalid JSON - {e}")
                return False
    print(f"✅ Validation passed for {filename} ({len(lines)} lines)")
    return True

if __name__ == "__main__":
    scorer_path = DATA_DIR / "training_data_scorer.jsonl"
    cover_path = DATA_DIR / "training_data_coverletter.jsonl"
    
    print("Generating training data files...")
    write_jsonl(scorer_path, SCORER_DATA)
    write_jsonl(cover_path, COVER_LETTER_DATA)
    
    print("\nValidating files...")
    validate_jsonl(scorer_path)
    validate_jsonl(cover_path)
    
    print("\nNext steps:")
    print("1. Go to https://aistudio.google.com/tuning")
    print(f"2. Upload {scorer_path} to tune your scorer model")
    print(f"3. Upload {cover_path} to tune your cover letter model")
