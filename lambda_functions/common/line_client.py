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
from datetime import datetime, timezone


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
        self.session.headers.update(
            {
                "Authorization": f"Bearer {channel_access_token}",
                "Content-Type": "application/json",
            }
        )

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
            payload = {"to": user_id, "messages": messages}

            # 一時的なデバッグログ
            self.logger.error(
                f"DEBUG: 送信するJSON構造: {json.dumps(payload, ensure_ascii=False, indent=2)}"
            )

            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            self.logger.info(
                f"LINE プッシュメッセージを正常に送信しました。ユーザー: {user_id[:10]}..."
            )
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"LINE プッシュメッセージの送信に失敗しました: {e}")
            if hasattr(e, "response") and e.response is not None:
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
        message = {"type": "text", "text": text}
        return self.send_push_message(user_id, [message])

    def send_flex_message(
        self, user_id: str, alt_text: str, flex_contents: Dict
    ) -> bool:
        """
        Flexメッセージ送信

        Args:
            user_id: 送信先ユーザーID
            alt_text: 代替テキスト
            flex_contents: Flexメッセージ内容

        Returns:
            bool: 送信成功・失敗
        """
        message = {"type": "flex", "altText": alt_text, "contents": flex_contents}
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
            payload = {"chatId": user_id, "loadingSeconds": loading_seconds}

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            self.logger.info(
                f"Loading Animation を開始しました。ユーザー: {user_id[:10]}..."
            )
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
                self.channel_secret.encode(), body.encode(), hashlib.sha256
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
        "プログラミング": {"color": "#2E7D32", "icon": "💻", "priority": 1},
        "テクノロジー": {"color": "#1976D2", "icon": "🔧", "priority": 2},
        "マンガ・エンタメ": {"color": "#F57C00", "icon": "🎮", "priority": 3},
        "ニュース": {"color": "#5D4037", "icon": "📰", "priority": 4},
        "その他": {"color": "#616161", "icon": "📝", "priority": 99},
    }

    @classmethod
    def create_carousel_message(
        cls, categorized_articles: Dict[str, List[Dict]]
    ) -> Dict:
        """
        カテゴリ別記事のカルーセルメッセージ作成

        Args:
            categorized_articles: カテゴリ別記事辞書

        Returns:
            Dict: Flexカルーセルメッセージ
        """
        try:
            # 記事がない場合は記事なしメッセージ
            if not categorized_articles:
                return cls._create_no_articles_message()

            # 通常のカルーセル作成
            bubbles = []

            # 1. 概要バブル作成
            summary_bubble = cls._create_overview_bubble(categorized_articles)
            bubbles.append(summary_bubble)

            # 2. カテゴリ別バブル作成
            for category, articles in categorized_articles.items():
                if not articles:
                    continue

                bubble = cls._create_category_bubble(category, articles)
                if bubble:
                    bubbles.append(bubble)

            # カルーセルとして返却
            carousel = {"type": "carousel", "contents": bubbles}

            logger.info(f"カルーセルメッセージを作成しました。バブル数: {len(bubbles)}")
            return carousel

        except Exception as e:
            logger.error(f"カルーセルメッセージの作成でエラー: {e}")
            return cls._create_no_articles_message()

    @classmethod
    def _create_single_bubble_fallback(
        cls, categorized_articles: Dict[str, List[Dict]]
    ) -> Dict:
        """最終フォールバック：単一バブルメッセージ"""
        try:
            total_articles = sum(
                len(articles) for articles in categorized_articles.values()
            )

            # 最高スコア記事取得
            top_article = None
            max_score = 0

            for articles in categorized_articles.values():
                for article in articles:
                    score = article.get("metadata", {}).get("priority_score", 0)
                    if score > max_score:
                        max_score = score
                        top_article = article

            contents = [
                {
                    "type": "text",
                    "text": "📰 RSS通知",
                    "size": "xl",
                    "weight": "bold",
                    "align": "center",
                },
                {
                    "type": "text",
                    "text": f"新着記事 {total_articles}件",
                    "size": "md",
                    "align": "center",
                    "margin": "md",
                },
            ]

            if top_article:
                contents.extend(
                    [
                        {"type": "separator", "margin": "lg"},
                        {
                            "type": "text",
                            "text": "🏆 注目記事",
                            "size": "md",
                            "weight": "bold",
                            "margin": "lg",
                        },
                        {
                            "type": "text",
                            "text": top_article["title"],
                            "size": "sm",
                            "wrap": True,
                            "maxLines": 3,
                            "margin": "sm",
                        },
                    ]
                )

            bubble = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": contents,
                    "paddingAll": "20px",
                },
                "action": {
                    "type": "uri",
                    "uri": (
                        top_article["link"] if top_article else "https://example.com"
                    ),
                },
            }

            logger.info("単一バブルフォールバックメッセージを作成")
            return bubble

        except Exception as e:
            logger.error(f"単一バブルフォールバック作成でエラー: {e}")
            return cls._create_error_message()

    @classmethod
    def _create_overview_bubble(
        cls, categorized_articles: Dict[str, List[Dict]]
    ) -> Dict:
        """
        概要バブル作成（rss-line-notifier v2.1から移植）
        全記事の統計情報とトップ記事のハイライト表示
        """
        try:
            # 統計情報計算
            total_articles = sum(
                len(articles) for articles in categorized_articles.values()
            )
            category_count = len(categorized_articles)

            # トップ記事抽出（最高スコアの記事）
            top_article = None
            max_score = 0

            for articles in categorized_articles.values():
                for article in articles:
                    score = article.get("metadata", {}).get("priority_score", 0)
                    if score > max_score:
                        max_score = score
                        top_article = article

            # 記事タイプ統計
            type_stats = {}
            for articles in categorized_articles.values():
                for article in articles:
                    article_type = article.get("metadata", {}).get("article_type", "📰")
                    type_stats[article_type] = type_stats.get(article_type, 0) + 1

            # トップ3タイプ取得
            top_types = sorted(type_stats.items(), key=lambda x: x[1], reverse=True)[:3]
            type_summary = " ".join(
                [f"{type_icon}{count}" for type_icon, count in top_types]
            )

            body_contents = [
                {
                    "type": "text",
                    "text": "📰 RSS通知サマリー",
                    "size": "xl",
                    "weight": "bold",
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "text": f"新着記事 {total_articles}件 ({category_count}カテゴリ)",
                    "size": "md",
                    "color": "#FFFFFF",
                    "margin": "md",
                },
            ]

            if type_summary:
                body_contents.append(
                    {
                        "type": "text",
                        "text": type_summary,
                        "size": "sm",
                        "color": "#FFFFFF",
                        "margin": "sm",
                    }
                )

            # トップ記事表示
            if top_article:
                body_contents.extend(
                    [
                        {"type": "separator", "margin": "lg", "color": "#FFFFFF"},
                        {
                            "type": "text",
                            "text": "🏆 注目記事",
                            "size": "md",
                            "weight": "bold",
                            "color": "#FFFFFF",
                            "margin": "lg",
                        },
                        {
                            "type": "text",
                            "text": top_article["title"],
                            "size": "sm",
                            "color": "#FFFFFF",
                            "wrap": True,
                            "maxLines": 2,
                            "margin": "sm",
                        },
                    ]
                )

                # メタデータ表示
                metadata = top_article.get("metadata", {})
                meta_parts = []
                if metadata.get("article_type"):
                    meta_parts.append(metadata["article_type"])
                if metadata.get("difficulty"):
                    meta_parts.append(metadata["difficulty"])
                if metadata.get("reading_time"):
                    meta_parts.append(metadata["reading_time"])

                if meta_parts:
                    body_contents.append(
                        {
                            "type": "text",
                            "text": " · ".join(meta_parts),
                            "size": "xs",
                            "color": "#FFFFFF",
                            "margin": "xs",
                        }
                    )

            # グラデーション背景
            bubble = {
                "type": "bubble",
                "size": "giga",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": body_contents,
                    "paddingAll": "20px",
                    "backgroundColor": "#4A90E2",
                },
                "styles": {"body": {"backgroundColor": "#4A90E2"}},
                "action": {
                    "type": "uri",
                    "uri": (
                        top_article["link"] if top_article else "https://example.com"
                    ),
                },
            }

            return bubble

        except Exception as e:
            logger.error(f"概要バブル作成でエラー: {e}")
            return cls._create_fallback_overview_bubble(categorized_articles)

    @classmethod
    def _create_fallback_overview_bubble(
        cls, categorized_articles: Dict[str, List[Dict]]
    ) -> Dict:
        """概要バブル作成失敗時のフォールバック"""
        total_articles = sum(
            len(articles) for articles in categorized_articles.values()
        )

        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "📰 RSS通知",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#FFFFFF",
                    },
                    {
                        "type": "text",
                        "text": f"新着記事 {total_articles}件",
                        "size": "md",
                        "align": "center",
                        "margin": "md",
                        "color": "#FFFFFF",
                    },
                ],
                "paddingAll": "20px",
                "backgroundColor": "#4A90E2",
            },
        }

    @classmethod
    def _create_category_bubble(cls, category: str, articles: List[Dict]) -> Dict:
        """カテゴリ別バブル作成"""
        try:
            category_info = cls.FEED_CATEGORIES.get(
                category, cls.FEED_CATEGORIES["その他"]
            )

            # ヘッダー作成
            header = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{category_info['icon']} {category}",
                        "size": "lg",
                        "color": "#FFFFFF",
                        "flex": 1,
                    },
                    {
                        "type": "text",
                        "text": f"{len(articles)}件",
                        "size": "sm",
                        "color": "#FFFFFF",
                        "align": "end",
                    },
                ],
                "backgroundColor": category_info["color"],
                "paddingAll": "15px",
            }

            # ボディ作成
            body_contents = []

            for i, article in enumerate(articles[:10]):  # 最大10記事まで表示
                article_box = cls._create_article_box(article, i + 1)
                body_contents.append(article_box)

                # 記事間の区切り線（最後の記事以外）
                if i < len(articles[:10]) - 1:
                    body_contents.append({"type": "separator", "margin": "md"})

            body = {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents,
                "paddingAll": "15px",
            }

            bubble = {
                "type": "bubble",
                "size": "giga",
                "header": header,
                "body": body,
                "styles": {
                    "header": {"backgroundColor": category_info["color"]},
                    "body": {
                        "backgroundColor": "#FAFAFA",
                        "separator": True,
                        "separatorColor": "#E0E0E0",
                    },
                },
            }

            return bubble

        except Exception as e:
            logger.error(f"カテゴリバブル作成でエラー: {e}")
            return None

    @classmethod
    def _create_article_box(cls, article: Dict, rank: int) -> Dict:
        """記事ボックス作成（v2.1強化版）"""
        try:
            # ランキング絵文字
            rank_emoji = (
                "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else ""
            )

            # v2.1 メタデータ取得
            metadata = article.get("metadata", {})
            article_type = metadata.get("article_type", "📰")  # アイコン直接取得
            difficulty = metadata.get("difficulty", "")
            reading_time = metadata.get("reading_time", "")
            priority_score = metadata.get("priority_score", 0)

            # メタ情報文字列作成（v2.1強化）
            meta_parts = []

            # 記事タイプ（アイコン形式）
            if article_type:
                if difficulty:
                    meta_parts.append(f"{article_type} {difficulty}")
                else:
                    meta_parts.append(article_type)

            if reading_time:
                meta_parts.append(reading_time)

            # 公開時間取得（改良版）
            published_at = article.get("published_at", "")
            if published_at:
                try:
                    pub_datetime = datetime.fromisoformat(
                        published_at.replace("Z", "+00:00")
                    )
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

            # 高優先度スコアの記事にスコア表示
            if priority_score >= 80:
                meta_parts.append(f"⭐{int(priority_score)}")

            meta_text = " · ".join(meta_parts)

            # タイトル作成（ランキング + タイトル）
            title_text = (
                f"{rank_emoji} {article['title']}" if rank_emoji else article["title"]
            )

            # 背景色決定（v2.1強化）
            bg_color = "#FFF9C4"  # デフォルト（TOP3ゴールド）
            if rank == 1 and priority_score >= 90:
                bg_color = "#FFE082"  # 最優先記事（より濃いゴールド）
            elif rank <= 3:
                bg_color = "#FFF9C4"  # TOP3（ライトゴールド）
            elif priority_score >= 70:
                bg_color = "#E8F5E8"  # 高優先度（ライトグリーン）
            else:
                bg_color = "#F5F5F5"  # 通常

            article_box = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title_text,
                        "size": "md",
                        "wrap": True,
                        "maxLines": 2,
                        "color": "#333333",
                    }
                ],
                "action": {"type": "uri", "uri": article["link"]},
                "paddingAll": "12px",
                "cornerRadius": "8px",
                "backgroundColor": bg_color,
            }

            # メタ情報追加
            if meta_text:
                article_box["contents"].append(
                    {
                        "type": "text",
                        "text": meta_text,
                        "size": "xs",
                        "color": "#666666",
                        "margin": "sm",
                    }
                )

            # v2.1: 境界線追加（TOP3記事）
            if rank <= 3:
                article_box["borderWidth"] = "2px"
                article_box["borderColor"] = (
                    "#FFD700" if rank == 1 else "#C0C0C0" if rank == 2 else "#CD7F32"
                )

            return article_box

        except Exception as e:
            logger.error(f"記事ボックス作成でエラー: {e}")
            return {
                "type": "text",
                "text": f"記事{rank}: {article.get('title', 'タイトル不明')}",
                "wrap": True,
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
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": "新着記事はありませんでした",
                        "size": "md",
                        "align": "center",
                        "margin": "md",
                        "color": "#666666",
                    },
                ],
                "paddingAll": "20px",
            },
        }

    @classmethod
    def _create_action_bubble(cls, categorized_articles: Dict[str, List[Dict]]) -> Dict:
        """
        アクションバブル作成（rss-line-notifier v2.1から移植）
        フィード管理・通知設定・統計表示のアクション機能
        """
        try:
            total_articles = sum(
                len(articles) for articles in categorized_articles.values()
            )

            # 時刻取得（JST）
            now = datetime.now(timezone.utc).astimezone()
            time_str = now.strftime("%H:%M")

            body_contents = [
                {
                    "type": "text",
                    "text": "⚙️ 操作メニュー",
                    "size": "xl",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "align": "center",
                },
                {
                    "type": "text",
                    "text": f"更新時刻: {time_str}",
                    "size": "xs",
                    "color": "#FFFFFF",
                    "align": "center",
                    "margin": "sm",
                },
                {"type": "separator", "margin": "lg", "color": "#FFFFFF"},
            ]

            # アクションボタン作成
            action_buttons = [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🔄 手動更新",
                            "size": "sm",
                            "color": "#FFFFFF",
                            "flex": 1,
                        }
                    ],
                    "backgroundColor": "#28A745",
                    "paddingAll": "12px",
                    "cornerRadius": "8px",
                    "margin": "md",
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📊 統計表示",
                            "size": "sm",
                            "color": "#FFFFFF",
                            "flex": 1,
                        }
                    ],
                    "backgroundColor": "#17A2B8",
                    "paddingAll": "12px",
                    "cornerRadius": "8px",
                    "margin": "md",
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "⚙️ フィード設定",
                            "size": "sm",
                            "color": "#FFFFFF",
                            "flex": 1,
                        }
                    ],
                    "backgroundColor": "#6F42C1",
                    "paddingAll": "12px",
                    "cornerRadius": "8px",
                    "margin": "md",
                },
            ]

            body_contents.extend(action_buttons)

            # フッター情報
            body_contents.extend(
                [
                    {"type": "separator", "margin": "lg", "color": "#FFFFFF"},
                    {
                        "type": "text",
                        "text": f"今回の通知: {total_articles}件",
                        "size": "xs",
                        "color": "#FFFFFF",
                        "align": "center",
                        "margin": "md",
                    },
                ]
            )

            bubble = {
                "type": "bubble",
                "size": "giga",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": body_contents,
                    "paddingAll": "20px",
                    "backgroundColor": "#6C757D",
                },
                "styles": {"body": {"backgroundColor": "#6C757D"}},
            }

            return bubble

        except Exception as e:
            logger.error(f"アクションバブル作成でエラー: {e}")
            return cls._create_fallback_action_bubble()

    @classmethod
    def _create_fallback_action_bubble(cls) -> Dict:
        """アクションバブル作成失敗時のフォールバック"""
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚙️ 操作メニュー",
                        "size": "lg",
                        "weight": "bold",
                        "align": "center",
                        "color": "#FFFFFF",
                    },
                    {
                        "type": "text",
                        "text": "手動更新・設定変更",
                        "size": "sm",
                        "align": "center",
                        "margin": "md",
                        "color": "#FFFFFF",
                    },
                ],
                "paddingAll": "20px",
                "backgroundColor": "#6C757D",
            },
        }
