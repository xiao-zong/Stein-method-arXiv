import feedparser
import requests
import os
import time
import urllib.parse

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
DB_FILE = "processed_ids.txt"  # 存储已推送 ID 的文件

SEARCH_QUERY = 'all:"Stein\'s method" AND (cat:math.PR OR cat:stat.TH)'

def get_arxiv_preprints():
    base_url = 'http://export.arxiv.org/api/query?'
    params = {
        'search_query': SEARCH_QUERY,
        'start': 0,
        'max_results': 10, # 稍微多取几篇确保不遗漏
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    encoded_params = urllib.parse.urlencode(params)
    feed = feedparser.parse(base_url + encoded_params)
    return feed.entries

def send_to_telegram(entry):
    title = entry.title.replace('\n', ' ').strip()
    authors = ", ".join([a.name for a in entry.authors])
    link = entry.link
    
    message = (f"📚 <b>New Stein's Method Preprint</b>\n\n"
               f"<b>Title:</b> {title}\n"
               f"<b>Authors:</b> {authors}\n\n"
               f"🔗 <a href='{link}'>View on arXiv</a>")
              
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    # 1. 加载已处理的 ID
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            processed_ids = set(f.read().splitlines())
    else:
        processed_ids = set()

    entries = get_arxiv_preprints()
    new_ids = []

    # 2. 过滤并推送
    # arXiv 的 entries 是按时间倒序排列的，我们反转它，按时间顺序推送
    for entry in reversed(entries):
        paper_id = entry.id.split('/abs/')[-1] # 提取唯一 ID
        if paper_id not in processed_ids:
            print(f"New paper found: {paper_id}")
            send_to_telegram(entry)
            new_ids.append(paper_id)
            processed_ids.add(paper_id)
            time.sleep(1)

    # 3. 将新 ID 写入文件（供 GitHub Action 提交回仓库）
    if new_ids:
        with open(DB_FILE, "a") as f:
            for pid in new_ids:
                f.write(pid + "\n")
        print(f"Added {len(new_ids)} new IDs to database.")
    else:
        print("No new preprints to push.")
