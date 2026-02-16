"""Email integration — Send and receive emails via SMTP/IMAP."""

from __future__ import annotations

import asyncio
import email as email_lib
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import structlog

from seal_agent.config import settings
from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()


class EmailIntegration(BaseIntegration):
    """SMTP/IMAP email integration for sending and receiving sales emails."""

    def __init__(self) -> None:
        self._connected = False

    @property
    def name(self) -> str:
        return "email"

    @property
    def category(self) -> str:
        return "communication"

    async def connect(self, credentials: dict[str, str]) -> bool:
        """Verify SMTP/IMAP connectivity."""
        try:
            smtp_host = credentials.get("smtp_host", settings.smtp_host)
            smtp_port = int(credentials.get("smtp_port", settings.smtp_port))
            smtp_user = credentials.get("smtp_user", settings.smtp_user)
            smtp_password = credentials.get("smtp_password", settings.smtp_password)

            if not smtp_host or not smtp_user:
                log.warning("Email integration not configured — missing SMTP settings")
                return False

            # Test SMTP connection
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._test_smtp, smtp_host, smtp_port, smtp_user, smtp_password
            )
            self._connected = True
            log.info("Email integration connected")
            return True
        except Exception:
            log.exception("Failed to connect email integration")
            return False

    @staticmethod
    def _test_smtp(host: str, port: int, user: str, password: str) -> None:
        server = smtplib.SMTP(host, port, timeout=10)
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.quit()

    async def disconnect(self) -> None:
        self._connected = False
        log.info("Email integration disconnected")

    async def health_check(self) -> bool:
        return self._connected

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "send_email": self._send_email,
            "check_inbox": self._check_inbox,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for email")
        return await handler(params)

    async def _send_email(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send an email via SMTP."""
        to_email = params.get("to")
        subject = params.get("subject", "")
        body = params.get("body", "")
        html_body = params.get("html_body")

        if not to_email:
            return {"error": "Recipient email ('to') is required", "sent": False}

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, msg)

            log.info("Email sent", to=to_email, subject=subject)
            return {"sent": True, "to": to_email, "subject": subject}
        except Exception as e:
            log.exception("Failed to send email")
            return {"sent": False, "error": str(e)}

    @staticmethod
    def _smtp_send(msg: MIMEMultipart) -> None:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
        server.quit()

    async def _check_inbox(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check IMAP inbox for new emails."""
        folder = params.get("folder", "INBOX")
        limit = params.get("limit", 10)
        unseen_only = params.get("unseen_only", True)

        if not settings.imap_host or not settings.imap_user:
            return {"error": "IMAP not configured", "emails": []}

        try:
            loop = asyncio.get_event_loop()
            emails = await loop.run_in_executor(
                None, self._imap_fetch, folder, limit, unseen_only
            )
            return {"emails": emails, "count": len(emails)}
        except Exception as e:
            log.exception("Failed to check inbox")
            return {"error": str(e), "emails": []}

    @staticmethod
    def _imap_fetch(folder: str, limit: int, unseen_only: bool) -> list[dict]:
        mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        mail.login(settings.imap_user, settings.imap_password)
        mail.select(folder)

        criteria = "UNSEEN" if unseen_only else "ALL"
        _, message_numbers = mail.search(None, criteria)
        ids = message_numbers[0].split()

        emails = []
        for msg_id in ids[-limit:]:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw_email)

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")

            emails.append({
                "from": msg.get("From", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body": body[:1000],
                "message_id": msg.get("Message-ID", ""),
            })

        mail.close()
        mail.logout()
        return emails
