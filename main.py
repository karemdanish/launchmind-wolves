"""
main.py
-------
LaunchMind — Multi-Agent System Entry Point

Startup idea: CourseCompass
  A CLI tool that helps students search, filter, and compare online courses
  from platforms like Coursera, Udemy, and edX based on price, rating,
  duration, and skill level.

Run:
    python main.py

Make sure your .env file is configured before running.
"""

import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Validate required environment variables before starting
REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "GITHUB_USERNAME",
    "GITHUB_REPO",
    "SLACK_BOT_TOKEN",
    "SENDGRID_API_KEY",
    "SENDGRID_FROM_EMAIL",
    "TEST_EMAIL",
]

def validate_env():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        print("❌ Missing required environment variables:")
        for v in missing:
            print(f"   - {v}")
        print("\nPlease copy .env.example to .env and fill in all values.")
        sys.exit(1)
    print("✅ All environment variables loaded.")

# Add project root to path so agents can import message_bus and llm_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import message_bus as bus
from llm_client import call_llm_json

# Import agents
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
import ceo_agent
import product_agent
import engineer_agent
import marketing_agent
import qa_agent


STARTUP_IDEA = (
    "CourseCompass — a CLI tool that helps students search, filter, "
    "and compare online courses from platforms like Coursera, Udemy, "
    "and edX based on price, rating, duration, and skill level."
)


def main():
    print("\n" + "=" * 60)
    print("  🚀 LAUNCHMIND MULTI-AGENT SYSTEM")
    print("  Startup: CourseCompass")
    print("=" * 60)

    validate_env()

    print(f"\n📋 Startup Idea:\n   {STARTUP_IDEA}\n")

    # ── Phase 1: CEO decomposes idea and sends tasks ──────────────────────────
    print("\n" + "─" * 60)
    print("  PHASE 1: CEO — Task Decomposition")
    print("─" * 60)

    tasks = ceo_agent.decompose_idea(STARTUP_IDEA)
    ceo_agent.send_tasks(tasks, STARTUP_IDEA)

    # ── Phase 2: Product Agent runs ───────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  PHASE 2: Product Agent")
    print("─" * 60)

    product_result = product_agent.run()

    # ── Phase 3: Engineer Agent runs ──────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  PHASE 3: Engineer Agent")
    print("─" * 60)

    engineer_result = engineer_agent.run()
    pr_url = engineer_result.get("pr_url", "")

    # ── Phase 4: Marketing Agent runs ─────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  PHASE 4: Marketing Agent")
    print("─" * 60)

    marketing_result = marketing_agent.run(pr_url=pr_url)

    # ── Phase 5: QA Agent runs ────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  PHASE 5: QA Agent")
    print("─" * 60)

    qa_result = qa_agent.run()

    # ── Phase 6: CEO reviews all outputs and posts final summary ──────────────
    print("\n" + "─" * 60)
    print("  PHASE 6: CEO — Review, Feedback Loop & Final Summary")
    print("─" * 60)

    ceo_agent.run(
        product_result=product_result,
        engineer_result=engineer_result,
        marketing_result=marketing_result,
        qa_result=qa_result,
    )

    # ── Print full message history ────────────────────────────────────────────
    bus.print_full_history()

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ LAUNCHMIND RUN COMPLETE")
    print("=" * 60)
    print(f"\n  GitHub PR  : {engineer_result.get('pr_url', 'N/A')}")
    print(f"  Issue URL  : {engineer_result.get('issue_url', 'N/A')}")
    print(f"  Email sent : {os.environ.get('TEST_EMAIL', 'N/A')}")
    print(f"  Slack      : {os.environ.get('SLACK_CHANNEL', '#launches')}")
    print(f"  QA Verdict : {qa_result.get('verdict', 'N/A').upper()}")
    print(f"\n  Total messages sent: {len(bus.get_history())}")
    print("\n  🎉 All agents completed successfully!\n")


if __name__ == "__main__":
    main()
