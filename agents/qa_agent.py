"""
agents/qa_agent.py
------------------
QA / Reviewer Agent
Responsibilities:
  1. Receive Engineer's HTML and Marketing's copy from the message bus
  2. Use LLM to review HTML against product spec
  3. Use LLM to review marketing copy for quality
  4. Post inline review comments on the GitHub PR
  5. Send structured pass/fail report to CEO
"""

import os
import json
import requests as http

import message_bus as bus
from llm_client import call_llm_json


GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo() -> str:
    return f"{os.environ['GITHUB_USERNAME']}/{os.environ['GITHUB_REPO']}"


# ── Post PR review comments ───────────────────────────────────────────────────

def get_pr_number_from_url(pr_url: str) -> int | None:
    """Extract PR number from URL like https://github.com/user/repo/pull/1"""
    try:
        return int(pr_url.rstrip("/").split("/")[-1])
    except Exception:
        return None


def get_pr_commit_sha(pr_number: int) -> str | None:
    repo = _repo()
    r = http.get(f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}", headers=_headers())
    if r.status_code == 200:
        return r.json()["head"]["sha"]
    return None


def post_pr_review(pr_number: int, commit_sha: str, issues: list[str], verdict: str) -> bool:
    """Post a full PR review with inline comments on index.html"""
    repo = _repo()

    # Build review comments (inline on index.html)
    comments = []
    line_positions = [5, 15]  # line numbers to comment on
    for i, issue in enumerate(issues[:2]):  # max 2 inline comments
        comments.append({
            "path": "index.html",
            "position": line_positions[i],
            "body": f"🤖 **QA Agent:** {issue}",
        })

    review_body = (
        f"## QA Agent Review\n\n"
        f"**Verdict:** {'✅ PASS' if verdict == 'pass' else '❌ FAIL'}\n\n"
        f"**Issues found:**\n"
        + "\n".join([f"- {issue}" for issue in issues])
        + "\n\n_Reviewed automatically by QA Agent | LaunchMind MAS_"
    )

    payload = {
        "commit_id": commit_sha,
        "body": review_body,
        "event": "COMMENT",
        "comments": comments,
    }

    r = http.post(
        f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/reviews",
        headers=_headers(),
        json=payload,
    )

    if r.status_code == 200:
        print(f"[QA] ✅ PR review posted with {len(comments)} inline comments.")
        return True
    else:
        print(f"[QA] ❌ PR review failed: {r.status_code} — {r.text[:200]}")
        # Fallback: post a regular PR comment
        fallback = http.post(
            f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments",
            headers=_headers(),
            json={"body": review_body},
        )
        if fallback.status_code == 201:
            print("[QA] ✅ Fallback PR comment posted.")
            return True
        return False


# ── Main runner ───────────────────────────────────────────────────────────────

def run() -> dict:
    print("\n" + "=" * 60)
    print("  QA AGENT STARTING")
    print("=" * 60)

    # ── Receive messages ──────────────────────────────────────────────────────
    messages = bus.receive("qa")

    engineer_msg = next(
        (m for m in messages if m["from_agent"] == "engineer" and "html" in m["payload"]),
        None,
    )
    marketing_msg = next(
        (m for m in messages if m["from_agent"] == "marketing" and "copy" in m["payload"]),
        None,
    )

    if not engineer_msg:
        print("[QA] ❌ No engineer output received.")
        return {"verdict": "fail", "issues": ["No engineer output received."]}

    html = engineer_msg["payload"].get("html", "")
    pr_url = engineer_msg["payload"].get("pr_url", "")
    spec = engineer_msg["payload"].get("spec", {})

    print(f"[QA] 📥 Engineer HTML received ({len(html)} chars).")
    if marketing_msg:
        print(f"[QA] 📥 Marketing copy received.")

    # ── LLM Call 1: Review HTML landing page ──────────────────────────────────
    print("\n[QA] 🧠 Reviewing HTML landing page...")

    features_expected = [f["name"] for f in spec.get("features", [])]
    value_prop = spec.get("value_proposition", "")

    html_review = call_llm_json(
        system_prompt=(
            "You are a QA engineer reviewing an AI-generated HTML landing page. "
            "Check if it matches the product spec. "
            "Return JSON with keys:\n"
            "  html_pass: boolean\n"
            "  html_issues: array of strings (specific problems found, empty if pass)\n"
            "  html_feedback: string (overall assessment)"
        ),
        user_prompt=(
            f"Expected value proposition: {value_prop}\n"
            f"Expected features to mention: {features_expected}\n\n"
            f"HTML to review (first 3000 chars):\n{html[:3000]}\n\n"
            "Does the HTML have: headline, subheadline, features section, CTA button, CSS styling? "
            "Is the content relevant to the product spec?"
        ),
    )
    print(f"[QA] HTML review: {'PASS' if html_review.get('html_pass') else 'FAIL'}")
    if html_review.get("html_issues"):
        for issue in html_review["html_issues"]:
            print(f"  ⚠️  {issue}")

    # ── LLM Call 2: Review marketing copy ────────────────────────────────────
    copy_review = {"copy_pass": True, "copy_issues": [], "copy_feedback": "No copy received."}
    if marketing_msg:
        copy = marketing_msg["payload"].get("copy", {})
        print("\n[QA] 🧠 Reviewing marketing copy...")
        copy_review = call_llm_json(
            system_prompt=(
                "You are a QA reviewer checking marketing copy for a tech product. "
                "Return JSON with keys:\n"
                "  copy_pass: boolean\n"
                "  copy_issues: array of strings (specific problems, empty if pass)\n"
                "  copy_feedback: string"
            ),
            user_prompt=(
                f"Tagline: {copy.get('tagline', '')}\n"
                f"Description: {copy.get('description', '')}\n"
                f"Email subject: {copy.get('email_subject', '')}\n"
                f"Twitter post: {copy.get('twitter', '')}\n\n"
                "Check: Is the tagline under 10 words? Does the email have a clear CTA? "
                "Is the tone appropriate for a tech product? Is everything specific to CourseCompass?"
            ),
        )
        print(f"[QA] Copy review: {'PASS' if copy_review.get('copy_pass') else 'FAIL'}")

    # ── Aggregate verdict ─────────────────────────────────────────────────────
    all_issues = html_review.get("html_issues", []) + copy_review.get("copy_issues", [])
    overall_pass = html_review.get("html_pass", False) and copy_review.get("copy_pass", True)
    verdict = "pass" if overall_pass else "fail"

    print(f"\n[QA] 📋 Overall verdict: {'✅ PASS' if verdict == 'pass' else '❌ FAIL'}")

    # ── Post GitHub PR review ─────────────────────────────────────────────────
    if pr_url:
        pr_number = get_pr_number_from_url(pr_url)
        if pr_number:
            commit_sha = get_pr_commit_sha(pr_number)
            if commit_sha:
                display_issues = all_issues if all_issues else ["Landing page structure looks good.", "Content is relevant to the product spec."]
                post_pr_review(pr_number, commit_sha, display_issues, verdict)
            else:
                print("[QA] ⚠️  Could not get commit SHA for PR review.")
        else:
            print("[QA] ⚠️  Could not parse PR number from URL.")
    else:
        print("[QA] ⚠️  No PR URL — skipping GitHub review.")

    # ── Send report to CEO ────────────────────────────────────────────────────
    report = {
        "verdict": verdict,
        "issues": all_issues,
        "html_feedback": html_review.get("html_feedback", ""),
        "copy_feedback": copy_review.get("copy_feedback", ""),
        "pr_url": pr_url,
    }

    ceo_msg = bus.make_message(
        from_agent="qa",
        to_agent="ceo",
        message_type="result",
        payload=report,
    )
    bus.send(ceo_msg)

    print("\n[QA] ✅ Done. Review report sent to CEO.")
    return report
