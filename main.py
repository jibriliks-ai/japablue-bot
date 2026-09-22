"""
Japablueprint Bot - SMART PROFESSIONAL VERSION
- Answers ANY travel question from AI brain + Japablueprint.com.ng
- Professional, detailed, friendly
- Works on Render
"""
import os, json, re, sys
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
from flask import Flask, request as flask_request

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@japablueprint")
CRON_SECRET = os.getenv("CRON_SECRET", "japablueprint123")
WEBSITE = "https://japablueprint.com.ng"
POSTED_FILE = "posted.json"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

# Smart fallback knowledge
SMART_FALLBACK = {
    "sweden pof": "🇸🇪 <b>Sweden Proof of Funds (POF) 2025: 103,140 SEK</b>\n\n<b>Requirements:</b>\n• 103,140 SEK for main applicant (2025 update)\n• Must be in your account for 2-3 months\n• Bank statement not older than 1 month\n• Covers 10 months\n• Spouse: +51,570 SEK, Child: +25,785 SEK\n\n<b>How to show:</b> Personal savings, Fixed deposit\n",
    "japan student": "🇯🇵 <b>Japan Student Visa 2025</b>\n\n<b>Requirements:</b>\n• COE from Japanese school\n• Admission letter\n• Academic certs\n• POF: ~2M JPY (~$13k)\n• Sponsor letter\n\n<b>Steps:</b> 1. Apply to school (6 months before) 2. School gets COE (2-3 months) 3. Apply at Embassy with COE 4. Visa in 5-7 days\n<b>Work:</b> 28 hrs/week\n",
    "canada": "🇨🇦 <b>Canada Visa 2025</b>\n• Study: CAD 20,635 + tuition\n• Express Entry: CRS ~490+\n• Visitor: POF + ties to home\n• Work: Need LMIA\nKey: Strong SOP, 4-6 months POF history\n",
    "uk visa": "🇬🇧 <b>UK Student Visa 2025</b>\n• CAS from uni\n• POF: Tuition + £1,334/mo x9 London\n• 28 days old statement\n• TB test + IELTS\n• Work 20hrs/week\n• Graduate Route 2 years\n"
}

def get_smart_fallback(question):
    q = question.lower()
    for key, answer in SMART_FALLBACK.items():
        if key in q:
            return answer
    return f"""🌍 <b>Travel Guidance for: {question}</b>

<b>Key Requirements for ANY visa:</b>
• Passport 6+ months valid
• Bank statements 3-6 months, no lump sum, gradual buildup
• Academic/work docs, SOP
• Ties to home: family, job, property
• Travel history helps

<b>Tips:</b>
• Apply 3 months before travel
• Sponsor must show income source
• Be honest, no fake docs
• Explain study gaps

Ask specific: Sweden POF, Japan student, Canada, UK, Schengen etc for detailed answer!
"""

def search_website(query, limit=3):
    try:
        search_url = f"{WEBSITE}/?s={requests.utils.quote(query)}"
        r = requests.get(search_url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        text = r.text
        patterns = [r'<h[23][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>']
        results=[]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.I)
            for link, title in matches[:limit*2]:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if len(title)>15 and "japablueprint.com.ng" in link and link not in [x['link'] for x in results]:
                    results.append({"title": title, "link": link})
            if len(results) >= limit:
                break
        return results[:limit]
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

def get_all_latest(limit=5):
    try:
        r = requests.get(f"{WEBSITE}/feed/", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        content = r.content
        text = r.text
        if "<item>" in text:
            root = ET.fromstring(content)
            posts=[]
            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title","").strip()
                link = item.findtext("link","").strip()
                desc = item.findtext("description","")[:300]
                desc = re.sub(r'<[^>]+>', '', desc)
                if title and link:
                    posts.append({"title": title, "link": link, "desc": desc})
            if posts:
                return posts
    except Exception as e:
        print(f"RSS error: {e}", file=sys.stderr)
    return []

def get_latest_formatted(limit=3):
    posts = get_all_latest(limit)
    if not posts:
        return f"Visit latest guides 👉 {WEBSITE}/blog/"
    msg = "🔥 <b>Latest from Japablueprint.com.ng:</b>\n\n"
    for i, p in enumerate(posts, 1):
        msg += f"{i}. <b>{p['title']}</b>\n{p['link']}\n\n"
    msg += f"📚 More: {WEBSITE}"
    return msg

def send_message(chat_id, text):
    if not BOT_TOKEN:
        return False
    try:
        url = f"{TELEGRAM_API}/sendMessage"
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                payload = {"chat_id": chat_id, "text": part, "parse_mode": "HTML", "disable_web_page_preview": False}
                requests.post(url, json=payload, timeout=15)
            return True
        else:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
            r = requests.post(url, json=payload, timeout=15)
            return r.status_code==200
    except Exception as e:
        print(f"Send failed: {e}", file=sys.stderr)
        return False

def send_to_channel_direct(text):
    return send_message(CHANNEL_ID, text)

def auto_post_job():
    posts = get_all_latest(5)
    if not posts:
        return "No posts found"
    posted=[]
    if os.path.exists(POSTED_FILE):
        try:
            posted=json.load(open(POSTED_FILE))
        except:
            pass
    for p in posts:
        if p["link"] not in posted:
            caption = f"🇯🇵 <b>{p['title']}</b>\n\n{p['desc'][:250]}...\n\n👉 Read: {p['link']}\n\n#Japa #Japan #SwedenPOF"
            if send_to_channel_direct(caption):
                posted.append(p["link"])
                json.dump(posted[-100:], open(POSTED_FILE,"w"))
                return f"Posted: {p['title']}"
    return f"Reposted: {posts[0]['title']}"

def ask_ai_with_website_context(question):
    relevant = search_website(question, limit=3)
    website_context = ""
    links_text = ""
    if relevant:
        website_context = "\n".join([f"{i}. {r['title']} - {r['link']}" for i, r in enumerate(relevant, 1)])
        links_text = "\n".join([f"• {r['title']}\n{r['link']}" for r in relevant])
    
    if GEMINI_API_KEY:
        try:
            prompt = f"""You are Japablueprint.com.ng Professional Travel Consultant - expert in Japan, Sweden POF 103140 SEK 2025, Canada, UK, Schengen.

Answer ANY travel question professionally, detailed, friendly.

RULES:
1. Use AI brain for complete 2025 answer
2. Incorporate website guides if relevant: {website_context}
3. Specific amounts, docs, steps, timelines
4. Sweden POF = 103140 SEK 2025
5. Bullet points, bold numbers, emojis
6. Under 400 words but detailed
7. Professional encouraging expert tone

USER QUESTION: {question}

Give professional detailed answer with structure: direct answer, requirements, steps, tips, links.
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            r = requests.post(url, json=payload, timeout=25)
            if r.status_code==200:
                data = r.json()
                answer = data["candidates"][0]["content"]["parts"][0]["text"]
                if relevant and relevant[0]["link"] not in answer:
                    answer += f"\n\n📚 <b>Related guides:</b>\n{links_text}\n\n💬 More: {WEBSITE}"
                return answer
            else:
                print(f"Gemini error {r.status_code}: {r.text[:500]}", file=sys.stderr)
        except Exception as e:
            print(f"AI error: {e}", file=sys.stderr)
    
    fallback = get_smart_fallback(question)
    if relevant:
        fallback += f"\n📚 <b>Related:</b>\n{links_text}\n\n🔗 {WEBSITE}"
    else:
        fallback += f"\n📚 More: {WEBSITE} - Search '{question}'"
    return fallback

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    gemini_status = "✅ SET" if GEMINI_API_KEY else "❌ MISSING - Using fallback!"
    return f"Japablueprint SMART Bot ✅<br>Gemini: {gemini_status}<br>Channel: {CHANNEL_ID}<br>Health: <a href='/health'>/health</a><br>Time: {datetime.now()}"

@flask_app.route("/health")
def health():
    return "OK - SMART VERSION"

@flask_app.route("/autopost")
def autopost():
    key = flask_request.args.get("key", "")
    if key != CRON_SECRET:
        return "Unauthorized", 403
    result = auto_post_job()
    return f"Auto-post: {result} at {datetime.now()}"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = flask_request.get_json(force=True)
        if not data or "message" not in data:
            return "OK"
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text","")
        if not text:
            return "OK"
        if text.startswith("/start"):
            reply = f"🇯🇵 <b>Japablueprint SMART AI Online!</b>\n\nProfessional Japa assistant - Japablueprint.com.ng + 10 years expertise!\n\n<b>Ask ANY travel question:</b>\n• Sweden POF 103140 SEK 2025\n• Japan student visa\n• Canada, UK, Schengen\n\n<b>Try:</b>\nSweden POF?\nJapan student visa cost?\n\n<b>Commands:</b> /latest /search\n📚 {WEBSITE}"
            send_message(chat_id, reply)
        elif text.startswith("/latest"):
            send_message(chat_id, get_latest_formatted(3))
        elif text.startswith("/search"):
            query = text.replace("/search","").strip()
            if not query:
                send_message(chat_id, "Use: /search Sweden POF")
            else:
                results = search_website(query, limit=5)
                if not results:
                    send_message(chat_id, f"No results for '{query}'\nAsk me directly - I can answer from AI brain!")
                else:
                    msg = f"🔍 <b>Results for '{query}':</b>\n\n"
                    for i, r in enumerate(results, 1):
                        msg += f"{i}. <b>{r['title']}</b>\n{r['link']}\n\n"
                    send_message(chat_id, msg)
        else:
            answer = ask_ai_with_website_context(text)
            send_message(chat_id, answer)
    except Exception as e:
        print(f"Webhook error: {e}", file=sys.stderr)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting SMART bot on port {port} Gemini set: {bool(GEMINI_API_KEY)}", file=sys.stderr)
    flask_app.run(host="0.0.0.0", port=port)
