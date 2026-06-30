"""
指定したデータディレクトリを SimLingo / carla_commentary_generator 互換形式に変換する。

入力ディレクトリ構成:
  {src}/
    sync_images/front_center/*.png
    sync_boxes/*.json           (6桁連番)
    sync_measurements/*.json    (6桁連番)

出力ディレクトリ構成 (4-wildcard glob に合致):
  {src}_fix/
    data/simlingo/parking_lane/routes/Town01/Rep0_0_route_0/
      rgb/front_center/*.jpg          (PNG→JPG, 4桁連番)
      boxes/*.json.gz                 (4桁連番)
      measurements/*.json.gz          (4桁連番)
      results.json.gz                 (完璧スコアのダミー)

設計上の制約:
  - 4番目のディレクトリ名は正規表現 Rep*(\d+)_*(\d+)_route_*(\d+) に合致する必要がある
  - 先頭の parking_lane により get_scenario_name() 呼び出しをスキップ
  - ファイル名は4桁 (generator 内部のフレーム文字列置換が前提)
  - RGB は .jpg 形式が要求される

使い方:
  python convert_to_simlingo_structure.py src/datas/0626_105646
"""

import argparse
import gzip
import json
import shutil
from pathlib import Path
from PIL import Image

# carla_commentary_generator が期待する4階層
# --no-scenario フラグを使えば wildcard1 は parking_lane でなくても OK
# デフォルトを noScenarios/routes/Town01/Rep0_0_route_0 に変更
DEFAULT_HIERARCHY = 'noScenarios/routes/Town01/Rep0_0_route_0'

# carla_commentary_generator が求める完璧スコアの results 構造
DUMMY_RESULTS = {
    'infractions': {
        'collisions_layout': [],
        'collisions_pedestrian': [],
        'collisions_vehicle': [],
        'red_light': [],
        'stop_infraction': [],
        'outside_route_lanes': [],
        'route_dev': [],
        'route_timeout': [],
        'vehicle_blocked': [],
        'min_speed_infractions': [],
    },
    'scores': {
        'score_route': 100.0,
        'score_penalty': 1.0,
        'score_composed': 100.0,
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Convert dataset to SimLingo / carla_commentary_generator compatible structure')
    parser.add_argument('src', type=str,
                        help='変換元ディレクトリ (例: src/datas/0626_105646)')
    parser.add_argument('--hierarchy', type=str, default=DEFAULT_HIERARCHY,
                        help=f'data/simlingo/ 以下の4階層 (デフォルト: {DEFAULT_HIERARCHY})')
    return parser.parse_args()


def json_to_gz(src_json: Path, dst_gz: Path, extract_key: str = None) -> None:
    """JSON ファイルを読み込み .json.gz として保存する。
    extract_key が指定された場合、そのキーの値のみを保存する。
    """
    data = json.loads(src_json.read_bytes())
    if extract_key and isinstance(data, dict) and extract_key in data:
        data = data[extract_key]
    with gzip.open(dst_gz, 'wt', encoding='utf-8') as f:
        json.dump(data, f)


def png_to_jpg(src_png: Path, dst_jpg: Path) -> None:
    """PNG を JPG に変換する。"""
    with Image.open(src_png) as img:
        img.convert('RGB').save(dst_jpg, 'JPEG', quality=95)


def six_to_four(stem: str) -> str:
    """6桁連番のファイル名 stem を4桁連番に変換する。"""
    return str(int(stem)).zfill(4)


def main():
    args = parse_args()

    src_dir = Path(args.src).resolve()
    if not src_dir.exists():
        raise FileNotFoundError(f'指定されたディレクトリが存在しません: {src_dir}')

    route_name = src_dir.name
    # src_dir が .../src/datas/0626_105646 の場合、out_base を .../src/datas/0626_105646_fix にする
    out_base   = src_dir.parent / (route_name + '_fix')
    route_dir  = out_base / 'data' / 'simlingo' / args.hierarchy
    route_dir.mkdir(parents=True, exist_ok=True)

    # --- rgb (sync_images → rgb, PNG→JPG, 4桁リネーム) --------------------
    src_images = src_dir / 'sync_images'
    dst_rgb    = route_dir / 'rgb'
    if src_images.exists():
        print('[rgb] PNG→JPG 変換 + 4桁リネーム ...')
        dst_rgb.mkdir(parents=True, exist_ok=True)
        count = 0
        for cam_dir in sorted(src_images.iterdir()):
            if not cam_dir.is_dir():
                continue
            # generator は rgb/{frame}.jpg を期待（サブフォルダなし）
            # front_center のみを rgb/ 直下にフラット展開する
            for png in sorted(cam_dir.glob('*.png')):
                new_stem = six_to_four(png.stem)
                png_to_jpg(png, dst_rgb / f'{new_stem}.jpg')
                count += 1
        print(f'  完了: {count} ファイル → {dst_rgb}')
    else:
        print(f'[rgb] WARNING: {src_images} が存在しません')

    # --- boxes (sync_boxes → boxes, .json→.json.gz, 4桁リネーム) ----------
    src_boxes = src_dir / 'sync_boxes'
    dst_boxes = route_dir / 'boxes'
    if src_boxes.exists():
        dst_boxes.mkdir(parents=True, exist_ok=True)
        json_files = sorted(src_boxes.glob('*.json'))
        print(f'[boxes] {len(json_files)} ファイルを変換中 ...')
        for jf in json_files:
            new_stem = six_to_four(jf.stem)
            json_to_gz(jf, dst_boxes / f'{new_stem}.json.gz', extract_key='boxes')
        print(f'  完了: {dst_boxes}')
    else:
        print(f'[boxes] WARNING: {src_boxes} が存在しません')

    # --- measurements (sync_measurements → measurements, 4桁リネーム) ------
    src_meas = src_dir / 'sync_measurements'
    dst_meas = route_dir / 'measurements'
    if src_meas.exists():
        dst_meas.mkdir(parents=True, exist_ok=True)
        json_files = sorted(src_meas.glob('*.json'))
        print(f'[measurements] {len(json_files)} ファイルを変換中 ...')
        for jf in json_files:
            new_stem = six_to_four(jf.stem)
            data = json.loads(jf.read_bytes())
            # generator が要求するが収集データに存在しないキーをデフォルト値で補完
            data.setdefault('walker_close_id', None)
            with gzip.open(dst_meas / f'{new_stem}.json.gz', 'wt', encoding='utf-8') as f:
                json.dump(data, f)
        print(f'  完了: {dst_meas}')
    else:
        print(f'[measurements] WARNING: {src_meas} が存在しません')

    # --- results.json.gz (完璧スコアのダミー) --------------------------------
    results_path = route_dir / 'results.json.gz'
    with gzip.open(results_path, 'wt', encoding='utf-8') as f:
        json.dump(DUMMY_RESULTS, f)
    print(f'[results] ダミー results.json.gz を生成: {results_path}')

    print(f'\n出力先: {out_base}')
    print(f'ルートディレクトリ: {route_dir}')


if __name__ == '__main__':
    main()
