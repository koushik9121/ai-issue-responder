import os
import datetime
import logging
import requests
import azure.functions as func
from openai import OpenAI

app = func.FunctionApp()

# Timer trigger: runs every 2 hours
@app.schedule(schedule="0 0 */2 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=True)
def github_issue_triage_timer(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('GitHub Issue Triage Timer trigger function started at %s', utc_timestamp)

    # Load environment variables
    github_pat = os.getenv("GITHUB_PAT")
    github_repo = os.getenv("GITHUB_REPO")  # e.g., "owner/repo"
    openai_key = os.getenv("OPENAI_API_KEY")

    if not github_pat or not github_repo or not openai_key:
        logging.error("Missing required environment variables. GITHUB_PAT, GITHUB_REPO, and OPENAI_API_KEY must be set.")
        return

    # Initialize GitHub session headers
    gh_headers = {
        "Authorization": f"token {github_pat}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Initialize OpenAI Client
    openai_client = OpenAI(api_key=openai_key)

    # 1. Fetch open issues from repository
    issues_url = f"https://api.github.com/repos/{github_repo}/issues"
    params = {"state": "open", "per_page": 50}
    
    try:
        response = requests.get(issues_url, headers=gh_headers, params=params)
        response.raise_for_status()
        issues = response.json()
    except Exception as e:
        logging.error(f"Error fetching issues from GitHub: {e}")
        return

    logging.info(f"Found {len(issues)} open issues/PRs to inspect.")

    for issue in issues:
        # GitHub's issues API returns both issues and pull requests; pull requests have a 'pull_request' key
        if "pull_request" in issue:
            continue

        issue_number = issue.get("number")
        issue_title = issue.get("title")
        issue_body = issue.get("body") or ""
        comments_url = issue.get("comments_url")

        logging.info(f"Checking Issue #{issue_number}: {issue_title}")

        # 2. Check if agent has already commented on this issue
        try:
            comments_resp = requests.get(comments_url, headers=gh_headers)
            comments_resp.raise_for_status()
            comments = comments_resp.json()
        except Exception as e:
            logging.error(f"Error fetching comments for issue #{issue_number}: {e}")
            continue

        already_triaged = False
        for comment in comments:
            # We use a unique HTML comment to mark our bot's responses
            if "<!-- AI-AGENT-BOT -->" in (comment.get("body") or ""):
                already_triaged = True
                break

        if already_triaged:
            logging.info(f"Issue #{issue_number} has already been triaged by the AI agent. Skipping.")
            continue

        logging.info(f"Triaging Issue #{issue_number}...")

        # 3. Use OpenAI to analyze the issue and generate label and reply
        prompt = f"""
You are an AI-powered GitHub repository assistant. Analyze the following issue:
Title: {issue_title}
Body: {issue_body}

Perform two tasks:
1. Classify this issue into one of these labels:
   - "bug" (unexpected behavior, crashes, errors)
   - "enhancement" (new feature request, improvements)
   - "documentation" (docs issues, typos)
   - "question" (general query, support)
2. Generate a polite, professional, and helpful response to the user. Greet them, summarize what the issue seems to be, let them know that the maintainers have been notified, and list any additional diagnostic logs or info that might be helpful for them to provide.

Format your output EXACTLY as follows:
LABEL: [one of the 4 labels above]
---
RESPONSE:
[Your response text here]
"""

        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful GitHub project assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            result = completion.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error calling OpenAI API for issue #{issue_number}: {e}")
            continue

        # Parse OpenAI output
        try:
            parts = result.split("---")
            label_part = parts[0].strip().replace("LABEL:", "").strip().lower()
            response_part = parts[1].strip().replace("RESPONSE:", "").strip()
        except Exception as parse_err:
            logging.error(f"Error parsing OpenAI output for issue #{issue_number}: {parse_err}. Raw output: {result}")
            continue

        # Ensure label matches allowed set
        allowed_labels = ["bug", "enhancement", "documentation", "question"]
        assigned_label = label_part if label_part in allowed_labels else "question"

        # 4. Apply label to the issue
        labels_url = f"https://api.github.com/repos/{github_repo}/issues/{issue_number}/labels"
        try:
            # First ensure the label exists or simply try to add it (GitHub will add it if it exists)
            # Add the triage label plus the specific classification
            add_labels = [assigned_label, "ai-triaged"]
            label_resp = requests.post(labels_url, headers=gh_headers, json={"labels": add_labels})
            label_resp.raise_for_status()
            logging.info(f"Successfully labeled issue #{issue_number} as {add_labels}.")
        except Exception as e:
            logging.error(f"Failed to add labels to issue #{issue_number}: {e}")

        # 5. Post triage response comment
        final_comment = f"{response_part}\n\n---\n*This reply was generated automatically by the Azure AI Issue Responder agent. (Triage schedule: every 2 hours)* <!-- AI-AGENT-BOT -->"
        try:
            comment_resp = requests.post(comments_url, headers=gh_headers, json={"body": final_comment})
            comment_resp.raise_for_status()
            logging.info(f"Successfully posted triage response to issue #{issue_number}.")
        except Exception as e:
            logging.error(f"Failed to post comment to issue #{issue_number}: {e}")

    logging.info('GitHub Issue Triage Timer trigger function finished.')
