# RSS LINE Notifier - 環境変数・設定ファイル仕様書

## ⚙️ 環境変数設計

### 環境変数一覧

#### Notifier Lambda 環境変数
| 変数名 | 必須 | デフォルト値 | 説明 | 例 |
|--------|------|-------------|------|-----|
| **LINE_TOKEN** | ✅ | - | LINE Channel Access Token | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **LINE_USER_ID** | ✅ | - | 通知先 LINE User ID | `Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **BUCKET_NAME** | ✅ | - | S3バケット名 | `rss-line-notifier-v1-123456789012` |
| **AWS_REGION** | ❌ | `ap-northeast-1` | AWSリージョン | `ap-northeast-1` |
| **LOG_LEVEL** | ❌ | `INFO` | ログレベル | `DEBUG`, `INFO`, `WARN`, `ERROR` |
| **MAX_FEEDS** | ❌ | `100` | 最大フィード数 | `100` |
| **MAX_ARTICLES_PER_FEED** | ❌ | `10` | フィード毎最大記事数 | `10` |
| **ARTICLE_AGE_HOURS** | ❌ | `24` | 記事有効期間（時間） | `24` |
| **REQUEST_TIMEOUT** | ❌ | `30` | HTTP リクエストタイムアウト（秒） | `30` |
| **PARALLEL_WORKERS** | ❌ | `10` | 並列取得ワーカー数 | `10` |

#### Webhook Lambda 環境変数
| 変数名 | 必須 | デフォルト値 | 説明 | 例 |
|--------|------|-------------|------|-----|
| **LINE_TOKEN** | ✅ | - | LINE Channel Access Token | `（上記と同じ）` |
| **LINE_CHANNEL_SECRET** | ✅ | - | LINE Channel Secret | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| **BUCKET_NAME** | ✅ | - | S3バケット名 | `rss-line-notifier-v1-123456789012` |
| **NOTIFIER_FUNCTION_NAME** | ✅ | - | Notifier Lambda 関数名 | `rss-notifier-v1` |
| **AWS_REGION** | ❌ | `ap-northeast-1` | AWSリージョン | `ap-northeast-1` |
| **LOG_LEVEL** | ❌ | `INFO` | ログレベル | `DEBUG`, `INFO`, `WARN`, `ERROR` |
| **LOADING_TIMEOUT** | ❌ | `5` | Loading Animation 表示時間（秒） | `5` |
| **MAX_COMMAND_LENGTH** | ❌ | `1000` | コマンド最大文字数 | `1000` |

### 環境変数設定方法

#### CloudFormation での設定
```yaml
# cloudformation-template.yaml
NotifierLambdaFunction:
  Type: AWS::Lambda::Function
  Properties:
    Environment:
      Variables:
        LINE_TOKEN: !Ref LineToken
        LINE_USER_ID: !Ref LineUserId
        BUCKET_NAME: !Ref RssNotifierBucket
        AWS_REGION: !Ref "AWS::Region"
        LOG_LEVEL: INFO
        MAX_FEEDS: 100
        ARTICLE_AGE_HOURS: 24
        REQUEST_TIMEOUT: 30
        PARALLEL_WORKERS: 10
```

#### AWS CLI での設定
```bash
# Notifier Lambda 環境変数設定
aws lambda update-function-configuration \
  --function-name rss-notifier-v1 \
  --environment Variables='{
    "LINE_TOKEN":"your_line_token_here",
    "LINE_USER_ID":"your_user_id_here",
    "BUCKET_NAME":"rss-line-notifier-v1-123456789012",
    "LOG_LEVEL":"INFO",
    "MAX_FEEDS":"100",
    "ARTICLE_AGE_HOURS":"24",
    "REQUEST_TIMEOUT":"30",
    "PARALLEL_WORKERS":"10"
  }' \
  --region ap-northeast-1

# Webhook Lambda 環境変数設定
aws lambda update-function-configuration \
  --function-name rss-webhook-v1 \
  --environment Variables='{
    "LINE_TOKEN":"your_line_token_here",
    "LINE_CHANNEL_SECRET":"your_channel_secret_here",
    "BUCKET_NAME":"rss-line-notifier-v1-123456789012",
    "NOTIFIER_FUNCTION_NAME":"rss-notifier-v1",
    "LOG_LEVEL":"INFO",
    "LOADING_TIMEOUT":"5",
    "MAX_COMMAND_LENGTH":"1000"
  }' \
  --region ap-northeast-1
```

## 📁 設定ファイル仕様

### 1. CloudFormation パラメータファイル

#### parameters.json 構造
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

#### パラメータ詳細定義

| パラメータ | 必須 | タイプ | 制約 | 説明 |
|------------|------|-------|------|------|
| **LineToken** | ✅ | String | NoEcho: true | LINE Channel Access Token |
| **LineChannelSecret** | ✅ | String | NoEcho: true | LINE Channel Secret |
| **LineUserId** | ✅ | String | - | 通知先ユーザーID |
| **NotificationTime** | ❌ | String | Cron形式 | 通知実行時刻（UTC） |
| **Environment** | ❌ | String | dev/staging/v1 | 環境名 |

#### parameters.json.template
```json
[
  {
    "ParameterKey": "LineToken",
    "ParameterValue": "REPLACE_WITH_YOUR_LINE_CHANNEL_ACCESS_TOKEN"
  },
  {
    "ParameterKey": "LineChannelSecret",
    "ParameterValue": "REPLACE_WITH_YOUR_LINE_CHANNEL_SECRET"
  },
  {
    "ParameterKey": "LineUserId",
    "ParameterValue": "REPLACE_WITH_YOUR_LINE_USER_ID"
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

### 2. アプリケーション設定ファイル

#### RSS設定 (S3: rss-list.json)
```json
{
  "version": "2.1",
  "updated_at": "2024-01-01T12:00:00Z",
  "config": {
    "max_feeds": 100,
    "max_articles_per_notification": 30,
    "notification_hours": [12.5, 21.0],
    "timezone": "Asia/Tokyo",
    "retry_config": {
      "max_retries": 3,
      "retry_delay": 5,
      "backoff_multiplier": 2.0
    },
    "cache_config": {
      "feed_cache_ttl": 300,
      "image_cache_ttl": 3600
    },
    "notification_config": {
      "enable_images": true,
      "enable_priority_ranking": true,
      "enable_reading_time": true,
      "max_carousel_items": 10
    }
  },
  "feeds": [
    {
      "id": "feed_001",
      "url": "https://qiita.com/popular/items/feed",
      "title": "Qiita - 人気の記事",
      "category": "プログラミング",
      "enabled": true,
      "priority": 1,
      "added_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 通知履歴設定 (S3: notified-history.json)
```json
{
  "version": "2.1",
  "updated_at": "2024-01-01T12:00:00Z",
  "config": {
    "max_history_size": 1000,
    "cleanup_days": 30,
    "auto_cleanup": true,
    "duplicate_detection": {
      "method": "url_hash",
      "similarity_threshold": 0.9
    }
  },
  "history": []
}
```

### 3. Lambda 関数設定

#### requirements.txt (共通)
```
boto3>=1.26.0
feedparser>=6.0.10
requests>=2.28.0
python-dateutil>=2.8.2
```

#### Lambda レイヤー設定（オプション）
```yaml
# 共通ライブラリレイヤー
CommonLibrariesLayer:
  Type: AWS::Lambda::LayerVersion
  Properties:
    LayerName: !Sub "${Environment}-rss-notifier-common"
    Description: "Common libraries for RSS Notifier"
    Content:
      S3Bucket: !Ref DeploymentBucket
      S3Key: "layers/common-libraries.zip"
    CompatibleRuntimes:
      - python3.9
```

## 🔧 設定管理ユーティリティ

### 設定検証スクリプト
```python
#!/usr/bin/env python3
"""
設定ファイル検証スクリプト
"""

import json
import os
import sys
from typing import Dict, List, Optional
import boto3
from jsonschema import validate, ValidationError

def validate_parameters_json(file_path: str) -> bool:
    """parameters.json の検証"""
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "ParameterKey": {"type": "string"},
                "ParameterValue": {"type": "string"}
            },
            "required": ["ParameterKey", "ParameterValue"]
        }
    }

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        validate(data, schema)

        # 必須パラメータチェック
        required_keys = ["LineToken", "LineChannelSecret", "LineUserId"]
        parameter_keys = [p["ParameterKey"] for p in data]

        missing_keys = [key for key in required_keys if key not in parameter_keys]
        if missing_keys:
            print(f"❌ Missing required parameters: {missing_keys}")
            return False

        # 値の妥当性チェック
        for param in data:
            key, value = param["ParameterKey"], param["ParameterValue"]

            if key == "LineToken" and not value.startswith("REPLACE_"):
                if len(value) < 100:
                    print(f"❌ LineToken seems too short: {len(value)} chars")
                    return False

            if key == "LineUserId" and not value.startswith("REPLACE_"):
                if not value.startswith("U") or len(value) != 33:
                    print(f"❌ LineUserId format invalid: {value}")
                    return False

        print("✅ parameters.json validation passed")
        return True

    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False
    except ValidationError as e:
        print(f"❌ Schema validation error: {e}")
        return False

def validate_environment_variables() -> bool:
    """環境変数検証"""
    required_vars = {
        "LINE_TOKEN": str,
        "LINE_USER_ID": str,
        "BUCKET_NAME": str
    }

    missing_vars = []
    invalid_vars = []

    for var_name, var_type in required_vars.items():
        value = os.environ.get(var_name)

        if not value:
            missing_vars.append(var_name)
            continue

        # 型チェック
        try:
            if var_type == int:
                int(value)
            elif var_type == float:
                float(value)
        except ValueError:
            invalid_vars.append(f"{var_name}: expected {var_type.__name__}")

    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False

    if invalid_vars:
        print(f"❌ Invalid environment variables: {invalid_vars}")
        return False

    print("✅ Environment variables validation passed")
    return True

def test_aws_connectivity() -> bool:
    """AWS 接続テスト"""
    try:
        # S3 接続テスト
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('BUCKET_NAME')

        if bucket_name:
            s3_client.head_bucket(Bucket=bucket_name)
            print("✅ S3 bucket access confirmed")

        # Lambda 接続テスト
        lambda_client = boto3.client('lambda')
        function_name = os.environ.get('NOTIFIER_FUNCTION_NAME')

        if function_name:
            lambda_client.get_function(FunctionName=function_name)
            print("✅ Lambda function access confirmed")

        return True

    except Exception as e:
        print(f"❌ AWS connectivity test failed: {e}")
        return False

def main():
    """メイン実行"""
    print("🔧 Configuration Validation Starting...")

    all_passed = True

    # parameters.json 検証
    if os.path.exists("infrastructure/parameters.json"):
        all_passed &= validate_parameters_json("infrastructure/parameters.json")
    else:
        print("⚠️  parameters.json not found, skipping validation")

    # 環境変数検証
    all_passed &= validate_environment_variables()

    # AWS接続テスト
    all_passed &= test_aws_connectivity()

    if all_passed:
        print("🎉 All configuration validations passed!")
        sys.exit(0)
    else:
        print("💥 Configuration validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 設定生成スクリプト
```python
#!/usr/bin/env python3
"""
設定ファイル生成スクリプト
"""

import json
import os
from datetime import datetime, timezone

def create_default_rss_config() -> dict:
    """デフォルトRSS設定生成"""
    return {
        "version": "2.1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "max_feeds": 100,
            "max_articles_per_notification": 30,
            "notification_hours": [12.5, 21.0],
            "timezone": "Asia/Tokyo",
            "retry_config": {
                "max_retries": 3,
                "retry_delay": 5,
                "backoff_multiplier": 2.0
            },
            "notification_config": {
                "enable_images": True,
                "enable_priority_ranking": True,
                "enable_reading_time": True,
                "max_carousel_items": 10
            }
        },
        "feeds": [],
        "statistics": {
            "total_feeds": 0,
            "active_feeds": 0,
            "total_articles_processed": 0,
            "total_notifications_sent": 0
        }
    }

def create_default_history_config() -> dict:
    """デフォルト履歴設定生成"""
    return {
        "version": "2.1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "max_history_size": 1000,
            "cleanup_days": 30,
            "auto_cleanup": True,
            "duplicate_detection": {
                "method": "url_hash",
                "similarity_threshold": 0.9
            }
        },
        "history": [],
        "statistics": {
            "total_notifications": 0,
            "oldest_record": None,
            "last_cleanup": datetime.now(timezone.utc).isoformat(),
            "category_stats": {}
        }
    }

def create_parameters_template() -> list:
    """パラメータテンプレート生成"""
    return [
        {
            "ParameterKey": "LineToken",
            "ParameterValue": "REPLACE_WITH_YOUR_LINE_CHANNEL_ACCESS_TOKEN"
        },
        {
            "ParameterKey": "LineChannelSecret",
            "ParameterValue": "REPLACE_WITH_YOUR_LINE_CHANNEL_SECRET"
        },
        {
            "ParameterKey": "LineUserId",
            "ParameterValue": "REPLACE_WITH_YOUR_LINE_USER_ID"
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

def main():
    """設定ファイル生成実行"""
    print("📝 Generating configuration files...")

    # ディレクトリ作成
    os.makedirs("config/templates", exist_ok=True)

    # RSS設定テンプレート
    rss_config = create_default_rss_config()
    with open("config/templates/rss-list.json", "w", encoding="utf-8") as f:
        json.dump(rss_config, f, ensure_ascii=False, indent=2)
    print("✅ Generated: config/templates/rss-list.json")

    # 履歴設定テンプレート
    history_config = create_default_history_config()
    with open("config/templates/notified-history.json", "w", encoding="utf-8") as f:
        json.dump(history_config, f, ensure_ascii=False, indent=2)
    print("✅ Generated: config/templates/notified-history.json")

    # パラメータテンプレート
    if not os.path.exists("infrastructure/parameters.json"):
        params = create_parameters_template()
        with open("infrastructure/parameters.json.template", "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        print("✅ Generated: infrastructure/parameters.json.template")
    else:
        print("⚠️  parameters.json already exists, skipping")

    print("🎉 Configuration file generation completed!")

if __name__ == "__main__":
    main()
```

## 🔐 セキュリティ考慮事項

### 機密情報管理
```bash
# 環境変数の暗号化（KMS使用）
aws lambda update-function-configuration \
  --function-name rss-notifier-v1 \
  --kms-key-arn arn:aws:kms:ap-northeast-1:123456789012:key/abcd1234-a123-456a-a12b-a123b4cd56ef \
  --region ap-northeast-1

# SSM Parameter Store 使用（推奨）
aws ssm put-parameter \
  --name "/rss-notifier/v1/line-token" \
  --value "your_line_token" \
  --type "SecureString" \
  --region ap-northeast-1
```

### アクセス制御
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": [
        "arn:aws:ssm:ap-northeast-1:*:parameter/rss-notifier/v1/*"
      ]
    }
  ]
}
```

このドキュメントにより、環境変数と設定ファイルの適切な管理が可能になります。