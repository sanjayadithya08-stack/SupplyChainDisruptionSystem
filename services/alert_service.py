"""
Upgrade 4: Real Alert Service.
Sends alerts via Slack Webhook + SMTP Email.
Falls back to log-only mode if credentials are absent.
"""
from dataclasses import dataclass
from datetime import datetime
import json, os, sys, smtplib, html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

@dataclass
class Alert:
    id: str
    level: str
    message: str
    recipients: list
    timestamp: str
    acknowledged: bool
    channel: str = "log"

def _send_slack(level: str, message: str) -> bool:
    url = Config.SLACK_WEBHOOK_URL
    if not url or "hooks.slack.com" not in url:
        return False
    try:
        import requests as _req
        emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "EMERGENCY": "🔴", "INFO": "ℹ️"}.get(level, "📢")
        payload = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {level} — Supply Chain Alert"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"```{message[:2000]}```"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Sent at {datetime.utcnow().isoformat()} UTC by Antigravity V2"}]}
            ]
        }
        resp = _req.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            print(f"[Slack] Alert sent: {level}")
            return True
    except Exception as e:
        print(f"[Slack] Failed: {e}")
    return False

def _send_email(level: str, message: str, recipients: list, subject: str | None = None) -> bool:
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (subject or f"[{level}] Supply Chain Alert — Antigravity V2").replace("\r", " ").replace("\n", " ")
        msg["From"] = Config.SMTP_USER
        msg["To"] = ", ".join(recipients)
        html = f"""
        <html><body>
        <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto;padding:20px;border:2px solid #dc3545;border-radius:10px">
            <h2 style="color:#dc3545">{level} Alert</h2>
            <pre style="background:#f8f9fa;padding:15px;border-radius:6px;white-space:pre-wrap">{html.escape(message)}</pre>
            <p style="color:#6c757d;font-size:12px">Sent by Antigravity Supply Chain V2 · {datetime.utcnow().isoformat()} UTC</p>
        </div></body></html>"""
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_USER, recipients, msg.as_string())
        print(f"[Email] Alert sent to {recipients}")
        return True
    except Exception as e:
        print(f"[Email] Failed: {e}")
    return False

def send_recipient_email(level: str, subject: str, message: str, recipient: str, *, role: str) -> dict:
    """Email one named supplier/customer contact and report delivery truthfully."""
    ready = bool(Config.SMTP_USER and Config.SMTP_PASSWORD)
    delivered = _send_email(level, message, [recipient], subject=subject) if ready else False
    status = "sent" if delivered else "failed" if ready else "not_configured"
    channel = "email" if delivered else "log"
    alert = Alert(
        id=f"ALT-{int(datetime.utcnow().timestamp() * 1000)}", level=level,
        message=message, recipients=[recipient], timestamp=datetime.utcnow().isoformat(),
        acknowledged=False, channel=channel,
    )
    _log_alert(alert)
    try:
        from services.action_service import record_action
        record_action(
            "recipient_alert_sent" if delivered else "recipient_alert_logged",
            f"Critical disruption email to {role} {status.replace('_', ' ')}.",
            actor="system", status="completed" if delivered else "pending" if status == "not_configured" else "failed",
            metadata={"role": role, "delivery_status": status, "recipient": recipient, "channel": channel},
        )
    except Exception as exc:
        print(f"[ActionAudit] Recipient email result could not be recorded: {exc}")
    detail = ("Email sent successfully." if status == "sent" else
              "SMTP credentials are not configured." if status == "not_configured" else
              "SMTP delivery failed; the notice was logged locally.")
    return {"status": status, "channel": channel, "recipient": recipient, "detail": detail}

def _log_alert(alert: Alert):
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
    try:
        with open(Config.ALERTS_LOG_PATH, "a") as f:
            f.write(json.dumps(alert.__dict__) + "\n")
    except Exception as e:
        print(f"[AlertLog] Write failed: {e}")

def send_alert(level: str, message: str, recipients: list) -> bool:
    channels = []
    if _send_slack(level, message): channels.append("slack")
    if _send_email(level, message, recipients): channels.append("email")
    if not channels: channels.append("log")

    alert = Alert(
        id=f"ALT-{int(datetime.utcnow().timestamp())}",
        level=level, message=message, recipients=recipients,
        timestamp=datetime.utcnow().isoformat(),
        acknowledged=False,
        channel=",".join(channels)
    )
    _log_alert(alert)
    try:
        from services.action_service import record_action
        record_action("alert_sent" if any(channel in {"slack", "email"} for channel in channels) else "alert_logged",
                      f"{level} alert {'delivered' if any(channel in {'slack', 'email'} for channel in channels) else 'saved locally'} via {alert.channel}.", actor="system",
                      metadata={"recipients": recipients, "level": level, "channel": alert.channel})
    except Exception as e:
        print(f"[ActionAudit] Alert was logged but activity record failed: {e}")
    return any(channel in {"slack", "email"} for channel in channels)

def send_prevention_plan(plan: dict, recipients: list) -> bool:
    priority = plan.get("priority", "P3")
    level = "EMERGENCY" if priority == "P1" else "WARNING" if priority == "P2" else "INFO"
    summary = plan.get("llm_summary", "")
    actions = "\n".join([f"  • {a}" for a in plan.get("immediate_actions", [])])
    message = f"Supply Chain Action Required\nPriority: {priority} | Cost: {plan.get('estimated_cost_impact','?')}\n\n"
    if summary: message += f"AI Summary:\n{summary}\n\n"
    message += f"Immediate Actions:\n{actions}"
    return send_alert(level, message, recipients)

def get_recent_alerts(n: int = 10) -> list[Alert]:
    try:
        if not os.path.exists(Config.ALERTS_LOG_PATH): return []
        alerts = []
        with open(Config.ALERTS_LOG_PATH, "r") as f:
            for line in reversed(f.readlines()):
                if not line.strip(): continue
                data = json.loads(line)
                if "channel" not in data: data["channel"] = "log"
                alerts.append(Alert(**data))
                if len(alerts) >= n: break
        return alerts
    except Exception as e:
        print(f"[AlertLog] Read failed: {e}")
        return []
