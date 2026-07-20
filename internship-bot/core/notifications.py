import logging
from typing import Optional
from core.models import ApplicationLog, User

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Stub: In a real environment, initialize SendGrid or Telegram Bot clients here
        self.enabled = True

    def notify_application_success(self, user: User, app_log: ApplicationLog):
        if not self.enabled:
            return
            
        message = f"🎉 Application Submitted: {app_log.title} at {app_log.company} ({app_log.platform})"
        
        # Stub: Send email
        logger.info(f"[Notification] Sending email to {user.email}: {message}")
        
        # Stub: Send Telegram
        # if user.telegram_chat_id:
        #     telegram.send_message(user.telegram_chat_id, message)
        
    def notify_run_completed(self, user: User, platform: str, applied_count: int, error_count: int):
        if not self.enabled:
            return
            
        message = f"🤖 Run Completed on {platform}: Applied to {applied_count} jobs with {error_count} errors."
        logger.info(f"[Notification] Sending email to {user.email}: {message}")

notification_service = NotificationService()
