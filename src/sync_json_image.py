#!/usr/bin/env python3
"""
measurements/ と boxes/ の JSON に記録された ros_time を検証し、
マッチングした (JSON, 画像) ペアを時刻順に連番で
sync_measurements/ / sync_boxes/ / sync_images/ へコピーする。

JSON は 20Hz、画像は 10Hz など異なるレートを想定。
複数カメラがある場合は全カメラでマッチした JSON ステップの積集合を使用する。

Usage:
    cd carla_ros2_extractor
    python utils/sync_json_image.py carla_logs/20260616_152546
    python utils/sync_json_image.py carla_logs/20260616_152546 --dry-run
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def parse_image_timestamp(filename: str) -> float | None:
    """
    画像ファイル名からタイムスタンプを解析する。
    形式: {sec}_{nanosec_9digits}.{ext}  例: 29_027540155.png
    戻り値: float 秒 [s]、解析失敗時は None
    """
    stem = Path(filename).stem
    m = re.fullmatch(r'(\d+)_(\d{9})', stem)
    if not m:
        return None
    return int(m.group(1)) + int(m.group(2)) / 1_000_000_000


def ros_time_to_float(ros_time) -> float:
    """
    ros_time を浮動小数点秒に変換する。
    - 旧形式: {'sec': int, 'nanosec': int}
    - 新形式: {'ros_time_sec': int, 'ros_time_nanosec': int} (フラット)
    """
    if isinstance(ros_time, dict) and 'sec' in ros_time:
        return ros_time['sec'] + ros_time['nanosec'] / 1_000_000_000
    else:
        return ros_time['ros_time_sec'] + ros_time['ros_time_nanosec'] / 1_000_000_000


def match_images_to_json(
    img_list: list[tuple[float, Path]],
    json_t_list: list[float],
    json_t_to_stem: dict[float, str],
    max_dt: float,
) -> dict[str, tuple[float, Path]]:
    """
    各画像を最近傍の JSON に割り当てる (画像→JSON 方向)。
    戻り値: {json_stem: (dt, img_path)}
    複数の画像が同一 JSON に競合した場合は最も近い画像のみ採用。
    """
    best_for_json: dict[str, tuple[float, Path]] = {}

    for img_t, img_path in img_list:
        idx = bisect.bisect_left(json_t_list, img_t)
        best_stem, best_dt = None, float('inf')
        for i in (idx - 1, idx):
            if 0 <= i < len(json_t_list):
                dt = abs(json_t_list[i] - img_t)
                if dt < best_dt:
                    best_dt = dt
                    best_stem = json_t_to_stem[json_t_list[i]]

        if best_stem is None or best_dt > max_dt:
            continue

        if best_stem in best_for_json:
            prev_dt, _ = best_for_json[best_stem]
            if best_dt < prev_dt:
                best_for_json[best_stem] = (best_dt, img_path)
        else:
            best_for_json[best_stem] = (best_dt, img_path)

    return best_for_json


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='マッチングした JSON と画像を連番で sync_* ディレクトリへコピーする。')
    parser.add_argument('session_dir',
                        help='セッションディレクトリ (例: carla_logs/20260616_152546)')
    parser.add_argument('--max-dt', type=float, default=0.06,
                        help='マッチング許容時間差 [s] (デフォルト: 0.06)')
    parser.add_argument('--dry-run', action='store_true',
                        help='実際のコピーを行わず結果だけ表示する')
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    meas_dir   = session_dir / 'measurements'
    boxes_dir  = session_dir / 'boxes'
    images_dir = session_dir / 'images'

    for d in (meas_dir, boxes_dir, images_dir):
        if not d.exists():
            print(f'ERROR: ディレクトリが見つかりません: {d}', file=sys.stderr)
            sys.exit(1)

    # ----------------------------------------------------------------
    # 1. JSON 収集 & measurements/boxes の ros_time 整合性チェック
    # ----------------------------------------------------------------
    json_files = sorted(meas_dir.glob('*.json'))
    if not json_files:
        print('ERROR: measurements/ に JSON ファイルがありません', file=sys.stderr)
        sys.exit(1)

    print(f'JSON ファイル数: {len(json_files)}')
    print('ros_time 整合性チェック (measurements vs boxes) ...')

    mismatches   = 0
    json_t_list:    list[float]       = []
    json_t_to_stem: dict[float, str]  = {}
    stem_to_t:      dict[str, float]  = {}

    for jf in json_files:
        stem    = jf.stem
        meas_data = json.loads(jf.read_text())
        meas_rt = meas_data.get('ros_time') or meas_data

        boxes_jf = boxes_dir / jf.name
        t = ros_time_to_float(meas_rt)
        if boxes_jf.exists():
            boxes_data = json.loads(boxes_jf.read_text())
            boxes_rt = boxes_data.get('ros_time') or boxes_data
            boxes_t = ros_time_to_float(boxes_rt)
            if t != boxes_t:
                print(f'  MISMATCH {stem}.json: meas={t}  boxes={boxes_t}')
                mismatches += 1
        else:
            print(f'  WARNING: boxes/{jf.name} が存在しません')


        json_t_list.append(t)
        json_t_to_stem[t] = stem
        stem_to_t[stem]   = t

    if mismatches == 0:
        print('  -> OK: 全 JSON で measurements と boxes の ros_time が一致\n')
    else:
        print(f'  -> {mismatches} 件の不一致が見つかりました\n')

    # ----------------------------------------------------------------
    # 2. 各画像サブディレクトリでマッチング
    # ----------------------------------------------------------------
    image_subdirs = sorted(p for p in images_dir.iterdir() if p.is_dir())
    if not image_subdirs:
        print('ERROR: images/ にサブディレクトリがありません', file=sys.stderr)
        sys.exit(1)

    # subdir_name -> {json_stem: (dt, img_path)}
    all_matches: dict[str, dict[str, tuple[float, Path]]] = {}

    for subdir in image_subdirs:
        img_list: list[tuple[float, Path]] = []
        unparseable: list[str] = []
        for img in sorted(subdir.iterdir()):
            if not img.is_file():
                continue
            t = parse_image_timestamp(img.name)
            if t is not None:
                img_list.append((t, img))
            else:
                unparseable.append(img.name)

        if unparseable:
            print(f'WARNING [{subdir.name}]: タイムスタンプ解析不可: {unparseable}')
        if not img_list:
            print(f'WARNING [{subdir.name}]: 解析可能な画像なし — スキップ')
            continue

        img_list.sort(key=lambda x: x[0])
        matches = match_images_to_json(
            img_list, json_t_list, json_t_to_stem, args.max_dt)
        all_matches[subdir.name] = matches

        unmatched = len(img_list) - len(matches)
        print(f'[{subdir.name}] 画像数={len(img_list)}'
              f'  マッチ={len(matches)}  未マッチ={unmatched}')

    if not all_matches:
        print('ERROR: マッチングできた画像がありません', file=sys.stderr)
        sys.exit(1)

    # ----------------------------------------------------------------
    # 3. 有効な JSON stem を決定
    #    複数カメラがある場合は全カメラでマッチした stem の積集合を使用
    # ----------------------------------------------------------------
    matched_stem_sets = [set(m.keys()) for m in all_matches.values()]
    valid_stems: set[str] = matched_stem_sets[0]
    for s in matched_stem_sets[1:]:
        valid_stems &= s

    if len(matched_stem_sets) > 1:
        total = max(len(s) for s in matched_stem_sets)
        print(f'\nカメラ間の積集合: {len(valid_stems)}/{total} ステップ')

    # 時刻順 (昇順) にソートして連番を付与
    ordered_stems = sorted(valid_stems, key=lambda s: stem_to_t[s])
    print(f'出力ステップ数: {len(ordered_stems)}\n')

    # ----------------------------------------------------------------
    # 4. sync_* ディレクトリへコピー
    # ----------------------------------------------------------------
    sync_meas_dir  = session_dir / 'sync_measurements'
    sync_boxes_dir = session_dir / 'sync_boxes'
    sync_imgs_dir  = session_dir / 'sync_images'

    if not args.dry_run:
        sync_meas_dir.mkdir(exist_ok=True)
        sync_boxes_dir.mkdir(exist_ok=True)

    for new_idx, old_stem in enumerate(ordered_stems):
        new_name_json = f'{new_idx:06d}.json'

        src_meas  = meas_dir  / f'{old_stem}.json'
        dst_meas  = sync_meas_dir  / new_name_json
        src_boxes = boxes_dir / f'{old_stem}.json'
        dst_boxes = sync_boxes_dir / new_name_json

        img_info_parts = []
        for subdir_name, matches in all_matches.items():
            if old_stem not in matches:
                continue
            _, img_path = matches[old_stem]
            ext = img_path.suffix
            dst_img_dir = sync_imgs_dir / subdir_name
            dst_img = dst_img_dir / f'{new_idx:06d}{ext}'
            img_info_parts.append(
                f'{subdir_name}/{img_path.name} -> {new_idx:06d}{ext}')

            if not args.dry_run:
                dst_img_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img_path, dst_img)

        if args.dry_run:
            img_str = '  '.join(img_info_parts)
            print(f'[DRY-RUN] {new_name_json}'
                  f'  <- meas:{old_stem}.json  boxes:{old_stem}.json'
                  f'  {img_str}')
        else:
            shutil.copy2(src_meas,  dst_meas)
            shutil.copy2(src_boxes, dst_boxes)

    if args.dry_run:
        print(f'\n[DRY-RUN] 出力先 (予定):')
    else:
        print(f'コピー完了: {len(ordered_stems)} ステップ\n出力先:')

    print(f'  {sync_meas_dir}')
    print(f'  {sync_boxes_dir}')
    for subdir_name in all_matches:
        print(f'  {sync_imgs_dir / subdir_name}')

    print('\n完了')


if __name__ == '__main__':
    main()
