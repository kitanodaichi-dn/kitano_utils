"""
指定ディレクトリ内の JSON ファイルから commentary と commentary_template を
一つのテキストファイルにまとめて出力するスクリプト。

使い方:
  python src/commentary.py <directory>
  python src/commentary.py <directory> --output result.txt
  python src/commentary.py <directory> --recursive
"""

import argparse
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='JSON ファイルから commentary をまとめて出力')
    parser.add_argument('directory', type=str, help='JSONファイルが入っているディレクトリ')
    parser.add_argument('--output', type=str, default=None,
                        help='出力テキストファイルのパス (省略時: <directory>/commentary_all.txt)')
    parser.add_argument('--recursive', action='store_true',
                        help='サブディレクトリも再帰的に処理する')
    return parser.parse_args()


def main():
    args = parse_args()

    target_dir = Path(args.directory)
    if not target_dir.exists():
        raise FileNotFoundError(f'ディレクトリが存在しません: {target_dir}')

    pattern = '**/*.json' if args.recursive else '*.json'
    json_files = sorted(target_dir.glob(pattern))

    if not json_files:
        print(f'対象ファイルが見つかりませんでした: {target_dir}/{pattern}')
        return

    output_path = Path(args.output) if args.output else target_dir / 'commentary_all.txt'

    print(f'{len(json_files)} 件のJSONファイルを処理中 ...')

    lines = []
    errors = 0
    for json_path in json_files:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            commentary = data['commentary']
            template   = data['commentary_template']
            lines.append(f'[{json_path.name}]')
            lines.append(f'commentary          : {commentary}')
            lines.append(f'commentary_template : {template}')
            lines.append('')
        except KeyError as e:
            print(f'  WARNING: {json_path.name} にキー {e} がありません')
            errors += 1
        except Exception as e:
            print(f'  ERROR: {json_path.name}: {e}')
            errors += 1

    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'完了: {len(json_files) - errors} 件を出力 -> {output_path}')
    if errors:
        print(f'  スキップ: {errors} 件')


if __name__ == '__main__':
    main()
