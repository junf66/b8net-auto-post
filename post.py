import os
import random
import requests
import tweepy
from bs4 import BeautifulSoup

NOTE_URL = "https://note.com/affiliate_note"
TARGET_URL = "https://note.com/affiliate_note/n/na689ee7abbc9"

TEMPLATES = [
    "💡 {title}\n\n{excerpt}\n\n👇 詳しくはこちら\n{url}",
    "📢 {title}\n\n{excerpt}\n\n✅ {url}",
    "🔥 {title}\n\n{excerpt}\n\n詳細→ {url}",
]


def fetch_note_content():
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(NOTE_URL, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    # タイトル取得
    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"] if title_tag else "アフィリエイト攻略note"

    # ディスクリプション取得
    desc_tag = soup.find("meta", property="og:description")
    desc = desc_tag["content"] if desc_tag else ""

    # 150文字以内に収める（URLの分を引く）
    max_len = 150 - len(TARGET_URL) - 10
    if len(desc) > max_len:
        desc = desc[:max_len] + "…"

    return title, desc


def post_to_x(title, excerpt):
    template = random.choice(TEMPLATES)
    text = template.format(title=title, excerpt=excerpt, url=TARGET_URL)

    # Xの280文字制限チェック
    if len(text) > 280:
        text = text[:279]

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )

    # 認証確認
    me = client.get_me()
    print(f"認証OK: @{me.data.username}")

    response = client.create_tweet(text=text)
    print(f"投稿成功: tweet_id={response.data['id']}")
    print(f"内容:\n{text}")


if __name__ == "__main__":
    title, excerpt = fetch_note_content()
    post_to_x(title, excerpt)
