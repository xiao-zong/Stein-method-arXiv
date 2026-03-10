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

# 定义多关键词搜索字典 (Key: 标签名, Value: arXiv 查询语句)
SEARCH_QUERIES = {
    "Stein": 'all:"Stein\'s method" AND (cat:math.PR OR cat:stat.TH)',
    "RandomGraph": 'all:"Random Graph" AND (cat:math.PR OR cat:math.CO)',
    "PointProcess": 'all:"Point processes" AND cat:math.PR',
    "DPP": 'all:"Determinantal Point Process" OR all:"DPP"'
}

def get_ai_summary(title, abstract):
    """使用 Gemini 2.0 Flash 生成中文摘要总结"""
    if not GEMINI_KEY:
        return "（未配置 Gemini API Key，跳过总结）"
    
    prompt = (
        f"你是一位概率论专家。请简要总结以下论文的核心贡献（使用中文，分为3个要点，每点一行，总字数不超过150字）：\n\n"
        f"标题: {title}\n"
        f"摘要: {abstract}"
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "（AI 总结生成失败）"

def get_arxiv_preprints(query_string):
    base_url = 'http://export.arxiv.org/api/query?'
    params = {
        'search_query': query_string,
        'start': 0,
        'max_results': 5, # 每个关键词取最新的 5 篇
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
    
    # 获取 AI 总结
    ai_summary = get_ai_summary(title, abstract)
    
    # 构造 Markdown 格式消息
    message = (f"📚 <b>New #{category_tag} Preprint</b>\n\n"
               f"🔹 <b>Title:</b> {title}\n"
               f"👤 <b>Authors:</b> {authors}\n\n"
               f"💡 <b>AI Summary (CN):</b>\n{ai_summary}\n\n"
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
    # 1. 加载数据库
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            processed_ids = set(f.read().splitlines())
    else:
        processed_ids = set()

    all_new_ids = []

    # 2. 遍历所有关键词进行抓取
    for tag, query in SEARCH_QUERIES.items():
        print(f"Checking category: {tag}...")
        entries = get_arxiv_preprints(query)
        
        # 按时间正序推送
        for entry in reversed(entries):
            paper_id = entry.id.split('/abs/')[-1]
            if paper_id not in processed_ids:
                print(f"New paper in {tag}: {paper_id}")
                send_to_telegram(entry, tag)
                all_new_ids.append(paper_id)
                processed_ids.add(paper_id)
                time.sleep(2) # 稍微延长间隔，避免触发 Telegram/Gemini 频率限制

    # 3. 更新数据库
    if all_new_ids:
        with open(DB_FILE, "a") as f:
            for pid in all_new_ids:
                f.write(pid + "\n")
        print(f"Total added {len(all_new_ids)} new IDs to database.")
    else:
        print("No new preprints across all categories.")
