"""
RSS LINE Notifier - Notifier Lambda Function
RSS監視・記事収集・LINE通知を行うメインLambda関数（Python 3.12対応）
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# 共通ライブラリのパス追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))

from common.s3_manager import S3DataManager, HistorySearchManager
from common.line_client import LineClient, FlexMessageBuilder
from common.rss_analyzer import RSSAnalyzer


# ログ設定
def setup_logging():
    """ログ設定"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # 構造化ログフォーマット
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s %(name)s:%(lineno)d - %(message)s'
    )

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Lambda環境では既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 新しいハンドラー追加
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    return root_logger

logger = setup_logging()


class NotifierLambda:
    """Notifier Lambda メインクラス"""

    def __init__(self):
        """初期化"""
        self.bucket_name = os.environ.get('BUCKET_NAME')
        self.line_token = os.environ.get('LINE_TOKEN')
        self.line_user_id = os.environ.get('LINE_USER_ID')
        self.aws_region = os.environ.get('AWS_REGION', 'ap-northeast-1')

        # 設定パラメータ
        self.max_feeds = int(os.environ.get('MAX_FEEDS', '100'))
        self.article_age_hours = int(os.environ.get('ARTICLE_AGE_HOURS', '24'))
        self.request_timeout = int(os.environ.get('REQUEST_TIMEOUT', '30'))
        self.parallel_workers = int(os.environ.get('PARALLEL_WORKERS', '10'))

        # 必須パラメータ検証
        if not all([self.bucket_name, self.line_token, self.line_user_id]):
            raise ValueError("必須環境変数が設定されていません")

        # クライアント初期化
        self.s3_manager = S3DataManager(self.bucket_name, self.aws_region)
        self.line_client = LineClient(self.line_token)
        self.rss_analyzer = RSSAnalyzer(self.request_timeout, self.parallel_workers)
        self.history_manager = HistorySearchManager(self.s3_manager)

        logger.info("NotifierLambda初期化完了")

    def process_notification(self, event: Dict) -> Dict:
        """メイン通知処理"""
        try:
            logger.info("RSS通知処理を開始しました")
            logger.info(f"イベント: {json.dumps(event, ensure_ascii=False)}")

            # 1. RSS設定読み込み
            rss_config = self.s3_manager.load_rss_config()
            feeds = rss_config.get('feeds', [])

            if not feeds:
                logger.warning("RSSフィードが設定されていません")
                return self._create_response(200, "RSSフィードが設定されていません")

            logger.info(f"RSS設定読み込み完了。フィード数: {len(feeds)}")

            # 2. RSS記事取得・分析
            categorized_articles = self.rss_analyzer.fetch_and_analyze_feeds(feeds)

            if not categorized_articles:
                logger.info("新着記事がありませんでした")
                return self._create_response(200, "新着記事がありませんでした")

            # 3. 通知履歴との照合（重複除去）
            filtered_articles = self._deduplicate_articles(categorized_articles)

            if not filtered_articles:
                logger.info("通知済み記事のため、新規通知する記事がありません")
                return self._create_response(200, "通知済み記事のため、新規通知する記事がありません")

            # 4. LINE通知メッセージ作成
            flex_message = FlexMessageBuilder.create_carousel_message(filtered_articles)

            # 記事数カウント
            total_articles = sum(len(articles) for articles in filtered_articles.values())
            alt_text = f"RSS通知 - 新着記事 {total_articles}件"

            # 5. LINE通知送信
            success = self.line_client.send_flex_message(
                self.line_user_id,
                alt_text,
                flex_message
            )

            if not success:
                logger.error("LINE通知の送信に失敗しました")
                return self._create_response(500, "LINE通知の送信に失敗しました")

            # 6. 通知履歴更新
            all_articles = []
            for articles in filtered_articles.values():
                all_articles.extend(articles)

            history_success = self.s3_manager.append_notification_history(all_articles)

            if not history_success:
                logger.warning("通知履歴の更新に失敗しましたが、通知は正常に送信されました")

            # 7. RSS設定統計更新
            self._update_rss_statistics(rss_config, len(all_articles))

            logger.info(f"RSS通知処理が正常に完了しました。通知記事数: {total_articles}")

            return self._create_response(200, {
                "message": "RSS通知処理が正常に完了しました",
                "total_articles": total_articles,
                "categories": list(filtered_articles.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        except Exception as e:
            logger.error(f"RSS通知処理でエラーが発生しました: {e}")
            logger.error(f"トレースバック: {traceback.format_exc()}")

            # エラー通知送信（オプション）
            try:
                error_message = f"❌ RSS通知でエラーが発生しました\n\n{str(e)}"
                self.line_client.send_text_message(self.line_user_id, error_message)
            except:
                pass

            return self._create_response(500, f"RSS通知処理でエラーが発生しました: {str(e)}")

    def _deduplicate_articles(self, categorized_articles: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """記事重複除去"""
        try:
            filtered_categorized = {}
            total_original = 0
            total_filtered = 0

            for category, articles in categorized_articles.items():
                total_original += len(articles)
                filtered_articles = []

                for article in articles:
                    if not self.s3_manager.is_article_notified(article['link']):
                        filtered_articles.append(article)

                if filtered_articles:
                    filtered_categorized[category] = filtered_articles
                    total_filtered += len(filtered_articles)

            logger.info(f"重複除去完了: {total_filtered} / {total_original} 件が新規記事")
            return filtered_categorized

        except Exception as e:
            logger.error(f"記事重複除去でエラー: {e}")
            return categorized_articles

    def _update_rss_statistics(self, rss_config: Dict, notification_count: int) -> None:
        """RSS設定統計更新"""
        try:
            stats = rss_config.get('statistics', {})

            # 統計更新
            stats['total_notifications_sent'] = stats.get('total_notifications_sent', 0) + 1
            stats['total_articles_processed'] = stats.get('total_articles_processed', 0) + notification_count

            # 平均記事数更新
            if stats['total_notifications_sent'] > 0:
                stats['avg_articles_per_notification'] = round(
                    stats['total_articles_processed'] / stats['total_notifications_sent'], 1
                )

            rss_config['statistics'] = stats

            # 保存
            self.s3_manager.save_rss_config(rss_config)
            logger.info("RSS統計を更新しました")

        except Exception as e:
            logger.warning(f"RSS統計更新でエラー: {e}")

    def _create_response(self, status_code: int, body: Any) -> Dict:
        """レスポンス作成"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else str(body)
        }


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Lambda関数エントリーポイント

    Args:
        event: Lambda イベント
        context: Lambda コンテキスト

    Returns:
        Dict: レスポンス
    """
    try:
        logger.info("=== RSS Notifier Lambda 開始 ===")
        logger.info(f"イベント情報: {json.dumps(event, ensure_ascii=False, default=str)}")

        # NotifierLambdaインスタンス作成・実行
        notifier = NotifierLambda()
        result = notifier.process_notification(event)

        logger.info(f"=== RSS Notifier Lambda 完了 ===")
        return result

    except Exception as e:
        logger.error(f"Lambda関数で予期しないエラーが発生しました: {e}")
        logger.error(f"トレースバック: {traceback.format_exc()}")

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, ensure_ascii=False)
        }


# ローカルテスト用
if __name__ == "__main__":
    # テスト用環境変数設定
    test_event = {
        "source": "test",
        "schedule": "manual"
    }

    test_context = type('LambdaContext', (), {
        'function_name': 'test-function',
        'function_version': '$LATEST',
        'invoked_function_arn': 'arn:aws:lambda:test',
        'memory_limit_in_mb': '512',
        'remaining_time_in_millis': lambda: 300000,
        'log_group_name': '/aws/lambda/test',
        'log_stream_name': 'test-stream'
    })()

    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, ensure_ascii=False, indent=2))