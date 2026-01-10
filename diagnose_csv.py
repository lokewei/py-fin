#!/usr/bin/env python3
"""诊断CSV文件中的格式问题"""

import csv
from pathlib import Path


def diagnose_csv_file(filepath, expected_fields=None):
    """诊断CSV文件中的格式问题

    Args:
        filepath: CSV文件路径
        expected_fields: 期望的字段数（如果为None，使用第一行的字段数）

    Returns:
        dict: 包含诊断信息的字典
    """
    issues = []
    line_count = 0
    raw_lines = []

    # 先读取原始行内容
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        raw_lines = f.readlines()

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)

        # 读取表头
        try:
            header = next(reader)
            line_count += 1
            if expected_fields is None:
                expected_fields = len(header)

            print(f"\n文件: {filepath}")
            print(f"表头字段数: {len(header)}")
            print(f"表头: {', '.join(header[:5])}{'...' if len(header) > 5 else ''}")

        except StopIteration:
            return {"error": "文件为空"}

        # 检查每一行
        for row in reader:
            line_count += 1
            if len(row) != expected_fields:
                # 获取原始行内容
                raw_line = raw_lines[line_count - 1].strip() if line_count <= len(raw_lines) else ""
                issues.append({
                    'line': line_count,
                    'expected': expected_fields,
                    'actual': len(row),
                    'raw_content': raw_line[:150] + '...' if len(raw_line) > 150 else raw_line
                })

    return {
        'total_lines': line_count,
        'issues': issues,
        'expected_fields': expected_fields
    }


def diagnose_all_data_files(date='2026-01-09', data_dir='data'):
    """诊断所有数据文件"""

    file_types = ['data', 'redeem', 'adjust', 'put']

    print("=" * 60)
    print("CSV文件格式诊断报告")
    print("=" * 60)

    for file_type in file_types:
        filepath = f'{data_dir}/jisilu_cb_{file_type}_{date}.csv'

        if not Path(filepath).exists():
            print(f"\n⚠ 文件不存在: {filepath}")
            continue

        result = diagnose_csv_file(filepath)

        if 'error' in result:
            print(f"✗ 错误: {result['error']}")
            continue

        print(f"总行数: {result['total_lines']}")

        if result['issues']:
            print(f"⚠ 发现 {len(result['issues'])} 个格式问题:")
            for issue in result['issues']:
                print(f"  行 {issue['line']}: 期望{issue['expected']}个字段, 实际{issue['actual']}个")
                print(f"    原始内容: {issue['raw_content']}")
                print()
        else:
            print("✓ 无格式问题")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    diagnose_all_data_files()
