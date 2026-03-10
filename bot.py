import feedparser
import requests
import os
import time
import urllib.parse
import google.generativeai as genai

# --- 配置区 ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
DB_FILE = "processed_ids.txt"

# 配置 Gemini 2.0 Flash
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

# 定义多关键词搜索字典
SEARCH_QUERIES = {
    "Stein": 'all:"Stein\'s method" AND (cat:math.PR OR cat:stat.TH)',
    "RandomGraph": 'all:"Random Graph" AND (cat:math.PR OR cat:math.CO)',
    "PointProcess": 'all:"Point processes" AND cat:math.PR',
    "DPP": 'all:"Determinantal Point Process" OR all:"DPP"'
}

def get_ai_summary(title, abstract):
    """Generate professional English research insights using Gemini 2.0 Flash"""
    if not GEMINI_KEY:
        return "(Gemini API Key missing)"
    
    prompt = (
        f"You are an expert in Probability Theory and Stochastic Processes. "
        f"Provide a concise summary of this paper's key contributions in 3 bullet points (English). "
        f"Focus on the novelty and mathematical tools used. Max 150 words.\n\n"
        f"Title: {title}\n"
        f"Abstract: {abstract}"
    )
    
    try:
        # 核心修复：增加安全设置防止误拦截
        response = model.generate_content(
            prompt,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        if response.text:
            return response.text.strip()
        else:
            return "(AI returned an empty response. Check abstract length or safety filters.)"
    except Exception as e:
        # 打印错误到日志，方便排查
        print(f"Gemini API Error: {e}")
        return f"(AI Summary failed: {type(e).__name__})"

def get_arxiv_preprints(query_string):
    base_url = 'http://export.arxiv.org/api/query?'
    params = {
        'search_query': query_string,
        'start': 0,
        'max_results': 5,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    encoded_params = urllib.parse.urlencode(params)
    feed = feedparser.parse(base_url + encoded_params)
    return feed.entries

def send_to_telegram(entry, category_tag):
    title = entry.title.replace('\n', ' ').strip()
    authors = ", ".join([a.name for a in entry.authors])
    link = entry.link
    abstract = entry.summary
    
    # 获取英文 AI 总结
    ai_summary = get_ai_summary(title, abstract)
    
    # 消息模板更新
    message = (f"📚 <b>New #{category_tag} Preprint</b>\n\n"
               f"🔹 <b>Title:</b> {title}\n"
               f"👤 <b>Authors:</b> {authors}\n\n"
               f"💡 <b>AI Research Insights:</b>\n{ai_summary}\n\n"
               f"🔗 <a href='{link}'>View on arXiv</a>")
              
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": message, 
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram Send Error: {e}")

if __name__ == "__main__":
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            processed_ids = set(f.read().splitlines())
    else:
        processed_ids = set()

    all_new_ids = []

    for tag, query in SEARCH_QUERIES.items():
        print(f"Checking category: {tag}...")
        entries = get_arxiv_preprints(query)
        
        for entry in reversed(entries):
            paper_id = entry.id.split('/abs/')[-1]
            if paper_id not in processed_ids:
                print(f"New paper in {tag}: {paper_id}")
                send_to_telegram(entry, tag)
                all_new_ids.append(paper_id)
                processed_ids.add(paper_id)
                time.sleep(2) # 保护频率

    if all_new_ids:
        with open(DB_FILE, "a") as f:
            for pid in all_new_ids:
                f.write(pid + "\n")
        print(f"Total added {len(all_new_ids)} new IDs to database.")
    else:
        print("No new preprints found.")
