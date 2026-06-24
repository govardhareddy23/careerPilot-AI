"""
Notification Agent

Provides daily summaries, weekly reports, new opportunity alerts,
interview reminders, and follow-up reminders via email/Telegram/Discord
using the notification MCP tool.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.core.config import get_settings
from backend.db.session import SessionLocal
from backend.db.models import Notification, Job
from backend.mcp_servers.client_helpers import send_notification


class NotificationAgent(BaseAgent):
    name = "notification"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_id = state.get("user_id")
        settings = get_settings()

        db = SessionLocal()
        try:
            new_jobs = db.query(Job).filter(
                Job.user_id == user_id, Job.status == "discovered"
            ).count()
            awaiting = db.query(Job).filter(
                Job.user_id == user_id, Job.status == "awaiting_approval"
            ).count()
            interviews = db.query(Job).filter(
                Job.user_id == user_id, Job.status == "interview"
            ).count()

            title = "CareerPilot AI - Daily Summary"
            body = (
                f"New jobs discovered: {new_jobs}\n"
                f"Applications awaiting your approval: {awaiting}\n"
                f"Active interview processes: {interviews}\n\n"
                f"Log in to CareerPilot to review and approve pending applications."
            )

            channel_config = {
                "telegram_bot_token": settings.telegram_bot_token,
                "telegram_chat_id": settings.telegram_chat_id,
                "discord_webhook_url": settings.discord_webhook_url,
                "smtp_user": settings.smtp_user,
            }

            sent_any = False
            for channel in ["email", "telegram", "discord"]:
                sent = send_notification(channel, title, body, channel_config)
                db.add(Notification(
                    user_id=user_id, channel=channel, title=title, body=body, sent=sent
                ))
                sent_any = sent_any or sent
            db.commit()
        finally:
            db.close()

        return {
            "logs": [f"[notification] completed: daily summary prepared "
                     f"({'sent' if sent_any else 'no channels configured'})"],
        }
