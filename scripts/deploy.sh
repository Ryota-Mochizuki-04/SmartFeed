#!/bin/bash
#
# RSS LINE Notifier - 自動デプロイスクリプト
# AWS Lambda関数の自動ビルド・デプロイを行うスクリプト
#

set -e  # エラー時に終了

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
RSS LINE Notifier デプロイスクリプト

使用方法:
    $0 [オプション]

オプション:
    -h, --help              このヘルプを表示
    -r, --region REGION     AWS リージョン (デフォルト: ap-northeast-1)
    -s, --stack STACK_NAME  CloudFormation スタック名 (デフォルト: rss-line-notifier)
    -p, --package-only      パッケージ作成のみ実行
    -d, --deploy-only       デプロイのみ実行 (パッケージは既存のものを使用)
    -l, --lambda-only       Lambda関数のコードのみ更新
    -v, --validate          デプロイ前検証のみ実行
    --dry-run              実際のデプロイを行わずに確認のみ

環境変数:
    AWS_REGION             AWS リージョン
    STACK_NAME             CloudFormation スタック名
    LINE_CHANNEL_TOKEN     LINE Channel Access Token
    LINE_CHANNEL_SECRET    LINE Channel Secret
    LINE_USER_ID           LINE ユーザーID

例:
    # 通常のデプロイ
    $0

    # 特定リージョンへのデプロイ
    $0 --region us-east-1

    # パッケージのみ作成
    $0 --package-only

    # Lambda関数のみ更新
    $0 --lambda-only

    # デプロイ前確認
    $0 --dry-run
EOF
}

# 必須ツール確認
check_prerequisites() {
    log_info "必須ツールの確認を開始します"

    local missing_tools=()

    # AWS CLI確認
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi

    # Python 3.12確認
    if ! command -v python3.12 &> /dev/null && ! command -v python3 &> /dev/null; then
        missing_tools+=("python3.12")
    fi

    # jq確認（JSON処理用）
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "以下のツールがインストールされていません:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        echo
        echo "インストール方法:"
        echo "  AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        echo "  Python 3.12: https://www.python.org/downloads/"
        echo "  jq: sudo apt-get install jq (Ubuntu/Debian) または brew install jq (macOS)"
        exit 1
    fi

    # AWS認証確認
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS認証が設定されていません"
        echo "AWS CLIの設定を行ってください:"
        echo "  aws configure"
        exit 1
    fi

    log_success "必須ツールの確認が完了しました"
}

# 環境変数確認
check_environment_variables() {
    log_info "環境変数の確認を開始します"

    local missing_vars=()

    # 必須環境変数チェック
    if [ -z "$LINE_CHANNEL_TOKEN" ]; then
        missing_vars+=("LINE_CHANNEL_TOKEN")
    fi

    if [ -z "$LINE_CHANNEL_SECRET" ]; then
        missing_vars+=("LINE_CHANNEL_SECRET")
    fi

    if [ -z "$LINE_USER_ID" ]; then
        missing_vars+=("LINE_USER_ID")
    fi

    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "以下の環境変数が設定されていません:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo
        echo "環境変数の設定方法については、README.md を参照してください"
        exit 1
    fi

    log_success "環境変数の確認が完了しました"
}

# Lambda パッケージ作成
create_lambda_packages() {
    log_info "Lambda パッケージの作成を開始します"

    cd "$PROJECT_ROOT"

    # Python スクリプト実行
    if command -v python3.12 &> /dev/null; then
        python3.12 scripts/create_packages.py
    else
        python3 scripts/create_packages.py
    fi

    # パッケージファイル確認
    if [ ! -f "notifier-deployment.zip" ] || [ ! -f "webhook-deployment.zip" ]; then
        log_error "Lambda パッケージの作成に失敗しました"
        exit 1
    fi

    log_success "Lambda パッケージの作成が完了しました"
}

# CloudFormation テンプレート検証
validate_cloudformation_template() {
    log_info "CloudFormation テンプレートの検証を開始します"

    local template_file="$PROJECT_ROOT/infrastructure/cloudformation-template.yaml"

    if [ ! -f "$template_file" ]; then
        log_error "CloudFormation テンプレートが見つかりません: $template_file"
        exit 1
    fi

    aws cloudformation validate-template \
        --template-body "file://$template_file" \
        --region "$REGION" \
        > /dev/null

    log_success "CloudFormation テンプレートの検証が完了しました"
}

# S3バケット作成（デプロイ用）
create_deployment_bucket() {
    local bucket_name="$1"

    log_info "デプロイ用S3バケットの確認・作成: $bucket_name"

    # バケット存在確認
    if aws s3api head-bucket --bucket "$bucket_name" --region "$REGION" 2>/dev/null; then
        log_info "S3バケットは既に存在します: $bucket_name"
        return 0
    fi

    # バケット作成
    if [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$bucket_name" \
            --region "$REGION"
    else
        aws s3api create-bucket \
            --bucket "$bucket_name" \
            --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
    fi

    # パブリックアクセスブロック設定
    aws s3api put-public-access-block \
        --bucket "$bucket_name" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

    log_success "S3バケットの作成が完了しました: $bucket_name"
}

# Lambda パッケージアップロード
upload_lambda_packages() {
    local bucket_name="$1"

    log_info "Lambda パッケージのS3アップロードを開始します"

    cd "$PROJECT_ROOT"

    # Notifier パッケージアップロード
    aws s3 cp notifier-deployment.zip "s3://$bucket_name/lambda-packages/" \
        --region "$REGION"

    # Webhook パッケージアップロード
    aws s3 cp webhook-deployment.zip "s3://$bucket_name/lambda-packages/" \
        --region "$REGION"

    log_success "Lambda パッケージのアップロードが完了しました"
}

# CloudFormation デプロイ
deploy_cloudformation() {
    local bucket_name="$1"

    log_info "CloudFormation スタックのデプロイを開始します"

    local template_file="$PROJECT_ROOT/infrastructure/cloudformation-template.yaml"
    local timestamp=$(date +%Y%m%d-%H%M%S)

    # パラメータ設定
    local parameters=(
        "ParameterKey=LineChannelToken,ParameterValue=$LINE_CHANNEL_TOKEN"
        "ParameterKey=LineChannelSecret,ParameterValue=$LINE_CHANNEL_SECRET"
        "ParameterKey=LineUserId,ParameterValue=$LINE_USER_ID"
        "ParameterKey=Environment,ParameterValue=prod"
    )

    # スタック存在確認
    if aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" &> /dev/null; then

        log_info "既存スタックを更新します: $STACK_NAME"

        # CloudFormation更新を試行（変更がない場合はエラーになる）
        if aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body "file://$template_file" \
            --parameters "${parameters[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION" 2>&1; then

            log_info "スタック更新の完了を待機しています..."
            aws cloudformation wait stack-update-complete \
                --stack-name "$STACK_NAME" \
                --region "$REGION"
        else
            local exit_code=$?
            if [ $exit_code -eq 254 ]; then
                log_warning "テンプレートに変更がないため、CloudFormationの更新はスキップされました"
                log_info "Lambda関数のコードのみを直接更新します"
                update_lambda_functions_directly
            else
                log_error "CloudFormation更新でエラーが発生しました"
                exit $exit_code
            fi
        fi
    else
        log_info "新規スタックを作成します: $STACK_NAME"

        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body "file://$template_file" \
            --parameters "${parameters[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"

        log_info "スタック作成の完了を待機しています..."
        aws cloudformation wait stack-create-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
    fi

    log_success "CloudFormation スタックのデプロイが完了しました"
}

# Lambda関数のコードを直接更新
update_lambda_functions_directly() {
    log_info "Lambda関数のコードを直接更新します"

    cd "$PROJECT_ROOT"

    # Notifier Lambda更新
    log_info "Notifier Lambda関数を更新中..."
    aws lambda update-function-code \
        --function-name "rss-notifier-prod" \
        --zip-file fileb://notifier-deployment.zip \
        --region "$REGION" > /dev/null

    # Webhook Lambda更新
    log_info "Webhook Lambda関数を更新中..."
    aws lambda update-function-code \
        --function-name "rss-webhook-prod" \
        --zip-file fileb://webhook-deployment.zip \
        --region "$REGION" > /dev/null

    log_success "Lambda関数のコード更新が完了しました"
}

# デプロイ結果表示
show_deployment_results() {
    log_info "デプロイ結果を取得しています"

    # スタック出力取得
    local outputs=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' \
        --output json)

    if [ "$outputs" != "null" ] && [ -n "$outputs" ]; then
        echo
        log_success "=== デプロイ完了 ==="
        echo
        echo "$outputs" | jq -r '.[] | "  \(.OutputKey): \(.OutputValue)"'
        echo
    fi

    # 次のステップ案内
    cat << EOF
=== 次のステップ ===

1. LINE Bot設定
   - LINE Developers Console でWebhook URLを設定
   - Webhook URL: $(echo "$outputs" | jq -r '.[] | select(.OutputKey=="WebhookURL") | .OutputValue' 2>/dev/null || echo "CloudFormation出力から取得してください")

2. RSS設定
   - S3バケットに rss-config.json をアップロード
   - 設定例: config/rss-config.json.template

3. テスト実行
   - Lambda関数のテスト実行
   - LINE Botとの動作確認

詳細な設定方法については、README.md を参照してください。
EOF
}

# メイン実行
main() {
    local package_only=false
    local deploy_only=false
    local lambda_only=false
    local validate_only=false
    local dry_run=false

    # 引数解析
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
            -p|--package-only)
                package_only=true
                shift
                ;;
            -d|--deploy-only)
                deploy_only=true
                shift
                ;;
            -l|--lambda-only)
                lambda_only=true
                shift
                ;;
            -v|--validate)
                validate_only=true
                shift
                ;;
            --dry-run)
                dry_run=true
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
    echo "========================================"
    echo "  RSS LINE Notifier デプロイスクリプト"
    echo "========================================"
    echo "  リージョン: $REGION"
    echo "  スタック名: $STACK_NAME"
    echo "========================================"
    echo

    # 前提条件確認
    check_prerequisites

    if [ "$validate_only" = true ]; then
        validate_cloudformation_template
        log_success "検証が完了しました"
        exit 0
    fi

    # 環境変数確認（デプロイ時のみ）
    if [ "$package_only" = false ]; then
        check_environment_variables
    fi

    # パッケージ作成
    if [ "$deploy_only" = false ]; then
        create_lambda_packages
    fi

    if [ "$package_only" = true ]; then
        log_success "パッケージ作成が完了しました"
        exit 0
    fi

    # Lambda関数のみ更新
    if [ "$lambda_only" = true ]; then
        update_lambda_functions_directly
        log_success "Lambda関数の更新が完了しました"
        exit 0
    fi

    # CloudFormation テンプレート検証
    validate_cloudformation_template

    if [ "$dry_run" = true ]; then
        log_success "Dry-run が完了しました。実際のデプロイは行われませんでした"
        exit 0
    fi

    # デプロイ実行
    local bucket_name="${STACK_NAME}-deploy-$(date +%Y%m%d)"

    create_deployment_bucket "$bucket_name"
    upload_lambda_packages "$bucket_name"
    deploy_cloudformation "$bucket_name"
    show_deployment_results

    log_success "全てのデプロイ処理が正常に完了しました！"
}

# スクリプト実行
main "$@"