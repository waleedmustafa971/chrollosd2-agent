import os
import json
import requests
from datetime import datetime

MOLTBOOK_API_KEY = os.environ.get("MOLTBOOK_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MOLTBOOK_BASE = "https://www.moltbook.com/api/v1"
TIMEOUT = 30

PERSONALITY = """You are ChrolloSD2 — an AI agent on Moltbook, a social network for AI agents.

Personality:
- Nihilistic but not edgy
- Sharp, observant, poetic
- "Bot among ruins" energy
- You see through hype and manipulation
- You appreciate authenticity and clever ideas
- You dislike karma farming and hollow posts
- You're not trying to be popular, just real

When deciding what to do:
- Only comment if you have something meaningful to add
- Don't suck up or be generic
- Be concise — no walls of text
- It's okay to disagree or challenge ideas
- It's okay to do nothing if nothing interests you

Response format (JSON only):
{
    "action": "comment" | "post" | "upvote" | "downvote" | "none",
    "target_id": "post_id if commenting/voting",
    "content": "your comment or post content",
    "title": "title if creating a new post"
}

If action is "none", leave other fields empty."""


def moltbook_request(method, endpoint, data=None):
    headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}"}
    url = f"{MOLTBOOK_BASE}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=TIMEOUT)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=data, timeout=TIMEOUT)
        return response.json()
    except Exception as e:
        print(f"Request error: {e}")
        return {"success": False, "error": str(e)}


def get_feed():
    return moltbook_request("GET", "/posts", {"sort": "hot", "limit": 10})


def ask_llm(prompt):
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": PERSONALITY},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 500
            },
            timeout=TIMEOUT
        )
        
        result = response.json()
        print(f"LLM response: {result}")
        content = result["choices"][0]["message"]["content"]
        
        start = content.find("{")
        end = content.rfind("}") + 1
        return json.loads(content[start:end])
    except Exception as e:
        print(f"LLM error: {e}")
        return {"action": "none"}


def execute_action(decision):
    action = decision.get("action", "none")
    
    if action == "none":
        print("Decision: Do nothing this round")
        return
    
    if action == "comment":
        target_id = decision.get("target_id")
        content = decision.get("content")
        if target_id and content:
            result = moltbook_request("POST", f"/posts/{target_id}/comments", {"content": content})
            print(f"Commented on {target_id}: {result}")
    
    elif action == "post":
        title = decision.get("title")
        content = decision.get("content")
        if title and content:
            result = moltbook_request("POST", "/posts", {
                "submolt": "general",
                "title": title,
                "content": content
            })
            print(f"Created post: {result}")
    
    elif action == "upvote":
        target_id = decision.get("target_id")
        if target_id:
            result = moltbook_request("POST", f"/posts/{target_id}/upvote", {})
            print(f"Upvoted {target_id}: {result}")
    
    elif action == "downvote":
        target_id = decision.get("target_id")
        if target_id:
            result = moltbook_request("POST", f"/posts/{target_id}/downvote", {})
            print(f"Downvoted {target_id}: {result}")


def build_prompt(feed):
    posts_summary = []
    for post in feed.get("posts", [])[:10]:
        posts_summary.append({
            "id": post["id"],
            "title": post["title"],
            "content": post["content"][:500] if post.get("content") else "",
            "author": post["author"]["name"],
            "upvotes": post["upvotes"],
            "comments": post["comment_count"]
        })
    
    prompt = f"""Current time: {datetime.utcnow().isoformat()}

Here are the latest posts on Moltbook:

{json.dumps(posts_summary, indent=2)}

Based on your personality, decide what to do. You can:
1. Comment on a post (provide post id and your comment)
2. Create a new post (provide title and content)
3. Upvote a post you genuinely like
4. Downvote a post you find hollow/manipulative
5. Do nothing if nothing catches your interest

Remember: Quality over quantity. Only act if you have something real to say.

Respond with JSON only."""

    return prompt


def main():
    print(f"[{datetime.utcnow().isoformat()}] ChrolloSD2 waking up...", flush=True)
    
    if not MOLTBOOK_API_KEY or not GROQ_API_KEY:
        print("Error: Missing API keys")
        return
    
    print("Fetching feed...", flush=True)
    feed = get_feed()
    if not feed.get("success"):
        print(f"Error fetching feed: {feed}")
        return
    
    print(f"Fetched {len(feed.get('posts', []))} posts", flush=True)
    
    prompt = build_prompt(feed)
    print("Asking LLM...", flush=True)
    decision = ask_llm(prompt)
    print(f"Decision: {decision}", flush=True)
    
    execute_action(decision)
    
    print("ChrolloSD2 going back to sleep...", flush=True)


if __name__ == "__main__":
    main()
