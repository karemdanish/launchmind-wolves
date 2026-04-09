"""
message_bus.py
--------------
Shared in-memory message bus for all agents.
Every message must follow the standard schema defined below.
"""

import uuid
from datetime import datetime, timezone


# ── Global message store ──────────────────────────────────────────────────────
# Structure: { "agent_name": [ message, message, ... ] }
_bus: dict[str, list] = {
    "ceo":       [],
    "product":   [],
    "engineer":  [],
    "marketing": [],
    "qa":        [],
}

# Full history of every message ever sent (for demo / evaluator)
_history: list[dict] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_message(
    from_agent: str,
    to_agent: str,
    message_type: str,          # task | result | revision_request | confirmation
    payload: dict,
    parent_message_id: str = None,
) -> dict:
    """Build a correctly-structured agent message."""
    return {
        "message_id":        str(uuid.uuid4()),
        "from_agent":        from_agent,
        "to_agent":          to_agent,
        "message_type":      message_type,
        "payload":           payload,
        "timestamp":         _now(),
        "parent_message_id": parent_message_id,
    }


def send(message: dict) -> None:
    """Put a message into the recipient's inbox and log it."""
    recipient = message["to_agent"]
    if recipient not in _bus:
        raise ValueError(f"Unknown agent: {recipient}")
    _bus[recipient].append(message)
    _history.append(message)
    print(
        f"\n  📨  [{message['from_agent'].upper()} → {recipient.upper()}]"
        f"  type={message['message_type']}"
        f"  id={message['message_id'][:8]}..."
    )


def receive(agent_name: str) -> list[dict]:
    """Return and clear all pending messages for an agent."""
    msgs = _bus.get(agent_name, [])
    _bus[agent_name] = []
    return msgs


def get_history() -> list[dict]:
    """Return complete message history (for logging/demo)."""
    return _history


def print_full_history() -> None:
    """Pretty-print every message ever sent — for the demo video."""
    print("\n" + "=" * 60)
    print("  FULL MESSAGE BUS HISTORY")
    print("=" * 60)
    for m in _history:
        print(
            f"\n  [{m['timestamp']}]"
            f"  {m['from_agent'].upper()} → {m['to_agent'].upper()}"
            f"  ({m['message_type']})"
            f"  id={m['message_id'][:8]}"
        )
        if m.get("parent_message_id"):
            print(f"    re: {m['parent_message_id'][:8]}")
        # Print payload keys only (values can be long)
        print(f"    payload keys: {list(m['payload'].keys())}")
    print("\n" + "=" * 60)
