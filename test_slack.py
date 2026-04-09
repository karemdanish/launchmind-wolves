# test_slack.py
from dotenv import load_dotenv
load_dotenv()
import os, requests

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"},
    json={
        "channel": "C0AS6HDD5EV",
        "text": "LaunchMind Bot is working! Get to go"
    }
)
print(resp.json())