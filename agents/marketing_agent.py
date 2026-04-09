"""
agents/marketing_agent.py
-------------------------
Marketing Agent — Growth Marketer
Responsibilities:
  1. Receive product spec from Product agent
  2. Use LLM to generate: tagline, description, cold email, social posts
  3. Send cold outreach email via SendGrid
  4. Post launch message to Slack using Block Kit
  5. Send all copy back to CEO
"""

import os
import json
import requests as http
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import message_bus as bus
from llm_client import call_llm_json


# ── Email via SendGrid ────────────────────────────────────────────────────────

def send_email(subject: str, html_body: str, to_email: str) -> bool:
    print(f"\n[Marketing] 📧 Sending email to {to_email}...")
    try:
        message = Mail(
            from_email=os.environ["SENDGRID_FROM_EMAIL"],
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        response = sg.send(message)
        if response.status_code in (200, 202):
            print(f"[Marketing] ✅ Email sent successfully (status {response.status_code}).")
            return True
        else:
            print(f"[Marketing] ❌ Email failed with status {response.status_code}.")
            return False
    except Exception as e:
        print(f"[Marketing] ❌ Email error: {e}")
        return False


# ── Slack Block Kit post ──────────────────────────────────────────────────────

def post_to_slack(tagline: str, description: str, pr_url: str, social_posts: dict) -> bool:
    print("\n[Marketing] 💬 Posting to Slack...")
    token = os.environ["SLACK_BOT_TOKEN"]
    channel = os.environ.get("SLACK_CHANNEL", "#launches")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚀 New Product Launch: CourseCompass"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Tagline:* _{tagline}_",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": description},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"},
                {"type": "mrkdwn", "text": "*Status:* ✅ Ready for review"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Social Media Drafts:*\n"
                    f"🐦 *Twitter/X:* {social_posts.get('twitter', '')}\n\n"
                    f"💼 *LinkedIn:* {social_posts.get('linkedin', '')}\n\n"
                    f"📸 *Instagram:* {social_posts.get('instagram', '')}"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Posted automatically by MarketingAgent 🤖 | LaunchMind MAS_",
                }
            ],
        },
    ]

    resp = http.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "blocks": blocks},
    )
    data = resp.json()
    if data.get("ok"):
        print("[Marketing] ✅ Slack message posted successfully.")
        return True
    else:
        print(f"[Marketing] ❌ Slack post failed: {data.get('error')}")
        return False


# ── Main runner ───────────────────────────────────────────────────────────────

def run(pr_url: str = "") -> dict:
    print("\n" + "=" * 60)
    print("  MARKETING AGENT STARTING")
    print("=" * 60)

    # ── Receive product spec from Product agent ───────────────────────────────
    messages = bus.receive("marketing")
    spec_msg = next(
        (m for m in messages if m["message_type"] == "result" and "spec" in m["payload"]),
        None,
    )

    if not spec_msg:
        print("[Marketing] ❌ No product spec received.")
        return {}

    spec = spec_msg["payload"]["spec"]
    print(f"[Marketing] 📥 Product spec received from {spec_msg['from_agent'].upper()}.")

    # ── LLM Call: Generate all marketing copy ────────────────────────────────
    print("\n[Marketing] 🧠 Generating marketing copy...")

    features_text = ", ".join([f["name"] for f in spec.get("features", [])])

    copy = call_llm_json(
        system_prompt=(
            "You are a growth marketing expert at a tech startup. "
            "Generate compelling marketing copy for the given product. "
            "Return JSON with exactly these keys:\n"
            "  tagline: string (under 10 words, punchy)\n"
            "  description: string (2-3 sentences for landing page)\n"
            "  email_subject: string\n"
            "  email_body: string (HTML formatted cold outreach email, 150-200 words, "
            "  addressed to 'Hi there,' — persuasive, includes a CTA)\n"
            "  twitter: string (under 280 chars, includes relevant hashtags)\n"
            "  linkedin: string (professional, 2-3 sentences)\n"
            "  instagram: string (casual, with emojis and hashtags)"
        ),
        user_prompt=(
            f"Product: CourseCompass\n"
            f"Value proposition: {spec.get('value_proposition', '')}\n"
            f"Key features: {features_text}\n"
            f"Target users: students looking to learn online\n\n"
            "Generate all marketing copy now."
        ),
    )

    print(f"\n[Marketing] ✅ Copy generated:")
    print(f"  Tagline: {copy.get('tagline')}")
    print(f"  Twitter: {copy.get('twitter')}")

    # ── Send email ────────────────────────────────────────────────────────────
    to_email = os.environ.get("TEST_EMAIL", os.environ.get("SENDGRID_FROM_EMAIL"))
    email_sent = send_email(
        subject=copy.get("email_subject", "Introducing CourseCompass"),
        html_body=copy.get("email_body", ""),
        to_email=to_email,
    )

    # ── Post to Slack ─────────────────────────────────────────────────────────
    slack_sent = post_to_slack(
        tagline=copy.get("tagline", ""),
        description=copy.get("description", ""),
        pr_url=pr_url or "https://github.com",
        social_posts={
            "twitter": copy.get("twitter", ""),
            "linkedin": copy.get("linkedin", ""),
            "instagram": copy.get("instagram", ""),
        },
    )

    # ── Send result back to CEO ───────────────────────────────────────────────
    result_msg = bus.make_message(
        from_agent="marketing",
        to_agent="ceo",
        message_type="result",
        payload={
            "copy": copy,
            "email_sent": email_sent,
            "email_to": to_email,
            "slack_posted": slack_sent,
            "status": "done",
        },
        parent_message_id=spec_msg["message_id"],
    )
    bus.send(result_msg)

    # ── Also send copy to QA ──────────────────────────────────────────────────
    qa_msg = bus.make_message(
        from_agent="marketing",
        to_agent="qa",
        message_type="result",
        payload={"copy": copy, "spec": spec},
    )
    bus.send(qa_msg)

    print("\n[Marketing] ✅ Done. Email sent and Slack posted.")
    return {"copy": copy, "email_sent": email_sent, "slack_posted": slack_sent}
