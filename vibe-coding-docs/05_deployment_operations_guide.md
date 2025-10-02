# RSS LINE Notifier - デプロイメント・運用ガイド

## 🚀 デプロイメント概要

### デプロイメント戦略

- **インフラ**: CloudFormation による IaC (Infrastructure as Code)
- **アプリケーション**: Lambda ZIP パッケージによるコードデプロイ
- **設定管理**: 環境変数 + CloudFormation パラメータ
- **バージョニング**: 関数名サフィックス方式 (v1, v2...)

### 全体フロー

```
1. 前提条件確認 → 2. LINE設定 → 3. AWS設定 → 4. インフラ構築 → 5. アプリケーションデプロイ → 6. 初期設定 → 7. 動作確認
```

## 📋 前提条件・準備

### 1. 必要なツール・環境

```bash
# AWS CLI v2
aws --version  # aws-cli/2.x.x or higher

# Python 3.9+
python3 --version  # Python 3.9.x or higher

# zip コマンド
zip --version

# jq (JSONパース用、オプション)
jq --version
```

### 2. AWS 権限要件

必要な IAM ポリシー:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "apigateway:*",
        "events:*",
        "s3:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. LINE 設定

LINE Developer Console での設定項目:

- **Channel Access Token** 取得
- **Channel Secret** 取得
- **Webhook URL** 設定 (デプロイ後)
- **User ID** 取得

## 🔧 初回セットアップ（完全新規）

### Step 1: リポジトリクローン・セットアップ

```bash
# リポジトリクローン
git clone <repository-url>
cd rss-line-notifier

# 仮想環境作成・アクティベート
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 依存関係インストール
pip install -r lambda_functions/notifier/requirements.txt
pip install -r lambda_functions/webhook/requirements.txt
```

### Step 2: パラメータファイル作成

```bash
# パラメータテンプレートコピー
cp infrastructure/parameters.json.template infrastructure/parameters.json

# パラメータ編集
vim infrastructure/parameters.json
```

**parameters.json 設定例**:

```json
[
  {
    "ParameterKey": "LineToken",
    "ParameterValue": "YOUR_LINE_CHANNEL_ACCESS_TOKEN"
  },
  {
    "ParameterKey": "LineChannelSecret",
    "ParameterValue": "YOUR_LINE_CHANNEL_SECRET"
  },
  {
    "ParameterKey": "LineUserId",
    "ParameterValue": "YOUR_LINE_USER_ID"
  },
  {
    "ParameterKey": "NotificationTime",
    "ParameterValue": "00 12 * * ? *"
  },
  {
    "ParameterKey": "Environment",
    "ParameterValue": "v1"
  }
]
```

### Step 3: Lambda デプロイパッケージ作成

```bash
# パッケージ作成スクリプト実行
python scripts/create_packages.py

# 作成された ZIP ファイル確認
ls -la *.zip
# notifier-deployment.zip
# webhook-deployment.zip
```

### Step 4: CloudFormation スタック作成

```bash
# Git Bash の場合のパス変換無効化
export MSYS_NO_PATHCONV=1

# スタック作成
aws cloudformation create-stack \
  --stack-name rss-line-notifier-v1 \
  --template-body file://infrastructure/cloudformation-template.yaml \
  --parameters file://infrastructure/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1

# デプロイ状況確認
aws cloudformation describe-stacks \
  --stack-name rss-line-notifier-v1 \
  --region ap-northeast-1 \
  --query 'Stacks[0].StackStatus'
```

### Step 5: Lambda 関数コードアップロード

```bash
# Notifier Lambda 更新
aws lambda update-function-code \
  --function-name rss-notifier-v1 \
  --zip-file fileb://notifier-deployment.zip \
  --region ap-northeast-1

# Webhook Lambda 更新
aws lambda update-function-code \
  --function-name rss-webhook-v1 \
  --zip-file fileb://webhook-deployment.zip \
  --region ap-northeast-1
```

### Step 6: API Gateway URL 取得 & LINE 設定

```bash
# API Gateway URL 取得
aws cloudformation describe-stacks \
  --stack-name rss-line-notifier-v1 \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookApiUrl`].OutputValue' \
  --output text

# 出力例: https://abcd1234.execute-api.ap-northeast-1.amazonaws.com/webhook
```

**LINE Developer Console での設定**:

1. Messaging API Settings → Webhook URL に上記 URL を設定
2. Webhook の Use webhook を Enable に変更
3. Auto-reply messages を Disable に変更

### Step 7: 初期設定・動作確認

```bash
# 手動実行テスト
aws lambda invoke \
  --function-name rss-notifier-v1 \
  --payload '{}' \
  response.json \
  --region ap-northeast-1

# レスポンス確認
cat response.json

# ログ確認
aws logs tail /aws/lambda/rss-notifier-v1 --follow --region ap-northeast-1
```

## 🔄 コード更新デプロイ（通常運用）

### 日常的な更新フロー

```bash
# 1. コード変更・テスト
python tests/test_functions.py

# 2. パッケージ再作成
python scripts/create_packages.py

# 3. Lambda関数更新
aws lambda update-function-code \
  --function-name rss-notifier-v1 \
  --zip-file fileb://notifier-deployment.zip \
  --region ap-northeast-1

aws lambda update-function-code \
  --function-name rss-webhook-v1 \
  --zip-file fileb://webhook-deployment.zip \
  --region ap-northeast-1

# 4. 動作確認
aws lambda invoke \
  --function-name rss-notifier-v1 \
  --payload '{}' \
  response.json \
  --region ap-northeast-1
```

### 自動化スクリプト例

```bash
#!/bin/bash
# deploy.sh - 自動デプロイスクリプト

set -e

echo "🚀 Starting deployment..."

# パッケージ作成
echo "📦 Creating deployment packages..."
python scripts/create_packages.py

# Lambda更新
echo "⚡ Updating Lambda functions..."
aws lambda update-function-code \
  --function-name rss-notifier-v1 \
  --zip-file fileb://notifier-deployment.zip \
  --region ap-northeast-1

aws lambda update-function-code \
  --function-name rss-webhook-v1 \
  --zip-file fileb://webhook-deployment.zip \
  --region ap-northeast-1

echo "✅ Deployment completed!"

# 動作確認
echo "🧪 Running smoke test..."
aws lambda invoke \
  --function-name rss-notifier-v1 \
  --payload '{}' \
  response.json \
  --region ap-northeast-1

if grep -q "200" response.json; then
  echo "✅ Smoke test passed!"
else
  echo "❌ Smoke test failed!"
  cat response.json
  exit 1
fi
```

## 🏗️ インフラ更新・拡張

### CloudFormation テンプレート更新

```bash
# テンプレート変更後の更新
aws cloudformation update-stack \
  --stack-name rss-line-notifier-v1 \
  --template-body file://infrastructure/cloudformation-template.yaml \
  --parameters file://infrastructure/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1

# 更新状況監視
aws cloudformation describe-stack-events \
  --stack-name rss-line-notifier-v1 \
  --region ap-northeast-1
```

### 環境変数更新

```bash
# Notifier Lambda の環境変数更新
aws lambda update-function-configuration \
  --function-name rss-notifier-v1 \
  --environment Variables='{
    "LINE_TOKEN":"new_token_value",
    "LINE_USER_ID":"user_id",
    "BUCKET_NAME":"bucket_name"
  }' \
  --region ap-northeast-1

# Webhook Lambda の環境変数更新
aws lambda update-function-configuration \
  --function-name rss-webhook-v1 \
  --environment Variables='{
    "LINE_TOKEN":"new_token_value",
    "LINE_CHANNEL_SECRET":"new_secret",
    "BUCKET_NAME":"bucket_name",
    "NOTIFIER_FUNCTION_NAME":"rss-notifier-v1"
  }' \
  --region ap-northeast-1
```

## 📊 監視・運用

### CloudWatch メトリクス監視

```bash
# Lambda実行回数確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=rss-notifier-v1 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region ap-northeast-1

# エラー率確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=rss-notifier-v1 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region ap-northeast-1
```

### ログ分析・トラブルシューティング

```bash
# エラーログ検索
aws logs filter-log-events \
  --log-group-name /aws/lambda/rss-notifier-v1 \
  --filter-pattern "ERROR" \
  --start-time 1704067200000 \
  --region ap-northeast-1

# 特定期間のログストリーム表示
aws logs describe-log-streams \
  --log-group-name /aws/lambda/rss-notifier-v1 \
  --order-by LastEventTime \
  --descending \
  --max-items 5 \
  --region ap-northeast-1

# リアルタイムログ監視
aws logs tail /aws/lambda/rss-notifier-v1 --follow --region ap-northeast-1
```

### データベース（S3）管理

```bash
# RSS設定確認
aws s3 cp s3://rss-line-notifier-v1-{AccountId}/rss-list.json - | jq .

# 通知履歴確認
aws s3 cp s3://rss-line-notifier-v1-{AccountId}/notified-history.json - | jq '.history | length'

# バックアップ作成
aws s3 cp s3://rss-line-notifier-v1-{AccountId}/rss-list.json \
  s3://rss-line-notifier-v1-{AccountId}/backups/$(date +%Y%m%d)/rss-list.json

# データ復元
aws s3 cp s3://rss-line-notifier-v1-{AccountId}/backups/20240101/rss-list.json \
  s3://rss-line-notifier-v1-{AccountId}/rss-list.json
```

## 🚨 トラブルシューティング

### よくある問題と解決法

#### 1. Lambda デプロイエラー

```bash
# 問題: ZIP ファイルサイズ超過
# 解決: 不要ファイル除外、レイヤー使用検討

# ZIP ファイルサイズ確認
ls -lh *.zip

# 大きなファイル特定
unzip -l notifier-deployment.zip | sort -k4 -nr | head -20
```

#### 2. LINE Webhook 署名エラー

```bash
# ログでエラー詳細確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/rss-webhook-v1 \
  --filter-pattern "signature" \
  --region ap-northeast-1

# Channel Secret 再確認・更新
aws lambda update-function-configuration \
  --function-name rss-webhook-v1 \
  --environment Variables='{
    "LINE_CHANNEL_SECRET":"correct_secret_value"
  }' \
  --region ap-northeast-1
```

#### 3. RSS フィード取得失敗

```bash
# 手動でRSSフィード確認
curl -I "https://example.com/feed.xml"

# タイムアウト設定確認・調整
aws lambda update-function-configuration \
  --function-name rss-notifier-v1 \
  --timeout 900 \
  --region ap-northeast-1
```

#### 4. S3 アクセス権限エラー

```bash
# IAM ロール確認
aws iam get-role \
  --role-name NotifierLambdaRole

# S3 バケットポリシー確認
aws s3api get-bucket-policy \
  --bucket rss-line-notifier-v1-{AccountId}
```

## 🔄 バックアップ・復旧手順

### 定期バックアップ作成

```bash
#!/bin/bash
# backup.sh - 自動バックアップスクリプト

BUCKET_NAME="rss-line-notifier-v1-{AccountId}"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PREFIX="backups/${BACKUP_DATE}"

echo "📦 Creating backup: ${BACKUP_PREFIX}"

# データファイルバックアップ
aws s3 cp s3://${BUCKET_NAME}/rss-list.json \
  s3://${BUCKET_NAME}/${BACKUP_PREFIX}/rss-list.json

aws s3 cp s3://${BUCKET_NAME}/notified-history.json \
  s3://${BUCKET_NAME}/${BACKUP_PREFIX}/notified-history.json

# Lambda 関数コードバックアップ
aws lambda get-function \
  --function-name rss-notifier-v1 \
  --query 'Code.Location' \
  --output text > notifier_code_url.txt

aws lambda get-function \
  --function-name rss-webhook-v1 \
  --query 'Code.Location' \
  --output text > webhook_code_url.txt

echo "✅ Backup completed: ${BACKUP_PREFIX}"
```

### 災害復旧手順

```bash
# 1. インフラ復旧
aws cloudformation create-stack \
  --stack-name rss-line-notifier-v1-recovery \
  --template-body file://infrastructure/cloudformation-template.yaml \
  --parameters file://infrastructure/parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1

# 2. データ復元
RESTORE_DATE="20240101_120000"
aws s3 cp s3://rss-line-notifier-v1-{AccountId}/backups/${RESTORE_DATE}/rss-list.json \
  s3://rss-line-notifier-v1-{AccountId}/rss-list.json

# 3. Lambda 関数コード復元
python scripts/create_packages.py
aws lambda update-function-code \
  --function-name rss-notifier-v1 \
  --zip-file fileb://notifier-deployment.zip \
  --region ap-northeast-1

# 4. 動作確認
aws lambda invoke \
  --function-name rss-notifier-v1 \
  --payload '{}' \
  response.json \
  --region ap-northeast-1
```

## 📈 スケーリング・最適化

### コスト最適化

```bash
# Lambda メモリ使用量分析
aws logs filter-log-events \
  --log-group-name /aws/lambda/rss-notifier-v1 \
  --filter-pattern "Max Memory Used" \
  --region ap-northeast-1

# 最適メモリサイズ設定
aws lambda update-function-configuration \
  --function-name rss-notifier-v1 \
  --memory-size 256 \
  --region ap-northeast-1
```

### パフォーマンス最適化

```bash
# 同時実行数制限設定
aws lambda put-provisioned-concurrency-config \
  --function-name rss-notifier-v1 \
  --provisioned-concurrency-config AllocatedProvisionedConcurrencyNumber=5 \
  --region ap-northeast-1

# タイムアウト調整
aws lambda update-function-configuration \
  --function-name rss-notifier-v1 \
  --timeout 600 \
  --region ap-northeast-1
```

このデプロイメント・運用ガイドにより、システムの安定した運用と効率的な更新が可能になります。
