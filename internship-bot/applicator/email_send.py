"""
applicator/email_send.py
────────────────────────
Cold email sender using Gmail SMTP + App Password.
- Sends a professional application email with the AI-generated cover note
- Attaches the candidate's resume PDF if the file exists
- Subject line includes role and candidate name
- Uses .env credentials — never hardcoded
"""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)

# Gmail SMTP settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_cold_email(
    company: str,
    role: str,
    to_email: str,
    cover_note: str,
    profile: dict,
) -> dict:
    """
    Send a cold application email via Gmail SMTP.

    Args:
        company:    Company name for the subject line.
        role:       Role/title for the subject line.
        to_email:   Recipient email address.
        cover_note: The AI-generated cover note (email body).
        profile:    Candidate profile dict (for sender info + resume path).

    Returns:
        Dict: { success: bool, message: str }
    """
    try:
        # Get Gmail credentials from environment
        gmail_address = os.getenv("GMAIL_ADDRESS", "")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")

        if not gmail_address or not gmail_password:
            logger.warning("[Email] ✗ Gmail credentials not configured in .env")
            return {"success": False, "message": "Gmail credentials not set"}

        if not to_email or "@" not in to_email:
            logger.warning(f"[Email] ✗ Invalid recipient email: {to_email}")
            return {"success": False, "message": f"Invalid recipient email: {to_email}"}

        # Build the email
        candidate_name = profile.get("name", "Candidate")
        college_short = profile.get("college", "").split(",")[0].strip()

        msg = MIMEMultipart()
        msg["From"] = f"{candidate_name} <{gmail_address}>"
        msg["To"] = to_email
        msg["Subject"] = (
            f"Application for {role} Internship — "
            f"{candidate_name} (B.Tech CSE, DBATU)"
        )

        # Email body — the cover note with a professional wrapper
        email_body = f"""{cover_note}

---
{candidate_name}
{profile.get('degree', 'B.Tech Computer Engineering')} — {profile.get('year', '')}
{profile.get('college', '')}

📧 {profile.get('email', gmail_address)}
🔗 GitHub: {profile.get('github', 'N/A')}
🔗 LinkedIn: {profile.get('linkedin', 'N/A')}
📍 {profile.get('location', 'India')}
"""

        msg.attach(MIMEText(email_body, "plain", "utf-8"))

        # Attach resume if it exists
        resume_path = Path(profile.get("resume_path", "./data/resume.pdf"))
        if resume_path.exists() and resume_path.is_file():
            try:
                with open(resume_path, "rb") as f:
                    attachment = MIMEBase("application", "pdf")
                    attachment.set_payload(f.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        "Content-Disposition",
                        f"attachment; filename={candidate_name.replace(' ', '_')}_Resume.pdf",
                    )
                    msg.attach(attachment)
                    logger.info("  📎 Resume attached to email")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not attach resume: {e}")
        else:
            logger.info(f"  ℹ️ Resume file not found at {resume_path} — sending without attachment")

        # Send via Gmail SMTP
        if os.getenv("DRY_RUN", "false").lower() == "true":
            logger.info(f"  [DRY RUN] Would send email to {to_email} for {role} @ {company}")
            return {"success": True, "message": "Dry run — not sent"}

        logger.info(f"[Email] Sending cold email to {to_email} for {role} @ {company}…")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, to_email, msg.as_string())

        logger.info(f"[Email] ✅ Email sent successfully to {to_email}")
        return {"success": True, "message": f"Email sent to {to_email}"}

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[Email] ✗ Gmail authentication failed — "
            "check GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env. "
            "Make sure you're using an App Password, not your regular password."
        )
        return {"success": False, "message": "Gmail authentication failed"}
    except smtplib.SMTPException as e:
        logger.error(f"[Email] ✗ SMTP error: {e}")
        return {"success": False, "message": f"SMTP error: {str(e)}"}
    except Exception as e:
        logger.error(f"[Email] ✗ Unexpected error sending email: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}
