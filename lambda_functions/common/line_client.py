"""
RSS LINE Notifier - LINE API連携クラス
LINE Messaging API を使用したメッセージ送信・署名検証の実装
"""

import json
import hmac
import hashlib
import base64
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


# ログ設定
logger = logging.getLogger(__name__)


class LineClient:
    """LINE Messaging API クライアント"""

    def __init__(self, channel_access_token: str, channel_secret: str = None):
        """
        LINE API クライアント初期化

        Args:
            channel_access_token: LINE Channel Access Token
            channel_secret: LINE Channel Secret (署名検証用)
        """
        self.channel_access_token = channel_access_token
        self.channel_secret = channel_secret
        self.base_url = "https://api.line.me/v2/bot"
        self.logger = logging.getLogger(__name__)

        # HTTP セッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {channel_access_token}',
            'Content-Type': 'application/json'
        })

    def send_push_message(self, user_id: str, messages: List[Dict]) -> bool:
        """
        プッシュメッセージ送信

        Args:
            user_id: 送信先ユーザーID
            messages: 送信するメッセージリスト

        Returns:
            bool: 送信成功・失敗
        """
        try:
            url = f"{self.base_url}/message/push"
            payload = {
                "to": user_id,
                "messages": messages
            }

            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            self.logger.info(f"LINE プッシュメッセージを正常に送信しました。ユーザー: {user_id[:10]}...")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"LINE プッシュメッセージの送信に失敗しました: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response body: {e.response.text}")
            return False
        except Exception as e:
            self.logger.error(f"予期しないエラーが発生しました: {e}")
            return False

    def send_text_message(self, user_id: str, text: str) -> bool:
        """
        テキストメッセージ送信

        Args:
            user_id: 送信先ユーザーID
            text: 送信するテキスト

        Returns:
            bool: 送信成功・失敗
        """
        message = {
            "type": "text",
            "text": text
        }
        return self.send_push_message(user_id, [message])

    def send_flex_message(self, user_id: str, alt_text: str, flex_contents: Dict) -> bool:
        """
        Flexメッセージ送信

        Args:
            user_id: 送信先ユーザーID
            alt_text: 代替テキスト
            flex_contents: Flexメッセージ内容

        Returns:
            bool: 送信成功・失敗
        """
        message = {
            "type": "flex",
            "altText": alt_text,
            "contents": flex_contents
        }
        return self.send_push_message(user_id, [message])

    def start_loading_animation(self, user_id: str, loading_seconds: int = 5) -> bool:
        """
        Loading Animation 開始

        Args:
            user_id: 対象ユーザーID
            loading_seconds: 表示時間（秒）

        Returns:
            bool: 開始成功・失敗
        """
        try:
            url = f"{self.base_url}/chat/loading/start"
            payload = {
                "chatId": user_id,
                "loadingSeconds": loading_seconds
            }

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            self.logger.info(f"Loading Animation を開始しました。ユーザー: {user_id[:10]}...")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Loading Animation の開始に失敗しました: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Loading Animation 開始時に予期しないエラー: {e}")
            return False

    def verify_signature(self, body: str, signature: str) -> bool:
        """
        LINE署名検証

        Args:
            body: リクエストボディ
            signature: X-Line-Signature ヘッダーの値

        Returns:
            bool: 署名検証結果
        """
        if not self.channel_secret:
            self.logger.warning("Channel Secret が設定されていません")
            return False

        try:
            hash_digest = hmac.new(
                self.channel_secret.encode(),
                body.encode(),
                hashlib.sha256
            ).digest()
            expected_signature = base64.b64encode(hash_digest).decode()

            is_valid = hmac.compare_digest(signature, expected_signature)

            if is_valid:
                self.logger.info("LINE署名検証に成功しました")
            else:
                self.logger.warning("LINE署名検証に失敗しました")

            return is_valid

        except Exception as e:
            self.logger.error(f"署名検証中にエラーが発生しました: {e}")
            return False


class FlexMessageBuilder:
    """Flex メッセージ作成ヘルパー"""

    # カテゴリ設定
    FEED_CATEGORIES = {
        "プログラミング": {
            "color": "#2E7D32",
            "icon": "💻",
            "priority": 1
        },
        "テクノロジー": {
            "color": "#1976D2",
            "icon": "🔧",
            "priority": 2
        },
        "マンガ・エンタメ": {
            "color": "#F57C00",
            "icon": "🎮",
            "priority": 3
        },
        "ニュース": {
            "color": "#5D4037",
            "icon": "📰",
            "priority": 4
        },
        "その他": {
            "color": "#616161",
            "icon": "📝",
            "priority": 99
        }
    }

    @classmethod
    def create_carousel_message(cls, categorized_articles: Dict[str, List[Dict]]) -> Dict:
        """
        カテゴリ別記事のカルーセルメッセージ作成

        Args:
            categorized_articles: カテゴリ別記事辞書

        Returns:
            Dict: Flexカルーセルメッセージ
        """
        try:
            bubbles = []

            for category, articles in categorized_articles.items():
                if not articles:
                    continue

                bubble = cls._create_category_bubble(category, articles)
                if bubble:
                    bubbles.append(bubble)

            if not bubbles:
                logger.warning("作成できるカルーセルバブルがありません")
                return cls._create_no_articles_message()

            # 最大10カテゴリまで制限
            bubbles = bubbles[:10]

            carousel = {
                "type": "carousel",
                "contents": bubbles
            }

            logger.info(f"カルーセルメッセージを作成しました。カテゴリ数: {len(bubbles)}")
            return carousel

        except Exception as e:
            logger.error(f"カルーセルメッセージの作成に失敗しました: {e}")
            return cls._create_error_message()

    @classmethod
    def _create_category_bubble(cls, category: str, articles: List[Dict]) -> Dict:
        """カテゴリ別バブル作成"""
        try:
            category_info = cls.FEED_CATEGORIES.get(category, cls.FEED_CATEGORIES["その他"])

            # ヘッダー作成
            header = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{category_info['icon']} {category}",
                        "size": "lg",
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": f"{len(articles)}件",
                        "size": "sm",
                        "color": "#FFFFFF",
                        "align": "end"
                    }
                ],
                "backgroundColor": category_info["color"],
                "paddingAll": "15px"
            }

            # ボディ作成
            body_contents = []

            for i, article in enumerate(articles[:5]):  # 最大5記事まで表示
                article_box = cls._create_article_box(article, i + 1)
                body_contents.append(article_box)

                # 記事間の区切り線（最後の記事以外）
                if i < len(articles[:5]) - 1:
                    body_contents.append({
                        "type": "separator",
                        "margin": "md"
                    })

            body = {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents,
                "paddingAll": "15px"
            }

            bubble = {
                "type": "bubble",
                "size": "giga",
                "header": header,
                "body": body
            }

            return bubble

        except Exception as e:
            logger.error(f"カテゴリバブル作成でエラー: {e}")
            return None

    @classmethod
    def _create_article_box(cls, article: Dict, rank: int) -> Dict:
        """記事ボックス作成"""
        try:
            # ランキング絵文字
            rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else ""

            # メタ情報取得
            metadata = article.get('metadata', {})
            article_type = metadata.get('article_type', '記事')
            difficulty = metadata.get('difficulty', '')
            reading_time = metadata.get('reading_time', '')

            # メタ情報文字列作成
            meta_parts = []
            if article_type:
                type_emoji = {
                    'トレンド': '🔥',
                    '技術解説': '⚡',
                    'ツール': '🛠️',
                    '分析': '📊',
                    'ニュース': '📰'
                }.get(article_type, '📝')
                meta_parts.append(f"{type_emoji} {difficulty}" if difficulty else type_emoji)

            if reading_time:
                meta_parts.append(reading_time)

            # 公開時間取得
            published_at = article.get('published_at', '')
            if published_at:
                try:
                    pub_datetime = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    now = datetime.now(pub_datetime.tzinfo)
                    time_diff = now - pub_datetime

                    if time_diff.days > 0:
                        meta_parts.append(f"{time_diff.days}日前")
                    elif time_diff.seconds > 3600:
                        hours = time_diff.seconds // 3600
                        meta_parts.append(f"{hours}時間前")
                    else:
                        minutes = max(1, time_diff.seconds // 60)
                        meta_parts.append(f"{minutes}分前")
                except:
                    pass

            meta_text = " · ".join(meta_parts)

            # タイトル作成（ランキング + タイトル）
            title_text = f"{rank_emoji} {article['title']}" if rank_emoji else article['title']

            article_box = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title_text,
                        "size": "md",
                        "weight": "bold",
                        "wrap": True,
                        "maxLines": 2,
                        "color": "#333333"
                    }
                ],
                "action": {
                    "type": "uri",
                    "uri": article['link']
                },
                "paddingAll": "12px",
                "cornerRadius": "8px",
                "backgroundColor": "#FFF9C4" if rank <= 3 else "#F5F5F5"
            }

            # メタ情報追加
            if meta_text:
                article_box["contents"].append({
                    "type": "text",
                    "text": meta_text,
                    "size": "xs",
                    "color": "#666666",
                    "margin": "sm"
                })

            return article_box

        except Exception as e:
            logger.error(f"記事ボックス作成でエラー: {e}")
            return {
                "type": "text",
                "text": f"記事{rank}: {article.get('title', 'タイトル不明')}",
                "wrap": True
            }

    @classmethod
    def _create_no_articles_message(cls) -> Dict:
        """記事なしメッセージ作成"""
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "📰 RSS通知",
                        "size": "lg",
                        "weight": "bold",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": "新着記事はありませんでした",
                        "size": "md",
                        "align": "center",
                        "margin": "md",
                        "color": "#666666"
                    }
                ],
                "paddingAll": "20px"
            }
        }

    @classmethod
    def _create_error_message(cls) -> Dict:
        """エラーメッセージ作成"""
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "❌ エラー",
                        "size": "lg",
                        "weight": "bold",
                        "align": "center",
                        "color": "#FF5722"
                    },
                    {
                        "type": "text",
                        "text": "メッセージの作成に失敗しました",
                        "size": "md",
                        "align": "center",
                        "margin": "md",
                        "color": "#666666"
                    }
                ],
                "paddingAll": "20px"
            }
        }