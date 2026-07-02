# commentary_utils

## 動作手順

以下の手順は `MMDD_HHMMSS` 形式のデータディレクトリを例に説明します。
ここでは `0629_141401` を例として使用します。

### 前提

- 作業ディレクトリは `/home/82597AD240002/ws/simlingo/commentary_utils`
- simlingo リポジトリは `/home/82597AD240002/ws/simlingo` に配置されている

---

## 一括実行 (Step 2〜6 を自動化)

Step 1 (データ格納) が完了していれば、以下の1コマンドで Step 2〜6 を自動実行できます。

```bash
# commentary_utils ディレクトリで実行
bash run_pipeline.sh 0629_141401
```

> `0629_141401` の部分を処理したいデータ名 (`MMDD_HHMMSS` 形式) に置き換えてください。

---

### Step 1: データファイルの格納

収集した生データを以下の構造で `src/datas/MMDD_HHMMSS/` 以下に配置します。

```
src/datas/
└── 0629_141401/            # MMDD_HHMMSS 形式で命名
    ├── boxes/              # バウンディングボックス JSON ファイル群
    ├── images/front_center # カメラ画像ファイル群()
    └── measurements/       # 計測データ JSON ファイル群
```

### Step 2: JSON と画像の同期

```bash
python src/sync_json_image.py src/datas/0629_141401/
```

### Step 3: simlingo 構造へ変換

```bash
python src/convert_to_simlingo_structure.py src/datas/0629_141401
```

変換後、`src/datas/0629_141401_fix/` ディレクトリが生成されます。

### Step 4: コメンタリー生成

simlingo リポジトリ直下に移動して実行します。

```bash
cd ..

PYTHONPATH=/home/82597AD240002/ws/simlingo \
python dataset_generation/language_labels/commentary/carla_commentary_generator_main.py \
  --data-directory /home/82597AD240002/ws/simlingo/commentary_utils/src/datas/0629_141401_fix \
  --output-directory commentary_utils/src/datas/0629_141401_fix/data/simlingo/noScenarios/routes/Town01/Rep0_0_route_0 \
  --path-keyframes /dev/null \
  --no-scenario
```

### Step 5: コメンタリーファイルの解凍

commentary_utils ディレクトリに戻り、生成された `.gz` ファイルを展開します。

```bash
cd commentary_utils

python src/ungz.py \
  /home/82597AD240002/ws/simlingo/commentary_utils/src/datas/0629_141401_fix/data/simlingo/noScenarios/routes/Town01/Rep0_0_route_0/simlingo/noScenarios/routes/Town01/Rep0_0_route_0/commentary
```

### Step 6: コメンタリーの集計・確認

```bash
python src/commentary.py \
  /home/82597AD240002/ws/simlingo/commentary_utils/src/datas/0629_141401_fix/data/simlingo/noScenarios/routes/Town01/Rep0_0_route_0/simlingo/noScenarios/routes/Town01/Rep0_0_route_0/commentary/json
```

---

## ディレクトリ構成

```
commentary_utils/
├── run_pipeline.sh             # Step 2〜6 一括実行スクリプト
├── src/
│   ├── data/                   # 入力データ (git 管理外)
│   │   ├── MMDD_HHMMSS/
│   │   │   ├── boxes/
│   │   │   ├── images/
│   │   │   └── measurements/
│   │   └── MMDD_HHMMSS_fix/    # 変換後データ (git 管理外)
│   ├── sync_json_image.py
│   ├── convert_to_simlingo_structure.py
│   ├── ungz.py
│   └── commentary.py
└── commentary_test/
```

> `src/datas/` および `MMDD_HHMMSS_fix/` ディレクトリは `.gitignore` により Git 管理から除外されています。
