#!/bin/bash
"""
RSS LINE Notifier - 環境セットアップスクリプト
開発・デプロイ環境の初期設定を行うスクリプト
"""

set -e

# スクリプトの設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 使用方法表示
show_usage() {
    cat << EOF
RSS LINE Notifier 環境セットアップスクリプト

使用方法:
    $0 [オプション]

オプション:
    -h, --help              このヘルプを表示
    --install-tools         必須ツールの自動インストール（Ubuntu/Debian向け）
    --setup-aws             AWS CLI の設定ガイド
    --setup-line            LINE API の設定ガイド
    --create-env            環境変数ファイルの作成
    --validate              環境の検証

例:
    # 全体的なセットアップ
    $0

    # 必須ツールのインストール（Ubuntu/Debian）
    $0 --install-tools

    # AWS設定のみ
    $0 --setup-aws

    # LINE設定のみ
    $0 --setup-line
EOF
}

# システム情報確認
check_system_info() {
    log_info "システム情報を確認しています"

    echo "  OS: $(uname -s)"
    echo "  アーキテクチャ: $(uname -m)"

    if command -v lsb_release &> /dev/null; then
        echo "  ディストリビューション: $(lsb_release -d | cut -f2)"
    fi

    echo "  シェル: $SHELL"
    echo
}

# 必須ツールインストール（Ubuntu/Debian用）
install_tools_ubuntu() {
    log_info "必須ツールのインストールを開始します（Ubuntu/Debian向け）"

    # パッケージ更新
    log_info "パッケージリストを更新しています..."
    sudo apt-get update

    # 基本ツール
    log_info "基本ツールをインストールしています..."
    sudo apt-get install -y curl wget unzip jq git

    # Python 3.12
    log_info "Python 3.12をインストールしています..."
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt-get update
    sudo apt-get install -y python3.12 python3.12-venv python3.12-pip

    # AWS CLI v2
    if ! command -v aws &> /dev/null; then
        log_info "AWS CLI v2をインストールしています..."
        cd /tmp
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf awscliv2.zip aws/
        cd "$PROJECT_ROOT"
    else
        log_info "AWS CLIは既にインストールされています"
    fi

    log_success "必須ツールのインストールが完了しました"
}

# AWS CLI設定ガイド
setup_aws_guide() {
    cat << EOF

====================================
     AWS CLI 設定ガイド
====================================

1. AWS アカウントの準備
   - AWS アカウントが必要です
   - IAM ユーザーを作成し、適切な権限を付与してください

2. 必要な IAM 権限
   - CloudFormation: フルアクセス
   - Lambda: フルアクセス
   - S3: フルアクセス
   - API Gateway: フルアクセス
   - EventBridge: フルアクセス
   - IAM: 限定的なアクセス（ロール作成用）

3. AWS CLI設定
   以下のコマンドを実行してください:

   aws configure

   入力する情報:
   - AWS Access Key ID: [IAMユーザーのアクセスキー]
   - AWS Secret Access Key: [IAMユーザーのシークレットキー]
   - Default region name: ap-northeast-1
   - Default output format: json

4. 設定確認
   以下のコマンドで確認できます:

   aws sts get-caller-identity

====================================

EOF

    read -p "AWS CLIの設定を今すぐ行いますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        aws configure

        log_info "設定を確認しています..."
        if aws sts get-caller-identity; then
            log_success "AWS CLIの設定が正常に完了しました"
        else
            log_error "AWS CLIの設定に問題があります"
        fi
    fi
}

# LINE API設定ガイド
setup_line_guide() {
    cat << EOF

====================================
      LINE API 設定ガイド
====================================

1. LINE Developers アカウント作成
   https://developers.line.biz/ja/

2. プロバイダー作成
   - LINE Developers Console にログイン
   - 「プロバイダー」を作成

3. Messaging API チャネル作成
   - 作成したプロバイダーで「Messaging API」チャネルを作成
   - チャネル名: 「RSS LINE Notifier」（任意）
   - チャネル説明: 「RSS記事の通知Bot」（任意）

4. 必要な情報取得

   a) Channel Access Token
      - チャネル設定 → Messaging API設定
      - 「Channel access token」を発行・コピー

   b) Channel Secret
      - チャネル設定 → Basic settings
      - 「Channel secret」をコピー

   c) User ID
      - LINE公式アカウントマネージャーでBotと友達になる
      - または以下の方法で取得:
        1. Botにメッセージを送信
        2. Webhook経由でUser IDを取得

5. Webhook設定（デプロイ後）
   - デプロイ完了後にWebhook URLが表示されます
   - チャネル設定 → Messaging API設定
   - 「Webhook URL」に設定
   - 「Webhookの利用」を有効にする

====================================

取得した情報は次のステップで環境変数ファイルに設定します。

EOF
}

# 環境変数ファイル作成
create_env_file() {
    log_info "環境変数ファイルを作成します"

    local env_file="$PROJECT_ROOT/.env"

    # 既存ファイル確認
    if [ -f "$env_file" ]; then
        log_warning "環境変数ファイルが既に存在します: $env_file"
        read -p "上書きしますか？ (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "環境変数ファイルの作成をスキップしました"
            return
        fi
    fi

    # 対話的入力
    echo "LINE API設定情報を入力してください:"
    echo

    read -p "LINE Channel Access Token: " line_token
    read -p "LINE Channel Secret: " line_secret
    read -p "LINE User ID: " line_user_id

    echo
    read -p "AWS リージョン (デフォルト: ap-northeast-1): " aws_region
    aws_region=${aws_region:-ap-northeast-1}

    read -p "CloudFormation スタック名 (デフォルト: rss-line-notifier): " stack_name
    stack_name=${stack_name:-rss-line-notifier}

    # 環境変数ファイル作成
    cat > "$env_file" << EOF
# RSS LINE Notifier 環境変数設定
# このファイルは機密情報を含むため、Gitにコミットしないでください

# LINE API設定
export LINE_CHANNEL_TOKEN="$line_token"
export LINE_CHANNEL_SECRET="$line_secret"
export LINE_USER_ID="$line_user_id"

# AWS設定
export AWS_REGION="$aws_region"
export STACK_NAME="$stack_name"

# その他の設定
export LOG_LEVEL="INFO"
export MAX_FEEDS="100"
export ARTICLE_AGE_HOURS="24"
export REQUEST_TIMEOUT="30"
export PARALLEL_WORKERS="10"
EOF

    log_success "環境変数ファイルが作成されました: $env_file"

    # .gitignore 更新
    local gitignore_file="$PROJECT_ROOT/.gitignore"
    if [ -f "$gitignore_file" ]; then
        if ! grep -q "^\.env$" "$gitignore_file"; then
            echo ".env" >> "$gitignore_file"
            log_info ".gitignore に .env を追加しました"
        fi
    fi

    # 使用方法案内
    cat << EOF

環境変数の読み込み方法:

1. 現在のシェルセッションで読み込み:
   source .env

2. デプロイ実行時に自動読み込み:
   source .env && ./scripts/deploy.sh

3. 継続的に使用する場合は ~/.bashrc に追加:
   echo "source $env_file" >> ~/.bashrc

EOF
}

# 環境検証
validate_environment() {
    log_info "環境の検証を開始します"

    local errors=0

    # Python 3.12確認
    if command -v python3.12 &> /dev/null; then
        local python_version=$(python3.12 --version)
        log_success "Python: $python_version"
    else
        log_error "Python 3.12が見つかりません"
        ((errors++))
    fi

    # AWS CLI確認
    if command -v aws &> /dev/null; then
        local aws_version=$(aws --version)
        log_success "AWS CLI: $aws_version"

        # AWS設定確認
        if aws sts get-caller-identity &> /dev/null; then
            log_success "AWS認証: 設定済み"
        else
            log_error "AWS認証が設定されていません"
            ((errors++))
        fi
    else
        log_error "AWS CLIが見つかりません"
        ((errors++))
    fi

    # jq確認
    if command -v jq &> /dev/null; then
        local jq_version=$(jq --version)
        log_success "jq: $jq_version"
    else
        log_error "jqが見つかりません"
        ((errors++))
    fi

    # 環境変数確認
    local env_file="$PROJECT_ROOT/.env"
    if [ -f "$env_file" ]; then
        log_success "環境変数ファイル: 作成済み ($env_file)"

        # 環境変数読み込み検証
        source "$env_file"
        if [ -n "$LINE_CHANNEL_TOKEN" ] && [ -n "$LINE_CHANNEL_SECRET" ] && [ -n "$LINE_USER_ID" ]; then
            log_success "LINE API設定: 設定済み"
        else
            log_warning "LINE API設定が不完全です"
        fi
    else
        log_warning "環境変数ファイルが見つかりません"
    fi

    # 結果表示
    echo
    if [ $errors -eq 0 ]; then
        log_success "環境検証が正常に完了しました"
        echo
        echo "次のステップ:"
        echo "1. RSS設定ファイルを作成: config/rss-config.json"
        echo "2. デプロイを実行: ./scripts/deploy.sh"
    else
        log_error "環境に $errors 個の問題があります"
        echo "上記の問題を解決してから再度実行してください"
        exit 1
    fi
}

# メイン実行
main() {
    local install_tools=false
    local setup_aws=false
    local setup_line=false
    local create_env=false
    local validate=false

    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --install-tools)
                install_tools=true
                shift
                ;;
            --setup-aws)
                setup_aws=true
                shift
                ;;
            --setup-line)
                setup_line=true
                shift
                ;;
            --create-env)
                create_env=true
                shift
                ;;
            --validate)
                validate=true
                shift
                ;;
            *)
                log_error "不明なオプション: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # バナー表示
    echo
    echo "=============================================="
    echo "  RSS LINE Notifier 環境セットアップ"
    echo "=============================================="
    echo

    # システム情報表示
    check_system_info

    # 個別実行
    if [ "$install_tools" = true ]; then
        install_tools_ubuntu
        exit 0
    fi

    if [ "$setup_aws" = true ]; then
        setup_aws_guide
        exit 0
    fi

    if [ "$setup_line" = true ]; then
        setup_line_guide
        exit 0
    fi

    if [ "$create_env" = true ]; then
        create_env_file
        exit 0
    fi

    if [ "$validate" = true ]; then
        validate_environment
        exit 0
    fi

    # 全体的なセットアップ（デフォルト）
    cat << EOF
=== RSS LINE Notifier セットアップ ===

このスクリプトでは以下のセットアップを行います:
1. システム要件の確認
2. AWS CLI設定
3. LINE API設定
4. 環境変数ファイル作成
5. 環境検証

続行しますか？
EOF

    read -p "(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "セットアップを中止しました"
        exit 0
    fi

    # セットアップ実行
    echo
    log_info "=== Step 1: AWS CLI設定 ==="
    setup_aws_guide

    echo
    log_info "=== Step 2: LINE API設定 ==="
    setup_line_guide

    echo
    log_info "=== Step 3: 環境変数ファイル作成 ==="
    create_env_file

    echo
    log_info "=== Step 4: 環境検証 ==="
    validate_environment

    echo
    log_success "環境セットアップが完了しました！"
}

# スクリプト実行
main "$@"