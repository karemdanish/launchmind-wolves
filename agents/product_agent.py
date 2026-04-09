"""
agents/product_agent.py
-----------------------
Product Agent — Product Manager
Responsibilities:
  1. Receive task from CEO agent
  2. Use LLM to generate full product specification
  3. Send spec to Engineer and Marketing agents
  4. Send confirmation back to CEO
"""

import json
import message_bus as bus
from llm_client import call_llm_json


def run() -> dict:
    print("\n" + "=" * 60)
    print("  PRODUCT AGENT STARTING")
    print("=" * 60)

    # ── Receive task from CEO ─────────────────────────────────────────────────
    messages = bus.receive("product")
    task_msg = next((m for m in messages if m["message_type"] == "task"), None)

    if not task_msg:
        print("[Product] ❌ No task message received from CEO.")
        return {}

    idea = task_msg["payload"]["idea"]
    focus = task_msg["payload"]["focus"]
    print(f"[Product] 📥 Task received from CEO.")
    print(f"[Product] Idea: {idea}")
    print(f"[Product] Focus: {focus}")

    # ── LLM Call 1: Generate product specification ────────────────────────────
    print("\n[Product] 🧠 Generating product specification...")
    spec = call_llm_json(
        system_prompt=(
            "You are a senior product manager at a startup. "
            "Generate a complete product specification for the given startup idea. "
            "Return a JSON object with exactly these keys:\n"
            "  value_proposition: string (one sentence)\n"
            "  personas: array of objects, each with: name, role, pain_point\n"
            "  features: array of objects, each with: name, description, priority (1=highest)\n"
            "  user_stories: array of 3 strings in format 'As a [user], I want to [action] so that [benefit]'\n"
            "Make everything specific to the startup idea — no generic placeholder text."
        ),
        user_prompt=(
            f"Startup idea: {idea}\n"
            f"Additional focus: {focus}\n\n"
            "Generate a product spec with exactly: "
            "1 value proposition, 3 personas, 5 features (priority 1-5), 3 user stories."
        ),
    )

    print(f"\n[Product] ✅ Product spec generated:")
    print(json.dumps(spec, indent=2))

    # ── Send spec to Engineer agent ───────────────────────────────────────────
    msg_to_engineer = bus.make_message(
        from_agent="product",
        to_agent="engineer",
        message_type="result",
        payload={"spec": spec},
        parent_message_id=task_msg["message_id"],
    )
    bus.send(msg_to_engineer)

    # ── Send spec to Marketing agent ──────────────────────────────────────────
    msg_to_marketing = bus.make_message(
        from_agent="product",
        to_agent="marketing",
        message_type="result",
        payload={"spec": spec},
        parent_message_id=task_msg["message_id"],
    )
    bus.send(msg_to_marketing)

    # ── Send confirmation back to CEO ─────────────────────────────────────────
    confirm = bus.make_message(
        from_agent="product",
        to_agent="ceo",
        message_type="confirmation",
        payload={
            "status": "done",
            "message": "Product specification is ready and sent to Engineer and Marketing.",
        },
        parent_message_id=task_msg["message_id"],
    )
    bus.send(confirm)

    print("\n[Product] ✅ Done. Spec sent to Engineer, Marketing, and CEO.")
    return {"spec": spec}
