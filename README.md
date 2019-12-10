# Twitter API

自分用のまとめ。参考サイトのほぼコピペです。</br>
本スクリプトはコンテンツの著作権侵害を助長するものではありません。</br>

<a href=https://help.twitter.com/ja/rules-and-policies/copyright-policy>著作権に関するポリシー</a></br>
<a href=https://help.twitter.com/ja/rules-and-policies/twitter-api>TwitterのAPIについて</a></br>


## 残タスク


## こんがらがる用語
|###|###|
---|---
| 名前(name) | 名前。なんでもいい |
| スクリーンネーム(screen_name) | @に続くユニークな名前。後から変えられる |
| ユーザーID(id) | 外からは基本見えない。変更不可 |

## 使い方

### APIキー、アクセストークンの取得
APIをたたくのに使う。</br>
Twitterアカウントの「設定」メニューの「モバイル」を開き電話番号を入力し認証。</br>
認証後は電話番号を削除すれば他アカウントにも使える（たぶん）

下記ＵＲＬからTwitterアプリを作成

https://apps.twitter.com/

「Key and Tokens」から「Access token & access token secret」のCreateをクリック

### API申請せずアクセストークンとアクセスシークレットを取得する
提携アプリを使ってトークンを発行する。</br>
上記同様アプリを作成、tokenviewにConsumer API keysを適用させてURLを発行。</br>
Access token & secretを発行したいアカウントでURLにアクセスする。</br>

### インストールするもの
gifコンバートあたりをあとで書く</br>


## 参考にさせていただいたサイト</br>
[Response codes — Twitter Developers](https://developer.twitter.com/en/docs/basics/response-codes)</br>
[自動化ルール](https://help.twitter.com/ja/rules-and-policies/twitter-automation)</br>
[Markdown記法一覧 - Qiita](https://qiita.com/oreo/items/82183bfbaac69971917f)</br>
</br>
[[Python] OAuth認証でTwitter連携/ログインを実装する - Qiita](https://qiita.com/mikan3rd/items/686e4978f9e1111628e9)</br>
[PHPのnull・空の判定・存在チェック方法5種の比較。 isset()、empty()、is_null()、== null、 ===null | WEMO](https://wemo.tech/464)</br>
[TwitterAPI でツイートを大量に取得。サーバー側エラーも考慮（pythonで） | コード７区](http://ailaby.com/twitter_api/)</br>
[辞書のPythonリスト、最大値インデックスの取得 - コードログ](https://codeday.me/jp/qa/20190410/506627.html)</br>

