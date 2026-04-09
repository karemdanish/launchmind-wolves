"""
agents/ceo_agent.py
-------------------
CEO Agent — Orchestrator
Responsibilities:
  1. Receive the startup idea
  2. Use LLM to decompose it into tasks for Product, Engineer, Marketing agents
  3. Send structured task messages via the message bus
  4. Review each agent's output using LLM reasoning
  5. Send revision_request if output is not good enough (feedback loop)
  6. Compile final summary and post to Slack
"""

import time
import json
import os
import requests

import message_bus as bus
from llm_client import call_llm, call_llm_json


STARTUP_IDEA = (
    "CourseCompass — a CLI tool that helps students search, filter, "
    "and compare online courses from platforms like Coursera, Udemy, "
    "and edX based on price, rating, duration, and skill level."
)


# ── Step 1: Decompose the idea into agent tasks ───────────────────────────────

def decompose_idea(idea: str) -> dict:
    print("\n[CEO] 🧠 Decomposing startup idea into agent tasks...")
    result = call_llm_json(
        system_prompt=(
            "You are the CEO of a micro-startup. You receive a startup idea "
            "and decompose it into specific tasks for three teams: product, engineer, marketing. "
            "Return JSON with keys: product_task, engineer_task, marketing_task. "
            "Each value is a string describing exactly what that team should do."
        ),
        user_prompt=f"Startup idea: {idea}",
    )
    print(f"[CEO] Tasks decomposed:\n{json.dumps(result, indent=2)}")
    return result


# ── Step 2: Send tasks to each sub-agent ─────────────────────────────────────

def send_tasks(tasks: dict, idea: str) -> None:
    print("\n[CEO] 📤 Sending tasks to agents...")

    msg_product = bus.make_message(
        from_agent="ceo",
        to_agent="product",
        message_type="task",
        payload={
            "idea": idea,
            "focus": tasks["product_task"],
        },
    )
    bus.send(msg_product)

    msg_engineer = bus.make_message(
        from_agent="ceo",
        to_agent="engineer",
        message_type="task",
        payload={
            "idea": idea,
            "focus": tasks["engineer_task"],
        },
    )
    bus.send(msg_engineer)

    msg_marketing = bus.make_message(
        from_agent="ceo",
        to_agent="marketing",
        message_type="task",
        payload={
            "idea": idea,
            "focus": tasks["marketing_task"],
        },
    )
    bus.send(msg_marketing)


# ── Step 3: Review an agent's output using LLM ───────────────────────────────

def review_output(agent_name: str, output: dict, idea: str) -> dict:
    """
    Ask LLM to review agent output.
    Returns: { "acceptable": bool, "feedback": str }
    """
    print(f"\n[CEO] 🔍 Reviewing output from {agent_name.upper()} agent...")
    result = call_llm_json(
        system_prompt=(
            "You are a strict startup CEO reviewing work from your team. "
            "You receive an agent's output and decide if it is good enough. "
            "Return JSON with keys: "
            "  acceptable (boolean), "
            "  feedback (string — specific issues if not acceptable, or 'Looks good.' if acceptable). "
            "Be strict: vague outputs, missing fields, or outputs not relevant to the startup idea must be rejected."
        ),
        user_prompt=(
            f"Startup idea: {idea}\n\n"
            f"Agent: {agent_name}\n\n"
            f"Agent output:\n{json.dumps(output, indent=2)}"
        ),
    )
    status = "✅ ACCEPTED" if result.get("acceptable") else "❌ REJECTED"
    print(f"[CEO] Review result for {agent_name}: {status}")
    print(f"[CEO] Feedback: {result.get('feedback')}")
    return result


# ── Step 4: Request revision if needed ───────────────────────────────────────

def request_revision(agent_name: str, feedback: str, original_msg_id: str) -> None:
    print(f"\n[CEO] 🔄 Sending revision request to {agent_name.upper()}...")
    msg = bus.make_message(
        from_agent="ceo",
        to_agent=agent_name,
        message_type="revision_request",
        payload={
            "feedback": feedback,
            "instruction": f"Please revise your output. Specific issues: {feedback}",
        },
        parent_message_id=original_msg_id,
    )
    bus.send(msg)


# ── Step 5: Post final summary to Slack ──────────────────────────────────────

def post_final_summary_to_slack(product_spec: dict, pr_url: str, email_sent_to: str) -> None:
    print("\n[CEO] 📣 Posting final summary to Slack...")

    token = os.environ["SLACK_BOT_TOKEN"]
    channel = os.environ.get("SLACK_CHANNEL", "#launches")

    tagline = product_spec.get("tagline", "CourseCompass — find your perfect course")
    value_prop = product_spec.get("value_proposition", "")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚀 LaunchMind — Startup Launch Complete!"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Startup:* CourseCompass\n*Tagline:* {tagline}",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Value Proposition:* {value_prop}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"},
                {"type": "mrkdwn", "text": f"*Email sent to:* {email_sent_to}"},
                {"type": "mrkdwn", "text": "*Status:* ✅ All agents completed"},
                {"type": "mrkdwn", "text": "*Agents:* CEO · Product · Engineer · Marketing · QA"},
            ],
        },
        {
            "type": "divider",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_Built autonomously by LaunchMind Multi-Agent System_ 🤖",
            },
        },
    ]

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "blocks": blocks},
    )
    data = resp.json()
    if data.get("ok"):
        print("[CEO] ✅ Final summary posted to Slack successfully.")
    else:
        print(f"[CEO] ❌ Slack post failed: {data.get('error')}")


# ── Main CEO runner ───────────────────────────────────────────────────────────

def run(
    product_result: dict,
    engineer_result: dict,
    marketing_result: dict,
    qa_result: dict,
) -> None:
    """
    Called from main.py after all sub-agents have run.
    CEO reviews each result and handles feedback loops.
    Returns aggregated results for final summary.
    """
    idea = STARTUP_IDEA

    # ── Review Product output ────────────────────────────────────────────────
    review = review_output("product", product_result, idea)
    if not review["acceptable"]:
        request_revision("product", review["feedback"], "initial-task")
        print("[CEO] ⚠️  Product agent needs revision — in a full async system it would re-run.")
        print("[CEO]     For this demo, logging the revision request and continuing.")
    else:
        confirm = bus.make_message(
            from_agent="ceo", to_agent="product",
            message_type="confirmation",
            payload={"status": "accepted", "message": "Product spec approved."},
        )
        bus.send(confirm)

    # ── Review Engineer output ───────────────────────────────────────────────
    review_eng = review_output("engineer", engineer_result, idea)
    if not review_eng["acceptable"]:
        request_revision("engineer", review_eng["feedback"], "initial-task")
        print("[CEO] ⚠️  Engineer agent needs revision — logging revision request.")
    else:
        confirm = bus.make_message(
            from_agent="ceo", to_agent="engineer",
            message_type="confirmation",
            payload={"status": "accepted", "message": "Engineer output approved."},
        )
        bus.send(confirm)

    # ── Review QA output ─────────────────────────────────────────────────────
    if qa_result.get("verdict") == "fail":
        print(f"\n[CEO] ❌ QA returned FAIL verdict. Issues: {qa_result.get('issues')}")
        print("[CEO] 🔄 Sending revision request to Engineer based on QA feedback...")
        revision_msg = bus.make_message(
            from_agent="ceo",
            to_agent="engineer",
            message_type="revision_request",
            payload={
                "feedback": qa_result.get("issues"),
                "instruction": "QA has flagged issues with the landing page. Please address them.",
                "qa_report": qa_result,
            },
        )
        bus.send(revision_msg)
        # CEO reasons about QA verdict using LLM
        ceo_reasoning = call_llm(
            system_prompt="You are a startup CEO. The QA agent has flagged issues with the landing page.",
            user_prompt=(
                f"QA issues: {qa_result.get('issues')}\n\n"
                "Write a brief instruction (2-3 sentences) to the Engineer on how to fix these."
            ),
        )
        print(f"[CEO] 💬 CEO reasoning on QA feedback:\n{ceo_reasoning}")
    else:
        print("\n[CEO] ✅ QA verdict: PASS — no revision needed.")

    # ── Post final Slack summary ─────────────────────────────────────────────
    pr_url = engineer_result.get("pr_url", "https://github.com")
    email_sent_to = os.environ.get("TEST_EMAIL", "test@example.com")
    product_spec = product_result.get("spec", {})
    product_spec["tagline"] = marketing_result.get("copy", {}).get("tagline", "")

    post_final_summary_to_slack(product_spec, pr_url, email_sent_to)

    print("\n[CEO] 🎉 All agents completed. LaunchMind run finished.")
