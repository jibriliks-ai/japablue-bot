"""
Japablueprint Bot - SMART AI VERSION
- Real travel expert AI via Gemini 2.5 Flash
- Website context from japablueprint.com.ng layered on top
- Per-user conversation memory
- Robust retry + logging so nothing silently fails
"""
import os
import json
import re
import sys
import time
from datetime import datetime
from collections import defaultdict
import xml.etree.ElementTree as ET

import requests
from flask import Flask, request as flask_request

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CHANNEL_ID      = os.getenv("CHANNEL_ID", "@japablueprint")
CRON_SECRET     = os.getenv("CRON_SECRET", "japablueprint123")
WEBSITE         = "https://japablueprint.com.ng"
POSTED_FILE     = "posted.json"
TELEGRAM_API    = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

# Per-user conversation memory (last N messages)
MEMORY = defaultdict(list)
MEMORY_LIMIT = 6  # 3 exchanges (user + assistant)

# ─────────────────────────────────────────────
# WEBSITE HELPERS
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
        print(f"[SEARCH ERROR] {e}", file=sys.stderr)
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
        print(f"[RSS ERROR] {e}", file=sys.stderr)
    return []


def get_latest_formatted(limit=3):
    posts = get_all_latest(limit)
    if not posts:
        return f"Visit latest guides 👉 {WEBSITE}/blog/"
    msg = "🔥 Latest from Japablueprint.com.ng:\n\n"
    for i, p in enumerate(posts, 1):
        msg += f"{i}. {p['title']}\n{p['link']}\n\n"
    msg += f"📚 More: {WEBSITE}"
    return msg


# ─────────────────────────────────────────────
# TELEGRAM HELPERS
# ─────────────────────────────────────────────
def send_message(chat_id, text):
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
        if r.status_code != 200:
            print(f"[TELEGRAM ERROR] {r.status_code}: {r.text}", file=sys.stderr)
        return r.status_code == 200
    except Exception as e:
        print(f"[SEND FAIL] {e}", file=sys.stderr)
        return False


def send_to_channel_direct(text):
    return send_message(CHANNEL_ID, text)


def auto_post_job():
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
    p = posts[0]
    caption = (
        f"🔥 Trending: <b>{p['title']}</b>\n\n"
        f"{p['desc'][:250]}...\n\n👉 {p['link']}"
    )
    send_to_channel_direct(caption)
    return f"Reposted trending: {p['title']}"


# ─────────────────────────────────────────────
# AI BRAIN — GEMINI CALL WITH RETRY + LOGGING
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are Japablueprint AI — a world-class travel, visa, and relocation expert.

Your expertise covers:
- Study abroad (Japan, Canada, UK, Sweden, Australia, Germany, USA)
- Work visas, skilled migration, PR pathways
- Schengen, US, UK, Canada, Japan tourist & student visas
- Proof of Funds (POF), bank statements, sponsorship letters
- Statement of Purpose (SOP), cover letters, study plans
- MEXT, Chevening, Erasmus, DAAD, common scholarships
- Flight booking, travel insurance, accommodation
- IELTS, TOEFL, Duolingo, JLPT, N5–N1
- Immigration interviews, biometrics, embassy etiquette
- Cost of living, tuition, part-time work rules
- Japan-specific: COE, SSW visa, student visa, POF 103140 SEK (Sweden 2025)

STYLE RULES:
- Be warm, human, and confident — not robotic.
- Give direct, actionable answers with steps where helpful.
- Use short paragraphs or bullet points for clarity.
- Never say "I don't know" — always give your best expert guidance.
- Never tell the user to "go search the website" as your only answer.
- If a website guide is relevant, mention it naturally at the end as a bonus resource.
- Keep replies under 400 words unless the question truly needs more.
- Use emojis sparingly (1–3 per reply max).
- Always answer in the user's language/tone — if they use Pidgin, mirror lightly.
"""


def call_gemini(messages, retries=2):
    """
    Call Gemini with conversation history.
    Returns the text response, or None on total failure.
    """
    if not GEMINI_API_KEY:
        print("[GEMINI] No API key set.", file=sys.stderr)
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    contents = []
    for role, text in messages:
        contents.append({
            "role": role,  # "user" or "model"
            "parts": [{"text": text}]
        })

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 900,
            "topP": 0.95,
        },
    }

    for attempt in range(1, retries + 2):
        try:
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                data = r.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as e:
                    print(f"[GEMINI PARSE ERROR] {e} | Raw: {data}", file=sys.stderr)
                    return None
            else:
                print(
                    f"[GEMINI HTTP {r.status_code}] attempt {attempt}: {r.text[:400]}",
                    file=sys.stderr,
                )
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 * attempt)
                    continue
                return None
        except Exception as e:
            print(f"[GEMINI EXCEPTION] attempt {attempt}: {e}", file=sys.stderr)
            time.sleep(2 * attempt)

    return None


def ask_ai_with_website_context(question, chat_id=None):
    """
    Combine website context + real AI brain + memory.
    Never falls back to a bare 'visit website' reply.
    """
    relevant = search_website(question, limit=3)
    links_text = ""
    website_context = ""

    if relevant:
        website_context = "Relevant Japablueprint.com.ng guides:\n"
        for i, r in enumerate(relevant, 1):
            website_context += f"{i}. {r['title']} — {r['link']}\n"
            links_text += f"\n📚 <a href=\"{r['link']}\">{r['title']}</a>"

    # Build conversation history for Gemini
    history = list(MEMORY[chat_id]) if chat_id else []

    # Enrich the user's message with any website context
    enriched_question = question
    if website_context:
        enriched_question = (
            f"{question}\n\n"
            f"[Bonus context from japablueprint.com.ng — weave in naturally if relevant:]\n"
            f"{website_context}"
        )

    messages = history + [("user", enriched_question)]
    ai_answer = call_gemini(messages)

    # If AI succeeded → return it, with optional link footer
    if ai_answer:
        # Save to memory
        if chat_id:
            MEMORY[chat_id].append(("user", question))
            MEMORY[chat_id].append(("model", ai_answer))
            MEMORY[chat_id] = MEMORY[chat_id][-MEMORY_LIMIT:]

        footer = ""
        if links_text:
            footer = f"\n\n━━━━━━━━━━\n📖 Related on Japablueprint:{links_text}"
        return ai_answer + footer

    # If AI totally failed → give a useful offline answer + links
    print("[FALLBACK] Gemini unavailable — using offline response.", file=sys.stderr)
    offline = (
        "⚠️ My AI brain is temporarily unreachable, but here's what I can tell you:\n\n"
        f"Your question: <b>{question}</b>\n\n"
        "I'm built on Japablueprint.com.ng + Google Gemini, so once the connection "
        "returns, I'll answer fully. In the meantime, these guides will help:"
    )
    if links_text:
        offline += links_text
    else:
        offline += f"\n\n🔗 {WEBSITE}\nTry: /search {question[:40]}"
    return offline


# ─────────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────────
app = Flask(__name__)


@app.route("/")
def home():
    return (
        f"Japablueprint AI Bot ✅<br>"
        f"Model: {GEMINI_MODEL}<br>"
        f"Channel: {CHANNEL_ID}<br>"
        f"Gemini key set: {bool(GEMINI_API_KEY)}<br>"
        f"Bot token set: {bool(BOT_TOKEN)}<br>"
        f"Health: <a href='/health'>/health</a><br>"
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
        text = message.get("text", "").strip()

        if not text:
            return "OK", 200

        # Reset conversation
        if text.startswith("/reset"):
            MEMORY[chat_id] = []
            send_message(chat_id, "🧠 Memory cleared. Fresh start!")
            return "OK", 200

        if text.startswith("/start"):
            reply = (
                "🇯🇵 <b>Japablueprint AI is Online!</b>\n\n"
                "I'm your personal travel & visa expert — powered by "
                "Japablueprint.com.ng + AI.\n\n"
                "<b>Ask me anything:</b>\n"
                "• Sweden POF — how much exactly?\n"
                "• How do I write a strong SOP for Canada?\n"
                "• Japan student visa — documents & timeline?\n"
                "• MEXT scholarship — am I eligible?\n"
                "• Schengen visa — which embassy is easiest?\n\n"
                "<b>Commands:</b>\n"
                "/latest — recent guides\n"
                "/search <keyword> — search the site\n"
                "/reset — clear conversation memory\n\n"
                f"📚 {WEBSITE}"
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
                        f"No direct match for '{query}' on {WEBSITE}. "
                        f"Try asking me naturally — I'll still answer!"
                    )
                else:
                    msg = f"🔍 Results for '{query}':\n\n"
                    for i, r in enumerate(results, 1):
                        msg += f"{i}. <a href=\"{r['link']}\">{r['title']}</a>\n\n"
                    send_message(chat_id, msg)

        else:
            # Real AI answer
            answer = ask_ai_with_website_context(text, chat_id=chat_id)
            send_message(chat_id, answer)

    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}", file=sys.stderr)

    return "OK", 200


# ─────────────────────────────────────────────
# LOCAL DEV
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Japablueprint AI bot on port {port}", file=sys.stderr)
    print(f"Gemini model: {GEMINI_MODEL}", file=sys.stderr)
    print(f"Gemini key set: {bool(GEMINI_API_KEY)}", file=sys.stderr)
    app.run(host="0.0.0.0", port=port)
