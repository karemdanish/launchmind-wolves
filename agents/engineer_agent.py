"""
agents/engineer_agent.py
------------------------
Engineer Agent — Builder
Responsibilities:
  1. Receive product spec from Product agent
  2. Use LLM to generate a complete HTML landing page
  3. Create a GitHub issue
  4. Commit HTML to a new branch on GitHub
  5. Open a Pull Request
  6. Send PR URL and issue URL back to CEO
"""

import os
import base64
import json
import requests as http

import message_bus as bus
from llm_client import call_llm, call_llm_json


GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo() -> str:
    return f"{os.environ['GITHUB_USERNAME']}/{os.environ['GITHUB_REPO']}"


# ── GitHub helpers ────────────────────────────────────────────────────────────

def get_default_branch_sha() -> str:
    """Get the SHA of the latest commit on the default branch (main or master)."""
    repo = _repo()
    # Try main first
    for branch in ["main", "master"]:
        r = http.get(f"{GITHUB_API}/repos/{repo}/git/ref/heads/{branch}", headers=_headers())
        if r.status_code == 200:
            sha = r.json()["object"]["sha"]
            print(f"[Engineer] Default branch '{branch}' SHA: {sha[:8]}...")
            return sha
    raise RuntimeError("Could not find main or master branch in GitHub repo.")


def create_branch(branch_name: str, base_sha: str) -> bool:
    repo = _repo()
    r = http.post(
        f"{GITHUB_API}/repos/{repo}/git/refs",
        headers=_headers(),
        json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
    )
    if r.status_code in (201, 422):  # 422 = branch already exists
        print(f"[Engineer] ✅ Branch '{branch_name}' ready.")
        return True
    print(f"[Engineer] ❌ Branch creation failed: {r.status_code} {r.text}")
    return False


def commit_file(branch_name: str, filename: str, content: str, commit_message: str) -> bool:
    repo = _repo()
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    # Check if file already exists (need its SHA to update)
    existing_sha = None
    check = http.get(
        f"{GITHUB_API}/repos/{repo}/contents/{filename}",
        headers=_headers(),
        params={"ref": branch_name},
    )
    if check.status_code == 200:
        existing_sha = check.json().get("sha")

    payload = {
        "message": commit_message,
        "content": encoded,
        "branch": branch_name,
        "author": {
            "name": "EngineerAgent",
            "email": "agent@launchmind.ai",
        },
    }
    if existing_sha:
        payload["sha"] = existing_sha

    r = http.put(
        f"{GITHUB_API}/repos/{repo}/contents/{filename}",
        headers=_headers(),
        json=payload,
    )
    if r.status_code in (200, 201):
        print(f"[Engineer] ✅ File '{filename}' committed to branch '{branch_name}'.")
        return True
    print(f"[Engineer] ❌ Commit failed: {r.status_code} {r.text}")
    return False


def create_issue(title: str, body: str) -> str:
    repo = _repo()
    r = http.post(
        f"{GITHUB_API}/repos/{repo}/issues",
        headers=_headers(),
        json={"title": title, "body": body},
    )
    if r.status_code == 201:
        url = r.json()["html_url"]
        print(f"[Engineer] ✅ GitHub issue created: {url}")
        return url
    print(f"[Engineer] ❌ Issue creation failed: {r.status_code} {r.text}")
    return ""


def open_pull_request(branch_name: str, title: str, body: str) -> str:
    repo = _repo()
    # Try main, then master as base
    for base in ["main", "master"]:
        r = http.post(
            f"{GITHUB_API}/repos/{repo}/pulls",
            headers=_headers(),
            json={
                "title": title,
                "body": body,
                "head": branch_name,
                "base": base,
            },
        )
        if r.status_code == 201:
            url = r.json()["html_url"]
            print(f"[Engineer] ✅ Pull Request opened: {url}")
            return url
        if r.status_code == 422:
            errors = r.json().get("errors", [])
            # If PR already exists, return the existing one
            for e in errors:
                if "pull request already exists" in str(e.get("message", "")):
                    print("[Engineer] PR already exists, fetching URL...")
                    prs = http.get(
                        f"{GITHUB_API}/repos/{repo}/pulls",
                        headers=_headers(),
                        params={"head": f"{os.environ['GITHUB_USERNAME']}:{branch_name}", "state": "open"},
                    )
                    if prs.status_code == 200 and prs.json():
                        return prs.json()[0]["html_url"]
    print(f"[Engineer] ❌ PR creation failed.")
    return ""


# ── Main runner ───────────────────────────────────────────────────────────────

def run() -> dict:
    print("\n" + "=" * 60)
    print("  ENGINEER AGENT STARTING")
    print("=" * 60)

    # ── Receive product spec ──────────────────────────────────────────────────
    messages = bus.receive("engineer")
    # Accept spec from product agent or task from CEO
    spec_msg = next(
        (m for m in messages if m["message_type"] in ("result", "task") and "spec" in m["payload"]),
        None,
    )

    if not spec_msg:
        print("[Engineer] ❌ No product spec received.")
        return {}

    spec = spec_msg["payload"]["spec"]
    print(f"[Engineer] 📥 Product spec received from {spec_msg['from_agent'].upper()}.")

    # ── LLM Call 1: Generate HTML landing page ────────────────────────────────
    print("\n[Engineer] 🧠 Generating HTML landing page...")

    features_text = "\n".join(
        [f"- {f['name']}: {f['description']}" for f in spec.get("features", [])]
    )
    personas_text = "\n".join(
        [f"- {p['name']} ({p['role']}): {p['pain_point']}" for p in spec.get("personas", [])]
    )

    html_content = call_llm(
        system_prompt=(
            "You are a front-end developer. Generate a complete, beautiful, single-file HTML landing page. "
            "Include: DOCTYPE, head with meta tags, embedded CSS (modern, clean design with a blue/white color scheme), "
            "a navbar with the product name, a hero section with headline and subheadline, "
            "a features section (cards), a target users section, and a call-to-action button. "
            "Make it professional. Output ONLY the raw HTML — no explanation, no markdown."
        ),
        user_prompt=(
            f"Product: CourseCompass\n"
            f"Value proposition: {spec.get('value_proposition', '')}\n"
            f"Features:\n{features_text}\n"
            f"Target users:\n{personas_text}\n\n"
            "Generate the complete HTML landing page now."
        ),
    )

    print(f"[Engineer] ✅ HTML generated ({len(html_content)} chars).")

    # ── LLM Call 2: Generate issue description and PR body ────────────────────
    print("\n[Engineer] 🧠 Generating GitHub issue and PR descriptions...")
    github_texts = call_llm_json(
        system_prompt=(
            "You are a software engineer writing GitHub issue and PR descriptions. "
            "Return JSON with keys: issue_title, issue_body, pr_title, pr_body."
        ),
        user_prompt=(
            f"Product: CourseCompass — {spec.get('value_proposition', '')}\n"
            "Write a GitHub issue titled 'Initial landing page' and a PR to merge it. "
            "Be professional and specific about what the landing page contains."
        ),
    )

    # ── GitHub Operations ─────────────────────────────────────────────────────
    branch_name = "agent-landing-page"

    print("\n[Engineer] 🐙 Starting GitHub operations...")
    base_sha = get_default_branch_sha()
    create_branch(branch_name, base_sha)
    commit_file(
        branch_name=branch_name,
        filename="index.html",
        content=html_content,
        commit_message="feat: Add AI-generated landing page for CourseCompass\n\nGenerated by EngineerAgent <agent@launchmind.ai>",
    )

    issue_url = create_issue(
        title=github_texts.get("issue_title", "Initial landing page"),
        body=github_texts.get("issue_body", "Add initial landing page for CourseCompass."),
    )

    pr_url = open_pull_request(
        branch_name=branch_name,
        title=github_texts.get("pr_title", "Initial landing page"),
        body=github_texts.get("pr_body", "This PR adds the initial landing page."),
    )

    # ── Send result to CEO ────────────────────────────────────────────────────
    result_msg = bus.make_message(
        from_agent="engineer",
        to_agent="ceo",
        message_type="result",
        payload={
            "pr_url": pr_url,
            "issue_url": issue_url,
            "branch": branch_name,
            "html_length": len(html_content),
            "status": "done",
        },
        parent_message_id=spec_msg["message_id"],
    )
    bus.send(result_msg)

    # Also forward HTML to QA
    qa_msg = bus.make_message(
        from_agent="engineer",
        to_agent="qa",
        message_type="result",
        payload={
            "html": html_content,
            "pr_url": pr_url,
            "spec": spec,
        },
    )
    bus.send(qa_msg)

    print("\n[Engineer] ✅ Done. PR and Issue created on GitHub.")
    return {
        "pr_url": pr_url,
        "issue_url": issue_url,
        "html": html_content,
        "spec": spec,
    }
