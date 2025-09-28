# RSS LINE Notifier - データベース・ストレージ設計書

## 💾 ストレージアーキテクチャ概要

### ストレージ戦略
- **メインストレージ**: Amazon S3 (JSON形式でのファイルベース管理)
- **設計思想**: シンプル・軽量・コスト効率重視
- **データ形式**: JSON (可読性・メンテナンス性・互換性)
- **アクセスパターン**: 低頻度読み書き、小サイズデータ

### なぜS3 + JSONか？
1. **シンプルさ**: データベース運用コスト削減
2. **コスト効率**: 小規模データに最適
3. **可用性**: 99.999999999% (11 9's) の耐久性
4. **バックアップ**: 自動バージョニング対応
5. **スケーラビリティ**: 将来的なDB移行も容易

## 📁 S3バケット設計

### バケット構成
```
rss-line-notifier-v1-{AccountId}/
├── rss-list.json                    # RSS設定マスター
├── notified-history.json            # 通知履歴
├── users/                           # マルチユーザー拡張用（将来）
│   ├── {user_id}/
│   │   ├── rss-list.json
│   │   └── notified-history.json
├── backups/                         # 定期バックアップ（オプション）
│   ├── {date}/
│   │   ├── rss-list.json
│   │   └── notified-history.json
└── temp/                           # 一時ファイル
    └── processing/
```

### バケットポリシー設計
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::rss-line-notifier-v1-{AccountId}",
        "arn:aws:s3:::rss-line-notifier-v1-{AccountId}/*"
      ],
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalServiceName": ["lambda.amazonaws.com"]
        }
      }
    },
    {
      "Sid": "AllowLambdaAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::{AccountId}:role/NotifierLambdaRole",
          "arn:aws:iam::{AccountId}:role/WebhookLambdaRole"
        ]
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::rss-line-notifier-v1-{AccountId}/*"
    }
  ]
}
```

## 📋 データモデル設計

### 1. RSS設定データ (rss-list.json)

#### データ構造
```json
{
  "version": "2.1",
  "updated_at": "2024-01-01T12:00:00Z",
  "config": {
    "max_feeds": 100,
    "notification_hours": [12.5, 21.0],
    "timezone": "Asia/Tokyo"
  },
  "feeds": [
    {
      "id": "feed_001",
      "url": "https://qiita.com/popular/items/feed",
      "title": "Qiita - 人気の記事",
      "category": "プログラミング",
      "enabled": true,
      "priority": 1,
      "added_at": "2024-01-01T00:00:00Z",
      "last_checked": "2024-01-01T12:00:00Z",
      "check_count": 150,
      "success_rate": 0.98,
      "metadata": {
        "description": "プログラマの技術情報共有サービス",
        "language": "ja",
        "feed_type": "rss2.0",
        "update_frequency": "hourly"
      },
      "validation": {
        "last_validated": "2024-01-01T00:00:00Z",
        "is_valid": true,
        "error_count": 2,
        "last_error": null
      }
    }
  ],
  "statistics": {
    "total_feeds": 15,
    "active_feeds": 13,
    "total_articles_processed": 5420,
    "total_notifications_sent": 486,
    "avg_articles_per_notification": 11.2
  }
}
```

#### フィールド定義

| フィールド | 型 | 必須 | 説明 |
|------------|----|----|------|
| **version** | string | ✅ | データスキーマバージョン |
| **updated_at** | ISO8601 | ✅ | 最終更新日時（UTC） |
| **feeds[].id** | string | ✅ | 一意のフィードID |
| **feeds[].url** | string | ✅ | RSSフィードURL |
| **feeds[].title** | string | ✅ | フィード表示名 |
| **feeds[].category** | string | ✅ | カテゴリ分類 |
| **feeds[].enabled** | boolean | ✅ | 有効/無効フラグ |
| **feeds[].priority** | integer | ❌ | 表示優先度（1-10） |
| **feeds[].added_at** | ISO8601 | ✅ | 追加日時 |
| **feeds[].last_checked** | ISO8601 | ❌ | 最終チェック日時 |
| **feeds[].success_rate** | float | ❌ | 成功率（0.0-1.0） |

#### カテゴリマスター
```python
FEED_CATEGORIES = {
    "プログラミング": {
        "keywords": ["プログラミング", "コード", "開発", "programming", "coding"],
        "color": "#2E7D32",
        "icon": "💻",
        "priority": 1
    },
    "テクノロジー": {
        "keywords": ["テクノロジー", "技術", "IT", "technology", "tech"],
        "color": "#1976D2",
        "icon": "🔧",
        "priority": 2
    },
    "マンガ・エンタメ": {
        "keywords": ["マンガ", "アニメ", "ゲーム", "エンタメ", "entertainment"],
        "color": "#F57C00",
        "icon": "🎮",
        "priority": 3
    },
    "ニュース": {
        "keywords": ["ニュース", "政治", "経済", "news", "politics"],
        "color": "#5D4037",
        "icon": "📰",
        "priority": 4
    },
    "その他": {
        "keywords": [],
        "color": "#616161",
        "icon": "📝",
        "priority": 99
    }
}
```

### 2. 通知履歴データ (notified-history.json)

#### データ構造
```json
{
  "version": "2.1",
  "updated_at": "2024-01-01T12:00:00Z",
  "config": {
    "max_history_size": 1000,
    "cleanup_days": 30,
    "auto_cleanup": true
  },
  "history": [
    {
      "id": "hist_001",
      "title": "Pythonの新機能について解説",
      "link": "https://qiita.com/example/items/12345",
      "feed_id": "feed_001",
      "feed_title": "Qiita - 人気の記事",
      "category": "プログラミング",
      "notified_at": "2024-01-01T12:00:00Z",
      "article_published_at": "2024-01-01T10:00:00Z",
      "article_hash": "sha256:abcd1234...",
      "notification_batch_id": "batch_20240101_120000",
      "metadata": {
        "article_type": "技術解説",
        "difficulty": "中級",
        "reading_time": "5分",
        "priority_rank": 1,
        "image_url": "https://example.com/image.jpg"
      }
    }
  ],
  "statistics": {
    "total_notifications": 486,
    "oldest_record": "2023-12-01T00:00:00Z",
    "last_cleanup": "2024-01-01T00:00:00Z",
    "avg_daily_notifications": 16.2,
    "category_stats": {
      "プログラミング": 245,
      "テクノロジー": 132,
      "マンガ・エンタメ": 89,
      "ニュース": 20
    }
  }
}
```

#### フィールド定義

| フィールド | 型 | 必須 | 説明 |
|------------|----|----|------|
| **history[].id** | string | ✅ | 通知履歴ID |
| **history[].title** | string | ✅ | 記事タイトル |
| **history[].link** | string | ✅ | 記事URL（一意キー） |
| **history[].feed_id** | string | ✅ | 元フィードID |
| **history[].notified_at** | ISO8601 | ✅ | 通知日時 |
| **history[].article_hash** | string | ✅ | 記事内容ハッシュ |
| **history[].batch_id** | string | ✅ | 通知バッチID |

## 🔧 データアクセス層設計

### S3操作クラス
```python
import boto3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

class S3DataManager:
    """S3データアクセス管理クラス"""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        self.logger = logging.getLogger(__name__)

    def load_rss_config(self) -> Dict:
        """RSS設定読み込み"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key='rss-list.json'
            )
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            self._validate_rss_config(data)
            return data
        except Exception as e:
            self.logger.error(f"Failed to load RSS config: {e}")
            return self._create_default_rss_config()

    def save_rss_config(self, config_data: Dict) -> bool:
        """RSS設定保存"""
        try:
            # バージョン・更新日時の自動設定
            config_data['version'] = '2.1'
            config_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            # バリデーション
            self._validate_rss_config(config_data)

            # S3保存
            json_content = json.dumps(config_data, ensure_ascii=False, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key='rss-list.json',
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to save RSS config: {e}")
            return False

    def load_notification_history(self) -> Dict:
        """通知履歴読み込み"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key='notified-history.json'
            )
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            return data
        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            return self._create_default_history()

    def append_notification_history(self, articles: List[Dict]) -> bool:
        """通知履歴追加"""
        try:
            # 既存履歴読み込み
            history_data = self.load_notification_history()

            # 新規履歴追加
            batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            for article in articles:
                history_entry = {
                    'id': f"hist_{int(datetime.now().timestamp() * 1000)}",
                    'title': article['title'],
                    'link': article['link'],
                    'feed_id': article.get('feed_id', ''),
                    'feed_title': article.get('feed_title', ''),
                    'category': article.get('category', 'その他'),
                    'notified_at': datetime.now(timezone.utc).isoformat(),
                    'article_published_at': article.get('published_at', ''),
                    'article_hash': self._generate_article_hash(article),
                    'notification_batch_id': batch_id,
                    'metadata': article.get('metadata', {})
                }
                history_data['history'].append(history_entry)

            # 履歴サイズ制限・クリーンアップ
            self._cleanup_history(history_data)

            # 統計更新
            self._update_history_statistics(history_data)

            # 保存
            return self.save_notification_history(history_data)

        except Exception as e:
            self.logger.error(f"Failed to append history: {e}")
            return False

    def _cleanup_history(self, history_data: Dict) -> None:
        """履歴クリーンアップ"""
        max_size = history_data.get('config', {}).get('max_history_size', 1000)

        # サイズ制限
        if len(history_data['history']) > max_size:
            # 古い順にソートして削除
            history_data['history'].sort(key=lambda x: x['notified_at'])
            history_data['history'] = history_data['history'][-max_size:]

        # 古い記録削除（30日以上前）
        cleanup_days = history_data.get('config', {}).get('cleanup_days', 30)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=cleanup_days)
        cutoff_iso = cutoff_date.isoformat()

        history_data['history'] = [
            h for h in history_data['history']
            if h['notified_at'] > cutoff_iso
        ]

    def _generate_article_hash(self, article: Dict) -> str:
        """記事ハッシュ生成"""
        import hashlib
        content = f"{article['title']}{article['link']}"
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
```

### データモデルクラス
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class RSSFeed:
    """RSSフィードデータモデル"""
    id: str
    url: str
    title: str
    category: str
    enabled: bool = True
    priority: int = 5
    added_at: Optional[str] = None
    last_checked: Optional[str] = None
    success_rate: float = 1.0
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now(timezone.utc).isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class NotificationHistory:
    """通知履歴データモデル"""
    id: str
    title: str
    link: str
    feed_id: str
    feed_title: str
    category: str
    notified_at: str
    article_hash: str
    notification_batch_id: str
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
```

## 🔍 データ検索・フィルタリング

### 履歴検索機能
```python
class HistorySearchManager:
    """履歴検索管理"""

    def __init__(self, s3_manager: S3DataManager):
        self.s3_manager = s3_manager

    def is_article_notified(self, article_link: str) -> bool:
        """記事通知済み判定"""
        history = self.s3_manager.load_notification_history()
        return any(h['link'] == article_link for h in history['history'])

    def get_recent_notifications(self, days: int = 7) -> List[Dict]:
        """最近の通知履歴取得"""
        history = self.s3_manager.load_notification_history()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        return [
            h for h in history['history']
            if h['notified_at'] > cutoff_iso
        ]

    def get_category_statistics(self) -> Dict[str, int]:
        """カテゴリ別統計"""
        history = self.s3_manager.load_notification_history()
        stats = {}
        for h in history['history']:
            category = h.get('category', 'その他')
            stats[category] = stats.get(category, 0) + 1
        return stats
```

## 🔐 データセキュリティ

### 暗号化設定
```yaml
S3 Encryption:
  Type: "AES256"
  KMS: false  # コスト考慮でAES256を選択

Lambda Environment Variables:
  Encryption: true
  KMS_Key: "alias/lambda-environment-keys"
```

### アクセスパターン
```python
# 読み取り専用操作
READ_OPERATIONS = [
    "s3:GetObject",
    "s3:GetObjectVersion"
]

# 書き込み操作
WRITE_OPERATIONS = [
    "s3:PutObject",
    "s3:PutObjectAcl"
]

# 禁止操作
FORBIDDEN_OPERATIONS = [
    "s3:DeleteObject",
    "s3:DeleteBucket",
    "s3:PutBucketPolicy"
]
```

## 📊 パフォーマンス最適化

### キャッシング戦略
```python
import functools
import time
from typing import Dict

class CacheManager:
    """シンプルなメモリキャッシュ"""

    def __init__(self):
        self._cache = {}
        self._timestamps = {}

    def cached_load(self, key: str, ttl: int = 300):
        """TTL付きキャッシュデコレータ"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                now = time.time()
                if (key in self._cache and
                    key in self._timestamps and
                    now - self._timestamps[key] < ttl):
                    return self._cache[key]

                result = func(*args, **kwargs)
                self._cache[key] = result
                self._timestamps[key] = now
                return result
            return wrapper
        return decorator

# 使用例
cache_manager = CacheManager()

@cache_manager.cached_load('rss_config', ttl=300)
def load_rss_config_cached():
    return s3_manager.load_rss_config()
```

### バッチ処理最適化
```python
def batch_update_feeds(feed_updates: List[Dict]) -> bool:
    """フィード情報一括更新"""
    try:
        config = load_rss_config()

        # フィードIDでインデックス作成
        feed_index = {feed['id']: i for i, feed in enumerate(config['feeds'])}

        # バッチ更新実行
        for update in feed_updates:
            feed_id = update['id']
            if feed_id in feed_index:
                idx = feed_index[feed_id]
                config['feeds'][idx].update(update)

        # 一括保存
        return save_rss_config(config)
    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        return False
```

## 🚀 将来の拡張設計

### マルチユーザー対応
```python
class MultiUserDataManager(S3DataManager):
    """マルチユーザー対応データ管理"""

    def __init__(self, bucket_name: str, user_id: str):
        super().__init__(bucket_name)
        self.user_id = user_id

    def get_user_rss_key(self) -> str:
        return f"users/{self.user_id}/rss-list.json"

    def get_user_history_key(self) -> str:
        return f"users/{self.user_id}/notified-history.json"

    def load_rss_config(self) -> Dict:
        """ユーザー固有RSS設定読み込み"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.get_user_rss_key()
            )
            # ... 既存実装
        except self.s3_client.exceptions.NoSuchKey:
            # ユーザー初回時のデフォルト設定作成
            return self._create_user_default_config()
```

### DynamoDB移行パス
```python
# 将来的なDynamoDB移行時の互換性維持
class DynamoDBDataManager:
    """DynamoDB対応データ管理（将来拡張）"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def migrate_from_s3(self, s3_manager: S3DataManager) -> bool:
        """S3からDynamoDBへのデータ移行"""
        # S3データ読み込み
        rss_config = s3_manager.load_rss_config()
        history = s3_manager.load_notification_history()

        # DynamoDB形式に変換・保存
        # ... 移行実装
```

このデータベース・ストレージ設計により、シンプルかつ拡張可能なデータ管理が実現されます。