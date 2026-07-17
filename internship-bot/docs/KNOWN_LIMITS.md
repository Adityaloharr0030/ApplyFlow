# ApplyFlow — Known Limitations

This document formally records all known constraints, failure modes, and unresolved issues in the ApplyFlow automation system.
It is updated as new limitations are discovered.

---

## 1. Browser & Bot Detection

| Limitation | Severity | Status |
|---|---|---|
| **TLS Fingerprinting (JA3/JA4)** | 🔴 High | Unresolved. Cloudflare/Akamai fingerprint the TLS handshake before any JS runs. Our CDP JavaScript injection does not help here. Residential proxies are the only known mitigation. |
| **PyAutoGUI incompatible with headless servers** | 🟠 Medium | `PyAutoGUI` requires a physical screen or virtual frame buffer (Xvfb). Will crash in a Docker container or AWS EC2 without a VirtualDisplay wrapper. |
| **Internshala CAPTCHA block rate** | 🟠 Medium | Estimated ~30% of Internshala runs trigger a CAPTCHA, causing the circuit breaker to fire. Rate clears after ~12–24 hours. |
| **Chrome profile lock** | 🟡 Low | If Chrome crashes, the `bot_chrome_profile/Default/` directory may be left locked. The `taskkill` workaround in `browser.py` handles this on Windows only. |

---

## 2. LinkedIn

| Limitation | Severity | Status |
|---|---|---|
| **Guest API rate limit** | 🟠 Medium | LinkedIn's guest jobs API (`seeMoreJobPostings`) throttles after ~50–100 requests/hour from a single IP. The bot will receive 429 or empty results. |
| **Easy Apply coverage** | 🟡 Low | Even with `f_AL=true`, LinkedIn may occasionally return listings where the Easy Apply button is gated behind a Premium account. The bot logs these and skips gracefully. |
| **Login required for some Easy Apply jobs** | 🟡 Low | Some Easy Apply flows require the user to be logged in. The bot detects authwall redirects and skips these. Ensure LinkedIn credentials are in `.env`. |

---

## 3. AI / LLM

| Limitation | Severity | Status |
|---|---|---|
| **Groq rate limits (free tier)** | 🟠 Medium | Groq free tier limits ~6,000 tokens/minute. Heavy runs (30+ listings) may hit the limit and fall back to Gemini. |
| **LLM JSON hallucination** | 🟠 Medium | If Groq/Gemini returns malformed JSON (e.g., with markdown fences), `json.loads()` will throw. Partial fix: `response_schema` enforcement is pending (Phase C). |
| **Scoring bias toward submission** | 🟡 Low | `outcome_tracker.py` learns from "Applied ✓" (form submission), NOT interview callbacks. The model may over-score "easy to apply" jobs. Fix pending (Phase D). |
| **Cover note quality** | 🟡 Low | Cover notes are generated per-listing but are not post-processed for length or tone consistency. Notes may occasionally exceed the Internshala character limit. |

---

## 4. Platform-Specific

| Platform | Limitation | Workaround |
|---|---|---|
| **Internshala** | Heavy anti-automation detection. Circuit breaker fires at 3 CAPTCHA failures. | Run in non-headless mode (`HEADLESS=false`). Use residential proxy in future. |
| **Naukri** | OTP verification via email can time out if the email client is slow. | OTP handler waits 120s. Ensure email access is live during runs. |
| **Indeed** | Listings are scraped from `in.indeed.com` RSS; apply URLs may redirect to company ATS. The bot detects this and marks as "Manual". | No automated fix; manual applications are logged separately. |
| **Unstop** | API is unofficial and may change without notice. | Re-inspect API endpoint if scraping breaks after Unstop updates. |

---

## 5. Operational

| Limitation | Severity | Notes |
|---|---|---|
| **Single-threaded execution** | 🟠 Medium | All platforms run sequentially. A run applying to 5 platforms takes 45–90 min. Parallelization would require thread-safe state management. |
| **No automated tests** | 🟠 Medium | Zero unit or integration tests exist. Changes must be manually verified. Pytest suite is planned (Phase B). |
| **Windows-only PyAutoGUI** | 🟡 Low | Real-mouse automation has only been tested on Windows. macOS may need screen permission grants; Linux needs Xvfb. |

---

*Last updated: July 2026*
