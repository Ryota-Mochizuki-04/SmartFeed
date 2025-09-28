# デプロイガイド

このガイドでは、RSS LINE Notifier のデプロイ手順を詳しく説明します。

## 目次

1. [事前準備の確認](#1-事前準備の確認)
2. [プロジェクトセットアップ](#2-プロジェクトセットアップ)
3. [環境設定](#3-環境設定)
4. [RSS設定ファイル作成](#4-rss設定ファイル作成)
5. [デプロイ実行](#5-デプロイ実行)
6. [デプロイ後設定](#6-デプロイ後設定)
7. [動作確認](#7-動作確認)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. 事前準備の確認

デプロイ前に以下が完了していることを確認してください：

### 1.1 必要な情報

```
✅ LINE Channel Access Token
✅ LINE Channel Secret
✅ LINE User ID
✅ AWS Access Key ID
✅ AWS Secret Access Key
```

### 1.2 環境要件

```
✅ Ubuntu/Debian Linux (推奨) または macOS
✅ Python 3.12+
✅ AWS CLI v2
✅ Git
✅ curl, wget, unzip, jq
```

### 1.3 アカウント要件

```
✅ AWS アカウント（適切なIAM権限）
✅ LINE Developers アカウント
✅ 設定したBotと友達追加済み
```

---

## 2. プロジェクトセットアップ

### 2.1 プロジェクトクローン

#### 方法1: GitHubからクローン（推奨）

```bash
# 作業ディレクトリに移動
cd ~/

# GitHubリポジトリをクローン
git clone https://github.com/Ryota-Mochizuki-04/SmartFeed

# プロジェクトディレクトリに移動
cd SmartFeed
```

> **注意**: このシステムは既にデプロイ済みで稼働中です。新規デプロイを行う場合は、既存のスタックを削除するか、異なるスタック名を使用してください。

#### 方法2: ZIPファイルをダウンロード

1. GitHubリポジトリページにアクセス
2. 「Code」ボタンをクリック
3. 「Download ZIP」を選択
4. ダウンロードしたZIPファイルを展開

```bash
# ZIPファイルを展開した場合
cd ~/Downloads
unzip SmartFeed-main.zip
cd SmartFeed-main
```

#### 方法3: 既存プロジェクトを使用

既にプロジェクトをお持ちの場合：

```bash
# 既存のプロジェクトディレクトリに移動
cd /path/to/your/SmartFeed
```

### 2.2 ディレクトリ構造確認

```bash
ls -la
```

期待される構造：
```
SmartFeed/
├── README.md
├── infrastructure/
│   └── cloudformation-template.yaml
├── lambda_functions/
│   ├── common/
│   ├── notifier/
│   └── webhook/
├── scripts/
│   ├── create_packages.py
│   ├── deploy.sh*
│   ├── setup-environment.sh*
│   └── dev-utils.sh*
├── config/
└── docs/
```

### 2.3 スクリプト実行権限確認

```bash
# 実行権限確認・付与
chmod +x scripts/*.sh
ls -la scripts/
```

---

## 3. 環境設定

### 3.1 自動セットアップ（推奨）

環境セットアップスクリプトを使用：

```bash
# 環境セットアップスクリプト実行
./scripts/setup-environment.sh
```

対話的に以下の設定を行います：
1. 必須ツールの確認・インストール
2. AWS CLI設定確認
3. LINE API設定ガイド
4. 環境変数ファイル作成

### 3.2 手動セットアップ

#### 必須ツールインストール（Ubuntu/Debian）
```bash
# パッケージ更新
sudo apt update

# 必須ツールインストール
sudo apt install -y python3.12 python3.12-pip python3.12-venv
sudo apt install -y curl wget unzip jq git

# AWS CLI v2インストール
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip aws/
```

#### 環境変数ファイル作成
```bash
# 環境変数ファイル作成
cp config/env.template .env

# エディタで編集
nano .env
```

`.env` ファイルに実際の値を設定：
```bash
# AWS認証情報
export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
export AWS_REGION="ap-northeast-1"
export STACK_NAME="rss-line-notifier"

# LINE API設定
export LINE_CHANNEL_ACCESS_TOKEN="YOUR_CHANNEL_ACCESS_TOKEN"
export LINE_CHANNEL_SECRET="YOUR_CHANNEL_SECRET"
export LINE_USER_ID="YOUR_USER_ID"

# 環境設定
export ENVIRONMENT="prod"
```

⚠️ **重要**:
- `YOUR_*` の部分を実際の値に置き換えてください
- AWS認証情報は IAM ユーザー作成時に取得したものを使用
- LINE API情報は LINE Developers Console から取得したものを使用

### 3.3 環境変数読み込み

```bash
# 環境変数読み込み
source .env

# 設定確認（一部のみ表示）
echo "AWS Region: $AWS_REGION"
echo "Stack Name: $STACK_NAME"
echo "LINE Channel Secret (最初の5文字): ${LINE_CHANNEL_SECRET:0:5}***"
```

---

## 4. RSS設定ファイル作成

### 4.1 設定ファイルテンプレート

```bash
# テンプレートから設定ファイル作成
cp config/rss-config.json.template config/rss-config.json
```

### 4.2 RSS設定編集

`config/rss-config.json` を編集してRSSフィードを設定：

```json
{
  "version": "2.1",
  "feeds": [
    {
      "url": "https://techcrunch.com/feed/",
      "name": "TechCrunch",
      "category": "テクノロジー",
      "enabled": true,
      "priority": 1
    },
    {
      "url": "https://www.itmedia.co.jp/news/rss/rss20.xml",
      "name": "ITmedia NEWS",
      "category": "テクノロジー",
      "enabled": true,
      "priority": 2
    },
    {
      "url": "https://github.blog/feed/",
      "name": "GitHub Blog",
      "category": "プログラミング",
      "enabled": true,
      "priority": 1
    }
  ],
  "settings": {
    "check_interval_minutes": 30,
    "max_articles_per_notification": 10,
    "enable_smart_filtering": true,
    "notification_time_range": {
      "start": "07:00",
      "end": "23:00"
    }
  },
  "analysis": {
    "enable_ai_categorization": true,
    "keyword_extraction": true,
    "duplicate_detection_threshold": 0.8
  },
  "statistics": {
    "total_notifications_sent": 0,
    "total_articles_processed": 0,
    "avg_articles_per_notification": 0.0,
    "last_execution": null
  }
}
```

### 4.3 設定ファイル検証

```bash
# JSON構文確認
python3.12 -m json.tool config/rss-config.json > /dev/null
echo "RSS設定ファイルの構文は正常です"
```

---

## 5. デプロイ実行

### 5.1 デプロイ前確認

```bash
# 環境検証
./scripts/setup-environment.sh --validate
```

### 5.2 デプロイ実行

#### 通常のデプロイ
```bash
# 環境変数読み込み
source .env

# デプロイ実行
./scripts/deploy.sh
```

#### オプション付きデプロイ
```bash
# 特定リージョンへのデプロイ
./scripts/deploy.sh --region us-east-1

# カスタムスタック名
./scripts/deploy.sh --stack my-rss-notifier

# デプロイ前確認のみ
./scripts/deploy.sh --dry-run
```

### 5.3 デプロイプロセス

デプロイは以下の順序で実行されます：

1. **前提条件確認**
   - 必須ツールの確認
   - AWS認証確認
   - 環境変数確認

2. **Lambda パッケージ作成**
   - ソースコードパッケージ化
   - 依存関係インストール
   - ZIPファイル作成

3. **CloudFormation テンプレート検証**
   - YAML構文確認
   - AWSリソース検証

4. **S3バケット作成**
   - デプロイ用バケット作成
   - パッケージアップロード

5. **CloudFormation デプロイ**
   - スタック作成/更新
   - AWSリソース作成

### 5.4 デプロイ完了確認

成功時の出力例：
```
=== デプロイ完了 ===

  S3BucketName: rss-line-notifier-prod-[ACCOUNT-ID]
  NotifierFunctionName: rss-notifier-prod
  WebhookFunctionName: rss-webhook-prod
  WebhookURL: https://[API-ID].execute-api.ap-northeast-1.amazonaws.com/prod/webhook
  NotificationSchedules: 30 03 * * ? * and 00 12 * * ? * (UTC)

=== 次のステップ ===

1. LINE Bot設定
   - LINE Developers Console でWebhook URLを設定
   - Webhook URL: https://[API-ID].execute-api.ap-northeast-1.amazonaws.com/prod/webhook

2. RSS設定
   - S3バケットに rss-config.json をアップロード

3. テスト実行
   - Lambda関数のテスト実行
   - LINE Botとの動作確認
```

> **注意**: 実際のWebhook URLとS3バケット名は、AWSによって自動生成される一意の値になります。デプロイ時の出力を確認してください。

---

## 6. デプロイ後設定

### 6.1 RSS設定ファイルアップロード

```bash
# S3バケット名を環境変数から取得
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text)

# RSS設定ファイルアップロード
aws s3 cp config/rss-config.json s3://$BUCKET_NAME/config/rss-config.json \
  --region $AWS_REGION

echo "RSS設定ファイルをアップロードしました: $BUCKET_NAME"
```

### 6.2 LINE Webhook URL設定

1. **Webhook URL取得**
   ```bash
   # 出力からWebhook URLをコピー
   WEBHOOK_URL=$(aws cloudformation describe-stacks \
     --stack-name $STACK_NAME \
     --region $AWS_REGION \
     --query 'Stacks[0].Outputs[?OutputKey==`WebhookApiUrl`].OutputValue' \
     --output text)

   echo "Webhook URL: $WEBHOOK_URL"
   ```

2. **LINE Developers Console で設定**
   - [LINE Developers Console](https://developers.line.biz/console/) にアクセス
   - 該当チャネルの「Messaging API設定」タブを開く
   - 「Webhook URL」に上記で取得したURLを設定
   - 「Webhookの利用」を有効にする
   - 「検証」をクリックして成功を確認

### 6.3 EventBridge スケジュール確認

```bash
# スケジュールルール確認
aws events list-rules \
  --name-prefix $STACK_NAME \
  --region $AWS_REGION
```

**デフォルトの通知スケジュール**:
- **朝の通知**: 毎日12:30（JST） - UTC 03:30
- **夜の通知**: 毎日21:00（JST） - UTC 12:00

通知は1日2回、指定された時間に自動実行されます。

---

## 7. 動作確認

### 7.1 Lambda関数テスト

```bash
# Notifier関数のテスト実行
./scripts/dev-utils.sh test-lambda notifier

# Webhook関数のテスト実行
./scripts/dev-utils.sh test-lambda webhook
```

### 7.2 LINE API接続テスト

```bash
# LINE API接続テスト
./scripts/dev-utils.sh test-line
```

成功すると設定したLINEアカウントにテストメッセージが届きます。

### 7.3 RSS取得テスト

```bash
# 個別RSSフィード取得テスト
./scripts/dev-utils.sh test-rss "https://techcrunch.com/feed/"
```

### 7.4 手動通知実行

```bash
# Notifier関数の手動実行
./scripts/dev-utils.sh invoke-notifier
```

### 7.5 ログ確認

```bash
# リアルタイムログ監視
./scripts/dev-utils.sh tail-logs notifier

# 過去のログ確認
./scripts/dev-utils.sh logs notifier
```

### 7.6 LINE Botコマンドテスト

LINEでBotに以下のコマンドを送信してテスト：

```
一覧          # RSS設定一覧表示
統計          # 通知統計表示
最新          # 最新記事手動取得
ヘルプ        # ヘルプ表示
```

---

## 8. トラブルシューティング

### 8.1 デプロイエラー

#### CloudFormation エラー
```bash
# スタックイベント確認
aws cloudformation describe-stack-events \
  --stack-name $STACK_NAME \
  --region $AWS_REGION

# エラー詳細確認
aws cloudformation describe-stack-events \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

#### Lambda パッケージエラー
```bash
# パッケージ再作成
python3.12 scripts/create_packages.py

# パッケージ検証
./scripts/deploy.sh --validate
```

### 8.2 実行時エラー

#### LINE API エラー
```bash
# 環境変数確認
echo $LINE_CHANNEL_TOKEN
echo $LINE_USER_ID

# 手動APIテスト
curl -X POST https://api.line.me/v2/bot/message/push \
  -H "Authorization: Bearer $LINE_CHANNEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to":"'$LINE_USER_ID'","messages":[{"type":"text","text":"テスト"}]}'
```

#### RSS取得エラー
```bash
# RSS設定確認
./scripts/dev-utils.sh validate-config

# 個別フィードテスト
./scripts/dev-utils.sh test-rss "https://問題のRSSURL"
```

### 8.3 よくある問題と解決策

| 問題 | 原因 | 解決策 |
|------|------|--------|
| デプロイに失敗 | IAM権限不足 | IAMポリシー確認・追加 |
| Lambda実行エラー | 環境変数未設定 | CloudFormation パラメータ確認 |
| LINE通知が届かない | Webhook URL未設定 | LINE Console で URL設定 |
| RSS取得できない | ネットワーク/SSL証明書 | Lambda VPC設定確認 |
| 重複通知 | 履歴データ破損 | S3履歴ファイル削除・再作成 |

### 8.4 ログ調査

```bash
# 詳細ログ出力
export LOG_LEVEL="DEBUG"
./scripts/deploy.sh

# Lambda関数ログ確認
./scripts/dev-utils.sh logs notifier
./scripts/dev-utils.sh logs webhook

# CloudFormation イベント確認
aws cloudformation describe-stack-events \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --max-items 20
```

### 8.5 設定リセット

問題が解決しない場合の完全リセット：

```bash
# スタック削除
aws cloudformation delete-stack \
  --stack-name $STACK_NAME \
  --region $AWS_REGION

# 削除完了待機
aws cloudformation wait stack-delete-complete \
  --stack-name $STACK_NAME \
  --region $AWS_REGION

# 再デプロイ
./scripts/deploy.sh
```

---

## 次のステップ

デプロイが完了したら、[運用ガイド](04_operation.md) を参照して日常的な運用方法を確認してください。

---

## 参考リンク

- [AWS CloudFormation ユーザーガイド](https://docs.aws.amazon.com/ja_jp/AWSCloudFormation/latest/UserGuide/)
- [AWS Lambda 開発者ガイド](https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/)
- [LINE Messaging API リファレンス](https://developers.line.biz/ja/reference/messaging-api/)