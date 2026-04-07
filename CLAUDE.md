# b8net-auto-post

## 目的
有料note記事（https://note.com/affiliate_note）の販売促進のため、X（@b8_net）に自動投稿するBotです。

## 構成
- **実行環境**: GitHub Actions
- **言語**: Python 3.11
- **投稿スケジュール**: 毎日 10:19 / 22:38 JST（2回）

## 動作フロー
1. note.com のRSSから記事一覧を取得
2. ランダムに1記事を選択し、本文をスクレイピング（無料記事のみ全文取得可能）
3. X API（@b8_net）から過去ツイートを取得して文体参考にする
4. Claude API（claude-haiku-4-5-20251001）でツイート生成
5. 1個目の投稿（150文字以内、URLなし）
6. 1個目へのリプライとして2個目を投稿（「詳しくはnoteで解説してます。\n{URL}」）

## ツイート生成のルール
- 150文字以内
- 絵文字なし
- @b8_netの過去X投稿の文体・言い回しに合わせる
- note記事を参考にしつつ、同テーマ（アフィリエイト・SEO・副業・AI活用）で新規生成もOK
- 「SEOの常識が変わった」等の使い古しフレーズは禁止
- 毎回異なる切り口（体験談・数字・問いかけ・逆説・具体例など）

## GitHub Secrets（必須）
| 名前 | 用途 |
|------|------|
| `X_API_KEY` | X API Key |
| `X_API_SECRET` | X API Key Secret |
| `X_ACCESS_TOKEN` | X Access Token |
| `X_ACCESS_TOKEN_SECRET` | X Access Token Secret |
| `ANTHROPIC_API_KEY` | Claude API Key |

## 外部サービスの課金状況
- **X API**: Pay Per Use（$5クレジット購入済み）
- **Anthropic API**: 従量課金（$5クレジット購入済み）

## リプライ・DMの対応
手動対応。Xのスマホ通知をONにして対応する。

## ファイル構成
```
.github/workflows/post.yml  # GitHub Actionsワークフロー
post.py                     # メインスクリプト
CLAUDE.md                   # このファイル
```
