#!/bin/bash
"""
RSS LINE Notifier - 開発ユーティリティスクリプト
開発・テスト・メンテナンス用のユーティリティ機能
"""

set -e

# スクリプトの設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGION="${AWS_REGION:-ap-northeast-1}"
STACK_NAME="${STACK_NAME:-rss-line-notifier}"

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_dev() {
    echo -e "${CYAN}[DEV]${NC} $1"
}

# 使用方法表示
show_usage() {
    cat << EOF
RSS LINE Notifier 開発ユーティリティ

使用方法:
    $0 <コマンド> [オプション]

コマンド:
    test-lambda <function-name>     Lambda関数のテスト実行
    test-line                       LINE API接続テスト
    logs <function-name>            Lambda関数のログ表示
    status                          デプロイ状況確認
    clean                           一時ファイル・キャッシュクリーンアップ
    validate-config                 RSS設定ファイル検証
    test-rss <feed-url>             個別RSSフィード取得テスト
    backup-config                   S3設定ファイルのバックアップ
    restore-config <backup-file>    S3設定ファイルの復元
    invoke-notifier                 Notifier Lambda の手動実行
    tail-logs <function-name>       Lambda ログのリアルタイム監視

オプション:
    -h, --help                      このヘルプを表示
    -r, --region <region>           AWS リージョン指定
    -s, --stack <stack-name>        CloudFormation スタック名指定
    -v, --verbose                   詳細出力

例:
    # Lambda関数テスト
    $0 test-lambda notifier

    # LINE API接続テスト
    $0 test-line

    # ログ表示
    $0 logs webhook

    # RSS フィード取得テスト
    $0 test-rss "https://example.com/feed.xml"

    # リアルタイムログ監視
    $0 tail-logs notifier
EOF
}

# Lambda関数名取得
get_lambda_function_name() {
    local function_type="$1"

    local function_name=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='${function_type^}FunctionName'].OutputValue" \
        --output text 2>/dev/null)

    if [ -z "$function_name" ] || [ "$function_name" = "None" ]; then
        # フォールバック: 命名規則から推測
        function_name="${STACK_NAME}-${function_type}"
    fi

    echo "$function_name"
}

# S3バケット名取得
get_s3_bucket_name() {
    local bucket_name=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" \
        --output text 2>/dev/null)

    if [ -z "$bucket_name" ] || [ "$bucket_name" = "None" ]; then
        log_error "S3バケット名を取得できませんでした"
        exit 1
    fi

    echo "$bucket_name"
}

# Lambda関数テスト
test_lambda() {
    local function_type="$1"

    if [ -z "$function_type" ]; then
        log_error "Lambda関数タイプを指定してください (notifier または webhook)"
        exit 1
    fi

    local function_name=$(get_lambda_function_name "$function_type")

    log_info "Lambda関数のテストを実行します: $function_name"

    # テストイベント作成
    local test_event
    if [ "$function_type" = "notifier" ]; then
        test_event='{
            "source": "test",
            "detail-type": "Scheduled Event",
            "detail": {}
        }'
    else
        test_event='{
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/json",
                "X-Line-Signature": "test-signature"
            },
            "body": "{\"events\":[]}"
        }'
    fi

    # Lambda実行
    log_dev "テストイベント: $test_event"

    aws lambda invoke \
        --function-name "$function_name" \
        --payload "$test_event" \
        --region "$REGION" \
        /tmp/lambda-response.json

    # 結果表示
    echo
    log_success "Lambda実行結果:"
    cat /tmp/lambda-response.json | jq .

    # エラーログ確認
    local error_type=$(cat /tmp/lambda-response.json | jq -r '.errorType // empty')
    if [ -n "$error_type" ]; then
        log_error "Lambda関数でエラーが発生しました"
        echo "ログを確認してください: $0 logs $function_type"
    fi

    rm -f /tmp/lambda-response.json
}

# LINE API接続テスト
test_line() {
    log_info "LINE API接続テストを実行します"

    # 環境変数確認
    if [ -z "$LINE_CHANNEL_TOKEN" ] || [ -z "$LINE_USER_ID" ]; then
        log_error "LINE API設定が不足しています"
        echo "環境変数を設定してください: LINE_CHANNEL_TOKEN, LINE_USER_ID"
        exit 1
    fi

    # テストメッセージ送信
    local test_message="🧪 RSS LINE Notifier テストメッセージ\\n送信時刻: $(date)"

    local response=$(curl -s -X POST https://api.line.me/v2/bot/message/push \
        -H "Authorization: Bearer $LINE_CHANNEL_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"to\": \"$LINE_USER_ID\",
            \"messages\": [{
                \"type\": \"text\",
                \"text\": \"$test_message\"
            }]
        }")

    if echo "$response" | jq -e '.message' >/dev/null 2>&1; then
        log_error "LINE API呼び出しでエラーが発生しました:"
        echo "$response" | jq .
    else
        log_success "LINE APIテストメッセージが正常に送信されました"
    fi
}

# Lambda関数ログ表示
show_lambda_logs() {
    local function_type="$1"
    local lines="${2:-50}"

    if [ -z "$function_type" ]; then
        log_error "Lambda関数タイプを指定してください (notifier または webhook)"
        exit 1
    fi

    local function_name=$(get_lambda_function_name "$function_type")
    local log_group="/aws/lambda/$function_name"

    log_info "Lambda関数のログを表示します: $function_name"
    log_info "ロググループ: $log_group"

    aws logs tail "$log_group" \
        --region "$REGION" \
        --since 1h \
        --format short
}

# リアルタイムログ監視
tail_lambda_logs() {
    local function_type="$1"

    if [ -z "$function_type" ]; then
        log_error "Lambda関数タイプを指定してください (notifier または webhook)"
        exit 1
    fi

    local function_name=$(get_lambda_function_name "$function_type")
    local log_group="/aws/lambda/$function_name"

    log_info "Lambda関数のリアルタイムログ監視を開始します: $function_name"
    log_info "終了するには Ctrl+C を押してください"
    echo

    aws logs tail "$log_group" \
        --region "$REGION" \
        --follow \
        --format short
}

# デプロイ状況確認
check_status() {
    log_info "デプロイ状況を確認しています"

    # CloudFormationスタック状況
    local stack_status=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    echo
    echo "=== CloudFormation スタック ==="
    echo "  スタック名: $STACK_NAME"
    echo "  リージョン: $REGION"
    echo "  ステータス: $stack_status"

    if [ "$stack_status" = "NOT_FOUND" ]; then
        log_warning "CloudFormationスタックが見つかりません"
        return
    fi

    # Lambda関数状況
    echo
    echo "=== Lambda 関数 ==="

    for func_type in notifier webhook; do
        local func_name=$(get_lambda_function_name "$func_type")
        local func_status=$(aws lambda get-function \
            --function-name "$func_name" \
            --region "$REGION" \
            --query 'Configuration.State' \
            --output text 2>/dev/null || echo "NOT_FOUND")

        echo "  $func_type: $func_name ($func_status)"
    done

    # S3バケット状況
    echo
    echo "=== S3 バケット ==="
    local bucket_name=$(get_s3_bucket_name)

    if aws s3api head-bucket --bucket "$bucket_name" --region "$REGION" 2>/dev/null; then
        local file_count=$(aws s3 ls "s3://$bucket_name" --recursive | wc -l)
        echo "  バケット名: $bucket_name (ファイル数: $file_count)"

        # RSS設定ファイル確認
        if aws s3api head-object --bucket "$bucket_name" --key "rss-config.json" --region "$REGION" 2>/dev/null; then
            echo "  RSS設定: 設定済み"
        else
            echo "  RSS設定: 未設定"
        fi
    else
        echo "  バケット名: $bucket_name (アクセス不可)"
    fi

    # スタック出力
    echo
    echo "=== スタック出力 ==="
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' \
        --output table 2>/dev/null || echo "出力情報を取得できませんでした"
}

# クリーンアップ
clean_up() {
    log_info "クリーンアップを実行します"

    # 一時ファイル削除
    find "$PROJECT_ROOT" -name "*.pyc" -delete
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.zip" -path "*/scripts/*" -delete 2>/dev/null || true

    # デプロイパッケージ削除
    rm -f "$PROJECT_ROOT"/*.zip

    # ログファイル削除
    rm -f /tmp/lambda-response.json
    rm -f /tmp/rss-test-*.json

    log_success "クリーンアップが完了しました"
}

# RSS設定ファイル検証
validate_rss_config() {
    log_info "RSS設定ファイルを検証します"

    local bucket_name=$(get_s3_bucket_name)

    # S3から設定ファイル取得
    if ! aws s3 cp "s3://$bucket_name/rss-config.json" /tmp/rss-config.json --region "$REGION" 2>/dev/null; then
        log_error "RSS設定ファイルが見つかりません"
        echo "設定ファイルを作成してS3にアップロードしてください"
        exit 1
    fi

    # JSON構文確認
    if ! jq . /tmp/rss-config.json >/dev/null 2>&1; then
        log_error "RSS設定ファイルのJSON構文が正しくありません"
        exit 1
    fi

    # 設定内容確認
    local feed_count=$(jq '.feeds | length' /tmp/rss-config.json)
    log_success "RSS設定ファイルは正常です (フィード数: $feed_count)"

    # 設定内容表示
    echo
    echo "=== RSS設定内容 ==="
    jq . /tmp/rss-config.json

    rm -f /tmp/rss-config.json
}

# 個別RSSフィード取得テスト
test_rss_feed() {
    local feed_url="$1"

    if [ -z "$feed_url" ]; then
        log_error "RSSフィードURLを指定してください"
        exit 1
    fi

    log_info "RSSフィード取得テストを実行します: $feed_url"

    # Python テストスクリプト作成・実行
    python3.12 << EOF
import feedparser
import json
from datetime import datetime, timezone

try:
    # RSSフィード取得
    feed = feedparser.parse('$feed_url')

    if feed.bozo:
        print("⚠️ RSS解析でwarningが発生しました:")
        print(f"   {feed.bozo_exception}")

    print(f"📡 フィードタイトル: {feed.feed.get('title', 'N/A')}")
    print(f"📝 フィード説明: {feed.feed.get('description', 'N/A')}")
    print(f"📊 記事数: {len(feed.entries)}")

    if feed.entries:
        print("\n=== 最新記事 (最大5件) ===")
        for i, entry in enumerate(feed.entries[:5]):
            print(f"\n{i+1}. {entry.get('title', 'タイトル不明')}")
            print(f"   URL: {entry.get('link', 'N/A')}")
            print(f"   公開日: {entry.get('published', 'N/A')}")
            if hasattr(entry, 'summary'):
                summary = entry.summary[:100] + "..." if len(entry.summary) > 100 else entry.summary
                print(f"   概要: {summary}")

    # 結果をJSONで保存
    result = {
        'feed_url': '$feed_url',
        'title': feed.feed.get('title', ''),
        'description': feed.feed.get('description', ''),
        'entry_count': len(feed.entries),
        'entries': [
            {
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'summary': entry.get('summary', '')[:200]
            }
            for entry in feed.entries[:5]
        ],
        'tested_at': datetime.now(timezone.utc).isoformat()
    }

    with open('/tmp/rss-test-result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ RSSフィード取得テストが完了しました")
    print(f"詳細結果: /tmp/rss-test-result.json")

except Exception as e:
    print(f"❌ RSSフィード取得でエラーが発生しました: {e}")
    exit(1)
EOF
}

# 設定ファイルバックアップ
backup_config() {
    log_info "S3設定ファイルのバックアップを作成します"

    local bucket_name=$(get_s3_bucket_name)
    local backup_dir="$PROJECT_ROOT/backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    mkdir -p "$backup_dir"

    # RSS設定バックアップ
    if aws s3 cp "s3://$bucket_name/rss-config.json" "$backup_dir/rss-config_$timestamp.json" --region "$REGION"; then
        log_success "RSS設定ファイルをバックアップしました: $backup_dir/rss-config_$timestamp.json"
    else
        log_warning "RSS設定ファイルのバックアップに失敗しました"
    fi

    # 通知履歴バックアップ
    if aws s3 cp "s3://$bucket_name/notification-history.json" "$backup_dir/notification-history_$timestamp.json" --region "$REGION" 2>/dev/null; then
        log_success "通知履歴ファイルをバックアップしました: $backup_dir/notification-history_$timestamp.json"
    else
        log_info "通知履歴ファイルは存在しないか、バックアップできませんでした"
    fi
}

# 設定ファイル復元
restore_config() {
    local backup_file="$1"

    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        log_error "バックアップファイルを指定してください"
        exit 1
    fi

    local bucket_name=$(get_s3_bucket_name)

    log_info "設定ファイルを復元します: $backup_file"

    # JSON構文確認
    if ! jq . "$backup_file" >/dev/null 2>&1; then
        log_error "バックアップファイルのJSON構文が正しくありません"
        exit 1
    fi

    # S3にアップロード
    if aws s3 cp "$backup_file" "s3://$bucket_name/rss-config.json" --region "$REGION"; then
        log_success "設定ファイルの復元が完了しました"
    else
        log_error "設定ファイルの復元に失敗しました"
        exit 1
    fi
}

# Notifier Lambda手動実行
invoke_notifier() {
    log_info "Notifier Lambda関数を手動実行します"

    local function_name=$(get_lambda_function_name "notifier")

    # 実行イベント作成
    local invoke_event='{
        "source": "manual",
        "detail-type": "Manual Trigger",
        "detail": {
            "triggered_by": "dev-utils",
            "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
        }
    }'

    log_dev "実行イベント: $invoke_event"

    # Lambda実行（非同期）
    aws lambda invoke \
        --function-name "$function_name" \
        --invocation-type Event \
        --payload "$invoke_event" \
        --region "$REGION" \
        /tmp/lambda-invoke-response.json

    log_success "Notifier Lambda関数を実行しました（非同期）"
    log_info "実行結果を確認するには: $0 logs notifier"

    rm -f /tmp/lambda-invoke-response.json
}

# メイン実行
main() {
    local verbose=false

    # 引数が空の場合はヘルプ表示
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi

    # 共通オプション解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -s|--stack)
                STACK_NAME="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            test-lambda)
                test_lambda "$2"
                exit 0
                ;;
            test-line)
                test_line
                exit 0
                ;;
            logs)
                show_lambda_logs "$2" "$3"
                exit 0
                ;;
            tail-logs)
                tail_lambda_logs "$2"
                exit 0
                ;;
            status)
                check_status
                exit 0
                ;;
            clean)
                clean_up
                exit 0
                ;;
            validate-config)
                validate_rss_config
                exit 0
                ;;
            test-rss)
                test_rss_feed "$2"
                exit 0
                ;;
            backup-config)
                backup_config
                exit 0
                ;;
            restore-config)
                restore_config "$2"
                exit 0
                ;;
            invoke-notifier)
                invoke_notifier
                exit 0
                ;;
            *)
                log_error "不明なコマンド: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# スクリプト実行
main "$@"