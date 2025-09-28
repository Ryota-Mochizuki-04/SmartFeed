# LINE API セットアップガイド

このガイドでは、RSS LINE Notifier で使用する LINE API の設定方法を詳しく説明します。

## 目次

1. [LINE Developers アカウント作成](#1-line-developers-アカウント作成)
2. [プロバイダー作成](#2-プロバイダー作成)
3. [Messaging API チャネル作成](#3-messaging-api-チャネル作成)
4. [必要な情報の取得](#4-必要な情報の取得)
5. [Bot の基本設定](#5-bot-の基本設定)
6. [友達追加と User ID 取得](#6-友達追加とuser-id取得)
7. [トラブルシューティング](#7-トラブルシューティング)

---

## 1. LINE Developers アカウント作成

### 1.1 LINE Developers にアクセス

1. ブラウザで [LINE Developers](https://developers.line.biz/ja/) にアクセス
2. 「ログイン」をクリック

### 1.2 LINE アカウントでログイン

1. 普段使用している LINE アカウントでログイン
2. 必要に応じて電話番号認証を完了

### 1.3 開発者情報登録

初回ログイン時は以下の情報を入力：

- **名前**: 本名または開発者名
- **メールアドレス**: 連絡可能なメールアドレス
- **開発者タイプ**: 「個人」を選択（個人利用の場合）

---

## 2. プロバイダー作成

### 2.1 プロバイダー作成

1. LINE Developers Console で「プロバイダー」タブをクリック
2. 「新規プロバイダー作成」をクリック

### 2.2 プロバイダー情報入力

- **プロバイダー名**: `RSS Notifier` （任意の名前）
- **説明**: `個人用RSSフィード通知システム` （任意）

### 2.3 利用規約同意

利用規約を確認し、同意にチェックして「作成」をクリック

---

## 3. Messaging API チャネル作成

### 3.1 チャネル作成開始

1. 作成したプロバイダーをクリック
2. 「Messaging API」をクリック

### 3.2 チャネル情報入力

#### 基本情報

- **チャネル名**: `RSS通知`
- **チャネル説明**: `RSSフィードの新着記事を通知するBot`
- **大業種**: `個人`
- **小業種**: `個人（その他）`

#### その他設定

- **利用規約 URL**: 空欄（個人利用のため）
- **プライバシーポリシー URL**: 空欄（個人利用のため）

### 3.3 利用規約同意

各種利用規約を確認し、すべてにチェックして「作成」をクリック

---

## 4. 必要な情報の取得

チャネル作成後、以下の 3 つの重要な情報を取得します。

### 4.1 Channel Access Token 取得

1. 作成したチャネルをクリック
2. 「Messaging API 設定」タブをクリック
3. 「Channel access token」セクションで「発行」をクリック
4. 生成されたトークンをコピーして安全な場所に保存

```
例: eyJhbGciOiJIUzI1NiIsIn...（長い文字列）
```

⚠️ **重要**: このトークンは秘密情報です。第三者に漏れないよう注意してください。

### 4.2 Channel Secret 取得

1. 「Basic settings」タブをクリック
2. 「Channel secret」をコピー

```
例: 1234567890abcdef1234567890abcdef
```

### 4.3 User ID 取得（後で実施）

User ID は Bot と友達になった後に取得します（後述）。

---

## 5. Bot の基本設定

### 5.1 応答設定

1. 「Messaging API 設定」タブで以下を設定：
   - **応答メッセージ**: `無効` にする
   - **Webhook**: `有効` にする
   - **Webhook URL**: システムデプロイ後に設定
   - **グループ・複数人トークへの参加**: `無効` にする

> **注意**: Webhook URLは AWS Lambda デプロイ完了後に設定します。デプロイ時に生成されるAPI Gateway URLを使用してください。

### 5.2 友達追加時の設定

1. 「Messaging API 設定」タブで：
   - **友だち追加時あいさつ**: `有効` のまま
   - **自動応答メッセージ**: `無効` にする

---

## 6. 友達追加と User ID 取得

### 6.1 QR コードで Bot 追加

1. 「Messaging API 設定」タブで「QR コード」を表示
2. LINE アプリで QR コードを読み取り、友達追加

### 6.2 User ID 取得方法

#### 方法 1: テスト用 Webhook（推奨）

1. 一時的な Webhook URL サービスを使用

   - [Webhook.site](https://webhook.site/) にアクセス
   - 表示された URL をコピー

2. LINE Developers Console で設定

   - 「Messaging API 設定」で「Webhook URL」に上記 URL を設定
   - 「検証」をクリックして成功を確認

3. User ID 取得
   - LINE で Bot にメッセージを送信
   - Webhook.site でリクエストを確認
   - JSON 内の `events[0].source.userId` が User ID

```json
{
  "events": [
    {
      "source": {
        "userId": "U1234567890abcdef1234567890abcdef1",
        "type": "user"
      }
    }
  ]
}
```

#### 方法 2: LINE Bot SDK 使用（上級者向け）

開発環境でテスト用 Bot を起動して User ID を取得

### 6.3 情報の確認

以下の 3 つの情報が揃ったことを確認：

```
✅ Channel Access Token: eyJhbGciOiJIUzI1NiIsIn...
✅ Channel Secret: 1234567890abcdef1234567890abcdef
✅ User ID: U1234567890abcdef1234567890abcdef1
```

---

## 7. トラブルシューティング

### 7.1 よくある問題

#### チャネル作成できない

- **原因**: LINE アカウントの認証が不完全
- **解決**: 電話番号認証を完了する

#### Channel Access Token が発行できない

- **原因**: チャネル設定が不完全
- **解決**: 必須項目をすべて入力してチャネルを作成し直す

#### User ID が取得できない

- **原因**: Webhook 設定や Bot 設定の問題
- **解決**:
  1. Webhook URL が正しく設定されているか確認
  2. Bot が有効になっているか確認
  3. 友達追加が完了しているか確認

### 7.2 設定確認チェックリスト

```
□ LINE Developers アカウント作成完了
□ プロバイダー作成完了
□ Messaging API チャネル作成完了
□ Channel Access Token 取得・保存完了
□ Channel Secret 取得・保存完了
□ Bot基本設定完了（応答メッセージ無効など）
□ Bot友達追加完了
□ User ID 取得・保存完了
```

### 7.3 テスト方法

取得した情報で API テストを実行：

```bash
curl -X POST https://api.line.me/v2/bot/message/push \
  -H "Authorization: Bearer YOUR_CHANNEL_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "YOUR_USER_ID",
    "messages": [{
      "type": "text",
      "text": "テストメッセージ"
    }]
  }'
```

成功すると空のレスポンス `{}` が返され、LINE にメッセージが届きます。

---

## 次のステップ

LINE API 設定が完了したら、[AWS セットアップガイド](02_aws_setup.md) に進んでください。

---

## 参考リンク

- [LINE Developers](https://developers.line.biz/ja/)
- [LINE Bot SDK Documentation](https://developers.line.biz/ja/docs/)
- [Messaging API Reference](https://developers.line.biz/ja/reference/messaging-api/)
