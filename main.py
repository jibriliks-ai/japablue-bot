"""
Japablueprint Bot - ULTRA SMART VERSION FOR NIGERIA/AFRICA -> ABROAD
- Broad knowledge: work, study, all countries
- Auto-scans japablueprint.com.ng posts content for every answer
- Extensive AI brain + website knowledge combined
- Professional consultant for Nigerians/Africans
"""
import os, json, re, sys, time
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

# Cache for fetched post contents to avoid re-scraping
POST_CONTENT_CACHE = {}
CACHE_TIME = {}

def fetch_post_content(url, max_chars=4000):
    """Auto-scan actual post content from japablueprint.com.ng"""
    try:
        # Check cache (1 hour)
        if url in POST_CONTENT_CACHE and time.time() - CACHE_TIME.get(url, 0) < 3600:
            return POST_CONTENT_CACHE[url]
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, timeout=12, headers=headers)
        html = r.text
        
        # Try to extract main article content (WordPress)
        # Look for <article> or <div class="entry-content">
        article_match = re.search(r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>\s*<', html, re.I | re.S)
        if not article_match:
            article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.I | re.S)
        
        content = ""
        if article_match:
            raw = article_match.group(1)
            # Strip HTML tags
            raw = re.sub(r'<script.*?</script>', '', raw, flags=re.I | re.S)
            raw = re.sub(r'<style.*?</style>', '', raw, flags=re.I | re.S)
            raw = re.sub(r'<[^>]+>', ' ', raw)
            raw = re.sub(r'\s+', ' ', raw).strip()
            content = raw[:max_chars]
        else:
            # Fallback: strip all tags and take first 4000 chars
            raw = re.sub(r'<[^>]+>', ' ', html)
            raw = re.sub(r'\s+', ' ', raw).strip()
            content = raw[:max_chars]
        
        POST_CONTENT_CACHE[url] = content
        CACHE_TIME[url] = time.time()
        return content
    except Exception as e:
        print(f"Fetch content error {url}: {e}", file=sys.stderr)
        return ""

def search_website(query, limit=5):
    """Search japablueprint.com.ng and auto-fetch content"""
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
                payload = {"chat_id": chat_id, "text": part, "parse_mode": "HTML", "disable_web_page_preview": True}
                requests.post(url, json=payload, timeout=15)
            return True
        else:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code != 200:
                print(f"Telegram error: {r.text[:500]}", file=sys.stderr)
            return r.status_code==200
    except Exception as e:
        print(f"Send failed: {e}", file=sys.stderr)
        return False

# ============ EXTENSIVE KNOWLEDGE BASE FOR NIGERIA/AFRICA -> ABROAD ============
EXTENSIVE_KNOWLEDGE = """
You are Japablueprint.com.ng ULTRA SMART Travel Consultant for Nigerians & Africans moving abroad to WORK or STUDY.

YOUR EXPERTISE (2025 Updated):
1. STUDY ABROAD:
- Sweden: POF 103,140 SEK 2025, residence permit, 12 months job seeker after studies, bring family
- Japan: MEXT Scholarship, Language School, COE process, SSW work visa, TITP, Engineer visa, 2M JPY POF, 28hrs work, N3/N4 Japanese needed, apply at Abuja embassy
- Canada: Study permit POF CAD 20,635 + tuition (2025), SDS, SPP, DLI, PGWP 3 years, Express Entry CRS 490+, PNP, proof of funds 6 months history, SOP critical, no lump sum
- UK: CAS, POF tuition + £1,334 x9 London / £1,023 outside, 28-day rule, TB test at IOM Lagos/Abuja, IELTS, Graduate Route 2 years, dependent rules 2024 update
- Germany: Blocked Account €11,208/year, Chancenkarte (Opportunity Card), DAAD scholarship, no tuition public uni, Anabin, APS for Nigeria
- USA: F1 visa, SEVIS, I-20, proof of funds, visa interview Lagos/Abuja, strong ties to home, 2-year home residency for J1
- Australia: Genuine Student, POF AUD 29,710 + tuition + travel, OSHC, 48hrs/fortnight work, post-study 2-4 years
- Schengen: France, Poland, Lithuania, Malta, Finland - low tuition, POF varies

2. WORK ABROAD:
- Japan SSW (Tokutei Ginou) 14 sectors, N4 Japanese, skill test, no degree needed, 5 years + extension
- Japan TITP: Technical Intern, 3-5 years, via sending org in Nigeria, age 20-35
- Canada Work: LMIA, Global Talent Stream, Caregiver, Seasonal Agric, POF
- UK Skilled Worker: Need licensed sponsor, CoS, salary threshold £26,200+, IELTS, POF £1,270, health surcharge
- Germany Work: Opportunity Card 6 points system, Skilled Worker visa, EU Blue Card €45,300 salary, blocked account not needed if job offer
- Poland Work: Work permit type A, B, seasonal, via agency, POF, age 21-55
- UAE/Saudi: Direct hiring, no POF, attestation, age 21-45
- Australia Work: TSS 482, skilled migration 189/190/491, points test, skills assessment VETASSESS

3. NIGERIA-SPECIFIC:
- Where to apply: Embassy Lagos (VI) and Abuja, VFS TLS, IOM for TB/medical
- POF in Naira: Always calculate at current CBN rate + 20% buffer for exchange fluctuation, 6 months statement, explain source, salary + business
- Common rejections: Lump sum, insufficient ties, weak SOP, fake docs, insufficient travel history
- Travel history: Start with Dubai, Turkey, South Africa, Rwanda to build passport
- Age: Study up to 35-40 ok with good SOP, work 21-50 depending on country
- Family: Can go with spouse/children for Sweden, Canada, UK (PhD/research), Germany family reunion
- Costs from Nigeria: Show in Naira + foreign currency, include flight, visa fee, insurance, blocked account

4. SCHOLARSHIPS & FUNDING:
- MEXT Japan full, Erasmus Mundus, DAAD Germany, Chevening UK, Mastercard Canada, CSC China, Swedish Institute
- How to win: Strong academic, SOP, recommendations, volunteer, apply early (Oct-Jan for next year)

5. DOCUMENTS:
- Passport 6-12 months valid, 2 blank pages
- Academic: WAEC, BSc, transcripts, evaluation WES for Canada
- POF: Bank statement 4-6 months, sponsor letter, source of funds, business CAC if self-employed
- SOP: Why this country, why this course/job, why now, career plan, ties to Nigeria, why not Nigeria
- Police character, medical, birth certificate

Answer in professional, encouraging tone for Nigerian audience. Use Naira equivalent where helpful. Give exact numbers for 2025. Always mention Japablueprint.com.ng has detailed guides.
"""

def get_extensive_fallback(question):
    q = question.lower()
    base = f"🌍 <b>Expert Answer for Nigerians: {question}</b>\n\n"
    
    if "sweden" in q:
        base += "🇸🇪 <b>Sweden 2025: POF 103,140 SEK (~₦14.5M at ₦140/SEK + buffer)</b>\n\n<b>Study Route:</b>\n• Admission via universityadmissions.se (Oct-Jan)\n• POF 103,140 SEK x10 months, 2-3 months history\n• Apply residence permit online, biometrics at VFS Lagos/Abuja\n• Can bring family (spouse +51,570 SEK, child +25,785 SEK)\n• Work unlimited after permit, 12 months job seeker after graduation\n• PR after 4 years work\n\n<b>Work Route:</b> Need job offer, employer applies work permit, salary ~SEK 28k+\n"
    elif "japan" in q:
        base += "🇯🇵 <b>Japan for Nigerians 2025</b>\n\n<b>Study (Language School):</b>\n• COE via school, POF ~2M JPY (~₦20M), ~700k-900k JPY tuition\n• N5 Japanese, 6 months process\n• Work 28hrs/week @ ¥1,100/hr, full-time holidays\n• SSW work visa after: 14 sectors (caregiver, food, construction), N4 + skill test, no degree, 5 years\n• TITP intern: via licensed agency in Lagos, age 20-35, 3 years\n• Engineer/Specialist: BSc + job offer\n\n<b>Scholarship:</b> MEXT full via Embassy Abuja (April-May)\n• Embassy: Abuja, fees ~₦15k\n"
    elif "canada" in q:
        base += "🇨🇦 <b>Canada for Nigerians 2025</b>\n\n<b>Study:</b>\n• POF CAD 20,635 + tuition + CAD 10k travel (~₦28M total)\n• 6 months bank history, NO lump sum! Gradual buildup\n• SOP critical: why Canada not Nigeria, career plan\n• DLI admission, pay 1 year tuition\n• PGWP 3 years after, PR via Express Entry CEC\n\n<b>Express Entry Work:</b>\n• CRS 490+, age 20-35 max points, IELTS 8/7/7/7, BSc + WES, 3 years experience\n• PNP: OINP, AINP, SINP easier for Nigerians\n• Caregiver: Need job offer + 1yr experience\n• Processing: 6-8 months\n"
    elif "uk" in q:
        base += "🇬🇧 <b>UK for Nigerians 2025</b>\n\n<b>Study:</b>\n• CAS from uni, POF: tuition + £1,334x9 London (£12k) or £1,023x9 outside (~₦25M-₦40M)\n• 28-day rule, TB test IOM Lagos/Abuja ₦80k, IELTS 6.0+\n• Apply via TLS Lagos/Abuja, 3 weeks\n• Work 20hrs/week, Graduate Route 2 years (3yrs PhD)\n• Dependent: Only PhD/research/masters by research can bring family 2024 rule\n\n<b>Skilled Worker:</b>\n• Licensed sponsor, CoS, salary £26,200+, IELTS, POF £1,270, IHS £1,035/year\n"
    elif "germany" in q:
        base += "🇩🇪 <b>Germany for Nigerians 2025</b>\n\n<b>Study:</b>\n• Public uni NO tuition! Blocked Account €11,208 (~₦19M) + admission\n• Chancenkarte (Opportunity Card): Points system, 6 points needed - age, degree, experience, language\n• DAAD scholarship full\n• Anabin check, APS certificate for Nigeria now required\n• Work 20hrs/week, 18 months job seeker after\n\n<b>Work:</b>\n• Job offer + degree, EU Blue Card €45,300 salary, PR in 21 months with B1 German\n• Skilled worker without degree possible with experience\n"
    elif "work" in q or "job" in q:
        base += "<b>Work Abroad Routes for Nigerians (No Degree to Degree):</b>\n\n• <b>Japan SSW:</b> N4 Japanese + skill test, 14 sectors, no degree, 5 years, ~¥200k/month\n• <b>Poland Work Permit:</b> Type A via agency, 21-55yrs, factory/warehouse, €700-1000\n• <b>Canada LMIA:</b> Employer gets LMIA, you apply work permit, need experience\n• <b>UK Care Worker:</b> Licensed sponsor, IELTS, ₦15-20M total cost, £20k+ salary\n• <b>Germany Chancenkarte:</b> Points - BSc 4pts, 3yrs exp 3pts, age <35 2pts, English B2 1pt\n• <b>UAE:</b> Direct hiring, attestation, no POF\n\n<b>Requirements all:</b> Passport, police, medical, age 21-50, no fake docs!\n"
    else:
        base += "<b>Broad Guidance for Nigerians/Africans Traveling Abroad to Work/Study:</b>\n\n• <b>Choose Route:</b> Study = easier visa + work rights + PR pathway. Work = need job offer/LMIA/CoS\n• <b>POF:</b> 4-6 months history, gradual, explain source (salary/business), add 20% buffer for Naira fluctuation, CBN rate\n• <b>Ties to Home:</b> Family, job, property, business, reason to return\n• <b>Documents:</b> Passport 12 months valid, WAEC/BSc, transcripts, WES for Canada, police, birth cert\n• <b>Where to Apply:</b> VFS Lagos/Abuja, TLS, Embassy Abuja for Japan/Canada/UK/US\n• <b>Build Travel History:</b> Start Dubai, Turkey, SA, Rwanda\n• <b>Avoid:</b> Lump sum, fake docs, agent scam - verify via embassy website\n"
    
    base += "\n💡 <b>Costs from Nigeria 2025 estimate:</b> Visa fee + POF + flight + insurance + agency (if any). Always budget extra ₦2-3M for misc.\n\n✅ <b>Next Steps:</b>\n1. Choose country + route (study/work)\n2. Check admission/job offer\n3. Prepare POF 6 months ahead\n4. Write strong SOP\n5. Apply 3 months before travel\n"
    return base

def ask_ai_with_website_context(question):
    # 1. Search website
    relevant = search_website(question, limit=5)
    website_context = ""
    links_text = ""
    fetched_contents = ""
    
    if relevant:
        links_text = "\n".join([f"• <b>{r['title']}</b>\n{r['link']}" for r in relevant[:3]])
        # Auto-fetch content of top 2 posts for deep context
        for r in relevant[:2]:
            content = fetch_post_content(r['link'], max_chars=3000)
            if content:
                fetched_contents += f"\n\n--- Content from {r['title']} ({r['link']}) ---\n{content[:2500]}\n"
        website_context = "\n".join([f"{i}. {r['title']} - {r['link']}" for i, r in enumerate(relevant, 1)])
    
    # 2. Try Gemini with extensive prompt + website content
    if GEMINI_API_KEY:
        try:
            prompt = f"""{EXTENSIVE_KNOWLEDGE}

WEBSITE SEARCH RESULTS for query "{question}":
{website_context if website_context else "No exact match"}

ACTUAL CONTENT FROM JAPABLUEPRINT.COM.NG POSTS (auto-scanned):
{fetched_contents if fetched_contents else "No content fetched, use general knowledge"}

USER QUESTION (Nigerian/African perspective - wants to travel abroad from Nigeria/Africa to work or study):
{question}

INSTRUCTIONS:
- Answer as ULTRA SMART professional consultant for Nigerians/Africans
- Combine: 1) Your extensive AI brain 2) Actual content scanned from Japablueprint.com.ng above 3) Nigeria-specific context (Naira, Lagos/Abuja application, costs)
- Be VERY detailed: exact POF in foreign currency + Naira equivalent (~), documents, steps, timelines, costs, age limits, family, work rights, PR pathway
- Sweden POF is 103,140 SEK 2025 (approx ₦14-15M)
- Format: Use bold, emojis, bullet points, sections
- Under 500 words but comprehensive
- End with: Related guides from Japablueprint + call to action
- Tone: Expert, encouraging, practical for Nigerian audience, no generic advice
- If question is broad like "how to japa", give roadmap for work vs study routes

Give final professional answer now:
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code==200:
                data = r.json()
                answer = data["candidates"][0]["content"]["parts"][0]["text"]
                # Ensure links included
                if relevant and relevant[0]["link"] not in answer:
                    answer += f"\n\n📚 <b>Related guides from {WEBSITE} (auto-scanned):</b>\n{links_text}\n\n🔗 More: {WEBSITE} - We auto-scanned these posts to answer you!"
                elif not relevant:
                    answer += f"\n\n📚 Full guides: {WEBSITE}/blog/ - Search '{question}'"
                return answer
            else:
                print(f"Gemini error {r.status_code}: {r.text[:800]}", file=sys.stderr)
        except Exception as e:
            print(f"AI error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    # 3. EXTENSIVE FALLBACK if Gemini fails
    fallback = get_extensive_fallback(question)
    if relevant:
        fallback += f"\n\n📚 <b>Auto-scanned from {WEBSITE}:</b>\n{links_text}\n\nWe scanned these posts to give you this answer! Visit {WEBSITE} for full guides."
        if fetched_contents:
            fallback += f"\n\n<i>Tip: Our bot auto-reads post contents to answer you better!</i>"
    else:
        fallback += f"\n\n📚 More detailed guides: {WEBSITE}/blog/ - Search '{question}'"
    return fallback

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
            caption = f"🇯🇵 <b>{p['title']}</b>\n\n{p['desc'][:250]}...\n\n👉 Read: {p['link']}\n\n#Japa #NigeriaToAbroad #Japan #Sweden #Canada #Japablueprint"
            if send_message(CHANNEL_ID, caption):
                posted.append(p["link"])
                json.dump(posted[-100:], open(POSTED_FILE,"w"))
                return f"Posted: {p['title']}"
    return f"Reposted: {posts[0]['title']}"

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    gemini_status = "✅ SET - ULTRA SMART MODE" if GEMINI_API_KEY else "❌ MISSING - Using extensive fallback!"
    return f"Japablueprint Bot ULTRA SMART ✅<br>Gemini: {gemini_status}<br>Features: Auto-scan japablueprint.com.ng posts + Extensive Nigeria->Abroad knowledge<br>Channel: {CHANNEL_ID}<br>Health: <a href='/health'>/health</a><br>Time: {datetime.now()}"

@flask_app.route("/health")
def health():
    return "OK - ULTRA SMART VERSION - Auto-scan + Broad knowledge"

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
            reply = f"🇯🇵 <b>Japablueprint ULTRA SMART AI Online!</b>\n\nI'm your professional Japa consultant for Nigerians & Africans! 🌍\n\n<b>BROAD EXPERTISE:</b>\n• 🇸🇪 Sweden POF 103,140 SEK + family\n• 🇯🇵 Japan: MEXT, Language School, SSW work (no degree), TITP\n• 🇨🇦 Canada: Study, Express Entry, PNP, Caregiver\n• 🇬🇧 UK: Study, Skilled Worker, Care Worker\n• 🇩🇪 Germany: Blocked Account €11,208, Chancenkarte, Blue Card\n• 🇵🇱 Poland, 🇦🇺 Australia, 🇺🇸 USA, Schengen\n• 💼 Work abroad: LMIA, CoS, SSW, TITP\n• 🎓 Study: Scholarships, POF in Naira, SOP\n\n<b>HOW I WORK:</b>\n✅ Extensive AI brain for Nigeria->Abroad\n✅ Auto-scan {WEBSITE} posts content for every answer\n✅ Give Naira equivalent, Lagos/Abuja application points\n✅ Exact 2025 numbers\n\n<b>Ask me ANYTHING:</b>\n• How to Japa from Nigeria to work?\n• Sweden POF in Naira?\n• Japan SSW no degree?\n• Canada Express Entry from Nigeria?\n\n<b>Commands:</b> /latest /search\n📚 {WEBSITE}"
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
                    send_message(chat_id, f"No results for '{query}' on {WEBSITE}\n\nBut ask me directly - I have extensive AI brain for Nigeria->Abroad!")
                else:
                    msg = f"🔍 <b>Search results for '{query}' (auto-scanned):</b>\n\n"
                    for i, r in enumerate(results, 1):
                        msg += f"{i}. <b>{r['title']}</b>\n{r['link']}\n\n"
                    msg += "I auto-scan these posts when answering your questions!"
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
    print(f"Starting ULTRA SMART bot port {port} Gemini: {bool(GEMINI_API_KEY)}", file=sys.stderr)
    flask_app.run(host="0.0.0.0", port=port)
