import pandas as pd
import re
from pathlib import Path
import warnings
from typing import Any, Dict, Literal, Optional


def get_latest_data_file(data_type: str = 'data', data_dir: str = 'data') -> Path:
    """获取最新的数据文件"""
    pattern = f'jisilu_cb_{data_type}_*.csv'
    files = list(Path(data_dir).glob(pattern))
    if not files:
        raise FileNotFoundError(f"未找到匹配 {pattern} 的文件")
    return max(files, key=lambda x: x.stat().st_mtime)


def load_cb_data(date: Optional[str] = None, data_dir: str = 'data') -> Dict[str, pd.DataFrame]:
    """加载可转债数据，支持指定日期或自动获取最新"""
    if date is None:
        # 自动获取最新文件
        files = {
            'data': get_latest_data_file('data', data_dir),
            'redeem': get_latest_data_file('redeem', data_dir),
            'adjust': get_latest_data_file('adjust', data_dir),
            'put': get_latest_data_file('put', data_dir)
        }
    else:
        # 使用指定日期
        files = {
            'data': f'{data_dir}/jisilu_cb_data_{date}.csv',
            'redeem': f'{data_dir}/jisilu_cb_redeem_{date}.csv',
            'adjust': f'{data_dir}/jisilu_cb_adjust_{date}.csv',
            'put': f'{data_dir}/jisilu_cb_put_{date}.csv'
        }

    result = {}
    for key, filepath in files.items():
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig', on_bad_lines='warn')
            result[key] = df
            print(f"✓ 加载 {key} 表: {len(df)} 行")
        except Exception as e:
            warnings.warn(f"加载 {filepath} 时出错: {e}")
            raise

    return result


def parse_clause(
    clause_text: Any,
    clause_type: Literal['redeem', 'adjust', 'put']
) -> Dict[str, Any]:
    """解析条款文本，提取关键信息

    Args:
        clause_text: 条款文本
        clause_type: 条款类型 ('redeem', 'adjust', 'put')

    Returns:
        dict: 归一化的条款信息
    """
    if pd.isna(clause_text):
        return {}

    result = {'原文': clause_text}

    # 提取连续天数（支持中文和阿拉伯数字，支持空格）
    match = re.search(r'(?:连续|任意连续|任何连续)\s*(\d+|三十|二十|十五)\s*个?交易日', clause_text)
    if match:
        num_map = {'三十': 30, '二十': 20, '十五': 15}
        num_str = match.group(1)
        if num_str in num_map:
            result['连续天数'] = num_map[num_str]
        elif num_str.isdigit():
            result['连续天数'] = int(num_str)

    # 提取满足天数（支持中文和阿拉伯数字，支持空格）
    match = re.search(r'至少(?:有)?\s*(\d+|三十|二十|十五|十)\s*个?交易日', clause_text)
    if match:
        num_map = {'三十': 30, '二十': 20, '十五': 15, '十': 10}
        num_str = match.group(1)
        if num_str in num_map:
            result['满足天数'] = num_map[num_str]
        elif num_str.isdigit():
            result['满足天数'] = int(num_str)

    # 提取触发比例（如"130%"、"80%"、"70%"）
    match = re.search(r'(\d+)%', clause_text)
    if match:
        result['触发比例'] = int(match.group(1))

    # 提取价格比较方向
    if '不低于' in clause_text or '高于' in clause_text:
        result['比较方向'] = '高于'
    elif '低于' in clause_text:
        result['比较方向'] = '低于'

    # 特殊条件提取
    if clause_type == 'put':
        if '最后' in clause_text:
            match = re.search(r'最后([一二两三四五六七八九十]+)(?:个)?(?:计息)?年度', clause_text)
            if match:
                result['时间限制'] = match.group(0)

    return result


def merge_cb_data(data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """合并四个表并归一化条款信息"""
    df_main = data_dict['data']
    df_redeem = data_dict['redeem']
    df_adjust = data_dict['adjust']
    df_put = data_dict['put']

    # 解析条款
    df_redeem['强赎条款_解析'] = df_redeem['强赎条款'].apply(
        lambda x: parse_clause(x, 'redeem')
    )
    df_adjust['下修条款_解析'] = df_adjust['下修条款'].apply(
        lambda x: parse_clause(x, 'adjust')
    )
    df_put['回售条款_解析'] = df_put['回售条款'].apply(
        lambda x: parse_clause(x, 'put')
    )

    # 合并表
    df_merged = df_main.merge(
        df_redeem[['转债代码', '强赎价', '强赎天计数', '强赎条款_解析']],
        left_on='代码', right_on='转债代码', how='left', suffixes=('', '_强赎')
    ).merge(
        df_adjust[['转债代码', '下修触发价', '下修天计数', '下修条款_解析']],
        left_on='代码', right_on='转债代码', how='left', suffixes=('', '_下修')
    ).merge(
        df_put[['转债代码', '回售价', '回售触及天数', '回售条款_解析']],
        left_on='代码', right_on='转债代码', how='left', suffixes=('', '_回售')
    )

    # 删除重复的转债代码列
    df_merged = df_merged.drop(columns=['转债代码_强赁', '转债代码_下修', '转债代码_回售'], errors='ignore')

    return df_merged


if __name__ == '__main__':
    # 示例：加载最新数据
    data = load_cb_data()
    df = merge_cb_data(data)
    print(f"加载了 {len(df)} 条可转债数据")

    # 示例：加载指定日期数据
    # data = load_cb_data(date='2026-01-09')
    # df = merge_cb_data(data)
