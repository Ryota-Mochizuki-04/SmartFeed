"""
RSS LINE Notifier - S3データ管理クラス
Amazon S3を使用したデータアクセス層の実装
"""

import boto3
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from botocore.exceptions import ClientError, NoCredentialsError


# ログ設定
logger = logging.getLogger(__name__)


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
    validation: Optional[Dict] = None

    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now(timezone.utc).isoformat()
        if self.metadata is None:
            self.metadata = {}
        if self.validation is None:
            self.validation = {
                "last_validated": self.added_at,
                "is_valid": True,
                "error_count": 0,
                "last_error": None
            }


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
    article_published_at: Optional[str] = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class S3DataManager:
    """S3データアクセス管理クラス"""

    def __init__(self, bucket_name: str, region_name: str = 'ap-northeast-1'):
        """
        S3データマネージャー初期化

        Args:
            bucket_name: S3バケット名
            region_name: AWSリージョン名
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.s3_client = boto3.client('s3', region_name=region_name)
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
            self.logger.info(f"RSS設定を正常に読み込みました。フィード数: {len(data.get('feeds', []))}")
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                self.logger.info("RSS設定ファイルが存在しません。デフォルト設定を作成します。")
                return self._create_default_rss_config()
            else:
                self.logger.error(f"RSS設定の読み込みに失敗しました: {e}")
                raise
        except Exception as e:
            self.logger.error(f"RSS設定の読み込み中に予期しないエラーが発生: {e}")
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

            self.logger.info("RSS設定を正常に保存しました")
            return True
        except Exception as e:
            self.logger.error(f"RSS設定の保存に失敗しました: {e}")
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

            self.logger.info(f"通知履歴を正常に読み込みました。履歴数: {len(data.get('history', []))}")
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                self.logger.info("通知履歴ファイルが存在しません。デフォルト履歴を作成します。")
                return self._create_default_history()
            else:
                self.logger.error(f"通知履歴の読み込みに失敗しました: {e}")
                raise
        except Exception as e:
            self.logger.error(f"通知履歴の読み込み中に予期しないエラーが発生: {e}")
            return self._create_default_history()

    def save_notification_history(self, history_data: Dict) -> bool:
        """通知履歴保存"""
        try:
            # バージョン・更新日時の自動設定
            history_data['version'] = '2.1'
            history_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            # S3保存
            json_content = json.dumps(history_data, ensure_ascii=False, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key='notified-history.json',
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )

            self.logger.info("通知履歴を正常に保存しました")
            return True
        except Exception as e:
            self.logger.error(f"通知履歴の保存に失敗しました: {e}")
            return False

    def append_notification_history(self, articles: List[Dict]) -> bool:
        """通知履歴追加"""
        try:
            # 既存履歴読み込み
            history_data = self.load_notification_history()

            # 新規履歴追加
            batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            new_entries = []

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
                new_entries.append(history_entry)
                history_data['history'].append(history_entry)

            # 履歴サイズ制限・クリーンアップ
            self._cleanup_history(history_data)

            # 統計更新
            self._update_history_statistics(history_data)

            # 保存
            success = self.save_notification_history(history_data)
            if success:
                self.logger.info(f"通知履歴に{len(new_entries)}件の記事を追加しました")
            return success

        except Exception as e:
            self.logger.error(f"通知履歴の追加に失敗しました: {e}")
            return False

    def is_article_notified(self, article_link: str) -> bool:
        """記事通知済み判定"""
        try:
            history = self.load_notification_history()
            return any(h['link'] == article_link for h in history['history'])
        except Exception as e:
            self.logger.error(f"通知履歴の確認に失敗しました: {e}")
            return False

    def get_recent_notifications(self, days: int = 7) -> List[Dict]:
        """最近の通知履歴取得"""
        try:
            history = self.load_notification_history()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            recent_notifications = [
                h for h in history['history']
                if h['notified_at'] > cutoff_iso
            ]

            self.logger.info(f"過去{days}日間の通知履歴: {len(recent_notifications)}件")
            return recent_notifications
        except Exception as e:
            self.logger.error(f"最近の通知履歴取得に失敗しました: {e}")
            return []

    def _validate_rss_config(self, data: Dict) -> None:
        """RSS設定データのバリデーション"""
        required_fields = ['version', 'feeds']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"RSS設定に必須フィールド'{field}'がありません")

        if not isinstance(data['feeds'], list):
            raise ValueError("feedsフィールドはリスト形式である必要があります")

        for i, feed in enumerate(data['feeds']):
            required_feed_fields = ['id', 'url', 'title', 'category']
            for field in required_feed_fields:
                if field not in feed:
                    raise ValueError(f"フィード{i}に必須フィールド'{field}'がありません")

    def _create_default_rss_config(self) -> Dict:
        """デフォルトRSS設定生成"""
        default_config = {
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
                "total_notifications_sent": 0,
                "avg_articles_per_notification": 0
            }
        }

        # デフォルト設定を保存
        self.save_rss_config(default_config)
        return default_config

    def _create_default_history(self) -> Dict:
        """デフォルト履歴設定生成"""
        default_history = {
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
                "avg_daily_notifications": 0,
                "category_stats": {}
            }
        }

        # デフォルト履歴を保存
        self.save_notification_history(default_history)
        return default_history

    def _cleanup_history(self, history_data: Dict) -> None:
        """履歴クリーンアップ"""
        max_size = history_data.get('config', {}).get('max_history_size', 1000)

        # サイズ制限
        if len(history_data['history']) > max_size:
            # 古い順にソートして削除
            history_data['history'].sort(key=lambda x: x['notified_at'])
            deleted_count = len(history_data['history']) - max_size
            history_data['history'] = history_data['history'][-max_size:]
            self.logger.info(f"履歴サイズ制限により{deleted_count}件の古い履歴を削除しました")

        # 古い記録削除（30日以上前）
        cleanup_days = history_data.get('config', {}).get('cleanup_days', 30)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=cleanup_days)
        cutoff_iso = cutoff_date.isoformat()

        original_count = len(history_data['history'])
        history_data['history'] = [
            h for h in history_data['history']
            if h['notified_at'] > cutoff_iso
        ]

        deleted_count = original_count - len(history_data['history'])
        if deleted_count > 0:
            self.logger.info(f"保持期間({cleanup_days}日)を超えた{deleted_count}件の履歴を削除しました")

    def _update_history_statistics(self, history_data: Dict) -> None:
        """履歴統計更新"""
        history_entries = history_data['history']

        # 基本統計
        history_data['statistics']['total_notifications'] = len(history_entries)

        if history_entries:
            # 最古記録
            oldest_entry = min(history_entries, key=lambda x: x['notified_at'])
            history_data['statistics']['oldest_record'] = oldest_entry['notified_at']

            # カテゴリ別統計
            category_stats = {}
            for entry in history_entries:
                category = entry.get('category', 'その他')
                category_stats[category] = category_stats.get(category, 0) + 1

            history_data['statistics']['category_stats'] = category_stats

            # 平均日次通知数計算
            if history_data['statistics']['oldest_record']:
                oldest_date = datetime.fromisoformat(history_data['statistics']['oldest_record'].replace('Z', '+00:00'))
                days_diff = (datetime.now(timezone.utc) - oldest_date).days
                if days_diff > 0:
                    avg_daily = len(history_entries) / days_diff
                    history_data['statistics']['avg_daily_notifications'] = round(avg_daily, 1)

    def _generate_article_hash(self, article: Dict) -> str:
        """記事ハッシュ生成"""
        content = f"{article['title']}{article['link']}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()
        return f"sha256:{hash_digest[:16]}"


class HistorySearchManager:
    """履歴検索管理"""

    def __init__(self, s3_manager: S3DataManager):
        self.s3_manager = s3_manager
        self.logger = logging.getLogger(__name__)

    def get_category_statistics(self) -> Dict[str, int]:
        """カテゴリ別統計取得"""
        try:
            history = self.s3_manager.load_notification_history()
            return history.get('statistics', {}).get('category_stats', {})
        except Exception as e:
            self.logger.error(f"カテゴリ統計の取得に失敗しました: {e}")
            return {}

    def get_feed_statistics(self) -> Dict[str, Any]:
        """フィード統計取得"""
        try:
            rss_config = self.s3_manager.load_rss_config()
            return rss_config.get('statistics', {})
        except Exception as e:
            self.logger.error(f"フィード統計の取得に失敗しました: {e}")
            return {}