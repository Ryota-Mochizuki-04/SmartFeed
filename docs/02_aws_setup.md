# AWS セットアップガイド

このガイドでは、RSS LINE Notifier をデプロイするための AWS 環境の設定方法を説明します。

## 目次

1. [AWS アカウントの準備](#1-aws-アカウントの準備)
2. [IAM ユーザー作成](#2-iam-ユーザー作成)
3. [AWS CLI インストール](#3-aws-cli-インストール)
4. [AWS CLI 設定](#4-aws-cli-設定)
5. [必要な AWS サービス](#5-必要なaws-サービス)
6. [料金について](#6-料金について)
7. [トラブルシューティング](#7-トラブルシューティング)

---

## 1. AWS アカウントの準備

### 1.1 AWS アカウント作成

1. [AWS 公式サイト](https://aws.amazon.com/jp/) にアクセス
2. 「無料で始める」をクリック
3. 必要な情報を入力してアカウント作成：
   - **メールアドレス**: 連絡可能なメールアドレス
   - **パスワード**: 強力なパスワード
   - **AWS アカウント名**: 任意の名前

### 1.2 支払い情報登録

1. クレジットカード情報を登録
2. 住所情報を入力
3. 電話番号認証を完了

⚠️ **注意**: 無料利用枠を超えた場合のみ課金されます。個人利用であれば月額数十円程度です。

### 1.3 サポートプラン選択

**無料の「Basic サポート」** を選択（個人利用には十分）

---

## 2. IAM ユーザー作成

セキュリティのため、root ユーザーではなく専用の IAM ユーザーを作成します。

### 2.1 IAM コンソールにアクセス

1. AWS Management Console にログイン
2. 検索で「IAM」と入力してサービスにアクセス

### 2.2 ユーザー作成

1. 左側メニューで「ユーザー」をクリック
2. 「ユーザーを追加」をクリック

### 2.3 ユーザー詳細設定

#### ユーザー名

```
rss-notifier-deploy
```

#### アクセスの種類

- ✅ **プログラムによるアクセス** にチェック
- AWS Management Console アクセスは不要（チェック外す）

### 2.4 アクセス許可設定

「既存のポリシーを直接アタッチ」を選択し、以下のポリシーを検索・選択：

#### 必須ポリシー

```
✅ IAMFullAccess
✅ AmazonS3FullAccess
✅ AWSLambda_FullAccess
✅ AmazonAPIGatewayAdministrator
✅ CloudFormationFullAccess
✅ AmazonEventBridgeFullAccess
✅ CloudWatchLogsFullAccess
```

⚠️ **セキュリティ注意**: これらは開発・デプロイ用の権限です。本番環境では最小権限の原則に従ってください。

### 2.5 タグ設定（オプション）

任意でタグを追加：

```
Key: Project, Value: RSS-LINE-Notifier
Key: Environment, Value: Development
```

### 2.6 確認・作成

1. 設定内容を確認
2. 「ユーザーの作成」をクリック

### 2.7 アクセスキーの作成

ユーザー作成後、プログラムからアクセスするためのアクセスキーを作成します。

#### 2.7.1 アクセスキー作成手順

1. **作成したユーザーをクリック**
   - IAM ユーザー一覧で `rss-notifier-deploy` をクリック

2. **「セキュリティ認証情報」タブをクリック**

3. **「アクセスキーを作成」をクリック**

4. **使用事例を選択**
   - 「コマンドラインインターフェイス (CLI)」を選択
   - 確認のチェックボックスにチェック
   - 「次へ」をクリック

5. **説明タグを設定（オプション）**
   - 説明タグ: `RSS Notifier CLI Access`
   - 「アクセスキーを作成」をクリック

#### 2.7.2 認証情報の保存

アクセスキー作成が完了すると、以下の情報が表示されます：

```
✅ アクセスキーが正常に作成されました

Access Key ID: AKIA1234567890ABCDEF
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfic...

⚠️ この情報は再度表示されません
```

#### 📝 保存方法（必須）

**方法1: CSVファイルのダウンロード（推奨）**
1. 「.csv ファイルをダウンロード」ボタンをクリック
2. ファイルを安全な場所に保存

**方法2: 手動でコピー**
1. Access Key ID と Secret Access Key をそれぞれコピー
2. テキストファイルに以下の形式で保存：

```
# AWS RSS Notifier 認証情報
Access Key ID: AKIA1234567890ABCDEF
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
作成日: 2024-XX-XX
```

⚠️ **重要**: この画面を閉じると Secret Access Key は二度と表示されません。必ず保存してから「完了」をクリックしてください。

---

## 3. AWS CLI インストール

### 3.1 OS 別インストール方法

#### Ubuntu/Debian (推奨)

```bash
# パッケージ更新
sudo apt update

# 必要なツールインストール
sudo apt install -y curl unzip

# AWS CLI v2 ダウンロード・インストール
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 確認
aws --version
```

#### macOS

```bash
# Homebrew使用
brew install awscli

# または直接ダウンロード
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

#### Windows

1. [AWS CLI Windows インストーラー](https://awscli.amazonaws.com/AWSCLIV2.msi) をダウンロード
2. インストーラーを実行
3. コマンドプロンプトまたは PowerShell で確認: `aws --version`

### 3.2 インストール確認

```bash
aws --version
```

出力例:

```
aws-cli/2.15.0 Python/3.11.6 Linux/6.2.0 exe/x86_64.ubuntu.22
```

---

## 4. AWS CLI 設定

### 4.1 基本設定

```bash
aws configure
```

以下の情報を入力：

```
AWS Access Key ID [None]: AKIA...（作成したIAMユーザーのAccess Key）
AWS Secret Access Key [None]: wJalrXUtn...（Secret Access Key）
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

#### リージョンについて

- `ap-northeast-1`: 東京リージョン（推奨、日本からのレイテンシが最小）
- `us-east-1`: バージニア北部（一部サービスが安価）

### 4.2 設定確認

```bash
aws sts get-caller-identity
```

成功時の出力例:

```json
{
  "UserId": "AIDACKCEVSQ6C2EXAMPLE",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/rss-notifier-deploy"
}
```

### 4.3 プロファイル設定（複数アカウント使用時）

複数の AWS アカウントを使用する場合：

```bash
# 専用プロファイル作成
aws configure --profile rss-notifier

# 使用時にプロファイル指定
export AWS_PROFILE=rss-notifier
```

---

## 5. 必要な AWS サービス

本プロジェクトで使用する AWS サービスの概要：

### 5.1 主要サービス

| サービス           | 用途                | 料金目安（月額） |
| ------------------ | ------------------- | ---------------- |
| **Lambda**         | RSS 処理・LINE 通知 | 無料枠内         |
| **S3**             | 設定・履歴保存      | 数円             |
| **API Gateway**    | Webhook 受信        | 無料枠内         |
| **EventBridge**    | スケジュール実行    | 無料枠内         |
| **CloudFormation** | インフラ管理        | 無料             |
| **CloudWatch**     | ログ・監視          | 無料枠内         |

### 5.2 サービス有効化確認

以下コマンドで各サービスにアクセスできることを確認：

```bash
# Lambda
aws lambda list-functions --region ap-northeast-1

# S3
aws s3 ls

# CloudFormation
aws cloudformation list-stacks --region ap-northeast-1
```

エラーが出ない場合は正常に設定されています。

---

## 6. 料金について

### 6.1 無料利用枠

新規 AWS アカウントでは 12 ヶ月間の無料利用枠があります：

| サービス    | 無料枠                                |
| ----------- | ------------------------------------- |
| Lambda      | 100 万リクエスト/月、400,000 GB 秒/月 |
| S3          | 5GB ストレージ、20,000 GET、2,000 PUT |
| API Gateway | 100 万回の API 呼び出し/月            |
| EventBridge | 無料（カスタムバス使用時のみ課金）    |

### 6.2 想定料金（無料枠超過後）

一般的な個人利用での月額料金：

```
Lambda（1日1回実行）: ¥0
S3（設定ファイル保存）: ¥1-5
API Gateway（LINE Webhook）: ¥1-10
CloudWatch（ログ保存）: ¥5-20

合計: ¥10-50/月
```

### 6.3 コスト監視設定

#### 予算アラート設定

1. AWS Billing and Cost Management コンソールにアクセス
2. 「予算」から「予算を作成」
3. 月額 ¥100 でアラート設定（推奨）

#### 使用量アラート

主要サービスの使用量監視を設定することを推奨

---

## 7. トラブルシューティング

### 7.1 よくある問題

#### AWS CLI インストールエラー

```bash
# 権限エラーの場合
sudo /usr/local/bin/pip3 install --upgrade awscli

# パス問題の場合
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc
```

#### 認証エラー

```bash
# 設定確認
aws configure list

# 新しいプロファイル作成
aws configure --profile new-profile

# 認証情報確認
aws sts get-caller-identity
```

#### リージョンエラー

```bash
# リージョン確認
aws configure get region

# リージョン変更
aws configure set region ap-northeast-1
```

### 7.2 権限エラーの解決

#### IAM ポリシー不足

1. IAM コンソールで該当ユーザーにアクセス
2. 必要なポリシーが添付されているか確認
3. 不足している場合は追加

#### サービス制限

一部リージョンで利用できないサービスがある場合は、`us-east-1`（バージニア北部）を試してください。

### 7.3 設定確認チェックリスト

```
□ AWS アカウント作成完了
□ IAM ユーザー作成完了
□ Access Key・Secret Key 取得・保存完了
□ AWS CLI インストール完了
□ AWS CLI 設定完了（aws configure）
□ 認証確認完了（aws sts get-caller-identity）
□ 必要なサービスアクセス確認完了
□ コスト監視設定完了（推奨）
```

---

## 次のステップ

AWS 設定が完了したら、[デプロイガイド](03_deployment.md) に進んでください。

---

## 参考リンク

- [AWS 無料利用枠](https://aws.amazon.com/jp/free/)
- [AWS CLI ユーザーガイド](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/)
- [IAM ユーザーガイド](https://docs.aws.amazon.com/ja_jp/IAM/latest/UserGuide/)
- [AWS 料金体系](https://aws.amazon.com/jp/pricing/)
