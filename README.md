# 📡 RSS LINE Notifier

RSSフィードから新着記事を自動取得し、LINEメッセージとして美しいカルーセル形式で通知するサーバーレスシステムです。

## 🎯 プロジェクト概要

### 主な機能
- **自動RSS監視**: 定期的に複数のRSSフィードを監視
- **インテリジェント記事分析**: 記事の自動分類・難易度判定・読了時間推定
- **LINE通知**: 美しいカルーセル形式でのリッチメッセージ配信
- **LINEコマンド**: チャットでのフィード管理（追加・削除・一覧）
- **サーバーレス**: AWS Lambda による完全サーバーレス運用

## 🏗️ アーキテクチャ

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   LINE Platform │────│ API Gateway  │────│   Webhook   │
│                 │    │              │    │   Lambda    │
└─────────────────┘    └──────────────┘    └─────────────┘
                                                    │
                                                    ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   EventBridge   │────│   Schedule   │────│  Notifier   │
│  (Cron Trigger) │    │  (JST 12:30  │    │   Lambda    │
│                 │    │       21:00) │    │             │
└─────────────────┘    └──────────────┘    └─────────────┘
                                                    │
                                                    ▼
                       ┌──────────────┐    ┌─────────────┐
                       │   Amazon S3  │────│  RSS Feeds  │
                       │              │    │  External   │
                       └──────────────┘    └─────────────┘
```

## 🛠️ 技術スタック

### AWS サービス
- **Lambda**: サーバーレス実行環境（Python 3.12）
- **S3**: データストレージ（RSS設定・通知履歴）
- **API Gateway**: Webhook エンドポイント
- **EventBridge**: 定期実行スケジューラー
- **CloudWatch**: ログ・メトリクス監視
- **CloudFormation**: インフラコード化

### 開発技術
- **Python 3.12**: メイン開発言語
- **feedparser**: RSS解析
- **requests**: HTTP通信
- **boto3**: AWS SDK

### 外部API
- **LINE Messaging API**: メッセージ送信・Webhook
- **RSS Feeds**: 記事データ取得

## 📋 前提条件

### 必要なツール

#### Linux/macOS
```bash
# Python 3.12+
python3.12 --version  # Python 3.12.x

# AWS CLI v2
aws --version  # aws-cli/2.x.x

# zip コマンド
zip --version
```

#### Windows
```powershell
# Python 3.12+
python --version  # Python 3.12.x

# AWS CLI v2
aws --version  # aws-cli/2.x.x

# PowerShell（標準で利用可能）
$PSVersionTable.PSVersion
```

**サポート対象OS:**
- ✅ Ubuntu/Debian Linux（推奨）
- ✅ macOS（Intel/Apple Silicon）
- ✅ Windows 10/11（PowerShell/コマンドプロンプト）

> **Windows ユーザーへの注意**:
> - 管理者権限でPowerShellを実行することを推奨します
> - Git Bash または WSL (Windows Subsystem for Linux) の使用でより快適に開発できます
> - 環境変数の読み込み方法が異なるため、ドキュメント内のWindows向け手順を必ず確認してください

### 必要なアカウント
- **AWSアカウント**: Lambda、S3、API Gateway等の利用
- **LINE Developersアカウント**: Messaging API利用

## 🚀 クイックスタート

### プロジェクト取得
```bash
# GitHubからクローン
git clone https://github.com/Ryota-Mochizuki-04/SmartFeed
cd SmartFeed
```

### 自動セットアップ（推奨）

初学者向けの自動セットアップスクリプトを使用：

```bash
# 1. 環境セットアップ（対話形式）
./scripts/setup-environment.sh

# 2. 環境変数設定
cp config/env.template .env
# エディタで .env を編集し、実際の値を設定

# 3. RSS設定ファイル作成
cp config/rss-config.json.template config/rss-config.json
# エディタで RSS フィードを追加・編集

# 4. 環境変数読み込み
source .env

# 5. デプロイ実行
./scripts/deploy.sh
```

### 🎉 デプロイ後の構成

デプロイ完了後のシステム構成：

- **Webhook URL**: `https://[API-ID].execute-api.ap-northeast-1.amazonaws.com/prod/webhook`
- **S3バケット**: `rss-line-notifier-prod-[ACCOUNT-ID]`
- **通知スケジュール**: 毎日12:30と21:00（JST）
- **推奨デプロイ地域**: Asia Pacific (Tokyo) - ap-northeast-1

> 実際のURL・バケット名は、デプロイ時にAWSによって自動生成されます。

### 手動セットアップ

#### 1. 前提条件の確認
```bash
# Python 3.12+ の確認
python3.12 --version

# AWS CLI v2 の確認
aws --version

# 必須ツールのインストール（Ubuntu/Debian）
sudo apt update && sudo apt install -y python3.12 curl wget unzip jq
```

#### 2. LINE API設定
[👉 LINE API設定ガイド](docs/01_line_api_setup.md) の詳細手順に従って設定

#### 3. AWS設定
[👉 AWS設定ガイド](docs/02_aws_setup.md) の詳細手順に従って設定

#### 4. デプロイ実行
[👉 デプロイガイド](docs/03_deployment.md) の手順に従ってデプロイ

## 📚 ドキュメント

### 🔰 初学者向けガイド
- [📱 LINE API設定ガイド](docs/01_line_api_setup.md) - LINE Bot作成から認証情報取得まで
- [☁️ AWS設定ガイド](docs/02_aws_setup.md) - AWSアカウント作成からCLI設定まで
- [🚀 デプロイガイド](docs/03_deployment.md) - ステップバイステップデプロイ手順
- [⚡ 運用ガイド](docs/04_operation.md) - 日常運用・設定変更・監視方法
- [🔧 トラブルシューティング](docs/05_troubleshooting.md) - よくある問題と解決方法

### 📖 技術仕様書
- [📊 プロジェクト概要](vibe-coding-docs/01_project_overview.md)
- [🏗️ アーキテクチャ設計](vibe-coding-docs/02_architecture_design.md)
- [🔌 API仕様](vibe-coding-docs/03_api_specifications.md)
- [💾 データベース設計](vibe-coding-docs/04_database_storage_design.md)
- [⚙️ 環境設定](vibe-coding-docs/06_environment_configuration.md)

## 🔧 利用可能なコマンド

### LINEコマンド
| コマンド | 機能 | 例 |
|----------|------|-----|
| `一覧` | 登録済みRSSフィード表示 | `一覧` |
| `追加 <URL>` | RSSフィード追加 | `追加 https://qiita.com/popular/items/feed` |
| `削除 <番号>` | RSSフィード削除 | `削除 1` |
| `通知` | 手動通知実行 | `通知` |
| `ヘルプ` | 使用方法表示 | `ヘルプ` |

### 開発・運用コマンド
```bash
# 環境セットアップ（初回のみ）
./scripts/setup-environment.sh

# Lambda パッケージ作成
python3.12 scripts/create_packages.py

# デプロイ実行
./scripts/deploy.sh

# システム状況確認
./scripts/dev-utils.sh status

# ログ確認
./scripts/dev-utils.sh logs notifier
./scripts/dev-utils.sh logs webhook

# テスト実行
./scripts/dev-utils.sh test-lambda notifier
./scripts/dev-utils.sh test-line

# RSS設定検証
./scripts/dev-utils.sh validate-config
```

## 🎨 v2.1 新機能

### インテリジェント記事分析システム
- **記事タイプ自動分類**: 🔥トレンド、⚡技術解説、🛠️ツール、📊分析、📰ニュース
- **難易度推定**: 初級・中級・上級の3段階判定
- **読了時間推定**: 記事長に基づく読了時間算出
- **優先順位表示**: カテゴリ内での🥇🥈🥉ランキング
- **強化デザイン**: グラデーション背景、視覚的メタ情報

## 📊 プロジェクト構成

```
SmartFeed/
├── README.md                          # プロジェクト概要・使用方法
├── lambda_functions/                  # Lambda関数ソースコード
│   ├── common/                       # 共通ライブラリ
│   │   ├── line_client.py           # LINE API クライアント
│   │   ├── rss_analyzer.py          # RSS解析・分類エンジン
│   │   └── s3_manager.py            # S3データ管理
│   ├── notifier/                    # RSS監視・通知機能
│   │   ├── lambda_function.py       # メイン処理
│   │   └── requirements.txt         # 依存関係
│   └── webhook/                     # LINEコマンド処理機能
│       ├── lambda_function.py       # Webhook処理
│       └── requirements.txt         # 依存関係
├── infrastructure/                   # AWS CloudFormationテンプレート
│   ├── cloudformation-template.yaml # インフラ定義
│   └── parameters.json.template     # パラメータテンプレート
├── config/                          # 設定ファイル・テンプレート
│   ├── rss-config.json.template     # RSS設定テンプレート
│   ├── env.template                 # 環境変数テンプレート
│   └── templates/                   # 各種テンプレート
├── scripts/                         # デプロイ・運用スクリプト
│   ├── create_packages.py           # Lambda パッケージ作成
│   ├── deploy.sh                    # 自動デプロイスクリプト
│   ├── setup-environment.sh         # 環境セットアップ
│   └── dev-utils.sh                 # 開発・運用ユーティリティ
├── docs/                            # 初学者向けドキュメント
│   ├── 01_line_api_setup.md         # LINE API設定ガイド
│   ├── 02_aws_setup.md              # AWS設定ガイド
│   ├── 03_deployment.md             # デプロイガイド
│   ├── 04_operation.md              # 運用ガイド
│   └── 05_troubleshooting.md        # トラブルシューティング
└── vibe-coding-docs/                # 技術仕様書
    └── *.md                         # 詳細設計ドキュメント
```

## 🤝 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🆘 サポート

問題が発生した場合：
1. [docs/troubleshooting.md](docs/troubleshooting.md) を確認
2. [Issues](../../issues) で既存の問題を検索
3. 新しいIssueを作成

---

📚 **詳細なドキュメント**: [vibe-coding-docs/](vibe-coding-docs/) フォルダに完全な技術仕様書があります。