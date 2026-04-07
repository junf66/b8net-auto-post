import os
import random
import requests
from requests_oauthlib import OAuth1

TARGET_URL = "https://note.com/affiliate_note/n/na689ee7abbc9"

TWEETS = [
    f"X APIがついに従量課金に！ツイート投稿1回わずか約1.5円。月3万円→月数百円へ激変。個人開発者に革命が来た🔥\n詳細→ {TARGET_URL}",
    f"2026年2月、X APIが従量課金（pay-as-you-go）に移行。1日10投稿しても月450円程度。ボット開発の参入障壁が劇的に下がった件を徹底解説📖\n{TARGET_URL}",
    f"X API月額200ドル→従量課金へ。使わなければ料金ゼロ。スタートアップや個人開発者にとってゲームチェンジャーな変化を解説🦄\n{TARGET_URL}",
    f"LocalLLM × X API従量課金の組み合わせが最強。AI連携ボットを初期コストほぼゼロで作れる時代が来た。その全貌を解説👇\n{TARGET_URL}",
    f"「X APIが高すぎて諦めた」という人へ。2026年2月から従量課金になり、趣味のボット開発が現実的なコストで可能に。詳細はこちら→ {TARGET_URL}",
    f"X API新料金まとめ\n・投稿取得: 約0.75円/件\n・ツイート投稿: 約1.5円/回\n月200ドル固定から大幅コストダウン。開発者エコシステム復活なるか🔥\n{TARGET_URL}",
    f"ニュースボット・自動投稿・センチメント分析…X API従量課金で個人が作れるサービスの可能性が爆増。具体的な活用法を徹底解説📊\n{TARGET_URL}",
]


def post_to_x():
    text = random.choice(TWEETS)

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

    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {response.text}")

    if response.status_code == 201:
        data = response.json()
        print(f"投稿成功: tweet_id={data['data']['id']}")
        print(f"内容:\n{text}")
    else:
        raise Exception(f"投稿失敗: {response.status_code} {response.text}")


if __name__ == "__main__":
    post_to_x()
