# LaunchMind — Multi-Agent System

> **Course:** Agentic AI
> **University:** FAST National University of Computer & Emerging Sciences, Islamabad  
>
> ## Author
> | Member |
> |--------|
> | Danish Karim 

---

## Project Description

LaunchMind is a Multi-Agent System (MAS) that autonomously runs a micro-startup from a single idea all the way to code, marketing, and deployment — without any human doing it manually. The system is powered by a team of 5 collaborating AI agents, each with a specific role, that communicate with each other using structured JSON messages and take real actions on real platforms including GitHub, Slack, and email.

The startup idea chosen for this project is **CourseCompass** — a CLI tool that helps students search, filter, and compare online courses from platforms like Coursera, Udemy, and edX based on price, rating, duration, and skill level. Students waste hours browsing multiple platforms trying to find the right course. CourseCompass solves that by giving them one unified search and comparison experience.

The agents autonomously define the product, build a landing page, push it to GitHub, send marketing emails, post to Slack, and review the output — all without manual intervention. The CEO agent uses LLM reasoning to review each agent's output and trigger feedback loops if the output is not good enough.

---

## Agent Architecture

```
                        ┌─────────────────────────┐
                        │       CEO Agent          │
                        │     (Orchestrator)        │
                        │                           │
                        │  1. Receives startup idea │
                        │  2. Decomposes into tasks │
                        │  3. Reviews all outputs   │
                        │  4. Sends revision reqs   │
                        │  5. Posts final summary   │
                        └────────────┬──────────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               ▼                     ▼                      ▼
   ┌───────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
   │   Product Agent   │  │  Engineer Agent  │  │  Marketing Agent    │
   │                   │  │                  │  │                     │
   │ Generates:        │  │ Generates:       │  │ Generates:          │
   │ • Value prop      │  │ • HTML page      │  │ • Tagline           │
   │ • 3 Personas      │  │ • GitHub Issue   │  │ • Cold email        │
   │ • 5 Features      │  │ • Branch + commit│  │ • Social posts      │
   │ • 3 User stories  │  │ • Pull Request   │  │                     │
   │                   │  │                  │  │ Actions:            │
   │ Sends spec to:    │  │ Sends HTML to QA │  │ • Sends email       │
   │ Engineer +        │  │ Sends PR URL     │  │ • Posts to Slack    │
   │ Marketing         │  │ to CEO           │  │ • Sends copy to QA  │
   └────────┬──────────┘  └────────┬─────────┘  └──────────┬──────────┘
            │                      │                        │
            └──────────────────────┴────────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────────┐
                        │        QA Agent          │
                        │                          │
                        │ Reviews:                 │
                        │ • HTML vs product spec   │
                        │ • Marketing copy quality │
                        │                          │
                        │ Actions:                 │
                        │ • Posts GitHub PR review │
                        │ • Sends pass/fail to CEO │
                        └─────────────────────────┘
```

### Message Flow Between Agents

```
CEO        ──task──────────────►  Product
CEO        ──task──────────────►  Engineer
CEO        ──task──────────────►  Marketing
Product    ──result────────────►  Engineer    (product spec)
Product    ──result────────────►  Marketing   (product spec)
Product    ──confirmation──────►  CEO
Engineer   ──result────────────►  CEO         (PR URL + issue URL)
Engineer   ──result────────────►  QA          (HTML + PR URL)
Marketing  ──result────────────►  CEO         (copy + email + slack status)
Marketing  ──result────────────►  QA          (copy)
QA         ──result────────────►  CEO         (pass/fail verdict)
CEO        ──confirmation──────►  Product     (if accepted)
CEO        ──confirmation──────►  Engineer    (if accepted)
CEO        ──revision_request──►  Engineer    (FEEDBACK LOOP if QA fails)
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/karemdanish/launchmind-wolves.git
cd launchmind-wolves
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash

Open `.env` and fill in all values:

```env
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=...
GITHUB_REPO=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=...
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=your-verified-email@gmail.com
TEST_EMAIL=your-inbox@gmail.com
```

### 4. Run the System

```bash
python main.py
```

---

## Platform Integrations

| Platform | Agent | Action |
|----------|-------|--------|
| **OpenAI GPT-4o-mini** | All agents | LLM reasoning for task decomposition, content generation, and reviews |
| **GitHub** | Engineer, QA | Creates branch, commits `index.html`, opens Pull Request, posts PR review comments |
| **Slack** | Marketing, CEO | Posts launch announcement using Block Kit and final summary to `#launches` |
| **SendGrid** | Marketing | Sends cold outreach email to test inbox |

---

## Repository Structure

```
launchmind-wolves/
├── agents/
│   ├── __init__.py
│   ├── ceo_agent.py          # Orchestrator — task decomposition, reviews, feedback loops
│   ├── product_agent.py      # Product Manager — generates product spec JSON
│   ├── engineer_agent.py     # Builder — HTML generation + GitHub operations
│   ├── marketing_agent.py    # Growth — copy generation + email + Slack
│   └── qa_agent.py           # Reviewer — HTML/copy review + GitHub PR comments
├── main.py                   # Single entry point — runs entire system
├── message_bus.py            # Shared in-memory message bus
├── llm_client.py             # Shared OpenAI wrapper used by all agents
├── requirements.txt          # All dependencies
├── .env.example              # Template — copy to .env and fill in keys
├── .gitignore                # Includes .env
└── README.md
```

---

## Message Schema

Every message between agents follows this exact structure:

```json
{
  "message_id": "uuid-string",
  "from_agent": "ceo",
  "to_agent": "product",
  "message_type": "task | result | revision_request | confirmation",
  "payload": { },
  "timestamp": "2026-04-09T11:49:17.193837+00:00",
  "parent_message_id": "optional-uuid"
}
```

---

## Submission Links

- **GitHub PR:** https://github.com/karemdanish/launchmind-wolves/pull/9
- **Slack Workspace:** https://join.slack.com/t/launchmindglobal/shared_invite/zt-3ulz0yhcn-FvWBORnAKpjV__ea0bbLnQ
- **Demo Video:** https://www.youtube.com/watch?v=dB-_2Vcpnsk

---



---
