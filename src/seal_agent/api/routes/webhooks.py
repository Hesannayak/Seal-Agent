"""Webhook endpoints — Receive inbound events from external services."""

from __future__ import annotations

import hashlib
import hmac
import time

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from seal_agent.config import settings
from seal_agent.db.database import get_session
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.db.repositories.prospect_repo import ProspectRepository

log = structlog.get_logger()

router = APIRouter()


# ─── Inbound Email Webhook ────────────────────────────────────────────────────
# Compatible with SendGrid Inbound Parse, Mailgun, and similar providers
# that POST parsed email data to a webhook URL.


@router.post("/email/inbound")
async def inbound_email(request: Request) -> dict:
    """Receive an inbound email via webhook (SendGrid / Mailgun format).

    Expected form fields or JSON:
        from, to, subject, text, html (optional)
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    sender = payload.get("from", payload.get("sender", ""))
    subject = payload.get("subject", "")
    body = payload.get("text", payload.get("body", ""))

    if not sender or not body:
        raise HTTPException(status_code=400, detail="Missing 'from' or 'text' field")

    log.info("Inbound email received", sender=sender, subject=subject)

    # Extract email address from "Name <email>" format
    email_addr = sender
    if "<" in sender and ">" in sender:
        email_addr = sender.split("<")[1].rstrip(">").strip()

    try:
        async with get_session() as session:
            # Look up prospect by email
            prospect_repo = ProspectRepository(session)
            prospect = await prospect_repo.get_by_email(email_addr)

            prospect_id = prospect.id if prospect else "unknown"

            # Store as inbound interaction
            interaction_repo = InteractionRepository(session)
            interaction = await interaction_repo.create({
                "prospect_id": prospect_id,
                "channel": "email",
                "direction": "inbound",
                "subject": subject,
                "content": body[:5000],
            })

            # If prospect exists, mark as replied (they responded to our outreach)
            if prospect:
                await prospect_repo.update(prospect.id, {"sentiment": "positive"})

            log.info(
                "Inbound email stored",
                interaction_id=interaction.id,
                prospect_id=prospect_id,
            )

            return {
                "status": "received",
                "interaction_id": interaction.id,
                "prospect_id": prospect_id,
                "known_prospect": prospect is not None,
            }
    except Exception:
        log.exception("Error processing inbound email")
        raise HTTPException(status_code=500, detail="Failed to process email")


# ─── Email Tracking Webhook ───────────────────────────────────────────────────
# For open/click tracking from email service providers


@router.post("/email/tracking")
async def email_tracking(request: Request) -> dict:
    """Track email opens and clicks from ESP webhooks."""
    payload = await request.json()

    events = payload if isinstance(payload, list) else [payload]
    processed = 0

    try:
        async with get_session() as session:
            interaction_repo = InteractionRepository(session)

            for event in events:
                event_type = event.get("event", event.get("type", ""))
                interaction_id = event.get("interaction_id", event.get("sg_message_id", ""))

                if not interaction_id:
                    continue

                interaction = await interaction_repo.get_by_id(interaction_id)
                if not interaction:
                    continue

                if event_type in ("open", "opened"):
                    interaction.opened = True
                    processed += 1
                elif event_type in ("click", "clicked"):
                    interaction.clicked = True
                    processed += 1
                elif event_type in ("reply", "replied"):
                    interaction.replied = True
                    processed += 1

            await session.flush()
    except Exception:
        log.exception("Error processing tracking events")

    return {"status": "ok", "processed": processed}


# ─── Slack Events Webhook ─────────────────────────────────────────────────────


@router.post("/slack/events")
async def slack_events(request: Request) -> dict:
    """Receive Slack events (messages, mentions, etc.).

    Handles:
    - URL verification challenge
    - Message events directed at the bot
    """
    body = await request.body()
    payload = await request.json()

    # Slack URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    # Verify Slack signature if signing secret is configured
    if settings.slack_signing_secret:
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        slack_signature = request.headers.get("X-Slack-Signature", "")

        # Reject requests older than 5 minutes (replay protection)
        if abs(time.time() - int(timestamp or 0)) > 300:
            raise HTTPException(status_code=403, detail="Request too old")

        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        computed = (
            "v0="
            + hmac.new(
                settings.slack_signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        if not hmac.compare_digest(computed, slack_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Process event
    event = payload.get("event", {})
    event_type = event.get("type", "")

    if event_type == "message" and not event.get("bot_id"):
        user = event.get("user", "unknown")
        text = event.get("text", "")
        channel = event.get("channel", "")

        log.info("Slack message received", user=user, channel=channel)

        # Process the message through the agent
        try:
            agent = request.app.state.agent
            response = await agent.process_message(
                message=text,
                context={
                    "channel": "slack",
                    "slack_user": user,
                    "slack_channel": channel,
                },
            )

            # Send response back to Slack
            from seal_agent.integrations.communication.slack import SlackIntegration

            slack = SlackIntegration()
            connected = await slack.connect({})
            if connected:
                await slack.execute("send_message", {
                    "channel": channel,
                    "text": response,
                })
                await slack.disconnect()

            return {"status": "responded"}
        except Exception:
            log.exception("Error processing Slack message")

    return {"status": "ok"}


# ─── Generic CRM Webhook ─────────────────────────────────────────────────────


@router.post("/crm/events")
async def crm_events(request: Request) -> dict:
    """Receive CRM events (deal stage changes, contact updates, etc.).

    Works with HubSpot webhooks, Salesforce outbound messages, etc.
    """
    payload = await request.json()

    events = payload if isinstance(payload, list) else [payload]
    processed = 0

    for event in events:
        event_type = event.get("subscriptionType", event.get("type", ""))
        object_type = event.get("objectType", event.get("object", ""))

        log.info("CRM event received", event_type=event_type, object_type=object_type)

        if object_type == "deal" and "propertyName" in event:
            prop = event.get("propertyName", "")
            if prop == "dealstage":
                # Deal stage changed in CRM — sync back to our DB
                from seal_agent.db.repositories.deal_repo import DealRepository

                try:
                    async with get_session() as session:
                        deal_repo = DealRepository(session)
                        crm_deal_id = str(event.get("objectId", ""))
                        new_stage = event.get("propertyValue", "")

                        # Look up deal by CRM reference in custom_fields
                        # (in production, add a crm_id column for direct lookup)
                        log.info(
                            "CRM deal stage change",
                            crm_deal_id=crm_deal_id,
                            new_stage=new_stage,
                        )
                        processed += 1
                except Exception:
                    log.exception("Error processing CRM deal event")

        processed += 1

    return {"status": "ok", "processed": processed}
