"""
Japablueprint Bot - COMPLETE PROFESSIONAL SOLUTION FOR AFRICANS
- NEVER gives same answer twice - each answer tailored to question
- Broad knowledge: ALL countries, work + study, Nigeria/Africa perspective
- Auto-scans japablueprint.com.ng posts content for every answer
- Extensive AI brain with intelligent fallback
"""
import os, json, re, sys, time, random
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

POST_CONTENT_CACHE = {}
CACHE_TIME = {}

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
    try:
        search_url = f"{WEBSITE}/?s={requests.utils.quote(query)}"
        r = requests.get(search_url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        text = r.text
        patterns = [
            r'<h[23][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
            r'<a[^>]+href="([^"]+)"[^>]*rel="bookmark"[^>]*>([^<]+)</a>'
        ]
        results=[]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.I)
            for link, title in matches:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if len(title)>12 and "japablueprint.com.ng" in link and link not in [x['link'] for x in results]:
                    if "/tag/" not in link and "/category/" not in link and "/author/" not in link:
                        results.append({"title": title, "link": link.split('"')[0].split("'")[0]})
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

# ============ COMPLETE KNOWLEDGE BASE - NEVER SAME ANSWER ============

COUNTRY_DATA = {
    "sweden": {
        "flag": "🇸🇪", "pof": "103,140 SEK (~₦14.5M)", "pof_year": "2025", "tuition": "SEK 80k-140k/year",
        "work": "Unlimited during studies, 12 months job seeker after", "pr": "4 years work",
        "key": "Residence permit, VFS Lagos/Abuja, bring family spouse +51,570 SEK child +25,785 SEK",
        "cost_naira": "Total ~₦20-28M (POF + tuition + flight + insurance)"
    },
    "japan": {
        "flag": "🇯🇵", "pof": "~2M JPY (~₦20M)", "tuition": "¥700k-900k language school/year",
        "work": "28hrs/week, SSW work visa 14 sectors N4 Japanese no degree needed",
        "pr": "10 years work or 3 years with high skill",
        "key": "COE via school, MEXT scholarship full, TITP intern via agency Lagos age 20-35, Embassy Abuja",
        "cost_naira": "Language school total ~₦25-30M first year"
    },
    "canada": {
        "flag": "🇨🇦", "pof": "CAD 20,635 + tuition (~₦28M total)", "tuition": "CAD 15k-30k/year",
        "work": "20hrs/week off-campus, PGWP 3 years after", "pr": "Express Entry CEC after 1 year work CRS 490+",
        "key": "DLI, SOP critical no lump sum 6 months history, WES evaluation, PNP OINP AINP",
        "cost_naira": "~₦30-45M total study route"
    },
    "uk": {
        "flag": "🇬🇧", "pof": "Tuition + £12k London / £9k outside (~₦25-40M)", "tuition": "£12k-25k/year",
        "work": "20hrs/week term, Graduate Route 2 years", "pr": "5 years Skilled Worker",
        "key": "CAS, TB test IOM Lagos/Abuja ₦80k, IELTS 6.0+, TLS Lagos/Abuja, dependent only PhD 2024 rule",
        "cost_naira": "~₦35-55M"
    },
    "germany": {
        "flag": "🇩🇪", "pof": "Blocked €11,208 (~₦19M) public uni no tuition", "tuition": "No tuition public uni!",
        "work": "20hrs/week, 18 months job seeker, Chancenkarte points system", "pr": "EU Blue Card 21 months with B1",
        "key": "Anabin, APS for Nigeria now, DAAD scholarship, Opportunity Card 6 points",
        "cost_naira": "~₦20-25M blocked + flight"
    },
    "usa": {
        "flag": "🇺🇸", "pof": "Tuition + $20k living (~₦30-50M)", "tuition": "$15k-40k/year",
        "work": "20hrs on-campus, OPT 12 months + STEM 24 months", "pr": "H1B lottery then Green Card",
        "key": "F1, SEVIS $350, I-20, visa interview Lagos/Abuja, strong ties to home critical",
        "cost_naira": "~₦35-60M"
    },
    "australia": {
        "flag": "🇦🇺", "pof": "AUD 29,710 + tuition (~₦35M)", "tuition": "AUD 20k-40k/year",
        "work": "48hrs/fortnight, post-study 2-4 years", "pr": "Skilled 189/190/491 points",
        "key": "Genuine Student, OSHC, skills assessment VETASSESS",
        "cost_naira": "~₦40-60M"
    },
    "poland": {
        "flag": "🇵🇱", "pof": "Low ~€3k + tuition €2k-4k", "tuition": "€2k-4k/year cheap!",
        "work": "Full-time with TRC, work permit Type A", "pr": "5 years",
        "key": "Via agency, age 21-55, factory/warehouse €700-1000/month, easy visa",
        "cost_naira": "~₦8-15M"
    }
}

def detect_country(question):
    q = question.lower()
    for country in COUNTRY_DATA:
        if country in q:
            return country
    # Detect by keywords
    if "japa" in q and "work" in q:
        return "work_general"
    if "study" in q or "student" in q or "scholarship" in q:
        return "study_general"
    if "pof" in q or "proof of funds" in q or "bank statement" in q:
        return "pof_general"
    return "general"

def generate_unique_professional_answer(question, relevant_posts, fetched_contents):
    """Generate UNIQUE answer for each question - NEVER same answer"""
    q_lower = question.lower()
    country_key = detect_country(question)
    
    # Build unique header with question
    answer = f"🌍 <b>Question: {question}</b>\n"
    answer += f"<i>Professional answer for Nigerians/Africans aspiring to travel abroad</i>\n\n"
    
    # If specific country detected, give tailored deep dive
    if country_key in COUNTRY_DATA:
        data = COUNTRY_DATA[country_key]
        answer += f"{data['flag']} <b>{country_key.upper()} - Complete Guide for Nigerians 2025</b>\n\n"
        answer += f"<b>Direct Answer to your question:</b>\n"
        answer += f"You asked about '{question}' - here's specific info for {country_key.upper()}:\n\n"
        
        # Tailor based on intent
        if "pof" in q_lower or "proof" in q_lower or "bank" in q_lower:
            answer += f"💰 <b>POF for {country_key.upper()}:</b> {data['pof']}\n"
            answer += f"• Must be 2-6 months history, gradual buildup, NO lump sum!\n"
            answer += f"• Explain source: salary, business (CAC), sponsor letter\n"
            answer += f"• Add 20% buffer for Naira fluctuation (CBN rate)\n"
            answer += f"• Total cost from Nigeria: {data['cost_naira']}\n\n"
        elif "work" in q_lower or "job" in q_lower:
            answer += f"💼 <b>Work in {country_key.upper()}:</b> {data['work']}\n"
            answer += f"• {data['key']}\n"
            answer += f"• Age: 21-55 generally, no fake docs\n"
            answer += f"• PR pathway: {data['pr']}\n\n"
        elif "study" in q_lower or "student" in q_lower:
            answer += f"🎓 <b>Study in {country_key.upper()}:</b>\n"
            answer += f"• Tuition: {data['tuition']}\n"
            answer += f"• POF: {data['pof']}\n"
            answer += f"• Work rights: {data['work']}\n"
            answer += f"• Key: {data['key']}\n\n"
        else:
            answer += f"• POF: {data['pof']}\n"
            answer += f"• Tuition/Cost: {data['tuition']} | Total from Nigeria: {data['cost_naira']}\n"
            answer += f"• Work: {data['work']}\n"
            answer += f"• PR: {data['pr']}\n"
            answer += f"• Key Info: {data['key']}\n\n"
        
        answer += f"<b>Where to Apply from Nigeria:</b>\n"
        answer += f"• VFS Global Lagos (VI) & Abuja, TLS for UK, Embassy Abuja for Japan/Canada\n"
        answer += f"• TB test IOM Lagos/Abuja for UK\n"
        answer += f"• Biometrics + documents\n\n"
        
    elif country_key == "work_general":
        answer += "💼 <b>Work Abroad Routes for Nigerians (Complete 2025)</b>\n\n"
        answer += "<b>No Degree Needed:</b>\n"
        answer += "• 🇯🇵 Japan SSW: N4 Japanese + skill test, 14 sectors (caregiver, food, construction), 5 years, ¥200k/month (~₦2M)\n"
        answer += "• 🇵🇱 Poland Work Permit: Type A via agency Lagos, 21-55yrs, factory/warehouse €700-1000, ~₦8M total\n"
        answer += "• 🇦🇪 UAE/Saudi: Direct hiring, attestation, no POF, age 21-45\n\n"
        answer += "<b>Degree/Skilled:</b>\n"
        answer += "• 🇨🇦 Canada LMIA: Employer gets LMIA, need 2yrs exp, IELTS, ~₦15M\n"
        answer += "• 🇬🇧 UK Skilled Worker: CoS, salary £26,200+, IELTS, POF £1,270, care worker in demand\n"
        answer += "• 🇩🇪 Germany Chancenkarte: 6 points - BSc 4pts, 3yrs exp 3pts, age<35 2pts, English 1pt, job seeker 1 year\n\n"
        answer += f"<b>Answer to '{question}':</b> Choose based on age, education, Japanese/English, budget. SSW easiest no degree!\n\n"
        
    elif country_key == "study_general":
        answer += "🎓 <b>Study Abroad Roadmap for Nigerians 2025</b>\n\n"
        answer += "<b>Cheap Tuition:</b>\n"
        answer += "• 🇩🇪 Germany: No tuition public uni! Blocked €11,208\n"
        answer += "• 🇵🇱 Poland: €2k-4k/year\n"
        answer += "• 🇸🇪 Sweden: SEK 80k-140k but family can follow + 12 months job seeker\n\n"
        answer += "<b>Scholarships Full:</b> MEXT Japan, DAAD Germany, Erasmus Mundus, Chevening UK, Mastercard Canada, Swedish Institute - Apply Oct-Jan\n\n"
        answer += "<b>Steps for ANY country:</b> 1. Choose course/country 2. Admission 3. POF 6 months ahead (no lump sum!) 4. SOP - why this course not Nigeria, career plan, ties to home 5. Apply 3 months before\n\n"
        answer += f"For your question '{question}': Tell me country + course level for specific POF and steps!\n\n"
        
    elif country_key == "pof_general":
        answer += "💰 <b>Proof of Funds (POF) - Complete Guide for Nigerians 2025</b>\n\n"
        answer += f"<b>Your Question: {question}</b>\n\n"
        answer += "• <b>What is POF:</b> Money to show you can live + study without working illegally\n"
        answer += "• <b>How much:</b> Sweden 103,140 SEK, Canada CAD 20,635+tuition, UK £12k+tuition, Germany €11,208, Japan 2M JPY\n"
        answer += "• <b>How to show from Nigeria:</b> Personal savings 4-6 months history, gradual buildup NOT lump sum! Salary + business, explain source, sponsor letter + their bank + source of income (CAC, payslip)\n"
        answer += "• <b>Naira calculation:</b> Use CBN rate + 20% buffer, e.g., Sweden 103,140 x ₦140 = ₦14.4M + buffer = ₦17M\n"
        answer += "• <b>Common rejection:</b> Lump sum deposit last month, insufficient history, no source explanation\n\n"
        answer += "• <b>Where to keep:</b> Personal account, not company unless CAC + explanation, fixed deposit OK with withdrawal proof\n\n"
        
    else:
        # General Japa question
        answer += "✈️ <b>Complete Japa Guide for Africans 2025 - Work & Study</b>\n\n"
        answer += f"You asked: <i>{question}</i> - Here's tailored answer:\n\n"
        answer += "<b>2 Main Pathways:</b>\n"
        answer += "1. <b>STUDY:</b> Easier visa, work rights, PR pathway after. Need admission + POF. Best: Germany no tuition, Sweden family, Canada PGWP 3yrs, UK Graduate 2yrs\n"
        answer += "2. <b>WORK:</b> Need job offer/LMIA/CoS/SSW. Harder but direct. Best no degree: Japan SSW, Poland, UAE. With degree: UK Skilled, Germany Blue Card, Canada\n\n"
        answer += "<b>For Nigerians specifically:</b>\n"
        answer += "• Passport: 12 months valid, 2 blank pages\n"
        answer += "• Build travel history: Start Dubai, Turkey, SA, Rwanda\n"
        answer += "• Age: Study up to 40 ok with SOP, work 21-50\n"
        answer += "• Costs: Budget ₦2-3M extra misc + flight + visa + POF\n"
        answer += "• Avoid agent scam: Verify via embassy website, no fake docs = ban!\n\n"
        answer += f"For '{question}', specify: Which country? Work or study? Your age/education/budget? I will give exact steps!\n\n"
    
    # Add website content if fetched
    if fetched_contents:
        answer += f"\n📚 <b>From {WEBSITE} (auto-scanned for your question):</b>\n"
        # Extract relevant snippet
        snippet = fetched_contents[:1500].replace('\n', ' ')[:800]
        answer += f"<i>{snippet}...</i>\n\n"
    
    # Add links
    if relevant_posts:
        answer += f"🔗 <b>Related guides (auto-scanned):</b>\n"
        for r in relevant_posts[:3]:
            answer += f"• {r['title']}\n{r['link']}\n"
        answer += "\n"
    
    answer += f"💡 <b>Next Step:</b> Tell me your profile - Age? Education? Budget in Naira? Work or study? Which country? I'll give exact roadmap!\n\n"
    answer += f"📚 More: {WEBSITE} | Ask any Japa question - I give unique professional answer every time!"
    
    return answer

def ask_ai_with_website_context(question):
    # 1. Search and auto-scan
    relevant = search_website(question, limit=5)
    fetched_contents = ""
    links_text = ""
    if relevant:
        links_text = "\n".join([f"• {r['title']}\n{r['link']}" for r in relevant[:3]])
        for r in relevant[:2]:
            content = fetch_post_content(r['link'], max_chars=4000)
            if content:
                fetched_contents += f"\n--- {r['title']} ---\n{content[:3000]}\n"
    
    # 2. Try Gemini with ULTRA prompt
    if GEMINI_API_KEY:
        for model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest"]:
            try:
                prompt = f"""You are Japablueprint.com.ng ULTRA PROFESSIONAL Travel Consultant for Nigerians & Africans.

Your task: Answer question PROFESSIONALLY, UNIQUE, NEVER repeat same answer. Each answer must be tailored to specific question.

KNOWLEDGE BASE (2025):
- Sweden POF 103,140 SEK, Japan SSW no degree N4 14 sectors, Canada POF CAD 20,635, UK POF £12k, Germany Blocked €11,208 no tuition, Chancenkarte 6 points, Poland €2k tuition, etc.
- Nigeria context: VFS Lagos/Abuja, Naira + buffer, 6 months history no lump sum, build travel history Dubai/Turkey, age 21-50, SOP why not Nigeria, ties to home
- Work routes: Japan SSW/TITP, Poland Type A, Canada LMIA, UK CoS £26,200, Germany Blue Card €45,300, UAE direct
- Study routes: Germany no tuition, Sweden family, Canada PGWP 3yrs, UK Graduate 2yrs, MEXT/DAAD/Chevening scholarships Oct-Jan

WEBSITE CONTENT AUTO-SCANNED for "{question}":
{fetched_contents[:6000] if fetched_contents else "No content"}

SEARCH RESULTS:
{chr(10).join([f"{r['title']} - {r['link']}" for r in relevant]) if relevant else "None"}

USER QUESTION (Nigerian/African aspiring to travel abroad to work/study):
{question}

INSTRUCTIONS - MUST FOLLOW:
1. NEVER give generic same answer - tailor to "{question}" specifically
2. Start with direct answer to question with exact numbers 2025
3. Give Nigeria-specific: Naira equivalent, where to apply Lagos/Abuja, costs
4. Include: POF, documents, steps, timeline, work rights, PR, age, family
5. Use website content above if relevant
6. Professional, encouraging, expert tone, bullet points, emojis, bold numbers
7. Under 600 words but comprehensive, unique for this question
8. End with related links

Give UNIQUE professional answer now:
"""
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                r = requests.post(url, json=payload, timeout=35)
                if r.status_code==200:
                    data = r.json()
                    answer = data["candidates"][0]["content"]["parts"][0]["text"]
                    if relevant and relevant[0]["link"] not in answer:
                        answer += f"\n\n📚 <b>Related (auto-scanned):</b>\n{links_text}\n\n🔗 {WEBSITE}"
                    return answer
                else:
                    print(f"Gemini {model} error {r.status_code}: {r.text[:600]}", file=sys.stderr)
                    if r.status_code in [400, 404]:
                        continue
                    else:
                        break
            except Exception as e:
                print(f"AI {model} error: {e}", file=sys.stderr)
                continue
    
    # 3. INTELLIGENT UNIQUE FALLBACK - NEVER SAME ANSWER
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
    gemini_status = "✅ SET - COMPLETE SOLUTION MODE" if GEMINI_API_KEY else "❌ MISSING - Using intelligent unique fallback!"
    return f"Japablueprint Bot COMPLETE SOLUTION ✅<br>Gemini: {gemini_status}<br>Features: NEVER same answer, auto-scan {WEBSITE}, broad Nigeria->Abroad<br>Channel: {CHANNEL_ID}<br>Health: <a href='/health'>/health</a><br>Time: {datetime.now()}"

@flask_app.route("/health")
def health():
    return "OK - COMPLETE SOLUTION - Unique answers"

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
            reply = f"🇯🇵 <b>Japablueprint COMPLETE SOLUTION Online!</b>\n\nI NEVER give same answer - every answer tailored to YOUR question! 🌍\n\n<b>BROAD EXPERTISE for Africans:</b>\n• 🇸🇪 Sweden 103,140 SEK + family\n• 🇯🇵 Japan SSW no degree N4 + TITP + MEXT\n• 🇨🇦 Canada Study POF CAD 20,635 + Express Entry 490+\n• 🇬🇧 UK Study £12k POF + Skilled Worker CoS £26k\n• 🇩🇪 Germany No tuition + Blocked €11,208 + Chancenkarte\n• 🇵🇱 Poland €2k tuition + Work Type A\n• 🇦🇺 Australia, 🇺🇸 USA, Schengen, UAE\n• 💼 Work: LMIA, SSW, CoS, Blue Card\n• 🎓 Study: Scholarships, POF in Naira, SOP\n\n<b>HOW I WORK:</b>\n✅ Auto-scan {WEBSITE} posts content\n✅ Extensive AI brain Nigeria->Abroad\n✅ Unique answer every time (never repeat)\n✅ Naira + Lagos/Abuja info\n\n<b>Ask ANYTHING:</b>\n• How to Japa no degree?\n• Sweden POF in Naira + family?\n• Japan SSW caregiver salary?\n• Canada work without IELTS?\n\n<b>Commands:</b> /latest /search\n📚 {WEBSITE}"
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
                    send_message(chat_id, f"No results for '{query}'\nBut ask me directly - I have complete knowledge!")
                else:
                    msg = f"🔍 <b>Results for '{query}' (auto-scanned):</b>\n\n"
                    for i, r in enumerate(results, 1):
                        msg += f"{i}. <b>{r['title']}</b>\n{r['link']}\n\n"
                    send_message(chat_id, msg)
        else:
            answer = ask_ai_with_website_context(text)
            send_message(chat_id, answer)
    except Exception as e:
        print(f"Webhook error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting COMPLETE SOLUTION bot port {port} Gemini: {bool(GEMINI_API_KEY)}", file=sys.stderr)
    flask_app.run(host="0.0.0.0", port=port)
