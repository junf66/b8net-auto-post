import os
import random
import requests
import anthropic
import feedparser
from requests_oauthlib import OAuth1

NOTE_RSS_URL = "https://note.com/affiliate_note/rss"
NOTE_AUTHOR_URL = "https://note.com/affiliate_note"


def fetch_articles():
    feed = feedparser.parse(NOTE_RSS_URL)
    articles = []
    for entry in feed.entries[:10]:
        articles.append({
            "title": entry.title,
            "url": entry.link,
            "summary": entry.get("summary", "")[:300],
        })
    return articles


def generate_tweet(article):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""以下のnote記事を宣伝するXのツイートを1つ生成してください。

記事タイトル: {article['title']}
記事URL: {article['url']}
記事概要: {article['summary']}

条件:
- URL除いて150文字以内
- アフィリエイト・副業・AI活用に興味がある人に響く内容
- 絵文字を適度に使う
- 記事にない新しい切り口・角度でもOK
- URLは必ず末尾に入れる
- ツイート本文のみ出力（説明文不要）"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def post_to_x(text):
    auth = OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )

    response = requests.post(
        "https://api.twitter.com/2/tweets",
        json={"text": text},
        auth=auth,
    )

    if response.status_code == 201:
        data = response.json()
        print(f"投稿成功: tweet_id={data['data']['id']}")
        print(f"内容:\n{text}")
    else:
        raise Exception(f"投稿失敗: {response.status_code} {response.text}")


if __name__ == "__main__":
    articles = fetch_articles()
    if not articles:
        raise Exception("記事が取得できませんでした")

    article = random.choice(articles)
    print(f"選択記事: {article['title']}")

    text = generate_tweet(article)
    post_to_x(text)
