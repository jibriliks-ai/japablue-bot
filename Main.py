"""
Japablueprint Bot - RENDER FIXED VERSION
Production-ready: uses 'app' convention, Gunicorn-compatible, robust error handling.
"""
import os
import json
import re
import sys
from datetime import datetime
import xml.etree.ElementTree as ET

import requests
from flask import Flask, request as flask_request

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID      = os.getenv("CHANNEL_ID", "@japablueprint")
CRON_SECRET     = os.getenv("CRON_SECRET", "japablueprint123")
WEBSITE         = "https://japablueprint.com.ng"
POSTED_FILE     = "posted.json"
TELEGRAM_API    = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────
def search_website(query, limit=3):
    """Search japablueprint.com.ng for relevant guides."""
    try:
        search_url = f"{WEBSITE}/?s={requests.utils.quote(query)}"
        r = requests.get(search_url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        pattern = r'<h[23][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, r.text, re.I)[:limit]
        results = []
        for link, title in matches:
            title = title.strip()
            if len(title) > 15 and "japablueprint" in link:
                results.append({"title": title, "link": link})
        return results
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []


def get_all_latest(limit=5):
    """Fetch latest posts from the RSS feed."""
    try:
        r = requests.get(f"{WEBSITE}/feed/", timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        if "<item>" in r.text:
            root = ET.fromstring(r.content)
            posts = []
            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                desc = item.findtext("description", "")[:300]
                desc = re.sub(r'<[^>]+>', '', desc)
                if title and link:
                    posts.append({"title": title, "link": link, "desc": desc})
            return posts
    except Exception as e:
        print(f"RSS error: {e}", file=sys.stderr)
    return []


def get_latest_formatted(limit=3):
    """Format latest posts for Telegram message."""
    posts = get_all_latest(limit)
    if not posts:
        return f"Visit latest guides 👉 {WEBSITE}/blog/"
    msg = "🔥 Latest from Japablueprint.com.ng:\n\n"
    for i, p in enumerate(posts, 1):
        msg += f"{i}. {p['title']}\n{p['link']}\n\n"
    msg += f"📚 More: {WEBSITE}"
    return msg


def send_message(chat_id, text):
    """Send a Telegram message. Returns True on success."""
    if not BOT_TOKEN:
        return False
    try:
        url = f"{TELEGRAM_API}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f"Send failed: {e}", file=sys.stderr)
        return False


def send_to_channel_direct(text):
    """Send a message directly to the configured channel."""
    return send_message(CHANNEL_ID, text)


def auto_post_job():
    """Auto-post the latest unposted article to the channel."""
    posts = get_all_latest(5)
    if not posts:
        return "No posts found"

    posted = []
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE) as f:
                posted = json.load(f)
        except Exception:
            posted = []

    for p in posts:
        if p["link"] not in posted:
            caption = (
                f"🇯🇵 <b>{p['title']}</b>\n\n"
                f"{p['desc'][:250]}...\n\n"
                f"👉 Read full guide: {p['link']}\n\n"
                f"#Japa #Japan #SwedenPOF #CanadaVisa #Japablueprint"
            )
            if send_to_channel_direct(caption):
                posted.append(p["link"])
                with open(POSTED_FILE, "w") as f:
                    json.dump(posted[-100:], f)
                return f"Posted: {p['title']}"
            return f"Failed to post: {p['title']}"

    # If all posts have been posted, repost the latest as trending
    p = posts[0]
    caption = (
        f"🔥 Trending: <b>{p['title']}</b>\n\n"
        f"{p['desc'][:250]}...\n\n👉 {p['link']}"
    )
    send_to_channel_direct(caption)
    return f"Reposted trending: {p['title']}"


def ask_ai_with_website_context(question):
    """Answer a user question using site context + Gemini AI fallback."""
    relevant = search_website(question, limit=3)
    website_context = ""
    links_text = ""

    if relevant:
        website_context = "\nRelevant guides from Japablueprint.com.ng:\n"
        for i, r in enumerate(relevant, 1):
            website_context += f"{i}. {r['title']} - {r['link']}\n"
            links_text += f"\n• {r['title']}\n{r['link']}"

    # Fallback if no Gemini key
    if not GEMINI_API_KEY:
        if relevant:
            return (
                f"Based on Japablueprint.com.ng, here are guides for "
                f"'{question}':{links_text}\n\n"
                f"Visit {WEBSITE} and search '{question}' for full details. 🛫"
            )
        return f"Visit {WEBSITE} and search '{question}' - all guides are there. 🛫"

    try:
        prompt = f"""You are Japablueprint.com.ng Official AI Assistant - friendly, helpful, expert in Japan, Sweden POF 103140 SEK, Canada, UK visas.
PRIORITY:
1. Use relevant guides from japablueprint.com.ng below if they match
2. Add your AI knowledge for 2025 updates
3. Include relevant links at end
4. Sweden POF is 103140 SEK for 2025
5. Keep under 350 words, bullet points
WEBSITE CONTEXT:
{website_context if website_context else "No exact match on site, use AI knowledge but mention website has general guides"}
USER QUESTION: {question}
Answer helpfully and end with links if available:"""

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(url, json=payload, timeout=20)

        if r.status_code == 200:
            data = r.json()
            answer = data["candidates"][0]["content"]["parts"][0]["text"]
            if relevant and relevant[0]["link"] not in answer:
                answer += f"\n\n📚 Related guides from {WEBSITE}:{links_text}"
            elif not relevant:
                answer += f"\n\n📚 Full guides: {WEBSITE} - Search '{question}' there"
            return answer

        # Gemini failed; return website links if available
        if relevant:
            return (
                f"Here are relevant guides from Japablueprint.com.ng for "
                f"'{question}':{links_text}\n\n"
                f"Visit {WEBSITE} for full details. 🛫"
            )
        return f"Visit {WEBSITE} and search '{question}' - all guides are there. 🛫"

    except Exception as e:
        print(f"AI error: {e}", file=sys.stderr)
        if relevant:
            return (
                f"Here are relevant guides from Japablueprint.com.ng for "
                f"'{question}':{links_text}\n\n"
                f"Visit {WEBSITE} for full details. 🛫"
            )
        return (
            f"I'm having small issue. Please visit {WEBSITE} and search "
            f"'{question}' - all guides are there. 🛫"
        )


# ─────────────────────────────────────────────
# FLASK APP  (named `app` for Render/Gunicorn)
# ─────────────────────────────────────────────
app = Flask(__name__)


@app.route("/")
def home():
    return (
        f"Japablueprint Bot Running ✅ Channel={CHANNEL_ID}<br>"
        f"Health: <a href='/health'>/health</a><br>"
        f"BOT_TOKEN set: {bool(BOT_TOKEN)}<br>"
        f"Time: {datetime.now()}"
    )


@app.route("/health")
def health():
    return "OK - Bot Alive - Flask OK", 200


@app.route("/autopost")
def autopost():
    key = flask_request.args.get("key", "")
    if key != CRON_SECRET:
        return "Unauthorized - invalid key", 403
    result = auto_post_job()
    return f"Auto-post: {result} at {datetime.now()}"


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = flask_request.get_json(force=True)
        if not data or "message" not in data:
            return "OK", 200

        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if not text:
            return "OK", 200

        if text.startswith("/start"):
            reply = (
                f"🇯🇵 <b>Japablueprint AI is Online!</b>\n\n"
                f"I'm like Meta AI but trained on "
                f"<b>Japablueprint.com.ng</b>!\n\n"
                f"<b>How I work:</b>\n"
                f"• I search {WEBSITE} FIRST\n"
                f"• Then add AI brain\n"
                f"• Always give links\n\n"
                f"<b>Try:</b>\n"
                f"• Sweden POF 103140 SEK?\n"
                f"• Japan student visa 2025\n\n"
                f"<b>Commands:</b>\n"
                f"/latest\n/search Sweden POF\n\n"
                f"📚 Website: {WEBSITE}"
            )
            send_message(chat_id, reply)

        elif text.startswith("/latest"):
            send_message(chat_id, get_latest_formatted(3))

        elif text.startswith("/search"):
            query = text.replace("/search", "").strip()
            if not query:
                send_message(chat_id, "Use: /search Sweden POF")
            else:
                results = search_website(query, limit=5)
                if not results:
                    send_message(
                        chat_id,
                        f"No results for '{query}' on {WEBSITE}"
                    )
                else:
                    msg = (
                        f"🔍 Search results for '{query}' on "
                        f"Japablueprint.com.ng:\n\n"
                    )
                    for i, r in enumerate(results, 1):
                        msg += f"{i}. {r['title']}\n{r['link']}\n\n"
                    send_message(chat_id, msg)

        else:
            answer = ask_ai_with_website_context(text)
            send_message(chat_id, answer)

    except Exception as e:
        print(f"Webhook error: {e}", file=sys.stderr)

    return "OK", 200


# ─────────────────────────────────────────────
# LOCAL DEV ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Japablueprint bot on port {port}", file=sys.stderr)
    app.run(host="0.0.0.0", port=port)
