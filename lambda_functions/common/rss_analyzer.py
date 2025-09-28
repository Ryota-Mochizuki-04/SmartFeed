"""
RSS LINE Notifier - RSS解析・記事分析クラス
feedparserを使用したRSS解析とインテリジェント記事分析の実装
"""

import re
import logging
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
import concurrent.futures


# ログ設定
logger = logging.getLogger(__name__)


class RSSAnalyzer:
    """RSS解析・記事分析クラス"""

    # 記事タイプ分類キーワード
    ARTICLE_TYPE_KEYWORDS = {
        'トレンド': ['人気', 'トレンド', 'バズ', '話題', 'ランキング', 'まとめ', 'トップ'],
        '技術解説': ['解説', '入門', 'チュートリアル', '使い方', '方法', 'ハウツー', '手順', '基礎'],
        'ツール': ['ツール', 'ライブラリ', 'フレームワーク', 'プラグイン', 'アプリ', 'ソフト'],
        '分析': ['分析', '検証', '比較', '調査', 'レポート', '統計', 'データ'],
        'ニュース': ['リリース', '発表', '発売', 'アップデート', '更新', 'バージョン', 'ニュース']
    }

    # 難易度判定キーワード
    DIFFICULTY_KEYWORDS = {
        '初級': ['初心者', '入門', '基礎', '基本', 'はじめて', '簡単', 'やさしい'],
        '上級': ['上級', '高度', 'アドバンス', '詳細', '深い', 'プロ', 'エキスパート'],
        # 中級はデフォルト
    }

    def __init__(self, request_timeout: int = 30, max_workers: int = 10):
        """
        RSS解析クラス初期化

        Args:
            request_timeout: HTTPリクエストタイムアウト（秒）
            max_workers: 並列処理ワーカー数
        """
        self.request_timeout = request_timeout
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)

        # HTTP セッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RSS-LINE-Notifier/2.1 (+Python feedparser)'
        })

    def fetch_and_analyze_feeds(self, feeds: List[Dict]) -> Dict[str, List[Dict]]:
        """
        複数RSSフィードを並列取得・分析

        Args:
            feeds: RSSフィード設定リスト

        Returns:
            Dict: カテゴリ別記事辞書
        """
        try:
            # 有効なフィードのみ処理
            active_feeds = [feed for feed in feeds if feed.get('enabled', True)]

            if not active_feeds:
                self.logger.warning("有効なRSSフィードがありません")
                return {}

            # 並列処理でRSSフィード取得
            all_articles = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_feed = {
                    executor.submit(self._fetch_single_feed, feed): feed
                    for feed in active_feeds
                }

                for future in concurrent.futures.as_completed(future_to_feed):
                    feed = future_to_feed[future]
                    try:
                        articles = future.result()
                        if articles:
                            all_articles.extend(articles)
                            self.logger.info(f"フィード '{feed['title']}' から {len(articles)} 件の記事を取得")
                    except Exception as e:
                        self.logger.error(f"フィード '{feed['title']}' の処理でエラー: {e}")

            if not all_articles:
                self.logger.warning("取得できた記事がありません")
                return {}

            # 新着記事フィルタリング
            recent_articles = self._filter_recent_articles(all_articles)
            self.logger.info(f"新着記事フィルタリング: {len(recent_articles)} / {len(all_articles)} 件")

            # 記事分析・カテゴリ分類
            analyzed_articles = self._analyze_articles(recent_articles)

            # カテゴリ別グループ化
            categorized = self._group_by_category(analyzed_articles)

            # カテゴリ内優先順位設定
            for category, articles in categorized.items():
                categorized[category] = self._rank_articles(articles)

            total_articles = sum(len(articles) for articles in categorized.values())
            self.logger.info(f"記事分析完了: {total_articles} 件をカテゴリ別に分類")

            return categorized

        except Exception as e:
            self.logger.error(f"RSS取得・分析処理でエラー: {e}")
            return {}

    def _fetch_single_feed(self, feed: Dict) -> List[Dict]:
        """単一RSSフィード取得"""
        try:
            url = feed['url']
            feed_id = feed['id']
            feed_title = feed['title']
            feed_category = feed['category']

            self.logger.info(f"RSSフィード取得開始: {feed_title}")

            # feedparser でRSS解析
            parsed_feed = feedparser.parse(url)

            if parsed_feed.bozo and parsed_feed.bozo_exception:
                self.logger.warning(f"RSS解析警告 '{feed_title}': {parsed_feed.bozo_exception}")

            if not hasattr(parsed_feed, 'entries') or not parsed_feed.entries:
                self.logger.warning(f"フィード '{feed_title}' に記事がありません")
                return []

            articles = []
            for entry in parsed_feed.entries:
                try:
                    article = self._parse_entry(entry, feed_id, feed_title, feed_category)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.warning(f"記事解析でエラー: {e}")
                    continue

            self.logger.info(f"フィード '{feed_title}' から {len(articles)} 件の記事を解析")
            return articles

        except Exception as e:
            self.logger.error(f"フィード '{feed['title']}' の取得に失敗: {e}")
            return []

    def _parse_entry(self, entry: Any, feed_id: str, feed_title: str, feed_category: str) -> Optional[Dict]:
        """RSS エントリ解析"""
        try:
            # 必須フィールド確認
            title = getattr(entry, 'title', '').strip()
            link = getattr(entry, 'link', '').strip()

            if not title or not link:
                return None

            # 公開日時処理
            published_at = self._parse_published_date(entry)

            # 概要・内容取得
            description = self._extract_description(entry)

            # 画像URL取得
            image_url = self._extract_image_url(entry)

            article = {
                'title': title,
                'link': link,
                'description': description,
                'published_at': published_at,
                'feed_id': feed_id,
                'feed_title': feed_title,
                'category': feed_category,
                'image_url': image_url,
                'raw_entry': {
                    'author': getattr(entry, 'author', ''),
                    'tags': [tag.term for tag in getattr(entry, 'tags', [])],
                    'id': getattr(entry, 'id', '')
                }
            }

            return article

        except Exception as e:
            self.logger.warning(f"エントリ解析でエラー: {e}")
            return None

    def _parse_published_date(self, entry: Any) -> str:
        """公開日時解析"""
        try:
            # 複数の日時フィールドを試行
            date_fields = ['published_parsed', 'updated_parsed']

            for field in date_fields:
                date_tuple = getattr(entry, field, None)
                if date_tuple:
                    dt = datetime(*date_tuple[:6], tzinfo=timezone.utc)
                    return dt.isoformat()

            # 文字列形式の日時を試行
            string_fields = ['published', 'updated']
            for field in string_fields:
                date_string = getattr(entry, field, '')
                if date_string:
                    # 簡易的な日時解析（feedparserが解析済みの場合）
                    return date_string

            # デフォルトは現在時刻
            return datetime.now(timezone.utc).isoformat()

        except Exception:
            return datetime.now(timezone.utc).isoformat()

    def _extract_description(self, entry: Any) -> str:
        """記事概要抽出"""
        try:
            # 複数の概要フィールドを試行
            desc_fields = ['summary', 'description', 'content']

            for field in desc_fields:
                content = getattr(entry, field, '')
                if isinstance(content, list) and content:
                    content = content[0].get('value', '') if isinstance(content[0], dict) else str(content[0])

                if content:
                    # HTMLタグ除去
                    clean_desc = re.sub(r'<[^>]+>', '', str(content))
                    # 余分な空白・改行除去
                    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                    # 文字数制限
                    if len(clean_desc) > 200:
                        clean_desc = clean_desc[:200] + '...'
                    return clean_desc

            return ''

        except Exception:
            return ''

    def _extract_image_url(self, entry: Any) -> Optional[str]:
        """記事画像URL抽出"""
        try:
            # enclosures（添付ファイル）から画像検索
            enclosures = getattr(entry, 'enclosures', [])
            for enclosure in enclosures:
                if hasattr(enclosure, 'type') and enclosure.type.startswith('image/'):
                    return enclosure.href

            # media_thumbnail（メディアサムネイル）
            if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                return entry.media_thumbnail[0]['url']

            # content内の画像検索
            content_fields = ['content', 'summary']
            for field in content_fields:
                content = getattr(entry, field, '')
                if isinstance(content, list) and content:
                    content = content[0].get('value', '') if isinstance(content[0], dict) else str(content[0])

                if content:
                    # img タグから src 属性抽出
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', str(content))
                    if img_match:
                        return img_match.group(1)

            return None

        except Exception:
            return None

    def _filter_recent_articles(self, articles: List[Dict], hours: int = 24) -> List[Dict]:
        """新着記事フィルタリング"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            recent_articles = []

            for article in articles:
                try:
                    published_str = article.get('published_at', '')
                    if published_str:
                        # ISO形式の日時をパース
                        published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        if published_dt >= cutoff_time:
                            recent_articles.append(article)
                    else:
                        # 公開日時不明の場合は含める
                        recent_articles.append(article)
                except Exception as e:
                    self.logger.warning(f"日時フィルタリングでエラー: {e}")
                    # エラーの場合は含める
                    recent_articles.append(article)

            return recent_articles

        except Exception as e:
            self.logger.error(f"新着記事フィルタリングでエラー: {e}")
            return articles

    def _analyze_articles(self, articles: List[Dict]) -> List[Dict]:
        """記事分析（v2.1 インテリジェント分析）"""
        try:
            analyzed_articles = []

            for article in articles:
                # 記事タイプ分類
                article_type = self._classify_article_type(article)

                # 難易度推定
                difficulty = self._estimate_difficulty(article)

                # 読了時間推定
                reading_time = self._estimate_reading_time(article)

                # 優先順位スコア計算
                priority_score = self._calculate_priority_score(article, article_type, difficulty)

                # メタデータ追加
                article['metadata'] = {
                    'article_type': article_type,
                    'difficulty': difficulty,
                    'reading_time': reading_time,
                    'priority_score': priority_score,
                    'analyzed_at': datetime.now(timezone.utc).isoformat()
                }

                analyzed_articles.append(article)

            return analyzed_articles

        except Exception as e:
            self.logger.error(f"記事分析でエラー: {e}")
            return articles

    def _classify_article_type(self, article: Dict) -> str:
        """記事タイプ自動分類"""
        try:
            text = f"{article['title']} {article.get('description', '')}"
            text_lower = text.lower()

            # キーワードマッチング
            for article_type, keywords in self.ARTICLE_TYPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return article_type

            return '記事'  # デフォルト

        except Exception:
            return '記事'

    def _estimate_difficulty(self, article: Dict) -> str:
        """難易度推定"""
        try:
            text = f"{article['title']} {article.get('description', '')}"
            text_lower = text.lower()

            # キーワードマッチング
            for difficulty, keywords in self.DIFFICULTY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return difficulty

            # デフォルトは中級
            return '中級'

        except Exception:
            return '中級'

    def _estimate_reading_time(self, article: Dict) -> str:
        """読了時間推定"""
        try:
            text = article.get('description', '')
            # 文字数ベースの簡易推定（日本語: 600文字/分）
            char_count = len(text)

            if char_count < 300:
                return '1分'
            elif char_count < 600:
                return '2分'
            elif char_count < 1200:
                return '3分'
            elif char_count < 1800:
                return '5分'
            else:
                minutes = max(5, char_count // 300)
                return f'{minutes}分'

        except Exception:
            return '3分'

    def _calculate_priority_score(self, article: Dict, article_type: str, difficulty: str) -> float:
        """優先順位スコア計算"""
        try:
            score = 50.0  # ベーススコア

            # 記事タイプによる重み付け
            type_weights = {
                'トレンド': 30,
                'ニュース': 25,
                '技術解説': 20,
                'ツール': 15,
                '分析': 10,
                '記事': 5
            }
            score += type_weights.get(article_type, 0)

            # 難易度による重み付け
            difficulty_weights = {
                '初級': 15,
                '中級': 10,
                '上級': 5
            }
            score += difficulty_weights.get(difficulty, 0)

            # 記事の新しさ（24時間以内の記事は高スコア）
            try:
                published_str = article.get('published_at', '')
                if published_str:
                    published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    hours_ago = (datetime.now(timezone.utc) - published_dt).total_seconds() / 3600
                    if hours_ago <= 6:
                        score += 20
                    elif hours_ago <= 12:
                        score += 10
                    elif hours_ago <= 24:
                        score += 5
            except:
                pass

            # タイトルの長さ（適度な長さが好ましい）
            title_len = len(article.get('title', ''))
            if 20 <= title_len <= 60:
                score += 5

            return min(100.0, max(0.0, score))

        except Exception:
            return 50.0

    def _group_by_category(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """カテゴリ別グループ化"""
        try:
            categorized = {}

            for article in articles:
                category = article.get('category', 'その他')
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(article)

            return categorized

        except Exception as e:
            self.logger.error(f"カテゴリ別グループ化でエラー: {e}")
            return {'その他': articles}

    def _rank_articles(self, articles: List[Dict]) -> List[Dict]:
        """記事ランキング設定"""
        try:
            # 優先順位スコアで降順ソート
            sorted_articles = sorted(
                articles,
                key=lambda x: x.get('metadata', {}).get('priority_score', 0),
                reverse=True
            )

            # ランキング情報追加
            for i, article in enumerate(sorted_articles):
                if 'metadata' not in article:
                    article['metadata'] = {}
                article['metadata']['rank'] = i + 1

            return sorted_articles

        except Exception as e:
            self.logger.error(f"記事ランキング設定でエラー: {e}")
            return articles