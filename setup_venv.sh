#!/usr/bin/env bash
# conda env create -f environment.yaml の代替: venv による環境構築スクリプト

set -e

VENV_DIR="${1:-/home/82597AD240002/venv/python3.8/simlingo}"

echo "==> pip をアップグレード"
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

echo "==> パッケージをインストール"
"${VENV_DIR}/bin/pip" install -r "$(dirname "$0")/requirements.txt"

echo ""
echo "==> 完了!"
echo "    有効化: source ${VENV_DIR}/bin/activate"
