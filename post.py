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
TWEET_LOG = "posted_tweets.json"

STYLE_SAMPLES = [
    "AIが得意な「情報整理」と人間が得意な「意図理解」、これを組み合わせるのが最強。AIで下書き100記事作るより、検索意図を徹底分析した10記事の方が確実に稼げますね。",
    "AIで大量記事生成してるアフィサイト、実はPVは増えるんだけど成約率ガタ落ちする傾向あります。理由は単純、ユーザーの検索意図を無視してるから。量より精度、これに尽きますね。",
    "claude codeアプリ、これまで画像しか添付できなかったけど、画像以外のデータも添付できるようになった。これかなり便利、地味だけど。",
    "リライトのたびにフェッチ叩く癖、実は危険信号かもしれません。アフィサイトの場合、毎回のフェッチはGoogleから「対策しすぎ」と判断される可能性がある。公開時の1回だけで十分。あとはサイトマップ送ってればクローラーは自然に回ってきます。",
    "アフィリエイトサイトで成約率が低い時、ほとんどの人は記事数を増やすことだけ考えてます。でも実際は、既存記事の購買意欲層への内部リンク導線が甘いだけ。質より導線、これが意外と効きますよ。",
    "新規ドメインから新規ドメインへの載せ替え、知ってますか？狙ってるキーワードをドメイン名に含めるだけで、Googleからの評価が変わることがある。専門性の判断材料になるんですね。何やっても上がらない特化サイトなら、最後の一手として試す価値ある。費用は1000円程度だし。",
    "AIで記事を自動生成してる人、内部リンク構造まで考えてますか？質の高いコンテンツでも、ページ同士の繋がりが弱いとSEO効果が半減する。戦略的な内部リンクこそが、AIコンテンツを活かす鍵ですよ。",
    "狙ってたキーワードなのに順位が上がらない？もしかしてカニバリ起きてるかも。複数ページが同じキーワードでランクインしてると、Googleの評価が分散して、どのページも浮上しない。GRCのランクインページ機能で日々チェック。同じキーワードなのに異なるURLが出てたら要注意だ。",
    "企業ドメ重視のアルゴのせいなのか、６位くらいに落ちてCV激減、、一時的？テコ入れしていい？SEO野郎と判定されるから時期尚早？",
    "AI記事の順位が上がらない？実は生成AIの出力をそのまま使ってる可能性が高い。Googleは検索意図への「応え方の工夫」を見てる。同じ情報でも、読者視点での整理や具体例の追加で評価が変わる。AIは下地作り、勝負は人間の編集力だ。",
    "コンテンツ制作の優先度で迷ってる？実は狙うキーワードをGoogleで検索して、検索結果の「並び順」を見るだけで答えが出る。ショッピング枠が上なら価格重視、画像が上なら見た目重視。Googleは何兆クリックのデータで判断してるから、理論より実データが勝つ。",
    "アフィリエイト記事で成約率が低い？実は商品紹介の前に、読者の悩み解決パートを厚くするだけで改善することが多い。売上を急ぐと逆効果だ。信頼が先で、販売は後。地味だが確実な方法。",
    "監修サービスで見つけた専門家に、そのまま依頼してない？実は直依頼すると、中間コスト減で単価が3～5割下がることもある。同じ専門家が監修するから品質も変わらず、やり取りも早い。フルネーム検索→公式HPで連絡、これだけで十分だ。",
    "AIで外注した記事、タイトルと見出しだけ手直しすると検索順位が2～3段階上がる。本文の大幅修正より、検索意図に合わせた構成の最適化の方が費用対効果が高い。地味だが、再現性がある施策だ。",
    "競合が中古ドメインなら、コンテンツで勝つより被リンクを削る方が早い。リンク元に「このリンク、今はアフィサイトに飛びますよ」と1通送るだけで、相手のドメインパワーが削れる。地味だが、合法的で穏便な対抗策だ。",
    "AIで生成した記事、そのままだと平均CTR40%。手直し加えると65%まで上がった。検索意図への微調整って地味だけど、収益化する上で無視できない差になるんだな。",
    "AIで記事の初稿作成して、そのまま公開するより手直しして公開した方がCTR上がるの気づいた。検索意図との微調整って地味だけど効くんだな。数記事試したらクリック数で差が出てきた。",
    "営業メールに返信するたびにダイレクトアクセス増やせるの知ってた？定型文でURL送るだけで、新規UUも滞在時間も地味に伸びるらしい。数ヶ月続けたらGAで変化出てくるって。うざいメールが資産になる感覚、面白い。",
    "Google完全オワコンになるまで、SEO粘らせてもらうわ。なんとか隙間見つけて、なんとかハック的なこと見つけて、なんとかなんとかする。",
    "SEOやってます！なサイトをGoogleが嫌ってるのがわかる。",
    "今でもペラとか含めて数十サイトGRC回してるんだけど、放置サイトが良さげな動き。頑張っていじってるのほど落とされてる。",
    "稼げるクエリだと個人ブログ皆無じゃない？たしかに趣味領域などはそうなのかもしれないけど。\n\n上位表示したくてアフィやってるんじゃない。稼ぎたいんだ。",
    "アタオカSEO、普通に気付きがあるな。上位に出てきてたアタオカについての見解、有料noteも購入させて頂きました。",
    "このタイミングで、急に中古とか元気玉リダイレクトでごぼう抜きしてくるサイトはおらんかの～？アタオカSEO。",
    "SEOのために社団法人立ち上げるくらいのガッツ必要だね、この感じ。SNSが～EEATが～被リンクが～コンテンツが～というレベルでは差がつかないからGoogleも困っていて、そこまでやればフィルター抜けて上行きやすいんじゃないかな。",
    "新規ドメのペラサイトがあがってるクエリあるんだけど特化うんぬんとかじゃなくて、内部リンクのあらゆる問題を勝手に回避してたから、って仮説がいま俺の中で出てきた。",
    "AIモード完全移行→稼げるアフィクエリ駆逐される→月500万円とか数千万円稼ぐ道が閉ざされる→大手企業（大手サブディレ）撤退→謎に個人メディアは撤退しない→粘り続けた個人だけ生き残る\n\nって未来あるかもよ。1サイト20万円でも十分だよね？個人なら。そういうのをひっそりこっそり増やしてく。",
    "上がったサイトがある、そして下がったサイトがある。相殺しても売上ダメージはある、、Googleウゴウゴ",
    "お宝キーワードの見つけ方③  \n\n2chまとめサイトにヒントあり。VIPPER速報とか。ネットスラングという表には出てこない独特なキーワード、略語を探すのです。特に出会いやエンタメ系の案件に繋げられそうなモノが多いです。大手サブディレも知らない、知っててもスラング狙いはできないので穴場。",
    "落ちたサイトと上位キープしてるサイトの違いがひとつある。アレかなー、アレ。",
    "ひとつ2ページ目に追いやられたのある。まだ静観。",
    "順位変わらないのにとても売上悪いよ。AI枠は前からずっと出てたしな。",
    "お宝キーワードの見つけ方②\n\nLPを見まくってください。アフィリエイターが作った記事LPではなく、案件LPです。時々、馴染みのない「造語のようなキーワード」があり、その中からアフィに繋がりそうなものに遭遇することがあります。簡単には見つからないですが、レアだからこそ競合がいないのです。",
    "エイチレフスのタグが外れてただけかも疑惑。次の監視クローリングでもとに戻る、、はず！",
    "お宝キーワードの見つけ方①\n\nTwitter内の「トレンド」をチェックしてると、見たことないキーワードが出てくることがあります。それを1つずつ調べるのです。繰り返し調べていくと50個に1個くらい、アフィに繋げられそうなものに遭遇します。言葉は生き物なので、日々新しいキーワードが誕生してます。",
    "まあそんな最初のサイトになれるのなんて、1年リサーチし続けてやっと1個誕生させられるかどうかだよね",
    "やっぱそのKWで最初のサイトになる、最初にインデックスされって大事やな。後発がいくら頑張ってもそこだけは抜けないし。",
    "順位いいパターン\n悪いパターン\nの2種類がここ最近サープスにあるんたけど、悪い方の出現頻度が高くなってる。頼むよ",
    "しばらくやることなかったんだけど、本読んだらやること無数に出てきて急に忙しくなってきた。波ありすぎ。アフィあるある。",
    "手打ちしたら嫌なパターン見た。いつも3位の位置にいる大事なKWが8位くらいにいた。抜いてきたのはアフィ掲載してる案件のオウンド。\n\n今見たらいつものに戻ってたけど、これはそろそろ覚悟しておくべきか。",
    "2年くらいノーメンテの記事、しかも商標+口コミの記事が復活して売上出始めている。謎。明日分析や。",
    "アフィリエイトはオワコン\nと言われてからが勝負。",
    "ahrefs（エイチレフス）、ちょっと前まではセムラッシュなどと対等かちょい下にいたようなイメージだけど、ここ2年くらいで頭ひとつ抜けた感ある。日本法人の中の人が積極的に発信、コラボなどしているのはでかい。",
    "旧ファビコンの時は3位\n新の時は1位\n\nみたいに順位もセット。",
    "ファビコン3週間くらい前変えたサイトあるんだけど、タイミングによって新旧どっちかのファビコンが出る。サープスが2つ以上ある、ロールバックなのか？とりあえず不安定で、アプデ予兆なのかも。",
    "使ってるSEOツール\n・GRC\n・エイチレフス\n・ウェイバックマシーン\n\n羅列しようと思ったらこんなんだったわ、あれ？",
    "簡単な自己紹介。SEOメイン、いわゆるブラック的なこともやってる。ブラックって死語？サブディレは検討したこともありますが、条件合わず白紙。基本、独自ドメでひっそりやっとります。",
    "AIコンテンツ増加で、逆に「運営者の顔出し・経歴公開」がE-E-A-Tの判断材料になってきた感。匿名性高いほどコンテンツの信頼度上げるハードル上がってる印象。",
    "AIコンテンツでも上位取れてる記事見ると、共通点が「公式情報より詳しい一次情報」入ってる。生成系の強みじゃなくて、情報量勝負になってきた感じ。",
    "中古ドメイン競合、コンテンツ勝負では勝てないなら被リンク見直して。リンク元に「このリンク、記事と関係なくなってますよ」と連絡するだけで、相手のドメインパワー削られる可能性ある。地味だけど案外効く。",
    "AIで記事生成→インデックスされない→手動ペナルティかと思ったら、単に品質が低くて埋もれてただけなんですよね。生成ツールは時短になるけど、Googleが評価する「体験」までは作れない。ここの線引き甘く見てました。",
    "「ビヨウ 効果」で上位狙ってるのに、解約方法まで網羅してたら、Googleには「なんのページなんだ」って思われてる。削るが怖いなら見出しレベルを下げる。ノイズを弱めるだけで順位がじわじわ変わる。",
    "今朝見たら収益柱のひとつの大事なクエリが3→12位くらいになってた。note書いてる場合じゃなかった、、",
    "新規ドメインを取った。Waybackでもahrefsでも使用歴なし。完全な新規のはず。でもアカウント凍結。原因は過去の持ち主による「メールスパム」。サイトの履歴だけ見ても、メールの履歴は見えない。30サイト消えた実体験",
    "アフィリエイトサイトで成約率が低いなら、商品ページへの導線を疑え。検索ユーザーが「比較したい」段階なのに、いきなり購入ボタン押させてないか。Googleの検索結果順位が教えてくれる。上位サイトの構成がそのまま「正解の道筋」だ。",
    "特化サイトなのに順位が上がらない。そんときドメイン名を狙いキーワード入りに変えるだけで、Googleからの評価がわかることがある。新規→新規ドメインへの載せ替えは費用1000円前後。上位独占されてて何やってもダメなら、ドメインの「顔」を変えて再スタートするのも戦略。",
    "AIツール使ってコンテンツ生成してる人、出力後に必ずシークレット検索で競合確認してる？生成物がそのまま記事になってる人ほど、検索順位が伸びない傾向。AIは平均値を出すから、Googleが求める「上位10位の共通点+α」を足さないと埋もれる。差分を作る作業がSEOの本質。",
    "コンテンツ企画で悩んだら、そのキーワードをシークレット検索してみろ。Googleの検索結果に出てくる順番がそのまま「何を重視すべきか」の優先度。ショッピング枠が最初なら価格重視、画像が上位なら見た目重視。何兆クリックのデータに基づいた回答が画面に映ってる。",
    "記事監修サービスで見つけた専門家に、サービス経由ではなく直接依頼するとコスト半減することがある。中間マージンが消えるから。ただし直受けしてない人も多いので、3〜5人に同時打診するのが現実的。YMYL系は監修の有無で信頼評価が決まりやすいから、今のSEOじゃほぼ必須装備。",
    "Whois非公開で運営してるサイト、実は地味に損してるかもしれない。Googleが「運営主体が誰か」を重視するようになってから、登録者情報を隠すのはSEO評価の取りこぼしになりやすい。公開すれば信頼性シグナルになるし、中長期的なドメイン評価の積み上げにもなる。",
    "AIツールで記事増やすより、既存コンテンツの被リンク構造を最適化する方が即効性ある。散らばってた外部リンク評価を1記事に集約させるだけで、手持ち記事がいきなり上位化する現象増えてる。",
    "AIでコンテンツ量産して順位上げるより、既存記事の内部リンク構造整え直すほうが効くようになった。分散してた評価を集約させるだけで、手持ちコンテンツが急に活躍し始める。",
    "中古ドメ精査ツール自作してる、こんなことができるとは。アンソロピック感謝",
    "MCP連携してからahrefs直で見に行くこと激減したな",
    "副業で月5万稼ぐまでは「とにかく記事数」で良いんだけど、そっから先は「記事の質」じゃなく「記事の評価の集約」が効く。散らばった評価を1本に寄せるだけで、AIコンテンツでも普通に上がる。",
    "アプデ後でいつものようにまだ順位変動が大きめですが、落ちてここでテコ入れすると「はいはいあなたSEOな人ね」認定されそう説。いったん我慢でまだ静観してみる。",
    "複数ページが同じキーワードで順位に出てる、これカニバリだ。Googleが「どれ上げればいいの？」って迷ってるんだよ。評価が散らばって、結果どのページも上がらない。GRCのランクインページ機能で、日によってURLがコロコロ変わってないかチェックするのが一番シンプル。評価を1記事に集約",
    "アフィ関係ない旧友からフォローされて、ちょっとビビッておりますなう",
    "AIで生成したコンテンツ、実は検索順位めちゃ上がるんだよな。ただし、AIが見落とす「ユーザーの本当の悩み」を1段階深掘りするだけで精度爆上がり。その部分、個人だからできるんだ、、、",
    "claude design、普通に最新opusに内包されてるって認識でOKなんか、、、？",
    "検索ボリューム70のKWで月1,000流入の可能性がある。ツールで見落とされた穴場KWを発掘できるのは、個人アフィリエイターの強み。大手が気付かないKWの本当の価値を見極める調査力が、これからの差。",
    "みなさんSNSやYouTubeや有料note、AIでアプリとかに行きまくってる。市場的には斜陽オーラあるけど、プレイヤー数的には？一周回ってワンチャンありなんじゃない？SEO。",
    "アフィリ案件選びで稼げるかどうか8割決まるんだけど、みんな報酬額と承認率しか見てないんだよな。実は「競合サイトの質」と「検索ユーザーの購買段階」を分析した方が、長期的には圧倒的に勝つ。地味だけどこれ重要。",
    "例のアレですが。アプデ完了後1週間はよく動く現象。我がサイトが落ちておる。おい！",
    "AIライティングツール使ってる人多いけど、実は出力精度より「プロンプトの検索意図の理解度」で差がつくんだよな。同じツールでも、ユーザー心理を掘り下げてる人のコンテンツが結局上位化する。",
    "営業メールって普通は削除してるけど、実はSEOの味方になるんだよな。URL付きで返信するだけで、新規UUやダイレクトアクセスが増える。相手も高確率でクリックしてくれるし、月3通の積み重ねで数ヶ月後に効く。",
    "Claude code、ターミナルからアプリに最近移行して便利さを感じてたんだけど、添付できるのが画像のみってのがきつい。。",
    "AIツールで大量生成した記事、上位表示してるの見かけるけど、実は検索意図の解像度の差なんだよな。同じKWでも「なぜユーザーがそれを検索したのか」を深掘りしてるコンテンツが結局勝つ。",
    "検索ボリューム70のKWで月1,000件の流入狙える。トラフィックポテンシャルで見えるのは「1位になったら関連KWで何個も引っ掛かる」という現実。Googleの検索ボリュームだけ見てスルーしてたら、絶対に穴場KW見落としてる。",
    "中古ばりばりいますな。被リンクうんぬんもそうだけどジャンルどころか、事業内容ピンポイントマッチくらいだと息長いね。",
    "AIライティングツールで記事を量産しても、E-E-A-Tが弱いと順位が上がらない。今は「誰が書いたか」が検索順位に直結する。だから専門家の監修じゃなく、専門家自身に執筆させるか、実績者のノウハウを活用する方が効率的。",
    "監修サービス経由だと手数料が乗るから割高。でも見つけた専門家に直接依頼すると、同じ人が監修するのに単価が20～30%下がることある。監修表記の誤りだけは最後に確認する。今のSEOで監修は「ないと負ける」装備。",
    "監修サービスは手数料が乗るから単価が高い。だから、サービスで専門家を見つけて、その人のサイトやSNSから直接依頼する。同じ専門家が監修するのに、中間コストが減るだけで費用が20～30%下がることもある。今のSEOで監修は「あるのが前提」。コスパ意識で導入する時代。",
    "ChatGPTで大量生成した記事、インデックスされてない？それなら構造化データを疑え。AIコンテンツはクローラビリティが低くなる傾向。schema.markupを正確に実装するだけで、インデックス率が劇的に改善することがある。量産の前に基盤整備。",
    "AIで記事100本作ったのに1本も売れない？それなら検索意図のズレを疑え。上位サイトが「比較」狙いなのに「解説」で勝負してたら、どんなに質良くても埋もれる。競合分析で意図を揃える。量より適正。",
    "検索ボリューム70のキーワード、1位取ったところで月1件しか来ない？そう思ってスルーしてたら機会損失。ahrefsのトラフィックポテンシャル見たら月1,000件の可能性だった。関連キーワードの積み重ねで、ボリューム以上の流入が期待できる穴場KWもある。丁寧に調査することが差をつける。",
    "AIツールで記事量産してるのに成果出ない場合、E-E-A-Tを疑え。生成AIは万能じゃなく、人間にしかできない体験や根拠が評価される。数より質。自分の経験をベースに、AIで効率化する使い方が正解。地味だけど効く。",
    "SEO頑張ってるのに順位上がらない場合、カニバリを疑え。同じキーワードで複数ページがランクインしてると、Google側でも評価が分散して迷ってる状態。GRCで「ランクインページ」確認して、日によってURLが変わってないか見てみ。地味だけど効く対策。",
    "ブログのアクセス増えてるのにCVが増えない場合、記事の導線見直した方がいい。内部リンクの張り方次第で、読者の行動パターン変わる。特にLP直前の記事から、自然な流れで送客できてるか確認してみ。",
    "中古ドメイン相手にコンテンツで勝てないなら、被リンク見てみ。昔の運営者がつけたリンク、そのまま残ってることがほとんど。リンク元に「このリンク今アフィサイトになってますよ」って教えてあげるだけで、競合のドメインパワー削れる。地味だけど効く。",
    "AIで大量生成した記事、インデックスすらされてないの結構多い。質より量の時代は終わった感じ。選別の目が必要。",
    "SEOのことツイートしてる人あんまりいなしねー、悪くないと思うんだけどなーまだ。",
    "ひさしぶりにいろいろツイートしたら反応してくださる方多くてちょっと楽しい",
    "SEOの常識が変わった。\n\n「記事が上がらない」の原因、実はカニバリかもしれません。複数ページがGoogleを迷わせ、評価が散らばる状態に。GRCとサチコで見つけて、ページ統合か301リダイレクトで解消。評価を1記事に集約させるだけで、順位は劇的に変わります。",
    "SEOの常識が変わった。\n\n毎日来る営業メールがSEOの味方に。URL付きで返信するだけで新規UU、ダイレクトアクセス、滞在時間が増加。劇的な効果はないが、週3通の返信を数ヶ月続ければじわじわ効く。地味な積み重ねが、結局あとで検索順位という差になる。",
    "2025年以降、個人がSEOで勝つには穴場キーワード開拓が必須。ahrefsの「トラフィックポテンシャル」を使えば、検索ボリーム70のキーワードが実は月1,000流入の可能性があることも判明。大手が狙わないKWを丁寧に調査することが、確実な売上につながります。",
    "SEOの常識が変わった。\n\n「コンテンツを足す」から「削る」へ。\n\n今のGoogleが評価するのは情報量ではなく「適切さ」。検索意図からズレたh2を丸ごと削除したり、見出しレベルを下げるだけで順位が改善することも。\n\n詰め込みすぎは逆効果。引き算で密度を高める時代です。",
    "比較サイトじゃない形でのアフィうまく行けるかもしれない",
    "この中古ターンにAI活用して一斉攻撃しておきたいところ",
    "Claude codeをなんとか使い倒したい",
    "中古であげてきてる個人系サイトさんがいてテンションあがる。",
    "ahrefsはかれこれ8年くらい使ってます。競合サイト調査はもちろん、自サイトを調べる時もサチコよりもahrefsのが見やすくて速いです。このツールがあったからこそ成功したSEOメディアがたくさん、感謝。これからも愛用させて頂きます！",
    "まだやってんの？と思われそうだが、この夏仕込んだ新規サイトから初発生があって嬉しい。かなり嬉しい。",
    "1つ上げやすい策を見つけた。が、これを横展しまくれるのが先か、AIモードによる駆逐が先か問題。",
    "話題のレ〇タルこわい人のHP、数日前に取得したばっかのドメだけどダイレクト流入が急増してるからゴニョゴニョ・・・\n\n実はこれ盛大なマーケで、こっからサブディレでもルートでもアフィサイト転生させて・・・（個人の勝手な妄想です）",
    "クッソ久しぶりにアナゴさんでググったら、まだあのサイトいたなｗ",
    "いにしえSEOを再開し始めたら、やること多くなってきた。この忙しい感じ、久しぶり。",
    "スタバで「サブドメインが～」「サブディレクトリが～」「自社サーバーが～」と聞こえてきてしまう。気になってしまう。自分も気を付けなければ。",
    "いやほんと3周くらいまわって鯖ドメワンチャンじゃない？",
    "月20産んでくれるサイトを今から新規ドメでも作れるかテスト。",
    "あとはハックされまくって対策される前に、仰る通り「最短最速」で逃げ切る。",
    "中古リダイレクトとかコテコテなことしてたりあるんだけどさ",
    "なんか1周まわって（3周くらい？）鯖止めちょいありじゃない？Xとか。犬餌はあれなんだけどそうじゃないとこそこそこ。",
    "ウゴ時に定点観測させて頂いている個人や中小零細系のザ・アフィサイトが軒並み１ページ目にいらっしゃらない。。",
    "5日間ほどプールやプールやプールでバケーションしてたので今日からアプデ振り返って色々考える！（おそっ）",
    "「飛ぶのが当たり前、飛ばないサイトは奇跡」1サイト飛ぶたびに落ち込む人は、最初から向いてない。\n\n↑の部分、とても共感。俺も昔はきつかったな、一喜一憂しかしてなかったよ。まあ今でも飛ぶと悲しいんだけど",
    "TOP入れて全7記事のうち6記事消した。欲張ってロングテール拾おうとしてたもの。選択と集中。",
]

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


# ── 投稿済みツイート履歴（重複検知用） ───────────────────
def load_tweet_history():
    if os.path.exists(TWEET_LOG):
        try:
            with open(TWEET_LOG, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_tweet_history(text):
    entries = load_tweet_history()
    entries.append({"text": text, "posted_at": datetime.now().isoformat()})
    entries = entries[-50:]
    with open(TWEET_LOG, "w") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def is_too_similar(new_text, history, threshold=10):
    """冒頭 threshold 文字が過去の投稿と一致したら重複とみなす"""
    new_opening = new_text[:threshold]
    for entry in history:
        if entry["text"][:threshold] == new_opening:
            return True
    return False


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

    samples = past_tweets[:5] if past_tweets else random.sample(STYLE_SAMPLES, 5)
    examples = "\n".join(f"- {t}" for t in samples)
    style_examples = f"\n\n【文体・言い回しの参考（過去のX投稿）】\n{examples}"

    body_section = f"\n\n【記事本文（抜粋）】\n{body}" if body else ""

    prompt = f"""以下のnote記事を参考に、Xの投稿文を1つ生成してください。

【記事タイトル】{article['title']}{body_section}{style_examples}

【条件】
- 125文字以内（日本語は1文字=2単位で計算されるため厳守）
- 「詳しくは↓」は含めない（自動付与するため）
- 絵文字は使わない
- 上記の過去X投稿の文体・言い回しに合わせる
- 基本はですます調（「〜です」「〜ますね」「〜ですよ」）をベースにしつつ、時々くだけた表現を混ぜる。完全な丁寧語でなくてよい
- 読者を見下すような表現（「奴」「やつ」等）は絶対に使わない
- 記事の内容を参考にしつつ、同じテーマ・文脈で新規の視点や気づきを生成してもOK
- 記事の引用だけに縛られず、アフィリエイト・SEO・副業・AI活用に関連する有益な内容であれば自由に展開してよい
- URLは入れない
- 投稿文のみ出力（説明文・前置き不要）
- 「SEOの常識が変わった」「常識が変わった」のような使い古されたフレーズは使わない
- 毎回異なる切り口・書き出しにする（体験談・数字・問いかけ・逆説・具体例など）
- 以下のテンプレパターンは禁止（使いすぎて飽きられている）:
  「AIで〜してる人、実は〜なんですよね」
  「〜してない？実は〜」
  「〜の場合、〜を疑え」
  冒頭が毎回「AI」から始まるパターン
- 書き出しのバリエーション例: 自分の体験（「先月〜した」）、数字（「CTRが〜%」）、逆説（「〜しない方がいい」）、素朴な疑問（「〜ってどうなの？」）、断言（「〜は効く」）
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

    samples = past_tweets[:5] if past_tweets else random.sample(STYLE_SAMPLES, 5)
    examples = "\n".join(f"- {t}" for t in samples)
    style_examples = f"\n\n【文体・言い回しの参考（過去のX投稿）】\n{examples}"

    prompt = f"""SEO・アフィリエイト・副業・AI活用に関する短い投稿文を1つ生成してください。{style_examples}

【条件】
- 100文字以内
- 絵文字は使わない
- 上記の過去X投稿の文体・言い回しに合わせる
- 基本はですます調（「〜です」「〜ますね」「〜ですよ」）をベースにしつつ、時々くだけた表現を混ぜる。完全な丁寧語でなくてよい
- 読者を見下すような表現（「奴」「やつ」等）は絶対に使わない
- 検索・コンテンツ・収益化に関する実践的な知見や気づきを簡潔に
- URLは入れない
- 投稿文のみ出力（説明文・前置き不要）
- 「SEOの常識が変わった」「常識が変わった」のような使い古されたフレーズは使わない
- 毎回異なる切り口・書き出しにする（体験談・数字・問いかけ・逆説・具体例など）
- 以下のテンプレパターンは禁止（使いすぎて飽きられている）:
  「AIで〜してる人、実は〜なんですよね」
  「〜してない？実は〜」
  「〜の場合、〜を疑え」
  冒頭が毎回「AI」から始まるパターン
- 書き出しのバリエーション例: 自分の体験（「先月〜した」）、数字（「CTRが〜%」）、逆説（「〜しない方がいい」）、素朴な疑問（「〜ってどうなの？」）、断言（「〜は効く」）"""

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

    tweet_history = load_tweet_history()

    if post_type == "seo":
        # SEO短文投稿（ぶら下げなし）
        for attempt in range(4):
            text = generate_seo_tweet(past_tweets)
            text = trim_to_weighted_limit(text, 280)
            if not is_too_similar(text, tweet_history):
                break
            print(f"重複検知（試行{attempt+1}）: 冒頭が過去投稿と類似。再生成...")
        post_to_x(text)
        save_tweet_history(text)

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

        for attempt in range(4):
            text = generate_note_tweet(article, body, past_tweets)
            text = re.sub(r"\n?詳しくは↓\s*$", "", text).rstrip()
            if not is_too_similar(text, tweet_history):
                break
            print(f"重複検知（試行{attempt+1}）: 冒頭が過去投稿と類似。再生成...")
        suffix = "\n詳しくは↓"
        body_limit = 280 - x_weighted_length(suffix)
        text = trim_to_weighted_limit(text, body_limit) + suffix
        tweet_id = post_to_x(text)
        save_tweet_history(text)

        # 投稿済みURLを記録
        save_posted_url(article["url"])

        # リプライ投稿（失敗してもメイン投稿は維持）
        reply_text = f"詳しくはnoteでまとめてます。\n{article['url']}"
        try:
            post_to_x(reply_text, reply_to_id=tweet_id)
        except Exception as e:
            print(f"リプライ投稿失敗（メイン投稿は成功済み）: {e}")
