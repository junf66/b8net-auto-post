import os
import random
import re
import requests
import anthropic
import feedparser
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1

NOTE_RSS_URL = "https://note.com/affiliate_note/rss"
X_USERNAME = "b8_net"
HEADERS = {"User-Agent": "Mozilla/5.0"}


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
        })
    return articles


def fetch_article_body(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        # note.comの本文要素を探す
        body = soup.find("div", class_=re.compile(r"note-common-styles__textnote-body|p-article__body|article-body"))
        if body:
            return body.get_text(separator="\n", strip=True)[:3000]

        # JSON埋め込みから取得を試みる
        scripts = soup.find_all("script", type="application/json")
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                text = json.dumps(data, ensure_ascii=False)
                # bodyテキストを抽出
                match = re.search(r'"body":"(.*?)"(?:,")', text)
                if match:
                    return match.group(1).replace("\\n", "\n")[:3000]
            except Exception:
                continue

        # フォールバック: 全テキストから記事部分を推定
        article_tag = soup.find("article")
        if article_tag:
            return article_tag.get_text(separator="\n", strip=True)[:3000]

        return ""
    except Exception as e:
        print(f"本文取得エラー: {e}")
        return ""


def fetch_past_tweets():
    # ユーザー名からIDを取得
    res = requests.get(
        f"https://api.twitter.com/2/users/by/username/{X_USERNAME}",
        auth=get_oauth(),
    )
    if res.status_code != 200:
        print(f"ユーザーID取得失敗: {res.status_code}")
        return []
    user_id = res.json()["data"]["id"]

    response = requests.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        params={"max_results": 10, "tweet.fields": "text"},
        auth=get_oauth(),
    )
    if response.status_code == 200:
        data = response.json().get("data", [])
        return [t["text"] for t in data]
    print(f"過去ツイート取得失敗: {response.status_code} {response.text[:200]}")
    return []


def generate_tweet(article, body, past_tweets):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style_examples = ""
    if past_tweets:
        examples = "\n".join(f"- {t}" for t in past_tweets[:5])
        style_examples = f"\n\n【文体・言い回しの参考（過去のX投稿）】\n{examples}"

    body_section = f"\n\n【記事本文（抜粋）】\n{body}" if body else ""

    prompt = f"""以下のnote記事を宣伝するXの投稿文を1つ生成してください。

【記事タイトル】{article['title']}{body_section}{style_examples}

【条件】
- 150文字以内
- 絵文字は使わない
- 上記の過去X投稿の文体・言い回しに合わせる
- 記事の具体的な内容・数字・気づきを盛り込む
- URLは入れない
- 投稿文のみ出力（説明文・前置き不要）"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def post_to_x(text, reply_to_id=None):
    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    response = requests.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
        auth=get_oauth(),
    )

    if response.status_code == 201:
        data = response.json()
        tweet_id = data["data"]["id"]
        print(f"投稿成功: tweet_id={tweet_id}")
        print(f"内容:\n{text}")
        return tweet_id
    else:
        raise Exception(f"投稿失敗: {response.status_code} {response.text}")


if __name__ == "__main__":
    articles = fetch_articles()
    if not articles:
        raise Exception("記事が取得できませんでした")

    article = random.choice(articles)
    print(f"選択記事: {article['title']}")

    body = fetch_article_body(article["url"])
    print(f"本文取得: {len(body)}文字")

    past_tweets = fetch_past_tweets()
    print(f"過去ツイート取得数: {len(past_tweets)}")

    # 1個目の投稿
    text = generate_tweet(article, body, past_tweets)
    tweet_id = post_to_x(text)

    # 2個目（ぶらさげ）：URL付き
    reply_text = f"詳しくはnoteで解説してます。\n{article['url']}"
    post_to_x(reply_text, reply_to_id=tweet_id)
