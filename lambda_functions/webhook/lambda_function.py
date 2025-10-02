"""
RSS LINE Notifier - Webhook Lambda Function
LINE Webhookハンドリング・ユーザーコマンド処理Lambda関数（Python 3.12対応）
"""

import os
import sys
import json
import logging
import traceback
import boto3
import feedparser
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

# 共通ライブラリのパス追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))

from common.s3_manager import S3DataManager, RSSFeed
from common.line_client import LineClient


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


class WebhookLambda:
    """Webhook Lambda メインクラス"""

    def __init__(self):
        """初期化"""
        self.bucket_name = os.environ.get('BUCKET_NAME')
        self.line_token = os.environ.get('LINE_TOKEN')
        self.line_channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
        self.notifier_function_name = os.environ.get('NOTIFIER_FUNCTION_NAME')
        self.aws_region = os.environ.get('AWS_REGION', 'ap-northeast-1')

        # 設定パラメータ
        self.loading_timeout = int(os.environ.get('LOADING_TIMEOUT', '5'))
        self.max_command_length = int(os.environ.get('MAX_COMMAND_LENGTH', '1000'))

        # 必須パラメータ検証
        if not all([self.bucket_name, self.line_token, self.line_channel_secret, self.notifier_function_name]):
            raise ValueError("必須環境変数が設定されていません")

        # クライアント初期化
        self.s3_manager = S3DataManager(self.bucket_name, self.aws_region)
        self.line_client = LineClient(self.line_token, self.line_channel_secret)
        self.lambda_client = boto3.client('lambda', region_name=self.aws_region)

        logger.info("WebhookLambda初期化完了")

    def process_webhook(self, event: Dict) -> Dict:
        """Webhook処理メイン"""
        try:
            logger.info("LINE Webhook処理を開始しました")

            # 1. リクエスト解析
            body = event.get('body', '')
            headers = event.get('headers', {})

            if not body:
                logger.warning("リクエストボディが空です")
                return self._create_response(400, "リクエストボディが必要です")

            # 2. 署名検証
            signature = headers.get('x-line-signature', headers.get('X-Line-Signature', ''))
            if not self.line_client.verify_signature(body, signature):
                logger.warning("LINE署名検証に失敗しました")
                return self._create_response(401, "署名検証に失敗しました")

            # 3. Webhookイベント解析
            try:
                webhook_data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"JSONデコードエラー: {e}")
                return self._create_response(400, "無効なJSON形式です")

            events = webhook_data.get('events', [])
            if not events:
                logger.info("処理すべきイベントがありません")
                return self._create_response(200, "OK")

            # 4. 各イベントを処理
            for line_event in events:
                try:
                    self._process_single_event(line_event)
                except Exception as e:
                    logger.error(f"イベント処理でエラー: {e}")
                    # 個別イベントのエラーは続行

            logger.info("LINE Webhook処理が正常に完了しました")
            return self._create_response(200, "OK")

        except Exception as e:
            logger.error(f"Webhook処理でエラーが発生しました: {e}")
            logger.error(f"トレースバック: {traceback.format_exc()}")
            return self._create_response(500, f"内部エラーが発生しました: {str(e)}")

    def _process_single_event(self, line_event: Dict) -> None:
        """単一LINEイベント処理"""
        try:
            event_type = line_event.get('type')

            if event_type != 'message':
                logger.info(f"未対応のイベントタイプ: {event_type}")
                return

            message = line_event.get('message', {})
            message_type = message.get('type')

            if message_type != 'text':
                logger.info(f"未対応のメッセージタイプ: {message_type}")
                return

            # ユーザー情報取得
            source = line_event.get('source', {})
            user_id = source.get('userId')

            if not user_id:
                logger.warning("ユーザーIDが取得できません")
                return

            # メッセージテキスト取得
            text = message.get('text', '').strip()

            if len(text) > self.max_command_length:
                logger.warning(f"コマンドが長すぎます: {len(text)} 文字")
                self.line_client.send_text_message(
                    user_id,
                    f"❌ コマンドが長すぎます（最大{self.max_command_length}文字）"
                )
                return

            logger.info(f"ユーザーコマンド受信: {text}")

            # Loading Animation 開始
            self.line_client.start_loading_animation(user_id, self.loading_timeout)

            # コマンド処理
            response_message = self._process_user_command(text, user_id)

            # レスポンス送信
            self.line_client.send_text_message(user_id, response_message)

        except Exception as e:
            logger.error(f"単一イベント処理でエラー: {e}")
            raise

    def _process_user_command(self, text: str, user_id: str) -> str:
        """ユーザーコマンド処理"""
        try:
            # コマンド解析
            parts = text.strip().split()
            if not parts:
                return self._get_help_message()

            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []

            logger.info(f"コマンド実行: {command}, 引数: {args}")

            # コマンド分岐
            if command == "一覧":
                return self._handle_list_command()
            elif command == "追加":
                return self._handle_add_command(args)
            elif command == "削除":
                return self._handle_delete_command(args)
            elif command == "通知":
                return self._handle_notification_command(user_id)
            elif command in ["ヘルプ", "help", "？", "?"]:
                return self._get_help_message()
            else:
                return f"❓ 不明なコマンドです: {command}\n\n「ヘルプ」と送信してコマンド一覧を確認してください。"

        except Exception as e:
            logger.error(f"コマンド処理でエラー: {e}")
            return f"❌ コマンド処理中にエラーが発生しました: {str(e)}"

    def _handle_list_command(self) -> str:
        """一覧コマンド処理"""
        try:
            rss_config = self.s3_manager.load_rss_config()
            feeds = rss_config.get('feeds', [])

            if not feeds:
                return "📋 登録されているRSSフィードはありません。\n\n「追加 <URL>」で新しいフィードを登録できます。"

            lines = ["📋 登録済みRSSフィード一覧:\n"]

            for i, feed in enumerate(feeds, 1):
                status = "✅" if feed.get('enabled', True) else "❌"
                lines.append(f"{i}. {status} {feed['title']}")
                lines.append(f"   📂 {feed['category']}")
                lines.append("")

            lines.append("🔧 コマンド:")
            lines.append("• 追加 <URL> - フィード追加")
            lines.append("• 削除 <番号> - フィード削除")
            lines.append("• 通知 - 手動通知実行")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"一覧コマンド処理でエラー: {e}")
            return f"❌ フィード一覧の取得に失敗しました: {str(e)}"

    def _handle_add_command(self, args: List[str]) -> str:
        """追加コマンド処理"""
        try:
            if not args:
                return "❌ URLを指定してください。\n\n例: 追加 https://example.com/feed.xml"

            url = args[0]

            # URL検証
            if not self._is_valid_url(url):
                return "❌ 無効なURLです。\n\nhttp:// または https:// で始まる有効なURLを指定してください。"

            # RSS フィード検証
            feed_info = self._validate_rss_feed(url)
            if not feed_info:
                return "❌ RSSフィードの取得に失敗しました。\n\nURLが正しいか、フィードが有効か確認してください。"

            # 重複チェック
            rss_config = self.s3_manager.load_rss_config()
            existing_feeds = rss_config.get('feeds', [])

            if any(feed['url'] == url for feed in existing_feeds):
                return "⚠️ このフィードは既に登録されています。"

            # フィード追加
            new_feed = {
                "id": f"feed_{int(datetime.now().timestamp())}",
                "url": url,
                "title": feed_info["title"],
                "category": self._categorize_feed(feed_info["title"]),
                "enabled": True,
                "priority": 5,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "description": feed_info.get("description", ""),
                    "language": "ja",
                    "feed_type": "rss2.0"
                }
            }

            existing_feeds.append(new_feed)
            rss_config['feeds'] = existing_feeds

            # 統計更新
            stats = rss_config.get('statistics', {})
            stats['total_feeds'] = len(existing_feeds)
            stats['active_feeds'] = len([f for f in existing_feeds if f.get('enabled', True)])
            rss_config['statistics'] = stats

            # 保存
            success = self.s3_manager.save_rss_config(rss_config)

            if success:
                return f"✅ RSSフィードを追加しました:\n\n📰 {feed_info['title']}\n📂 カテゴリ: {new_feed['category']}\n\n現在の登録フィード数: {len(existing_feeds)}"
            else:
                return "❌ RSSフィードの保存に失敗しました。"

        except Exception as e:
            logger.error(f"追加コマンド処理でエラー: {e}")
            return f"❌ フィード追加中にエラーが発生しました: {str(e)}"

    def _handle_delete_command(self, args: List[str]) -> str:
        """削除コマンド処理"""
        try:
            if not args:
                return "❌ 削除する番号を指定してください。\n\n例: 削除 1\n\n「一覧」コマンドで番号を確認できます。"

            # 番号検証
            try:
                index = int(args[0]) - 1
            except ValueError:
                return "❌ 無効な番号です。数字を指定してください。"

            # フィード存在確認
            rss_config = self.s3_manager.load_rss_config()
            feeds = rss_config.get('feeds', [])

            if index < 0 or index >= len(feeds):
                return f"❌ 番号{args[0]}のフィードは存在しません。\n\n「一覧」コマンドで確認してください。"

            # フィード削除
            deleted_feed = feeds.pop(index)
            rss_config['feeds'] = feeds

            # 統計更新
            stats = rss_config.get('statistics', {})
            stats['total_feeds'] = len(feeds)
            stats['active_feeds'] = len([f for f in feeds if f.get('enabled', True)])
            rss_config['statistics'] = stats

            # 保存
            success = self.s3_manager.save_rss_config(rss_config)

            if success:
                return f"✅ RSSフィードを削除しました:\n\n📰 {deleted_feed['title']}\n\n残りフィード数: {len(feeds)}"
            else:
                return "❌ RSSフィードの削除に失敗しました。"

        except Exception as e:
            logger.error(f"削除コマンド処理でエラー: {e}")
            return f"❌ フィード削除中にエラーが発生しました: {str(e)}"

    def _handle_notification_command(self, user_id: str) -> str:
        """通知コマンド処理（ローディングスピナー対応）"""
        try:
            # 1. ローディングアニメーション開始
            self.line_client.start_loading_animation(user_id, 60)
            logger.info(f"ローディングアニメーション開始: user_id={user_id}")

            # 2. Notifier Lambda 同期実行
            payload = {
                'source': 'webhook',
                'user_id': user_id,
                'trigger_type': 'manual'
            }

            logger.info("手動通知のため Notifier Lambda を同期実行します")
            response = self.lambda_client.invoke(
                FunctionName=self.notifier_function_name,
                InvocationType='RequestResponse',  # 同期実行
                Payload=json.dumps(payload)
            )

            # 3. Lambda 実行結果を解析
            if response['StatusCode'] != 200:
                logger.error(f"Lambda呼び出しエラー: Status {response['StatusCode']}")
                return "❌ 通知の実行に失敗しました。"

            # Lambda からのレスポンス取得
            response_payload = json.loads(response['Payload'].read())
            logger.info(f"Notifier Lambda レスポンス: {response_payload}")

            # 4. 結果に応じたメッセージ返却
            if response_payload.get('statusCode') == 200:
                body = response_payload.get('body', {})

                # body が文字列の場合は JSON パース
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        body = {}

                # 新着記事数を確認
                total_articles = body.get('total_articles', 0)

                if total_articles > 0:
                    # 通知が送信された場合は何もしない（通知が既に送られている）
                    logger.info(f"手動通知完了: {total_articles}件の記事を通知")
                    return None  # 追加メッセージ送信なし
                else:
                    # 新着記事がない場合
                    logger.info("手動通知: 新着記事なし")
                    return "📭 現在、新着記事はありません。\n\n定期通知（12:30・21:00）で最新情報をお届けします。"
            else:
                # エラーの場合
                error_msg = body.get('message', '不明なエラーが発生しました') if isinstance(body, dict) else str(body)
                logger.error(f"Notifier Lambda エラー: {error_msg}")
                return f"❌ 通知処理中にエラーが発生しました:\n{error_msg}"

        except Exception as e:
            logger.error(f"通知コマンド処理でエラー: {e}")
            logger.error(f"エラー詳細: {traceback.format_exc()}")
            return f"❌ 通知実行中にエラーが発生しました: {str(e)}"

    def _get_help_message(self) -> str:
        """ヘルプメッセージ取得"""
        return """📚 RSS LINE Notifier ヘルプ

🔧 利用可能なコマンド:

📋 一覧
登録済みRSSフィードを表示

➕ 追加 <URL>
RSSフィードを新規登録
例: 追加 https://example.com/feed

➖ 削除 <番号>
指定番号のフィードを削除
例: 削除 1

🔔 通知
手動で通知を実行

❓ ヘルプ
このヘルプを表示

⏰ 自動通知時間: 毎日12:30、21:00

💡 使い方のコツ:
• 信頼できるRSSフィードのみを追加
• 不要なフィードは定期的に削除
• 問題があれば「通知」で手動実行"""

    def _is_valid_url(self, url: str) -> bool:
        """URL妥当性検証"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)
        except Exception:
            return False

    def _validate_rss_feed(self, url: str) -> Optional[Dict]:
        """RSSフィード検証"""
        try:
            logger.info(f"RSSフィード検証開始: {url}")

            # feedparser でRSS解析
            parsed_feed = feedparser.parse(url)

            # 基本的な検証
            if parsed_feed.bozo and parsed_feed.bozo_exception:
                logger.warning(f"RSS解析警告: {parsed_feed.bozo_exception}")

            # フィード情報取得
            feed_title = getattr(parsed_feed.feed, 'title', '') or '無題のフィード'
            feed_description = getattr(parsed_feed.feed, 'description', '')

            # エントリ存在確認
            if not hasattr(parsed_feed, 'entries') or not parsed_feed.entries:
                logger.warning("フィードにエントリがありません")
                return None

            logger.info(f"RSSフィード検証成功: {feed_title}")

            return {
                'title': feed_title,
                'description': feed_description,
                'entry_count': len(parsed_feed.entries)
            }

        except Exception as e:
            logger.error(f"RSSフィード検証でエラー: {e}")
            return None

    def _categorize_feed(self, title: str) -> str:
        """フィードカテゴリ自動判定"""
        try:
            title_lower = title.lower()

            # カテゴリキーワード
            categories = {
                'プログラミング': ['プログラミング', 'コード', '開発', 'programming', 'coding', 'tech', 'qiita', 'github'],
                'テクノロジー': ['テクノロジー', '技術', 'it', 'technology', 'ai', 'iot'],
                'マンガ・エンタメ': ['マンガ', 'アニメ', 'ゲーム', 'エンタメ', 'entertainment', 'manga', 'anime'],
                'ニュース': ['ニュース', '政治', '経済', 'news', 'politics', 'business']
            }

            for category, keywords in categories.items():
                for keyword in keywords:
                    if keyword in title_lower:
                        return category

            return 'その他'

        except Exception:
            return 'その他'

    def _create_response(self, status_code: int, body: str) -> Dict:
        """レスポンス作成"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'text/plain; charset=utf-8'
            },
            'body': body
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
        logger.info("=== Webhook Lambda 開始 ===")
        logger.info(f"イベント情報: {json.dumps(event, ensure_ascii=False, default=str)}")

        # WebhookLambdaインスタンス作成・実行
        webhook = WebhookLambda()
        result = webhook.process_webhook(event)

        logger.info("=== Webhook Lambda 完了 ===")
        return result

    except Exception as e:
        logger.error(f"Lambda関数で予期しないエラーが発生しました: {e}")
        logger.error(f"トレースバック: {traceback.format_exc()}")

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/plain; charset=utf-8'
            },
            'body': f'Internal Server Error: {str(e)}'
        }


# ローカルテスト用
if __name__ == "__main__":
    # テスト用イベント
    test_event = {
        "body": json.dumps({
            "events": [
                {
                    "type": "message",
                    "message": {
                        "type": "text",
                        "text": "一覧"
                    },
                    "source": {
                        "userId": "test-user-id"
                    }
                }
            ]
        }),
        "headers": {
            "x-line-signature": "test-signature"
        }
    }

    test_context = type('LambdaContext', (), {
        'function_name': 'test-webhook-function',
        'function_version': '$LATEST',
        'remaining_time_in_millis': lambda: 30000
    })()

    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, ensure_ascii=False, indent=2))