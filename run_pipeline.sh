#!/bin/bash
# run_pipeline.sh
# Step 1 (データ格納) が完了している状態で Step 2〜6 を自動実行する。
#
# 使い方:
#   bash run_pipeline.sh <データ名>
#   例: bash run_pipeline.sh 0629_141401

set -euo pipefail

# ---- パス設定 ------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMENTARY_UTILS_DIR="${SCRIPT_DIR}"
SIMLINGO_DIR="${COMMENTARY_UTILS_DIR}/.."
HIERARCHY="noScenarios/routes/Town01/Rep0_0_route_0"

# ---- 引数チェック --------------------------------------------------------
if [ $# -ne 1 ]; then
    echo "使い方: $0 <データ名>"
    echo "  例: $0 0629_141401"
    exit 1
fi

DATA_NAME="$1"
FIX_NAME="${DATA_NAME}_fix"
DATA_DIR="${COMMENTARY_UTILS_DIR}/src/datas/${DATA_NAME}"
FIX_DIR="${COMMENTARY_UTILS_DIR}/src/datas/${FIX_NAME}"
COMMENTARY_DIR="${FIX_DIR}/data/simlingo/${HIERARCHY}/simlingo/${HIERARCHY}/commentary"

# ---- 入力確認 ------------------------------------------------------------
if [ ! -d "${DATA_DIR}" ]; then
    echo "[ERROR] データディレクトリが存在しません: ${DATA_DIR}"
    echo "  Step 1 (データ格納) を先に実施してください。"
    exit 1
fi

echo "=========================================="
echo " commentary_utils パイプライン開始"
echo " データ名: ${DATA_NAME}"
echo "=========================================="

# ---- Step 2: JSON と画像の同期 -------------------------------------------
echo ""
echo "[Step 2] JSON と画像の同期"
echo "------------------------------------------"
cd "${COMMENTARY_UTILS_DIR}"
python src/sync_json_image.py "src/datas/${DATA_NAME}/"

# ---- Step 3: simlingo 構造へ変換 -----------------------------------------
echo ""
echo "[Step 3] simlingo 構造へ変換"
echo "------------------------------------------"
python src/convert_to_simlingo_structure.py "src/datas/${DATA_NAME}"

# ---- Step 4: コメンタリー生成 --------------------------------------------
echo ""
echo "[Step 4] コメンタリー生成"
echo "------------------------------------------"
cd "${SIMLINGO_DIR}"
PYTHONPATH="${SIMLINGO_DIR}" \
python dataset_generation/language_labels/commentary/carla_commentary_generator_main.py \
    --data-directory "${FIX_DIR}" \
    --output-directory "commentary_utils/src/datas/${FIX_NAME}/data/simlingo/${HIERARCHY}" \
    --path-keyframes /dev/null \
    --no-scenario

# ---- Step 5: コメンタリーファイルの解凍 ----------------------------------
echo ""
echo "[Step 5] コメンタリーファイルの解凍"
echo "------------------------------------------"
cd "${COMMENTARY_UTILS_DIR}"
python src/ungz.py "${COMMENTARY_DIR}"

# ---- Step 6: コメンタリーの集計・確認 ------------------------------------
echo ""
echo "[Step 6] コメンタリーの集計・確認"
echo "------------------------------------------"
python src/commentary.py "${COMMENTARY_DIR}/json"

echo ""
echo "=========================================="
echo " 完了!"
echo " 出力先: ${FIX_DIR}"
echo "=========================================="
