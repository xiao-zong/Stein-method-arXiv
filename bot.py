import feedparser
import requests
import os
import time

# 从环境变量读取 Secrets
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 搜索关键词：针对 Stein's method 优化
SEARCH_QUERY = 'all:"Stein\'s method" AND (cat:math.PR OR cat:stat.TH)'

def get_arxiv_preprints():
    base_url = 'http://export.arxiv.org/api/query?'
    # 每次抓取最新的 5 篇
    params = f'search_query={SEARCH_QUERY}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending'
    feed = feedparser.parse(base_url + params)
    return feed.entries

def send_to_telegram(entry):
    title = entry.title.replace('\n', ' ')
    authors = ", ".join([a.name for a in entry.authors])
    link = entry.link
    
    # 构造 Markdown 格式消息
    message = (f"📑 *New Stein's Method Preprint*\n\n"
               f"🔹 *Title*: {title}\n"
               f"👤 *Authors*: {authors}\n\n"
               f"🔗 [arXiv Link]({link})")
              
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    entries = get_arxiv_preprints()
    for entry in reversed(entries): # 按时间正序推送
        send_to_telegram(entry)
        time.sleep(1) # 避免触发 API 频率限制
