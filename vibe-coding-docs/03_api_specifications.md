# RSS LINE Notifier - API仕様書

## 📋 API概要

### システム内API構成
1. **LINE Webhook API**: LINE Platformからのイベント受信
2. **LINE Messaging API**: LINEメッセージ送信（外部API）
3. **RSS Feed API**: 外部RSSフィード取得（外部API）
4. **Internal Lambda API**: Lambda関数間連携

## 🔗 1. LINE Webhook API

### エンドポイント情報
- **URL**: `https://{api-gateway-id}.execute-api.ap-northeast-1.amazonaws.com/webhook`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Authentication**: X-Line-Signature Header

### 1.1 Webhook Event Reception

#### Request Headers
```http
POST /webhook HTTP/1.1
Host: {api-gateway-id}.execute-api.ap-northeast-1.amazonaws.com
Content-Type: application/json
X-Line-Signature: {signature}
User-Agent: LineBotWebhook/2.0
```

#### Request Body - Text Message Event
```json
{
  "destination": "Udxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "events": [
    {
      "type": "message",
      "mode": "active",
      "timestamp": 1705123456789,
      "source": {
        "type": "user",
        "userId": "Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      },
      "webhookEventId": "01234567-89ab-cdef-0123-456789abcdef",
      "deliveryContext": {
        "isRedelivery": false
      },
      "message": {
        "id": "123456789012345678",
        "type": "text",
        "text": "一覧",
        "quoteToken": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      },
      "replyToken": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  ]
}
```

#### Response
```json
{
  "statusCode": 200,
  "body": "OK"
}
```

### 1.2 署名検証

#### 検証アルゴリズム
```python
import hmac
import hashlib
import base64

def verify_signature(body: str, signature: str, channel_secret: str) -> bool:
    """LINE署名検証"""
    hash_digest = hmac.new(
        channel_secret.encode(),
        body.encode(),
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_digest).decode()
    return hmac.compare_digest(signature, expected_signature)
```

## 💬 2. LINE Messaging API (外部API)

### 2.1 Push Message API

#### Endpoint
- **URL**: `https://api.line.me/v2/bot/message/push`
- **Method**: `POST`
- **Authentication**: `Bearer {Channel Access Token}`

#### Request - Text Message
```json
{
  "to": "Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "messages": [
    {
      "type": "text",
      "text": "登録済みRSSフィード一覧:\n\n1. Qiita - 人気の記事\n2. GitHub Trending"
    }
  ]
}
```

#### Request - Flex Message (Carousel)
```json
{
  "to": "Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "messages": [
    {
      "type": "flex",
      "altText": "RSS通知 - 新着記事 5件",
      "contents": {
        "type": "carousel",
        "contents": [
          {
            "type": "bubble",
            "size": "giga",
            "header": {
              "type": "box",
              "layout": "horizontal",
              "contents": [
                {
                  "type": "text",
                  "text": "💻 プログラミング",
                  "size": "lg",
                  "weight": "bold",
                  "color": "#FFFFFF",
                  "flex": 1
                },
                {
                  "type": "text",
                  "text": "3件  📰2 | ⚡1",
                  "size": "sm",
                  "color": "#FFFFFF",
                  "align": "end"
                }
              ],
              "backgroundColor": "#2E7D32",
              "paddingAll": "15px"
            },
            "body": {
              "type": "box",
              "layout": "vertical",
              "contents": [
                {
                  "type": "box",
                  "layout": "vertical",
                  "contents": [
                    {
                      "type": "box",
                      "layout": "horizontal",
                      "contents": [
                        {
                          "type": "text",
                          "text": "🥇",
                          "size": "sm",
                          "weight": "bold",
                          "color": "#FFD700"
                        },
                        {
                          "type": "text",
                          "text": "Pythonの新機能解説",
                          "size": "md",
                          "weight": "bold",
                          "wrap": true,
                          "flex": 1
                        }
                      ],
                      "spacing": "sm"
                    },
                    {
                      "type": "box",
                      "layout": "horizontal",
                      "contents": [
                        {
                          "type": "text",
                          "text": "🔥 中級 · 5分 · 2時間前",
                          "size": "xs",
                          "color": "#666666",
                          "flex": 1
                        }
                      ]
                    },
                    {
                      "type": "separator",
                      "margin": "md"
                    }
                  ],
                  "backgroundColor": "#FFF9C4",
                  "cornerRadius": "8px",
                  "paddingAll": "12px",
                  "action": {
                    "type": "uri",
                    "uri": "https://example.com/article"
                  }
                }
              ]
            }
          }
        ]
      }
    }
  ]
}
```

### 2.2 Loading Animation API

#### Request
```json
{
  "chatId": "Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "loadingSeconds": 5
}
```

#### Response
```json
{
  "statusCode": 200
}
```

## 📰 3. RSS Feed API (外部API)

### 3.1 RSS Feed Fetch

#### Request Example
```http
GET /feed.xml HTTP/1.1
Host: qiita.com
User-Agent: RSS-LINE-Notifier/2.1
Accept: application/rss+xml, application/xml, text/xml
```

#### Response - RSS 2.0 Format
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Qiita - 人気の記事</title>
    <link>https://qiita.com/popular/items</link>
    <description>プログラマの技術情報共有サービス</description>
    <lastBuildDate>Sat, 01 Jan 2024 12:00:00 +0900</lastBuildDate>

    <item>
      <title>Pythonの新機能について解説</title>
      <link>https://qiita.com/example/items/12345</link>
      <description>Python 3.12の新機能を詳しく解説します...</description>
      <pubDate>Sat, 01 Jan 2024 10:00:00 +0900</pubDate>
      <guid>https://qiita.com/example/items/12345</guid>
      <category>Python</category>
    </item>
  </channel>
</rss>
```

#### Response - Atom Format
```xml
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>GitHub Trending</title>
  <link href="https://github.com/trending" />
  <updated>2024-01-01T12:00:00Z</updated>
  <id>https://github.com/trending</id>

  <entry>
    <title>awesome-python</title>
    <link href="https://github.com/vinta/awesome-python" />
    <updated>2024-01-01T10:00:00Z</updated>
    <id>https://github.com/vinta/awesome-python</id>
    <content type="html">
      A curated list of awesome Python frameworks, libraries...
    </content>
  </entry>
</feed>
```

## 🔄 4. Internal Lambda API

### 4.1 Notifier Lambda Invocation

#### Request (from Webhook Lambda)
```python
import boto3

lambda_client = boto3.client('lambda')

response = lambda_client.invoke(
    FunctionName='rss-notifier-v1',
    InvocationType='Event',  # 非同期実行
    Payload=json.dumps({
        'source': 'webhook',
        'user_id': 'Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'trigger_type': 'manual'
    })
)
```

#### Response
```python
{
    'StatusCode': 202,
    'Payload': b'',
    'ExecutedVersion': '$LATEST'
}
```

## 📊 5. User Command API Specifications

### 5.1 Command Processing Interface

#### Input Command Format
```python
class UserCommand:
    def __init__(self, text: str, user_id: str):
        self.text = text
        self.user_id = user_id
        self.command, self.args = self.parse_command(text)

    def parse_command(self, text: str) -> tuple[str, list[str]]:
        """コマンド解析"""
        parts = text.strip().split()
        command = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        return command, args
```

#### Command Response Format
```python
class CommandResponse:
    def __init__(self, message_type: str, content: dict):
        self.message_type = message_type  # "text" or "flex"
        self.content = content
        self.success = True
        self.error_message = None
```

### 5.2 Individual Command Specifications

#### 5.2.1 一覧コマンド

**Input**:
```python
command = "一覧"
args = []
```

**Processing**:
```python
def handle_list_command(user_id: str) -> CommandResponse:
    # 1. S3からRSS設定読み込み
    feeds = load_rss_config()

    # 2. フィード一覧テキスト生成
    if not feeds:
        message = "登録されているRSSフィードはありません。\n\n「追加 <URL>」で新しいフィードを登録できます。"
    else:
        lines = ["登録済みRSSフィード一覧:\n"]
        for i, feed in enumerate(feeds, 1):
            lines.append(f"{i}. {feed['title']}")
        lines.append(f"\n通知時間: {NOTIFICATION_TIME_JST}")
        message = "\n".join(lines)

    return CommandResponse("text", {"text": message})
```

**Output**:
```json
{
  "type": "text",
  "text": "登録済みRSSフィード一覧:\n\n1. Qiita - 人気の記事\n2. GitHub Trending\n\n通知時間: 21時"
}
```

#### 5.2.2 追加コマンド

**Input**:
```python
command = "追加"
args = ["https://qiita.com/popular/items/feed"]
```

**Processing**:
```python
def handle_add_command(user_id: str, url: str) -> CommandResponse:
    # 1. URL検証
    if not is_valid_url(url):
        return CommandResponse("text", {"text": "無効なURLです。"})

    # 2. RSS フィード検証
    feed_info = validate_rss_feed(url)
    if not feed_info:
        return CommandResponse("text", {"text": "RSSフィードの取得に失敗しました。"})

    # 3. 重複チェック
    existing_feeds = load_rss_config()
    if any(feed['url'] == url for feed in existing_feeds):
        return CommandResponse("text", {"text": "このフィードは既に登録されています。"})

    # 4. フィード追加
    new_feed = {
        "url": url,
        "title": feed_info["title"],
        "category": categorize_feed(feed_info["title"]),
        "enabled": True,
        "added_at": datetime.utcnow().isoformat()
    }

    existing_feeds.append(new_feed)
    save_rss_config(existing_feeds)

    return CommandResponse("text", {
        "text": f"RSSフィードを追加しました:\n{feed_info['title']}\n\nカテゴリ: {new_feed['category']}"
    })
```

**Output (Success)**:
```json
{
  "type": "text",
  "text": "RSSフィードを追加しました:\nQiita - 人気の記事\n\nカテゴリ: プログラミング"
}
```

**Output (Error)**:
```json
{
  "type": "text",
  "text": "RSSフィードの取得に失敗しました。URLを確認してください。"
}
```

#### 5.2.3 削除コマンド

**Input**:
```python
command = "削除"
args = ["1"]
```

**Processing**:
```python
def handle_delete_command(user_id: str, number_str: str) -> CommandResponse:
    # 1. 番号検証
    try:
        index = int(number_str) - 1
    except ValueError:
        return CommandResponse("text", {"text": "無効な番号です。"})

    # 2. フィード存在確認
    feeds = load_rss_config()
    if index < 0 or index >= len(feeds):
        return CommandResponse("text", {"text": f"番号{number_str}のフィードは存在しません。"})

    # 3. フィード削除
    deleted_feed = feeds.pop(index)
    save_rss_config(feeds)

    return CommandResponse("text", {
        "text": f"RSSフィードを削除しました:\n{deleted_feed['title']}"
    })
```

#### 5.2.4 通知コマンド

**Input**:
```python
command = "通知"
args = []
```

**Processing**:
```python
def handle_notification_command(user_id: str) -> CommandResponse:
    # 1. Notifier Lambda非同期実行
    try:
        invoke_notifier_lambda({
            'source': 'webhook',
            'user_id': user_id,
            'trigger_type': 'manual'
        })

        return CommandResponse("text", {
            "text": "手動通知を開始しました。\n新着記事があれば数分以内に通知されます。"
        })
    except Exception as e:
        logger.error(f"Failed to invoke notifier: {e}")
        return CommandResponse("text", {
            "text": "通知の実行に失敗しました。しばらく後に再試行してください。"
        })
```

#### 5.2.5 ヘルプコマンド

**Input**:
```python
command = "ヘルプ"
args = []
```

**Output**:
```json
{
  "type": "text",
  "text": "📚 RSS LINE Notifier ヘルプ\n\n🔧 利用可能なコマンド:\n\n📋 一覧\n登録済みRSSフィードを表示\n\n➕ 追加 <URL>\nRSSフィードを新規登録\n例: 追加 https://example.com/feed\n\n➖ 削除 <番号>\n指定番号のフィードを削除\n例: 削除 1\n\n🔔 通知\n手動で通知を実行\n\n❓ ヘルプ\nこのヘルプを表示\n\n⏰ 自動通知時間: 毎日21時"
}
```

## 🔧 6. Error Handling API

### 6.1 HTTP Error Responses

#### 400 Bad Request
```json
{
  "statusCode": 400,
  "body": {
    "error": "BAD_REQUEST",
    "message": "Invalid request format",
    "details": "Missing required field: events"
  }
}
```

#### 401 Unauthorized
```json
{
  "statusCode": 401,
  "body": {
    "error": "UNAUTHORIZED",
    "message": "Invalid LINE signature",
    "details": "Signature verification failed"
  }
}
```

#### 500 Internal Server Error
```json
{
  "statusCode": 500,
  "body": {
    "error": "INTERNAL_ERROR",
    "message": "Processing failed",
    "details": "Failed to process LINE webhook event"
  }
}
```

### 6.2 LINE API Error Handling

#### Rate Limit Error
```json
{
  "message": "The request has been rate limited.",
  "details": [
    {
      "message": "You have exceeded the rate limit.",
      "property": "messages"
    }
  ]
}
```

#### Invalid Message Format
```json
{
  "message": "The request body has 1 error(s)",
  "details": [
    {
      "message": "Must be one of the following values: [text, image, video, audio, file, location, sticker, imagemap, template, flex]",
      "property": "messages[0].type"
    }
  ]
}
```

## 📏 7. API制限・制約

### LINE API制限
- **メッセージサイズ**: 最大50KB
- **Push Message**: 1000件/月（無料プラン）
- **Flex Message**: 最大12カラム、50アクション

### Lambda制限
- **実行時間**: 最大15分
- **メモリ**: 最大10GB
- **同時実行**: アカウント制限（デフォルト1000）

### RSS Feed制限
- **フィード数**: 推奨100フィード/ユーザー
- **記事数**: 最大30記事/通知
- **取得タイムアウト**: 30秒/フィード

この API仕様書により、システム間の連携とデータフォーマットが明確に定義されています。