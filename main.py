"""
Japablueprint Bot - DEEPSEEK VERSION - FASTER & MORE ACCURATE
- Replaced Gemini with DeepSeek Chat (deepseek-chat)
- Typing indicator before response
- Auto-scans japablueprint.com.ng posts
- Complete professional solution for Africans
"""
import os, json, re, sys, time
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
from flask import Flask, request as flask_request

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Support both GEMINI_API_KEY (old) and DEEPSEEK_API_KEY (new)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@japablueprint")
CRON_SECRET = os.getenv("CRON_SECRET", "japablueprint123")
WEBSITE = "https://japablueprint.com.ng"
POSTED_FILE = "posted.json"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

POST_CONTENT_CACHE = {}
CACHE_TIME = {}

def send_typing_action(chat_id):
    """Show typing indicator before bot responds - makes bot feel professional"""
    if not BOT_TOKEN:
        return False
    try:
        url = f"{TELEGRAM_API}/sendChatAction"
        payload = {"chat_id": chat_id, "action": "typing"}
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        print(f"Typing action failed: {e}", file=sys.stderr)
        return False

def fetch_post_content(url, max_chars=5000):
    try:
        if url in POST_CONTENT_CACHE and time.time() - CACHE_TIME.get(url, 0) < 3600:
            return POST_CONTENT_CACHE[url]
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=15, headers=headers)
        html = r.text
        m = re.search(r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>\s*<', html, re.I | re.S)
        if not m:
            m = re.search(r'<article[^>]*>(.*?)</article>', html, re.I | re.S)
        content = ""
        if m:
            raw = m.group(1)
            raw = re.sub(r'<script.*?</script>', '', raw, flags=re.I | re.S)
            raw = re.sub(r'<style.*?</style>', '', raw, flags=re.I | re.S)
            raw = re.sub(r'<[^>]+>', ' ', raw)
            raw = re.sub(r'\s+', ' ', raw).strip()
            content = raw[:max_chars]
        else:
            raw = re.sub(r'<[^>]+>', ' ', html)
            raw = re.sub(r'\s+', ' ', raw).strip()
            content = raw[:max_chars]
        POST_CONTENT_CACHE[url] = content
        CACHE_TIME[url] = time.time()
        return content
    except Exception as e:
        print(f"Fetch error {url}: {e}", file=sys.stderr)
        return ""

def search_website(query, limit=5):
    """Dynamic random scraping from japablueprint.com.ng"""
    try:
        import random
        # Randomize search to get dynamic results
        search_url = f"{WEBSITE}/?s={requests.utils.quote(query)}"
        r = requests.get(search_url, timeout=15, headers={"User-Agent": f"Mozilla/5.0 (random {random.randint(1,1000)})"})
        text = r.text
        patterns = [
            r'<h[23][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
            r'<a[^>]+href="([^"]+)"[^>]*rel="bookmark"[^>]*>([^<]+)</a>',
            r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*entry-title[^"]*"[^>]*>([^<]+)</a>'
        ]
        results=[]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.I)
            random.shuffle(matches)  # Randomize order for dynamic answers
            for link, title in matches:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if len(title)>12 and "japablueprint.com.ng" in link and link not in [x['link'] for x in results]:
                    if "/tag/" not in link and "/category/" not in link and "/author/" not in link and "/page/" not in link:
                        results.append({"title": title, "link": link.split('"')[0].split("'")[0]})
            if len(results) >= limit*2:
                break
        # Randomly select subset for dynamic behavior
        if len(results) > limit:
            results = random.sample(results, limit)
        else:
            random.shuffle(results)
        return results[:limit]
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

def get_all_latest(limit=5):
    try:
        r = requests.get(f"{WEBSITE}/feed/", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        content = r.content
        if b"<item>" in content:
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
                payload = {"chat_id": chat_id, "text": part, "parse_mode": "HTML", "disable_web_page_preview": True}
                requests.post(url, json=payload, timeout=15)
            return True
        else:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
            r = requests.post(url, json=payload, timeout=15)
            return r.status_code==200
    except Exception as e:
        print(f"Send failed: {e}", file=sys.stderr)
        return False

# ============ COMPLETE KNOWLEDGE BASE ============
COUNTRY_DATA = {
    "sweden": {"flag": "🇸🇪", "pof": "103,140 SEK (~₦14.5M)", "tuition": "SEK 80k-140k/year", "work": "Unlimited during studies, 12 months job seeker after", "pr": "4 years work", "key": "Residence permit, VFS Lagos/Abuja, bring family spouse +51,570 SEK child +25,785 SEK", "cost_naira": "Total ~₦20-28M"},
    "japan": {"flag": "🇯🇵", "pof": "~2M JPY (~₦20M)", "tuition": "¥700k-900k language school/year", "work": "28hrs/week, SSW work visa 14 sectors N4 Japanese no degree needed", "pr": "10 years work", "key": "COE via school, MEXT scholarship, TITP intern via agency Lagos age 20-35, Embassy Abuja", "cost_naira": "~₦25-30M first year"},
    "canada": {"flag": "🇨🇦", "pof": "CAD 20,635 + tuition (~₦28M total)", "tuition": "CAD 15k-30k/year", "work": "20hrs/week, PGWP 3 years", "pr": "Express Entry CRS 490+", "key": "DLI, SOP critical no lump sum 6 months history, WES", "cost_naira": "~₦30-45M"},
    "uk": {"flag": "🇬🇧", "pof": "Tuition + £12k London / £9k outside", "tuition": "£12k-25k/year", "work": "20hrs/week, Graduate Route 2 years", "pr": "5 years Skilled Worker", "key": "CAS, TB test IOM Lagos/Abuja, IELTS 6.0+", "cost_naira": "~₦35-55M"},
    "germany": {"flag": "🇩🇪", "pof": "Blocked €11,208 (~₦19M) no tuition public uni", "tuition": "No tuition public uni!", "work": "20hrs/week, Chancenkarte 6 points", "pr": "EU Blue Card 21 months", "key": "Anabin, APS, DAAD, Opportunity Card", "cost_naira": "~₦20-25M"},
    "usa": {"flag": "🇺🇸", "pof": "Tuition + $20k living", "tuition": "$15k-40k/year", "work": "20hrs on-campus, OPT 12 months", "pr": "H1B lottery", "key": "F1, SEVIS, I-20, Lagos/Abuja interview", "cost_naira": "~₦35-60M"},
    "australia": {"flag": "🇦🇺", "pof": "AUD 29,710 + tuition", "tuition": "AUD 20k-40k/year", "work": "48hrs/fortnight, post-study 2-4 years", "pr": "Skilled 189/190/491", "key": "Genuine Student, OSHC", "cost_naira": "~₦40-60M"},
    "poland": {"flag": "🇵🇱", "pof": "Low ~€3k + tuition €2k-4k", "tuition": "€2k-4k/year cheap!", "work": "Full-time with TRC", "pr": "5 years", "key": "Via agency, age 21-55, €700-1000/month", "cost_naira": "~₦8-15M"}
}

def detect_country(question):
    q = question.lower()
    for country in COUNTRY_DATA:
        if country in q:
            return country
    if "japa" in q and "work" in q:
        return "work_general"
    if "study" in q or "student" in q or "scholarship" in q:
        return "study_general"
    if "pof" in q or "proof of funds" in q or "bank statement" in q:
        return "pof_general"
    return "general"

def generate_unique_professional_answer(question, relevant_posts, fetched_contents):
    q_lower = question.lower()
    country_key = detect_country(question)
    answer = f"🌍 <b>Question: {question}</b>\n<i>Professional answer for Nigerians/Africans</i>\n\n"
    
    if country_key in COUNTRY_DATA:
        data = COUNTRY_DATA[country_key]
        answer += f"{data['flag']} <b>{country_key.upper()} - Complete Guide for Nigerians 2025</b>\n\n"
        answer += f"<b>Direct Answer:</b> For '{question}' - {country_key.upper()}:\n\n"
        if "pof" in q_lower or "proof" in q_lower or "bank" in q_lower:
            answer += f"💰 <b>POF:</b> {data['pof']} | Total: {data['cost_naira']}\n• 2-6 months history, gradual, NO lump sum!\n• Explain source: salary/business CAC\n• Add 20% buffer Naira\n\n"
        elif "work" in q_lower or "job" in q_lower:
            answer += f"💼 <b>Work:</b> {data['work']}\n• {data['key']}\n• PR: {data['pr']}\n\n"
        else:
            answer += f"• POF: {data['pof']}\n• Tuition: {data['tuition']} | {data['cost_naira']}\n• Work: {data['work']}\n• PR: {data['pr']}\n• Key: {data['key']}\n\n"
        answer += f"<b>Apply from Nigeria:</b> VFS Lagos/Abuja, TLS, Embassy Abuja\n\n"
    elif country_key == "work_general":
        answer += "💼 <b>Work Abroad for Nigerians 2025 - No Degree to Degree</b>\n\n"
        answer += "• 🇯🇵 Japan SSW: N4 + skill test, 14 sectors, no degree, ¥200k/month\n"
        answer += "• 🇵🇱 Poland: Type A via agency, 21-55yrs, €700-1000, ~₦8M\n"
        answer += "• 🇨🇦 Canada LMIA, 🇬🇧 UK CoS £26,200, 🇩🇪 Chancenkarte 6 points\n\n"
        answer += f"For '{question}': Choose based on age/education/budget. SSW easiest no degree!\n\n"
    elif country_key == "study_general":
        answer += "🎓 <b>Study Abroad Roadmap Nigerians 2025</b>\n\n"
        answer += "• 🇩🇪 Germany no tuition Blocked €11,208\n• 🇵🇱 Poland €2k-4k\n• Scholarships: MEXT, DAAD, Chevening Oct-Jan\n"
        answer += "• Steps: Admission, POF 6 months ahead no lump sum, SOP why not Nigeria\n\n"
    elif country_key == "pof_general":
        answer += "💰 <b>POF Guide Nigerians 2025</b>\n\n"
        answer += f"Q: {question}\n• Sweden 103,140 SEK, Canada CAD 20,635+tuition, UK £12k+tuition, Germany €11,208\n"
        answer += "• How: 4-6 months history gradual NOT lump sum, explain source, add 20% Naira buffer\n• Example: Sweden 103,140 x ₦140 = ₦14.4M + buffer ₦17M\n\n"
    else:
        answer += "✈️ <b>Complete Japa Guide Africans 2025</b>\n\n"
        answer += f"Q: {question}\n\n<b>2 Pathways:</b>\n1. STUDY: Easier visa + work rights + PR. Germany no tuition, Sweden family, Canada PGWP 3yrs\n"
        answer += "2. WORK: Need job offer. No degree: Japan SSW, Poland, UAE. Degree: UK Skilled, Germany Blue Card\n\n"
        answer += "For Nigerians: Passport 12 months, build history Dubai/Turkey, age 21-50, budget extra ₦2-3M\n\n"
    
    if fetched_contents:
        snippet = fetched_contents[:1500].replace('\n', ' ')[:600]
        answer += f"\n📚 <b>From {WEBSITE} (auto-scanned):</b>\n<i>{snippet}...</i>\n\n"
    if relevant_posts:
        answer += f"🔗 <b>Related guides:</b>\n"
        for r in relevant_posts[:3]:
            answer += f"• {r['title']}\n{r['link']}\n"
        answer += "\n"
    answer += f"💡 Next: Tell me age/education/budget work or study which country for exact roadmap!\n📚 {WEBSITE}"
    return answer

def ask_ai_with_deepseek(question, relevant_posts, fetched_contents):
    """DeepSeek API - Faster & More Accurate than Gemini"""
    if not DEEPSEEK_API_KEY:
        print("DEEPSEEK_API_KEY missing, using fallback", file=sys.stderr)
        return None
    
    # Build context
    website_context = "\n".join([f"{r['title']} - {r['link']}" for r in relevant_posts]) if relevant_posts else "No exact match"
    content_context = fetched_contents[:6000] if fetched_contents else "No content fetched"
    
    system_prompt = f"""You are Japablueprint.com.ng ULTRA PROFESSIONAL Travel Consultant for Nigerians & Africans moving abroad to WORK or STUDY.

EXPERTISE 2025:
- Sweden POF 103,140 SEK 2025, Japan SSW no degree N4 14 sectors, TITP, MEXT, Canada POF CAD 20,635 + tuition, UK POF £12k + tuition CAS TB test IOM, Germany Blocked €11,208 no tuition Chancenkarte 6 points Blue Card €45,300, Poland €2k tuition Work Type A, USA F1 SEVIS, Australia AUD 29,710, etc.
- Nigeria context: VFS Lagos/Abuja, Naira + 20% buffer, 6 months history NO lump sum, build travel history Dubai/Turkey/SA, age 21-50, SOP why not Nigeria ties to home, costs in Naira
- Work: Japan SSW/TITP, Poland, Canada LMIA, UK CoS £26,200 care worker, Germany Opportunity Card, UAE direct
- Study: Scholarships MEXT DAAD Chevening Erasmus Mastercard Oct-Jan, Germany no tuition, Sweden family, Canada PGWP 3yrs, UK Graduate 2yrs

WEBSITE AUTO-SCANNED:
{website_context}

ACTUAL CONTENT FROM JAPABLUEPRINT.COM.NG:
{content_context}

INSTRUCTIONS:
- Answer question PROFESSIONALLY, UNIQUE, NEVER repeat generic
- Tailor to Nigerian/African perspective: Naira equivalent (~), Lagos/Abuja application, costs from Nigeria
- Give exact 2025 numbers, POF, documents, steps, timeline, work rights, PR, age, family
- Use website content if relevant
- Professional encouraging expert tone, bullet points, emojis, bold numbers
- Under 600 words comprehensive
- End with related links
"""

    try:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question from Nigerian aspiring to travel abroad: {question}\n\nGive UNIQUE professional detailed answer tailored to this specific question. Include Naira, Lagos/Abuja, exact 2025 numbers."}
            ],
            "temperature": 0.7,
            "max_tokens": 1200,
            "stream": False
        }
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            answer = data["choices"][0]["message"]["content"]
            # Add links if not present
            if relevant_posts and relevant_posts[0]["link"] not in answer:
                links_text = "\n".join([f"• {r['title']}\n{r['link']}" for r in relevant_posts[:3]])
                answer += f"\n\n📚 <b>Related (auto-scanned from {WEBSITE}):</b>\n{links_text}"
            return answer
        else:
            print(f"DeepSeek error {r.status_code}: {r.text[:800]}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"DeepSeek exception: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None

def ask_ai_with_website_context(question):
    relevant = search_website(question, limit=5)
    fetched_contents = ""
    if relevant:
        for r in relevant[:2]:
            content = fetch_post_content(r['link'], max_chars=4000)
            if content:
                fetched_contents += f"\n--- {r['title']} ---\n{content[:3000]}\n"
    
    # Try DeepSeek first - faster & more accurate
    deepseek_answer = ask_ai_with_deepseek(question, relevant, fetched_contents)
    if deepseek_answer:
        return deepseek_answer
    
    # Fallback to intelligent unique answer
    return generate_unique_professional_answer(question, relevant, fetched_contents)

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
            caption = f"🇯🇵 <b>{p['title']}</b>\n\n{p['desc'][:250]}...\n\n👉 Read: {p['link']}\n\n#Japa #NigeriaToAbroad"
            if send_message(CHANNEL_ID, caption):
                posted.append(p["link"])
                json.dump(posted[-100:], open(POSTED_FILE,"w"))
                return f"Posted: {p['title']}"
    return f"Reposted: {posts[0]['title']}"

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    deepseek_status = "✅ SET - DEEPSEEK MODE (Faster & More Accurate)" if DEEPSEEK_API_KEY else "❌ MISSING - Using intelligent fallback!"
    return f"Japablueprint Bot DEEPSEEK ✅<br>DeepSeek: {deepseek_status}<br>Features: Typing indicator + Auto-scan {WEBSITE} + Broad Nigeria->Abroad<br>Channel: {CHANNEL_ID}<br>Health: <a href='/health'>/health</a><br>Time: {datetime.now()}"

@flask_app.route("/health")
def health():
    return "OK - DEEPSEEK VERSION - Faster + Typing"

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
            # Simple professional welcome - as requested
            reply = f"""🇯🇵 <b>Welcome to Japa Blue Print AI</b>

Ask me any Japa Question, i will answer you with exact details.

🌍 <b>I can help you with:</b>
• Sweden, Japan, Canada, UK, Germany, Poland, Australia, USA & more
• Study routes, work visas, POF, scholarships
• Costs in Naira, documents, steps from Nigeria

💬 <b>Just ask:</b>
• Sweden POF?
• How to Japa no degree?
• Japan student visa?

📚 <b>Commands:</b>
/latest - Latest guides
/search [topic] - Search website

{WEBSITE}"""
            send_message(chat_id, reply)
        elif text.startswith("/latest"):
            send_typing_action(chat_id)
            time.sleep(0.5)
            send_message(chat_id, get_latest_formatted(3))
        elif text.startswith("/search"):
            query = text.replace("/search","").strip()
            if not query:
                send_message(chat_id, "Use: /search Sweden POF")
            else:
                send_typing_action(chat_id)
                time.sleep(0.5)
                results = search_website(query, limit=5)
                if not results:
                    send_message(chat_id, f"No results for '{query}'\nBut ask me directly - I have complete knowledge!")
                else:
                    msg = f"🔍 <b>Results for '{query}' (auto-scanned):</b>\n\n"
                    for i, r in enumerate(results, 1):
                        msg += f"{i}. <b>{r['title']}</b>\n{r['link']}\n\n"
                    send_message(chat_id, msg)
        else:
            # Show Typing.... before bringing out answers - as requested
            send_typing_action(chat_id)
            time.sleep(1)  # Show typing for 1 sec for professional feel
            # For longer AI processing, keep typing indicator alive
            try:
                # Send typing again after 3 seconds if still processing
                import threading
                def keep_typing():
                    for _ in range(3):
                        time.sleep(4)
                        send_typing_action(chat_id)
                t = threading.Thread(target=keep_typing, daemon=True)
                t.start()
                answer = ask_ai_with_website_context(text)
            except:
                answer = ask_ai_with_website_context(text)
            send_message(chat_id, answer)
    except Exception as e:
        print(f"Webhook error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting DEEPSEEK bot port {port} DeepSeek: {bool(DEEPSEEK_API_KEY)}", file=sys.stderr)
    flask_app.run(host="0.0.0.0", port=port)
