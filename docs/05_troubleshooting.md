# トラブルシューティングガイド

このガイドでは、RSS LINE Notifier で発生する可能性のある問題と解決方法を詳しく説明します。

## 目次

1. [基本的なトラブルシューティング手順](#1-基本的なトラブルシューティング手順)
2. [デプロイ関連の問題](#2-デプロイ関連の問題)
3. [LINE API関連の問題](#3-line-api関連の問題)
4. [RSS取得関連の問題](#4-rss取得関連の問題)
5. [Lambda実行関連の問題](#5-lambda実行関連の問題)
6. [AWS関連の問題](#6-aws関連の問題)
7. [パフォーマンス関連の問題](#7-パフォーマンス関連の問題)
8. [設定関連の問題](#8-設定関連の問題)
9. [緊急時の対応](#9-緊急時の対応)

---

## 1. 基本的なトラブルシューティング手順

### 1.1 問題の特定

まず以下の手順で問題を特定します：

1. **症状の確認**
   ```bash
   # システム全体の状況確認
   ./scripts/dev-utils.sh status
   ```

2. **ログの確認**
   ```bash
   # 最新のエラーログ確認
   ./scripts/dev-utils.sh logs notifier
   ./scripts/dev-utils.sh logs webhook
   ```

3. **設定の確認**
   ```bash
   # RSS設定の検証
   ./scripts/dev-utils.sh validate-config

   # 環境変数の確認
   echo $LINE_CHANNEL_TOKEN
   echo $AWS_REGION
   ```

### 1.2 基本的な確認項目

問題が発生した場合、以下を順番に確認：

```
□ AWS認証情報は正しいか
□ LINE API設定は正しいか
□ CloudFormationスタックは正常か
□ Lambda関数は実行されているか
□ S3バケットにアクセスできるか
□ RSS設定ファイルは正しいか
□ ネットワーク接続は正常か
```

### 1.3 診断コマンド集

##### Linux/macOS
```bash
# 完全診断実行
./scripts/setup-environment.sh --validate

# 個別テスト
./scripts/dev-utils.sh test-lambda notifier
./scripts/dev-utils.sh test-line
./scripts/dev-utils.sh test-rss "https://techcrunch.com/feed/"

# ログ監視
./scripts/dev-utils.sh tail-logs notifier
```

##### Windows
```powershell
# 注意: Windows環境では独自スクリプト実行にGit BashまたはWSLを推奨

# Git Bashを使用（推奨）
bash ./scripts/setup-environment.sh --validate
bash ./scripts/dev-utils.sh test-lambda notifier

# PowerShellでAWSコマンド直接実行
# Lambda関数テスト
aws lambda invoke --function-name "rss-notifier-prod" --region $env:AWS_REGION response.json
Get-Content response.json

# ログ確認
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/rss" --region $env:AWS_REGION
```

---

## 2. デプロイ関連の問題

### 2.1 CloudFormation デプロイエラー

#### 問題: スタック作成に失敗する

**症状:**
```
An error occurred (ValidationError) when calling the CreateStack operation:
Template format error: JSON not well-formed
```

**原因と解決策:**

1. **テンプレート構文エラー**
   ```bash
   # テンプレート検証
   aws cloudformation validate-template \
     --template-body file://infrastructure/cloudformation-template.yaml \
     --region $AWS_REGION
   ```

2. **IAM権限不足**
   ```bash
   # IAMポリシー確認
   aws iam list-attached-user-policies --user-name rss-notifier-deploy

   # 必要な権限を追加
   aws iam attach-user-policy \
     --user-name rss-notifier-deploy \
     --policy-arn arn:aws:iam::aws:policy/CloudFormationFullAccess
   ```

3. **リソース制限**
   ```bash
   # Lambda関数制限確認
   aws service-quotas get-service-quota \
     --service-code lambda \
     --quota-code L-2ACBD22F \
     --region $AWS_REGION
   ```

#### 問題: スタック更新に失敗する

**症状:**
```
Resource handler returned message: "The role defined for the function cannot be assumed by Lambda."
```

**解決策:**
```bash
# スタックイベント詳細確認
aws cloudformation describe-stack-events \
  --stack-name rss-line-notifier \
  --region $AWS_REGION \
  --query 'StackEvents[?ResourceStatus==`UPDATE_FAILED`]'

# IAMロールの確認
aws iam get-role --role-name rss-line-notifier-LambdaExecutionRole
```

### 2.2 Lambda パッケージング エラー

#### 問題: パッケージ作成に失敗する

**症状:**
```
ERROR - 依存関係インストール失敗: No module named 'feedparser'
```

**解決策:**

1. **Python環境確認**

   ##### Linux/macOS
   ```bash
   # Python バージョン確認
   python3.12 --version

   # pip 更新
   python3.12 -m pip install --upgrade pip
   ```

   ##### Windows
   ```powershell
   # Python バージョン確認
   python --version

   # pip 更新（管理者権限推奨）
   python -m pip install --upgrade pip

   # 権限エラーの場合
   python -m pip install --upgrade pip --user
   ```

2. **依存関係の手動インストール**
   ```bash
   # 仮想環境作成
   python3.12 -m venv venv
   source venv/bin/activate

   # 依存関係インストールテスト
   pip install feedparser requests boto3
   ```

3. **パッケージ再作成**
   ```bash
   # キャッシュクリア
   ./scripts/dev-utils.sh clean

   # パッケージ再作成
   python3.12 scripts/create_packages.py
   ```

---

## 3. LINE API関連の問題

### 3.1 メッセージ送信エラー

#### 問題: 401 Unauthorized エラー

**症状:**
```
ERROR - LINE プッシュメッセージの送信に失敗: 401 Unauthorized
```

**原因と解決策:**

1. **Channel Access Token の確認**
   ```bash
   # トークンテスト
   curl -v https://api.line.me/v2/bot/info \
     -H "Authorization: Bearer $LINE_CHANNEL_TOKEN"
   ```

2. **トークンの更新**
   ```bash
   # 新しいトークンで環境変数更新
   export LINE_CHANNEL_TOKEN="新しいトークン"

   # CloudFormation パラメータ更新
   ./scripts/deploy.sh
   ```

#### 問題: 400 Bad Request エラー

**症状:**
```
ERROR - LINE API呼び出しでエラー: {"message":"The request body has 2 error(s)"}
```

**解決策:**

1. **メッセージ形式確認**
   ```bash
   # 手動でシンプルなメッセージテスト
   curl -X POST https://api.line.me/v2/bot/message/push \
     -H "Authorization: Bearer $LINE_CHANNEL_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"to":"'$LINE_USER_ID'","messages":[{"type":"text","text":"テスト"}]}'
   ```

2. **User ID の確認**
   ```bash
   # User ID形式確認（U + 32文字の英数字）
   echo $LINE_USER_ID | grep -E '^U[a-fA-F0-9]{32}$'
   ```

### 3.2 Webhook関連の問題

#### 問題: Webhookが応答しない

**症状:**
LINE Developers Console で「検証」が失敗する

**解決策:**

1. **Webhook URL確認**
   ```bash
   # 正しいWebhook URL取得
   WEBHOOK_URL=$(aws cloudformation describe-stacks \
     --stack-name rss-line-notifier \
     --region $AWS_REGION \
     --query 'Stacks[0].Outputs[?OutputKey==`WebhookURL`].OutputValue' \
     --output text)

   echo "Webhook URL: $WEBHOOK_URL"
   ```

2. **手動テスト**
   ```bash
   # Webhook関数直接テスト
   ./scripts/dev-utils.sh test-lambda webhook
   ```

3. **API Gateway確認**
   ```bash
   # API Gateway ログ有効化
   aws apigateway update-stage \
     --rest-api-id $(echo $WEBHOOK_URL | cut -d'.' -f1 | cut -d'/' -f3) \
     --stage-name prod \
     --patch-ops op=replace,path=/accessLogSettings/destinationArn,value=arn:aws:logs:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):log-group:API-Gateway-Execution-Logs \
     --region $AWS_REGION
   ```

---

## 4. RSS取得関連の問題

### 4.1 RSS取得失敗

#### 問題: 404 Not Found エラー

**症状:**
```
ERROR - RSS取得でエラー: HTTPError 404 Client Error: Not Found
```

**解決策:**

1. **フィードURL確認**
   ```bash
   # 個別フィードテスト
   ./scripts/dev-utils.sh test-rss "問題のURL"

   # 手動確認
   curl -I "問題のURL"
   ```

2. **代替フィードの検索**
   ```bash
   # 当該サイトのフィード一覧確認
   curl -s "https://example.com" | grep -i "rss\|feed\|atom"
   ```

#### 問題: SSL証明書エラー

**症状:**
```
ERROR - RSS取得でエラー: SSLError [SSL: CERTIFICATE_VERIFY_FAILED]
```

**解決策:**

1. **証明書の確認**
   ```bash
   # SSL証明書確認
   openssl s_client -connect example.com:443 -servername example.com
   ```

2. **設定でSSL検証無効化（一時的）**
   ```json
   {
     "feeds": [{
       "url": "https://problematic-site.com/feed",
       "ssl_verify": false
     }]
   }
   ```

#### 問題: タイムアウトエラー

**症状:**
```
ERROR - RSS取得でエラー: Timeout
```

**解決策:**

1. **タイムアウト時間延長**
   ```json
   {
     "settings": {
       "request_timeout": 60,
       "max_retries": 3
     }
   }
   ```

2. **Lambda タイムアウト延長**
   ```bash
   aws lambda update-function-configuration \
     --function-name "rss-notifier-prod" \
     --timeout 300 \
     --region $AWS_REGION
   ```

### 4.2 RSS解析エラー

#### 問題: XML/JSON解析失敗

**症状:**
```
ERROR - RSS解析でエラー: not well-formed (invalid token)
```

**解決策:**

1. **フィード形式確認**
   ```bash
   # フィード内容確認
   curl -s "問題のURL" | head -20

   # XML妥当性確認
   curl -s "問題のURL" | xmllint --format -
   ```

2. **エンコーディング問題の対応**
   ```python
   # Python でのエンコーディング確認
   import requests
   response = requests.get("問題のURL")
   print(f"Encoding: {response.encoding}")
   print(f"Content-Type: {response.headers.get('content-type')}")
   ```

---

## 5. Lambda実行関連の問題

### 5.1 Lambda関数エラー

#### 問題: メモリ不足エラー

**症状:**
```
ERROR - Process exited before completing request
```

**解決策:**

1. **メモリ使用量確認**
   ```bash
   # CloudWatch メトリクス確認
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name MemoryUtilization \
     --dimensions Name=FunctionName,Value="rss-notifier-prod" \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average,Maximum \
     --region $AWS_REGION
   ```

2. **メモリ割り当て増加**
   ```bash
   # メモリを1024MBに増加
   aws lambda update-function-configuration \
     --function-name "rss-notifier-prod" \
     --memory-size 1024 \
     --region $AWS_REGION
   ```

#### 問題: タイムアウトエラー

**症状:**
```
Task timed out after 30.00 seconds
```

**解決策:**

1. **処理時間分析**
   ```bash
   # 実行時間ログ確認
   aws logs filter-log-events \
     --log-group-name "/aws/lambda/rss-notifier-prod" \
     --filter-pattern "Duration" \
     --region $AWS_REGION
   ```

2. **タイムアウト延長**
   ```bash
   # タイムアウトを5分に延長
   aws lambda update-function-configuration \
     --function-name "rss-notifier-prod" \
     --timeout 300 \
     --region $AWS_REGION
   ```

3. **処理の最適化**
   - 並列処理数の調整
   - フィード数の削減
   - 不要な処理の除去

### 5.2 環境変数の問題

#### 問題: 環境変数が取得できない

**症状:**
```
KeyError: 'LINE_CHANNEL_TOKEN'
```

**解決策:**

1. **Lambda環境変数確認**
   ```bash
   aws lambda get-function-configuration \
     --function-name "rss-notifier-prod" \
     --region $AWS_REGION \
     --query 'Environment.Variables'
   ```

2. **CloudFormation パラメータ確認**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name rss-line-notifier \
     --region $AWS_REGION \
     --query 'Stacks[0].Parameters'
   ```

3. **環境変数更新**
   ```bash
   # CloudFormation 経由で更新
   ./scripts/deploy.sh
   ```

---

## 6. AWS関連の問題

### 6.1 認証・権限エラー

#### 問題: AccessDenied エラー

**症状:**
```
An error occurred (AccessDenied) when calling the PutObject operation: Access Denied
```

**解決策:**

1. **IAM権限確認**
   ```bash
   # 現在のユーザー確認
   aws sts get-caller-identity

   # アタッチされたポリシー確認
   aws iam list-attached-user-policies --user-name rss-notifier-deploy
   ```

2. **必要な権限の追加**
   ```bash
   # S3フルアクセス権限追加
   aws iam attach-user-policy \
     --user-name rss-notifier-deploy \
     --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
   ```

#### 問題: リージョン関連エラー

**症状:**
```
The specified bucket does not exist in the specified region
```

**解決策:**

1. **リージョン確認**
   ```bash
   # 設定リージョン確認
   aws configure get region

   # S3バケットのリージョン確認
   aws s3api get-bucket-location --bucket $BUCKET_NAME
   ```

2. **リージョン統一**
   ```bash
   # 環境変数でリージョン指定
   export AWS_REGION=ap-northeast-1

   # 再デプロイ
   ./scripts/deploy.sh --region ap-northeast-1
   ```

### 6.2 料金・制限関連

#### 問題: サービス制限に達した

**症状:**
```
LimitExceededException: Rate exceeded
```

**解決策:**

1. **現在の使用量確認**
   ```bash
   # Lambda実行回数確認
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Invocations \
     --dimensions Name=FunctionName,Value="rss-notifier-prod" \
     --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 3600 \
     --statistics Sum \
     --region $AWS_REGION
   ```

2. **制限緩和申請**
   ```bash
   # サービス制限確認
   aws service-quotas list-service-quotas \
     --service-code lambda \
     --region $AWS_REGION
   ```

---

## 7. パフォーマンス関連の問題

### 7.1 処理速度の問題

#### 問題: RSS取得が遅い

**診断:**
```bash
# 個別フィードの処理時間測定
time ./scripts/dev-utils.sh test-rss "https://example.com/feed"
```

**解決策:**

1. **並列処理数調整**
   ```json
   {
     "settings": {
       "parallel_workers": 20,
       "request_timeout": 10
     }
   }
   ```

2. **Lambda性能向上**
   ```bash
   # メモリ増加（CPU性能も向上）
   aws lambda update-function-configuration \
     --function-name "rss-notifier-prod" \
     --memory-size 2048 \
     --region $AWS_REGION
   ```

### 7.2 メモリ使用量の問題

#### 問題: メモリ使用量が高い

**診断:**
```bash
# メモリ使用量履歴
aws logs filter-log-events \
  --log-group-name "/aws/lambda/rss-notifier-prod" \
  --filter-pattern "Max Memory Used" \
  --region $AWS_REGION
```

**解決策:**

1. **処理方法の最適化**
   - ストリーミング処理の導入
   - バッチサイズの調整
   - 不要なデータの早期開放

2. **設定調整**
   ```json
   {
     "settings": {
       "max_articles_per_feed": 10,
       "enable_content_caching": false
     }
   }
   ```

---

## 8. 設定関連の問題

### 8.1 JSON設定ファイルエラー

#### 問題: JSON構文エラー

**症状:**
```
JSONDecodeError: Expecting ',' delimiter
```

**解決策:**

1. **構文確認**
   ```bash
   # JSON妥当性確認
   python3.12 -m json.tool config/rss-config.json

   # オンラインバリデータ使用
   cat config/rss-config.json | jq .
   ```

2. **設定ファイル修復**
   ```bash
   # バックアップから復元
   ./scripts/dev-utils.sh restore-config backups/rss-config_最新.json
   ```

### 8.2 フィード設定の問題

#### 問題: フィードカテゴリが正しく分類されない

**診断:**
```bash
# 記事分類テスト
./scripts/dev-utils.sh test-rss "https://techcrunch.com/feed/" | grep -A5 category
```

**解決策:**

1. **カテゴリキーワード調整**
   ```json
   {
     "category_keywords": {
       "プログラミング": ["Python", "JavaScript", "React", "API"],
       "AI・機械学習": ["AI", "機械学習", "深層学習", "ChatGPT"]
     }
   }
   ```

2. **優先度調整**
   ```json
   {
     "feeds": [{
       "category": "プログラミング",
       "priority": 1,
       "custom_keywords": ["Python", "AWS"]
     }]
   }
   ```

---

## 9. 緊急時の対応

### 9.1 システム停止

#### 完全停止が必要な場合

```bash
# EventBridge ルール無効化（定期実行停止）
aws events disable-rule \
  --name "${STACK_NAME}-ScheduleRule" \
  --region $AWS_REGION

# Lambda関数の無効化
aws lambda put-function-concurrency \
  --function-name "rss-notifier-prod" \
  --reserved-concurrent-executions 0 \
  --region $AWS_REGION
```

#### システム復旧

```bash
# EventBridge ルール有効化
aws events enable-rule \
  --name "${STACK_NAME}-ScheduleRule" \
  --region $AWS_REGION

# Lambda同時実行制限解除
aws lambda delete-function-concurrency \
  --function-name "rss-notifier-prod" \
  --region $AWS_REGION
```

### 9.2 データ復旧

#### S3データの緊急バックアップ

```bash
# 現在の設定をローカルにバックアップ
aws s3 sync s3://$BUCKET_NAME/ ./emergency-backup/ \
  --region $AWS_REGION

# 重要ファイルの個別バックアップ
aws s3 cp s3://$BUCKET_NAME/rss-config.json ./emergency-backup/ \
  --region $AWS_REGION
aws s3 cp s3://$BUCKET_NAME/notification-history.json ./emergency-backup/ \
  --region $AWS_REGION
```

#### システム完全再構築

```bash
# 1. 現在のリソース削除
aws cloudformation delete-stack \
  --stack-name rss-line-notifier \
  --region $AWS_REGION

# 2. 削除完了確認
aws cloudformation wait stack-delete-complete \
  --stack-name rss-line-notifier \
  --region $AWS_REGION

# 3. クリーンアップ
./scripts/dev-utils.sh clean

# 4. 再デプロイ
source .env
./scripts/deploy.sh

# 5. データ復元
aws s3 cp ./emergency-backup/rss-config.json s3://$NEW_BUCKET_NAME/ \
  --region $AWS_REGION
```

---

## トラブルシューティング チートシート

### クイック診断コマンド

```bash
# 全体状況確認
./scripts/dev-utils.sh status

# ログ確認
./scripts/dev-utils.sh logs notifier | tail -50

# テスト実行
./scripts/dev-utils.sh test-lambda notifier
./scripts/dev-utils.sh test-line

# 設定確認
./scripts/dev-utils.sh validate-config

# 手動実行
./scripts/dev-utils.sh invoke-notifier
```

### よくあるエラーと対処

| エラー | コマンド |
|--------|----------|
| デプロイ失敗 | `aws cloudformation describe-stack-events --stack-name rss-line-notifier` |
| Lambda エラー | `./scripts/dev-utils.sh logs notifier` |
| LINE API エラー | `./scripts/dev-utils.sh test-line` |
| RSS 取得エラー | `./scripts/dev-utils.sh test-rss URL` |
| 設定エラー | `./scripts/dev-utils.sh validate-config` |
| 権限エラー | `aws sts get-caller-identity` |

### 緊急連絡先

```
AWS サポート: https://aws.amazon.com/support/
LINE Developers: https://developers.line.biz/ja/support/
GitHub Issues: https://github.com/your-repo/issues
```

---

問題が解決しない場合は、システムログとエラーメッセージを添えて、プロジェクトのIssueトラッカーまたはサポートチャンネルにお問い合わせください。