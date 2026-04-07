import os
import random
import requests
import anthropic
import feedparser
from requests_oauthlib import OAuth1

NOTE_RSS_URL = "https://note.com/affiliate_note/rss"
NOTE_AUTHOR_URL = "https://note.com/affiliate_note"
X_USER_ID = "2041342368746790912"


def get_oauth():
    return OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def fetch_articles():
    feed = feedparser.parse(NOTE_RSS_URL)
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": entry.title,
            "url": entry.link,
            "summary": entry.get("summary", "")[:300],
        })
    return articles


def fetch_past_tweets():
    response = requests.get(
        f"https://api.twitter.com/2/users/{X_USER_ID}/tweets",
        params={"max_results": 10, "tweet.fields": "text"},
        auth=get_oauth(),
    )
    if response.status_code == 200:
        data = response.json().get("data", [])
        return [t["text"] for t in data]
    print(f"過去ツイート取得失敗: {response.status_code} {response.text}")
    return []


def generate_tweet(article, past_tweets, include_url):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style_examples = ""
    if past_tweets:
        examples = "\n".join(f"- {t}" for t in past_tweets[:5])
        style_examples = f"\n\n【文体・言い回しの参考（過去の投稿）】\n{examples}"

    url_instruction = (
        f"末尾に必ず以下のURLを入れる: {article['url']}"
        if include_url
        else "URLは入れない"
    )

    prompt = f"""以下のnote記事を宣伝するXの投稿文を1つ生成してください。

【記事タイトル】{article['title']}
【記事概要】{article['summary']}{style_examples}

【条件】
- 150文字以内（URL含まず）
- 絵文字は使わない
- 上記の過去投稿の文体・言い回しに合わせる
- 記事にない新しい切り口・角度でもOK
- {url_instruction}
- 投稿文のみ出力（説明文・前置き不要）"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def post_to_x(text):
    response = requests.post(
        "https://api.twitter.com/2/tweets",
        json={"text": text},
        auth=get_oauth(),
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

    past_tweets = fetch_past_tweets()
    print(f"過去ツイート取得数: {len(past_tweets)}")

    include_url = random.random() < 1 / 3
    print(f"URL含む: {include_url}")

    text = generate_tweet(article, past_tweets, include_url)
    post_to_x(text)
