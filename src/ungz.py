"""
指定ディレクトリ内の .json.gz ファイルをすべて .json に解凍するスクリプト。

使い方:
  python src/ungz.py <directory>
  python src/ungz.py <directory> --recursive   # サブディレクトリも対象
  python src/ungz.py <directory> --delete-gz   # 解凍後に .json.gz を削除
"""

import argparse
import gzip
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Decompress .json.gz files to .json')
    parser.add_argument('directory', type=str, help='解凍対象のディレクトリ')
    parser.add_argument('--recursive', action='store_true', help='サブディレクトリも再帰的に処理する')
    parser.add_argument('--delete-gz', action='store_true', help='解凍後に元の .json.gz を削除する')
    return parser.parse_args()


def main():
    args = parse_args()

    target_dir = Path(args.directory)
    if not target_dir.exists():
        raise FileNotFoundError(f'ディレクトリが存在しません: {target_dir}')

    pattern = '**/*.json.gz' if args.recursive else '*.json.gz'
    gz_files = sorted(target_dir.glob(pattern))

    if not gz_files:
        print(f'対象ファイルが見つかりませんでした: {target_dir}/{pattern}')
        return

    print(f'{len(gz_files)} 件の .json.gz を解凍中 ...')
    for gz_path in gz_files:
        # 出力先: gz_path の親ディレクトリに json/ フォルダを作成
        json_dir = gz_path.parent / 'json'
        json_dir.mkdir(exist_ok=True)
        json_path = json_dir / gz_path.stem  # .json.gz → json/{name}.json
        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if args.delete_gz:
            gz_path.unlink()

    print(f'完了: {len(gz_files)} ファイルを解凍{"・削除" if args.delete_gz else ""}')


if __name__ == '__main__':
    main()
