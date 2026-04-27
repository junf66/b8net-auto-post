import os
import json
import random
import re
import time
import requests
import anthropic
import feedparser
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1
from datetime import datetime

NOTE_RSS_URL = "https://note.com/affiliate_note/rss"
X_USERNAME = "b8_net"
HEADERS = {"User-Agent": "Mozilla/5.0"}
X_API_HEADERS = {
    "User-Agent": "b8net-auto-post/1.0",
    "Accept": "application/json",
}
POSTED_LOG = "posted_urls.json"

EXCLUDE_URLS = [
    "https://note.com/affiliate_note/n/ne273e4374d27",
]


# ── 環境変数チェック ──────────────────────────────────────
def check_required_env():
    required = [
        "X_API_KEY", "X_API_SECRET",
        "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET",
        "ANTHROPIC_API_KEY",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"必須環境変数が未設定: {', '.join(missing)}")


# ── OAuth ─────────────────────────────────────────────────
def get_oauth():
    return OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def is_cloudflare_block(response):
    return (response.status_code == 403
            and "text/html" in response.headers.get("content-type", "")
            and "cloudflare" in response.text.lower())


def x_api_request(method, url, max_retries=3, **kwargs):
    kwargs.setdefault("headers", {}).update(X_API_HEADERS)
    kwargs["auth"] = get_oauth()
    for attempt in range(max_retries + 1):
        response = requests.request(method, url, **kwargs)
        if not is_cloudflare_block(response):
            return response
        wait = 2 ** attempt * 5  # 5s, 10s, 20s, 40s
        print(f"Cloudflare ブロック検知 (試行{attempt+1}/{max_retries+1})。{wait}秒待機...")
        time.sleep(wait)
    print("Cloudflare ブロック: 全リトライ失敗")
    return response


# ── 投稿済みURL管理 ───────────────────────────────────────
def load_posted_urls():
    if os.path.exists(POSTED_LOG):
        try:
            with open(POSTED_LOG, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_posted_url(url):
    entries = load_posted_urls()
    entries.append({"url": url, "posted_at": datetime.now().isoformat()})
    entries = entries[-100:]  # 直近100件だけ保持
    with open(POSTED_LOG, "w") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# ── 文字数チェック ────────────────────────────────────────
# X の加重文字カウント（CJK・ひらがな・カタカナ・ハングル等は2単位、それ以外は1単位、上限280）
# 参考: https://developer.x.com/en/docs/counting-characters
_WEIGHT2_RANGES = [
    (0x1100, 0x115F),
    (0x2E80, 0x303E),
    (0x3041, 0x33FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xA000, 0xA4CF),
    (0xAC00, 0xD7A3),
    (0xF900, 0xFAFF),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFF60),
    (0xFFE0, 0xFFE6),
]


def x_weighted_length(text):
    total = 0
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _WEIGHT2_RANGES):
            total += 2
        else:
            total += 1
    return total


def check_tweet_length(text, label="ツイート"):
    weighted = x_weighted_length(text)
    if weighted > 280:
        raise ValueError(
            f"{label}が文字数制限超過: 加重{weighted}単位 / {len(text)}文字 (上限280)"
        )


def trim_to_weighted_limit(text, limit=280):
    """加重文字数が limit を超えないように末尾を削る"""
    if x_weighted_length(text) <= limit:
        return text
    out = []
    total = 0
    for ch in text:
        cp = ord(ch)
        w = 2 if any(lo <= cp <= hi for lo, hi in _WEIGHT2_RANGES) else 1
        if total + w > limit:
            break
        out.append(ch)
        total += w
    return "".join(out)


# ── 記事取得 ──────────────────────────────────────────────
def fetch_articles():
    feed = feedparser.parse(NOTE_RSS_URL)
    articles = []
    for entry in feed.entries:
        if entry.link not in EXCLUDE_URLS:
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
                data = json.loads(script.string)
                text = json.dumps(data, ensure_ascii=False)
                match = re.search(r'"body":"(.*?)"(?:,")', text)
                if match:
                    return match.group(1).replace("\\n", "\n")[:3000]
            except Exception:
                continue

        # フォールバック
        article_tag = soup.find("article")
        if article_tag:
            return article_tag.get_text(separator="\n", strip=True)[:3000]

        return ""
    except Exception as e:
        print(f"本文取得エラー: {e}")
        return ""


# ── 過去ツイート取得 ──────────────────────────────────────
def fetch_past_tweets():
    res = x_api_request(
        "GET",
        f"https://api.twitter.com/2/users/by/username/{X_USERNAME}",
    )
    if res.status_code != 200:
        print(f"ユーザーID取得失敗: {res.status_code}")
        return []
    user_id = res.json().get("data", {}).get("id")
    if not user_id:
        print("ユーザーIDが取得できませんでした")
        return []

    response = x_api_request(
        "GET",
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        params={"max_results": 10, "tweet.fields": "text"},
    )
    if response.status_code == 200:
        data = response.json().get("data", [])
        return [t["text"] for t in data]
    print(f"過去ツイート取得失敗: {response.status_code} {response.text[:200]}")
    return []


# ── ツイート生成 ──────────────────────────────────────────
def generate_note_tweet(article, body, past_tweets):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style_examples = ""
    if past_tweets:
        examples = "\n".join(f"- {t}" for t in past_tweets[:5])
        style_examples = f"\n\n【文体・言い回しの参考（過去のX投稿）】\n{examples}"

    body_section = f"\n\n【記事本文（抜粋）】\n{body}" if body else ""

    prompt = f"""以下のnote記事を参考に、Xの投稿文を1つ生成してください。

【記事タイトル】{article['title']}{body_section}{style_examples}

【条件】
- 125文字以内（日本語は1文字=2単位で計算されるため厳守）
- 「詳しくは↓」は含めない（自動付与するため）
- 絵文字は使わない
- 上記の過去X投稿の文体・言い回しに合わせる
- 記事の内容を参考にしつつ、同じテーマ・文脈で新規の視点や気づきを生成してもOK
- 記事の引用だけに縛られず、アフィリエイト・SEO・副業・AI活用に関連する有益な内容であれば自由に展開してよい
- URLは入れない
- 投稿文のみ出力（説明文・前置き不要）
- 「SEOの常識が変わった」「常識が変わった」のような使い古されたフレーズは使わない
- 毎回異なる切り口・書き出しにする（体験談・数字・問いかけ・逆説・具体例など）
- 「解説」「まとめ」「紹介」など、どこかで詳しく説明しているかのような言い回しは使わない（URLは投稿に含まれないため）
- 最後に「〜な時代。」「〜が重要。」「〜を意識する時代。」のようなまとめ・締めの一文を付けない。核心情報を述べたらそこで終わる"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_seo_tweet(past_tweets):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style_examples = ""
    if past_tweets:
        examples = "\n".join(f"- {t}" for t in past_tweets[:5])
        style_examples = f"\n\n【文体・言い回しの参考（過去のX投稿）】\n{examples}"

    prompt = f"""SEO・アフィリエイト・副業・AI活用に関する短い投稿文を1つ生成してください。{style_examples}

【条件】
- 100文字以内
- 絵文字は使わない
- 上記の過去X投稿の文体・言い回しに合わせる
- 検索・コンテンツ・収益化に関する実践的な知見や気づきを簡潔に
- URLは入れない
- 投稿文のみ出力（説明文・前置き不要）
- 「SEOの常識が変わった」「常識が変わった」のような使い古されたフレーズは使わない
- 毎回異なる切り口・書き出しにする（体験談・数字・問いかけ・逆説・具体例など）"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ── X投稿 ─────────────────────────────────────────────────
def post_to_x(text, reply_to_id=None):
    check_tweet_length(text)

    payload = {"text": text}
    if reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

    response = x_api_request(
        "POST",
        "https://api.twitter.com/2/tweets",
        max_retries=4,
        json=payload,
    )

    if response.status_code == 201:
        data = response.json()
        tweet_id = data["data"]["id"]
        print(f"投稿成功: tweet_id={tweet_id}")
        print(f"内容:\n{text}")
        return tweet_id
    else:
        raise Exception(f"投稿失敗: {response.status_code} {response.text[:500]}")


# ── メイン ────────────────────────────────────────────────
if __name__ == "__main__":
    check_required_env()

    post_type = os.environ.get("POST_TYPE", "note")
    print(f"投稿タイプ: {post_type}")

    past_tweets = fetch_past_tweets()
    print(f"過去ツイート取得数: {len(past_tweets)}")

    if post_type == "seo":
        # SEO短文投稿（ぶら下げなし）
        text = generate_seo_tweet(past_tweets)
        text = trim_to_weighted_limit(text, 280)
        post_to_x(text)

    else:
        # note記事引用投稿
        articles = fetch_articles()
        if not articles:
            raise Exception("記事が取得できませんでした")

        # 重複投稿防止：未投稿記事を優先選択
        posted_urls = {e["url"] for e in load_posted_urls()}
        unposted = [a for a in articles if a["url"] not in posted_urls]
        if not unposted:
            print("全記事投稿済み。リセットして再利用します。")
            unposted = articles

        article = random.choice(unposted)
        print(f"選択記事: {article['title']}")

        body = fetch_article_body(article["url"])
        print(f"本文取得: {len(body)}文字")

        text = generate_note_tweet(article, body, past_tweets)
        text = re.sub(r"\n?詳しくは↓\s*$", "", text).rstrip()
        suffix = "\n詳しくは↓"
        # suffix を含めて280加重単位に収まるよう本文を必要分だけ削る
        body_limit = 280 - x_weighted_length(suffix)
        text = trim_to_weighted_limit(text, body_limit) + suffix
        tweet_id = post_to_x(text)

        # 投稿済みURLを記録
        save_posted_url(article["url"])

        # リプライ投稿（失敗してもメイン投稿は維持）
        reply_text = f"詳しくはnoteでまとめてます。\n{article['url']}"
        try:
            post_to_x(reply_text, reply_to_id=tweet_id)
        except Exception as e:
            print(f"リプライ投稿失敗（メイン投稿は成功済み）: {e}")
