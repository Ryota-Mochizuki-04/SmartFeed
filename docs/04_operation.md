# 運用ガイド

このガイドでは、RSS LINE Notifier の日常的な運用方法について説明します。

## 目次

1. [日常的な監視](#1-日常的な監視)
2. [RSS設定の管理](#2-rss設定の管理)
3. [通知設定の調整](#3-通知設定の調整)
4. [ログ監視とトラブルシューティング](#4-ログ監視とトラブルシューティング)
5. [パフォーマンス最適化](#5-パフォーマンス最適化)
6. [セキュリティ管理](#6-セキュリティ管理)
7. [バックアップと復旧](#7-バックアップと復旧)
8. [コスト管理](#8-コスト管理)

---

## 1. 日常的な監視

### 1.1 システム状況確認

定期的（週1回程度）にシステム状況を確認します：

```bash
# システム全体の状況確認
./scripts/dev-utils.sh status
```

確認項目：
- CloudFormation スタック状況
- Lambda 関数の状態
- S3 バケットのアクセス状況
- スタック出力情報

### 1.2 LINE Bot動作確認

LINEでBotに以下のコマンドを送信して動作確認：

```
統計
```

期待される応答：
- 総通知送信数
- 総記事処理数
- 平均記事数/通知
- 最終実行時刻

### 1.3 通知履歴の確認

```bash
# 設定とバックアップ状況確認
./scripts/dev-utils.sh validate-config

# 設定ファイルバックアップ
./scripts/dev-utils.sh backup-config
```

---

## 2. RSS設定の管理

### 2.1 RSSフィードの追加

1. **設定ファイルダウンロード**
   ```bash
   # 現在の設定をダウンロード
   BUCKET_NAME=$(aws cloudformation describe-stacks \
     --stack-name $STACK_NAME \
     --region $AWS_REGION \
     --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
     --output text)

   aws s3 cp s3://$BUCKET_NAME/rss-config.json config/rss-config-current.json \
     --region $AWS_REGION
   ```

2. **新しいフィード追加**
   ```json
   {
     "url": "https://example.com/feed.xml",
     "name": "Example Blog",
     "category": "テクノロジー",
     "enabled": true,
     "priority": 2,
     "keywords": ["AI", "機械学習"],
     "filters": {
       "exclude_keywords": ["広告", "PR"],
       "min_content_length": 100
     }
   }
   ```

3. **フィードテスト**
   ```bash
   # 新しいフィードの動作確認
   ./scripts/dev-utils.sh test-rss "https://example.com/feed.xml"
   ```

4. **設定アップロード**
   ```bash
   # 設定ファイルをS3にアップロード
   aws s3 cp config/rss-config-current.json s3://$BUCKET_NAME/rss-config.json \
     --region $AWS_REGION
   ```

### 2.2 フィード品質の監視

定期的にフィードの品質を監視：

```bash
# 各フィードの取得テスト
./scripts/dev-utils.sh test-rss "https://techcrunch.com/feed/"
./scripts/dev-utils.sh test-rss "https://www.itmedia.co.jp/news/rss/rss20.xml"
```

問題のあるフィード：
- 404エラー（フィードが削除された）
- SSL証明書エラー
- タイムアウト
- 不正なXML/JSON形式

### 2.3 カテゴリ分類の調整

通知の分類を改善するためのキーワード調整：

```json
{
  "analysis": {
    "custom_categories": {
      "AI・機械学習": {
        "keywords": ["AI", "機械学習", "ディープラーニング", "ChatGPT"],
        "priority": 1
      },
      "Web開発": {
        "keywords": ["React", "Vue", "JavaScript", "TypeScript"],
        "priority": 2
      }
    }
  }
}
```

---

## 3. 通知設定の調整

### 3.1 通知頻度の調整

EventBridge ルールの変更：

```bash
# 現在のスケジュール確認
aws events describe-rule \
  --name "${STACK_NAME}-ScheduleRule" \
  --region $AWS_REGION

# スケジュール変更（例：1時間間隔）
aws events put-rule \
  --name "${STACK_NAME}-ScheduleRule" \
  --schedule-expression "rate(1 hour)" \
  --region $AWS_REGION
```

よく使用されるスケジュール：
- `rate(30 minutes)` - 30分間隔
- `rate(1 hour)` - 1時間間隔
- `rate(2 hours)` - 2時間間隔
- `cron(0 9,15,21 * * ? *)` - 9時、15時、21時

### 3.2 通知時間の制限

RSS設定で通知時間を制限：

```json
{
  "settings": {
    "notification_time_range": {
      "start": "07:00",
      "end": "23:00",
      "timezone": "Asia/Tokyo"
    },
    "weekend_notifications": false,
    "holiday_notifications": false
  }
}
```

### 3.3 フィルタリング設定

スパムや不要な記事を除外：

```json
{
  "settings": {
    "global_filters": {
      "exclude_keywords": ["広告", "PR", "スポンサード"],
      "min_content_length": 100,
      "max_articles_per_feed": 5,
      "duplicate_threshold": 0.8
    }
  }
}
```

---

## 4. ログ監視とトラブルシューティング

### 4.1 リアルタイムログ監視

```bash
# Notifier関数のリアルタイムログ
./scripts/dev-utils.sh tail-logs notifier

# Webhook関数のリアルタイムログ
./scripts/dev-utils.sh tail-logs webhook
```

### 4.2 エラーパターンの監視

よくあるエラーパターン：

#### RSS取得エラー
```
ERROR - RSS取得でエラー: HTTPError 404
```
**対処**: フィードURLの確認・修正

#### LINE API エラー
```
ERROR - LINE プッシュメッセージの送信に失敗: 401 Unauthorized
```
**対処**: Channel Access Token の確認・更新

#### Lambda タイムアウト
```
ERROR - Task timed out after 30.00 seconds
```
**対処**: タイムアウト時間の増加、処理の最適化

### 4.3 CloudWatch アラーム設定

重要なメトリクスにアラームを設定：

```bash
# Lambda エラー率アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name "RSS-Notifier-Errors" \
  --alarm-description "Lambda function error rate" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --statistic "Sum" \
  --period 300 \
  --threshold 1 \
  --comparison-operator "GreaterThanOrEqualToThreshold" \
  --dimensions Name=FunctionName,Value="rss-notifier-prod" \
  --evaluation-periods 1 \
  --region $AWS_REGION
```

### 4.4 ログ分析

```bash
# エラーログのみ抽出
aws logs filter-log-events \
  --log-group-name "/aws/lambda/rss-notifier-prod" \
  --filter-pattern "ERROR" \
  --region $AWS_REGION

# 特定期間のログ分析
aws logs filter-log-events \
  --log-group-name "/aws/lambda/rss-notifier-prod" \
  --start-time $(date -d "1 day ago" +%s)000 \
  --end-time $(date +%s)000 \
  --region $AWS_REGION
```

---

## 5. パフォーマンス最適化

### 5.1 Lambda関数の最適化

#### メモリ設定調整
```bash
# 現在の設定確認
aws lambda get-function-configuration \
  --function-name "rss-notifier-prod" \
  --region $AWS_REGION

# メモリ増加（処理速度向上）
aws lambda update-function-configuration \
  --function-name "rss-notifier-prod" \
  --memory-size 1024 \
  --region $AWS_REGION
```

#### タイムアウト調整
```bash
# タイムアウト延長
aws lambda update-function-configuration \
  --function-name "rss-notifier-prod" \
  --timeout 60 \
  --region $AWS_REGION
```

### 5.2 並列処理の調整

RSS設定で並列処理数を調整：

```json
{
  "settings": {
    "parallel_workers": 5,
    "request_timeout": 15,
    "max_retries": 2
  }
}
```

パフォーマンス指標：
- `parallel_workers`: 同時処理数（多いほど高速だが、メモリ使用量増加）
- `request_timeout`: タイムアウト時間（短いほど応答性向上）
- `max_retries`: リトライ回数（多いほど信頼性向上だが、処理時間増加）

### 5.3 キャッシュ戦略

重要なデータのキャッシュ：

```json
{
  "settings": {
    "cache_feeds_hours": 4,
    "cache_analysis_days": 1,
    "enable_local_cache": true
  }
}
```

---

## 6. セキュリティ管理

### 6.1 アクセスキーのローテーション

定期的（3-6ヶ月）にアクセスキーを更新：

1. **新しいアクセスキー作成**
   ```bash
   aws iam create-access-key --user-name rss-notifier-deploy
   ```

2. **環境変数更新**
   ```bash
   # 新しいキーで設定更新
   aws configure set aws_access_key_id NEW_ACCESS_KEY
   aws configure set aws_secret_access_key NEW_SECRET_KEY
   ```

3. **動作確認後、古いキー削除**
   ```bash
   aws iam delete-access-key \
     --user-name rss-notifier-deploy \
     --access-key-id OLD_ACCESS_KEY
   ```

### 6.2 LINE トークンの管理

Channel Access Token の定期更新：

1. LINE Developers Console で新しいトークン発行
2. 環境変数とCloudFormationパラメータを更新
3. Lambda関数の再デプロイ

### 6.3 CloudFormation スタックの保護

```bash
# スタック削除保護を有効化
aws cloudformation update-termination-protection \
  --enable-termination-protection \
  --stack-name $STACK_NAME \
  --region $AWS_REGION
```

### 6.4 S3バケットセキュリティ

```bash
# バケットのパブリックアクセス確認
aws s3api get-public-access-block \
  --bucket $BUCKET_NAME \
  --region $AWS_REGION

# 暗号化設定確認
aws s3api get-bucket-encryption \
  --bucket $BUCKET_NAME \
  --region $AWS_REGION
```

---

## 7. バックアップと復旧

### 7.1 定期バックアップ

週1回程度、設定ファイルをバックアップ：

```bash
# バックアップ作成
./scripts/dev-utils.sh backup-config

# バックアップファイル確認
ls -la backups/
```

### 7.2 設定復旧

問題が発生した場合の復旧手順：

```bash
# バックアップファイル一覧
ls backups/rss-config_*.json

# 最新バックアップで復旧
LATEST_BACKUP=$(ls -t backups/rss-config_*.json | head -1)
./scripts/dev-utils.sh restore-config "$LATEST_BACKUP"
```

### 7.3 完全復旧

システム全体を復旧する場合：

```bash
# 1. 現在のスタック削除
aws cloudformation delete-stack \
  --stack-name $STACK_NAME \
  --region $AWS_REGION

# 2. 削除完了待機
aws cloudformation wait stack-delete-complete \
  --stack-name $STACK_NAME \
  --region $AWS_REGION

# 3. 再デプロイ
source .env
./scripts/deploy.sh

# 4. 設定復元
./scripts/dev-utils.sh restore-config "$LATEST_BACKUP"
```

---

## 8. コスト管理

### 8.1 コスト監視

```bash
# 月間コスト確認
aws ce get-cost-and-usage \
  --time-period Start=2024-12-01,End=2024-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --region us-east-1
```

### 8.2 コスト最適化

#### Lambda実行回数の削減
- 通知頻度の調整（30分 → 1時間）
- フィード数の見直し
- 不要なフィードの無効化

#### S3ストレージの最適化
```bash
# 古い履歴ファイルの削除
aws s3 rm s3://$BUCKET_NAME/notification-history-old.json --region $AWS_REGION

# ライフサイクルポリシー設定（90日後削除）
aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --lifecycle-configuration file://lifecycle-policy.json \
  --region $AWS_REGION
```

#### CloudWatch ログの管理
```bash
# ログ保持期間設定（30日）
aws logs put-retention-policy \
  --log-group-name "/aws/lambda/rss-notifier-prod" \
  --retention-in-days 30 \
  --region $AWS_REGION
```

### 8.3 コスト予算アラート

月額予算アラートの設定：

```json
{
  "BudgetName": "RSS-LINE-Notifier-Budget",
  "BudgetLimit": {
    "Amount": "10.0",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

---

## 日常運用チェックリスト

### 週次チェック（5分程度）

```
□ システム状況確認（./scripts/dev-utils.sh status）
□ LINE Bot動作確認（統計コマンド送信）
□ エラーログ確認
□ 設定バックアップ作成
```

### 月次チェック（15分程度）

```
□ RSS フィード品質確認
□ 通知統計の分析
□ コスト確認
□ パフォーマンス確認
□ セキュリティ設定確認
```

### 四半期チェック（30分程度）

```
□ アクセスキーローテーション
□ LINE トークン更新確認
□ システム最適化検討
□ 不要なリソース削除
□ バックアップファイル整理
```

---

## トラブル発生時の対応フロー

1. **症状の確認**
   - LINE通知が届かない
   - エラーメッセージの確認

2. **ログ確認**
   ```bash
   ./scripts/dev-utils.sh logs notifier
   ./scripts/dev-utils.sh logs webhook
   ```

3. **システム状況確認**
   ```bash
   ./scripts/dev-utils.sh status
   ```

4. **設定確認**
   ```bash
   ./scripts/dev-utils.sh validate-config
   ```

5. **手動テスト実行**
   ```bash
   ./scripts/dev-utils.sh invoke-notifier
   ./scripts/dev-utils.sh test-line
   ```

6. **必要に応じて復旧実行**
   ```bash
   ./scripts/dev-utils.sh restore-config BACKUP_FILE
   ```

---

## 次のステップ

運用に慣れてきたら、以下の拡張を検討してください：

- カスタムフィルタリングロジックの追加
- 複数ユーザー対応
- Web UI の追加
- 外部サービス連携（Slack、Discord等）

詳細は [拡張ガイド](05_advanced.md) を参照してください。