import feedparser
import requests
import os
import time
import urllib.parse  # 新增：用于处理 URL 编码

# 从环境变量读取 Secrets
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 搜索关键词：针对 Stein's method 优化
SEARCH_QUERY = 'all:"Stein\'s method" AND (cat:math.PR OR cat:stat.TH)'

def get_arxiv_preprints():
    base_url = 'http://export.arxiv.org/api/query?'
    
    # 将参数放入字典中，方便自动进行 URL 编码
    query_params = {
        'search_query': SEARCH_QUERY,
        'start': 0,
        'max_results': 5,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    
    # 使用 urlencode 自动处理空格 (变成 + 或 %20) 和特殊字符
    encoded_params = urllib.parse.urlencode(query_params)
    full_url = base_url + encoded_params
    
    # 在日志中打印最终生成的 URL，方便调试
    print(f"Requesting arXiv API: {full_url}")
    
    feed = feedparser.parse(full_url)
    return feed.entries

def send_to_telegram(entry):
    # 清理标题中的换行符，防止 Markdown 格式失效
    title = entry.title.replace('\n', ' ').strip()
    authors = ", ".join([a.name for a in entry.authors])
    link = entry.link
    
    # 构造 Markdown 格式消息
    # 提示：如果标题里包含特殊字符，Markdown 可能会解析失败，这里用了基础格式
    message = (f"📑 *New Stein's Method Preprint*\n\n"
               f"🔹 *Title*: {title}\n"
               f"👤 *Authors*: {authors}\n\n"
               f"🔗 [arXiv Link]({link})")
              
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": False  # 允许显示文章预览图
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Error sending to Telegram: {response.text}")

if __name__ == "__main__":
    # 确保 Token 和 ID 存在
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment.")
    else:
        entries = get_arxiv_preprints()
        if not entries:
            print("No new preprints found or API error.")
        
        for entry in reversed(entries): # 按时间正序推送
            send_to_telegram(entry)
            time.sleep(1) # 避免触发 Telegram API 频率限制
