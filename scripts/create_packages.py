#!/usr/bin/env python3
"""
RSS LINE Notifier - デプロイパッケージ作成スクリプト
Lambda関数のZIPパッケージを作成するスクリプト（Python 3.12対応）
"""

import os
import sys
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PackageCreator:
    """Lambda パッケージ作成クラス"""

    def __init__(self, project_root: str):
        """初期化"""
        self.project_root = Path(project_root)
        self.lambda_functions_dir = self.project_root / "lambda_functions"
        self.output_dir = self.project_root

        # パッケージ情報
        self.packages = {
            'notifier': {
                'source_dir': self.lambda_functions_dir / 'notifier',
                'output_file': self.output_dir / 'notifier-deployment.zip',
                'dependencies': ['feedparser', 'requests', 'python-dateutil', 'jsonschema']
            },
            'webhook': {
                'source_dir': self.lambda_functions_dir / 'webhook',
                'output_file': self.output_dir / 'webhook-deployment.zip',
                'dependencies': ['requests', 'python-dateutil', 'jsonschema', 'cryptography']
            }
        }

    def create_all_packages(self) -> bool:
        """全パッケージ作成"""
        logger.info("Lambda デプロイパッケージ作成を開始します")

        success = True
        for package_name, package_info in self.packages.items():
            try:
                logger.info(f"パッケージ作成開始: {package_name}")
                self._create_single_package(package_name, package_info)
                logger.info(f"パッケージ作成完了: {package_name}")
            except Exception as e:
                logger.error(f"パッケージ作成失敗 {package_name}: {e}")
                success = False

        if success:
            logger.info("全パッケージの作成が正常に完了しました")
        else:
            logger.error("一部のパッケージ作成に失敗しました")

        return success

    def _create_single_package(self, package_name: str, package_info: dict) -> None:
        """単一パッケージ作成"""
        source_dir = package_info['source_dir']
        output_file = package_info['output_file']
        dependencies = package_info['dependencies']

        # 出力ファイルが既に存在する場合は削除
        if output_file.exists():
            output_file.unlink()
            logger.info(f"既存のパッケージファイルを削除: {output_file}")

        # 一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            package_dir = temp_path / package_name

            logger.info(f"一時ディレクトリ: {temp_path}")

            # 1. ソースコードコピー
            self._copy_source_code(source_dir, package_dir)

            # 2. 共通ライブラリコピー
            self._copy_common_libraries(package_dir)

            # 3. 依存関係インストール
            self._install_dependencies(package_dir, dependencies)

            # 4. ZIPパッケージ作成
            self._create_zip_package(package_dir, output_file)

        logger.info(f"パッケージファイルサイズ: {self._get_file_size_mb(output_file):.2f} MB")

    def _copy_source_code(self, source_dir: Path, target_dir: Path) -> None:
        """ソースコードコピー"""
        logger.info(f"ソースコードコピー: {source_dir} -> {target_dir}")

        target_dir.mkdir(parents=True, exist_ok=True)

        # Pythonファイルのみコピー
        for py_file in source_dir.glob("*.py"):
            shutil.copy2(py_file, target_dir)
            logger.debug(f"コピー: {py_file.name}")

        # requirements.txt は除外（後で処理）

    def _copy_common_libraries(self, target_dir: Path) -> None:
        """共通ライブラリコピー"""
        common_dir = self.lambda_functions_dir / 'common'
        logger.info(f"共通ライブラリコピー: {common_dir}")

        if not common_dir.exists():
            logger.warning("共通ライブラリディレクトリが存在しません")
            return

        # common ディレクトリ全体をコピー
        target_common_dir = target_dir / 'common'
        shutil.copytree(common_dir, target_common_dir)

        # __pycache__ 削除
        self._remove_pycache(target_common_dir)

    def _install_dependencies(self, target_dir: Path, dependencies: list) -> None:
        """依存関係インストール"""
        logger.info("依存関係インストール開始")

        # requirements.txt 作成
        requirements_content = "\n".join(dependencies)
        requirements_file = target_dir / "requirements.txt"

        with open(requirements_file, 'w') as f:
            f.write(requirements_content)

        logger.info(f"requirements.txt作成: {requirements_content}")

        # pip install 実行
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            '-r', str(requirements_file),
            '-t', str(target_dir),
            '--upgrade'
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=target_dir
            )
            logger.info("依存関係インストール成功")
            logger.debug(f"pip install output: {result.stdout}")

        except subprocess.CalledProcessError as e:
            logger.error(f"依存関係インストール失敗: {e}")
            logger.error(f"stderr: {e.stderr}")
            raise

        # 不要ファイル削除
        self._cleanup_installed_packages(target_dir)

    def _cleanup_installed_packages(self, target_dir: Path) -> None:
        """インストール済みパッケージのクリーンアップ"""
        logger.info("不要ファイルのクリーンアップ開始")

        cleanup_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/*.dist-info",
            "**/*.egg-info",
            "**/tests",
            "**/test",
            "**/docs",
            "**/examples",
            "**/*.so",  # バイナリファイル（必要に応じて）
        ]

        for pattern in cleanup_patterns:
            for path in target_dir.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    logger.debug(f"ディレクトリ削除: {path}")
                elif path.is_file():
                    path.unlink()
                    logger.debug(f"ファイル削除: {path}")

        # requirements.txt 削除
        requirements_file = target_dir / "requirements.txt"
        if requirements_file.exists():
            requirements_file.unlink()

    def _remove_pycache(self, directory: Path) -> None:
        """__pycache__ ディレクトリ削除"""
        for pycache in directory.rglob("__pycache__"):
            if pycache.is_dir():
                shutil.rmtree(pycache)
                logger.debug(f"__pycache__ 削除: {pycache}")

    def _create_zip_package(self, source_dir: Path, output_file: Path) -> None:
        """ZIPパッケージ作成"""
        logger.info(f"ZIPパッケージ作成: {output_file}")

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    # ソースディレクトリからの相対パス
                    arc_name = file_path.relative_to(source_dir)
                    zipf.write(file_path, arc_name)
                    logger.debug(f"ZIP追加: {arc_name}")

        logger.info(f"ZIPパッケージ作成完了: {output_file}")

    def _get_file_size_mb(self, file_path: Path) -> float:
        """ファイルサイズをMBで取得"""
        size_bytes = file_path.stat().st_size
        return size_bytes / (1024 * 1024)

    def validate_packages(self) -> bool:
        """パッケージ検証"""
        logger.info("パッケージ検証開始")

        all_valid = True

        for package_name, package_info in self.packages.items():
            output_file = package_info['output_file']

            if not output_file.exists():
                logger.error(f"パッケージファイルが存在しません: {output_file}")
                all_valid = False
                continue

            # ファイルサイズ確認
            size_mb = self._get_file_size_mb(output_file)
            if size_mb > 250:  # Lambda制限は250MB（解凍後）
                logger.warning(f"パッケージサイズが大きすぎます: {package_name} ({size_mb:.2f} MB)")

            # ZIP形式確認
            try:
                with zipfile.ZipFile(output_file, 'r') as zipf:
                    file_list = zipf.namelist()
                    logger.info(f"パッケージ {package_name} ファイル数: {len(file_list)}")

                    # lambda_function.py 存在確認
                    if 'lambda_function.py' not in file_list:
                        logger.error(f"lambda_function.py が見つかりません: {package_name}")
                        all_valid = False

            except zipfile.BadZipFile:
                logger.error(f"無効なZIPファイル: {output_file}")
                all_valid = False

        if all_valid:
            logger.info("全パッケージの検証が正常に完了しました")
        else:
            logger.error("パッケージ検証でエラーが発生しました")

        return all_valid


def main():
    """メイン実行"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    logger.info(f"プロジェクトルート: {project_root}")

    # パッケージ作成実行
    creator = PackageCreator(str(project_root))

    success = creator.create_all_packages()

    if success:
        # パッケージ検証
        success = creator.validate_packages()

    if success:
        logger.info("🎉 Lambda デプロイパッケージの作成が正常に完了しました！")
        return 0
    else:
        logger.error("💥 Lambda デプロイパッケージの作成に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())