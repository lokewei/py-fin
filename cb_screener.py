#!/usr/bin/env python3
"""可转债筛选和评分系统"""

import pandas as pd
from data_loader import load_cb_data, merge_cb_data


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """计算额外的评估指标"""
    df = df.copy()

    # 转换数值类型
    numeric_cols = ['现价', '正股价', '转股价值', '纯债价值', '剩余规模(亿元)',
                    '正股PB', '强赎触发价', '下修触发价', '回售触发价']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 转股溢价率转换为数值（去除%号）
    if '转股溢价率' in df.columns:
        df['转股溢价率_数值'] = df['转股溢价率'].astype(str).str.rstrip('%').astype(float)

    # 剩余年限转换为数值（处理"年"和"天"两种单位）
    if '剩余年限' in df.columns:
        def parse_remaining_time(val):
            val_str = str(val)
            if '年' in val_str:
                return float(val_str.rstrip('年'))
            elif '天' in val_str:
                return float(val_str.rstrip('天')) / 365  # 转换为年
            elif val_str == '-' or val_str == 'nan':
                return 0.0
            else:
                try:
                    return float(val_str)
                except ValueError:
                    return 0.0

        df['剩余年限_数值'] = df['剩余年限'].apply(parse_remaining_time)

    # 计算期权价值
    df['期权价值'] = df['现价'] - df['纯债价值']

    # 计算距离保本位置的距离（现价 - 纯债价值）
    df['距离保本'] = df['现价'] - df['纯债价值']

    # 计算正股价相对强赎触发价的比例
    df['正股价_强赎比'] = df['正股价'] / df['强赎触发价']

    # 计算正股价相对下修触发价的比例
    df['正股价_下修比'] = df['正股价'] / df['下修触发价']

    # 判断市值大小（小市值：<5亿，中市值：5-15亿，大市值：>15亿）
    df['市值类型'] = pd.cut(df['剩余规模(亿元)'],
                           bins=[0, 5, 15, float('inf')],
                           labels=['小市值', '中市值', '大市值'])

    # 判断是否临期（剩余年限<0.5年）
    df['是否临期'] = df['剩余年限_数值'] < 0.5

    # 判断是否双高（高价>130 且 高溢价>30%）
    df['是否双高'] = (df['现价'] > 130) & (df['转股溢价率_数值'] > 30)

    return df


def screen_avoid_bonds(df: pd.DataFrame) -> dict:
    """筛选需要回避的转债"""

    results = {}

    # 第一类：半年内到期且负收益的转债
    results['临期负收益'] = df[
        (df['剩余年限_数值'] < 0.5) &
        (df['到期税前收益'].astype(str).str.contains('-', na=False))
    ][['代码', '转债名称', '现价', '剩余年限', '到期税前收益', '期权价值']]

    # 第二类：超越强赎线但溢价明显的大市值高评级转债
    results['强赎线上大市值高溢价'] = df[
        (df['正股价_强赎比'] > 1.0) &  # 超越强赎线
        (df['转股溢价率_数值'] > 20) &  # 溢价明显
        (df['市值类型'] == '大市值') &
        (df['评级'].isin(['AAA', 'AA+', 'AA']))
    ][['代码', '转债名称', '现价', '转股溢价率', '剩余规模(亿元)', '评级', '正股价_强赎比']]

    # 第三类：一年内到期的双高小市值转债
    results['临期双高小市值'] = df[
        (df['剩余年限_数值'] < 1.0) &
        (df['是否双高']) &
        (df['市值类型'] == '小市值')
    ][['代码', '转债名称', '现价', '转股溢价率', '剩余年限', '剩余规模(亿元)']]

    # 第五类：质地不佳的转债（低评级、高PB、低纯债价值）
    results['质地不佳'] = df[
        (df['评级'].isin(['A+', 'A', 'A-', 'BBB+', 'BBB'])) |
        (df['正股PB'] > 5) |
        (df['纯债价值'] < 95)
    ][['代码', '转债名称', '现价', '评级', '正股PB', '纯债价值']]

    return results


def screen_focus_bonds(df: pd.DataFrame) -> dict:
    """筛选值得关注的转债"""

    results = {}

    # 第一类：小市值高溢价距离保本位置不远
    results['小市值高溢价近保本'] = df[
        (df['市值类型'] == '小市值') &
        (df['转股溢价率_数值'] > 30) &  # 高溢价
        (df['距离保本'] < 20) &  # 距离保本不远
        (df['距离保本'] > 0)  # 但还没破面
    ][['代码', '转债名称', '现价', '转股溢价率', '剩余规模(亿元)', '距离保本', '纯债价值']]

    # 第二类：低期权价值、质地安全的临期债
    results['低期权临期债'] = df[
        (df['剩余年限_数值'] < 0.25) &  # 3个月内到期
        (df['期权价值'] < 5) &  # 低期权价值
        (df['评级'].isin(['AAA', 'AA+', 'AA'])) &  # 质地安全
        (df['现价'] < 105)  # 价格不高
    ][['代码', '转债名称', '现价', '剩余年限', '期权价值', '评级', '到期税前收益']]

    # 第四类：存续期在2年附近的转债（1.5-2.5年）
    results['两年期转债'] = df[
        (df['剩余年限_数值'] >= 1.5) &
        (df['剩余年限_数值'] <= 2.5) &
        (df['转股溢价率_数值'] < 50)  # 溢价不太离谱
    ][['代码', '转债名称', '现价', '转股溢价率', '剩余年限', '剩余规模(亿元)', '评级']]

    return results


def score_bonds(df: pd.DataFrame) -> pd.DataFrame:
    """对转债进行综合评分"""
    df = df.copy()
    df['综合得分'] = 0

    # 正面因素加分
    # 1. 低溢价加分（溢价率越低越好）
    df.loc[df['转股溢价率_数值'] < 10, '综合得分'] += 3
    df.loc[(df['转股溢价率_数值'] >= 10) & (df['转股溢价率_数值'] < 20), '综合得分'] += 2
    df.loc[(df['转股溢价率_数值'] >= 20) & (df['转股溢价率_数值'] < 30), '综合得分'] += 1

    # 2. 高评级加分
    df.loc[df['评级'] == 'AAA', '综合得分'] += 3
    df.loc[df['评级'].isin(['AA+', 'AA']), '综合得分'] += 2
    df.loc[df['评级'].isin(['AA-', 'A+']), '综合得分'] += 1

    # 3. 合理存续期加分（1.5-3年）
    df.loc[(df['剩余年限_数值'] >= 1.5) & (df['剩余年限_数值'] <= 3), '综合得分'] += 2

    # 4. 低正股PB加分（价值股）
    df.loc[df['正股PB'] < 2, '综合得分'] += 2
    df.loc[(df['正股PB'] >= 2) & (df['正股PB'] < 3), '综合得分'] += 1

    # 5. 接近下修线加分
    df.loc[(df['正股价_下修比'] > 0.8) & (df['正股价_下修比'] < 1.0), '综合得分'] += 2

    # 负面因素扣分
    # 1. 双高扣分
    df.loc[df['是否双高'], '综合得分'] -= 3

    # 2. 临期且负收益扣分
    df.loc[(df['是否临期']) & (df['到期税前收益'].astype(str).str.contains('-', na=False)), '综合得分'] -= 2

    # 3. 超越强赎线且高溢价扣分
    df.loc[(df['正股价_强赎比'] > 1.1) & (df['转股溢价率_数值'] > 20), '综合得分'] -= 2

    # 4. 低评级扣分
    df.loc[df['评级'].isin(['A', 'A-', 'BBB+', 'BBB']), '综合得分'] -= 2

    return df


def generate_report(df: pd.DataFrame):
    """生成筛选报告"""

    print("=" * 80)
    print("可转债筛选报告")
    print("=" * 80)

    # 计算指标
    df = calculate_metrics(df)

    # 回避的转债
    print("\n【需要回避的转债】\n")
    avoid = screen_avoid_bonds(df)

    for category, bonds in avoid.items():
        print(f"\n{category}: {len(bonds)} 条")
        if len(bonds) > 0:
            print(bonds.head(10).to_string(index=False))

    # 关注的转债
    print("\n\n【值得关注的转债】\n")
    focus = screen_focus_bonds(df)

    for category, bonds in focus.items():
        print(f"\n{category}: {len(bonds)} 条")
        if len(bonds) > 0:
            print(bonds.head(10).to_string(index=False))

    # 综合评分
    print("\n\n【综合评分 TOP 20】\n")
    df_scored = score_bonds(df)
    top_bonds = df_scored.nlargest(20, '综合得分')[
        ['代码', '转债名称', '现价', '转股溢价率', '剩余年限', '剩余规模(亿元)',
         '评级', '综合得分']
    ]
    print(top_bonds.to_string(index=False))

    print("\n" + "=" * 80)

    return df_scored


if __name__ == '__main__':
    # 加载数据
    data = load_cb_data(date='2026-01-09')
    df = merge_cb_data(data)

    # 生成报告
    df_scored = generate_report(df)

    # 保存结果
    df_scored.to_csv('data/cb_scored.csv', index=False, encoding='utf-8-sig')
    print("\n评分结果已保存到 data/cb_scored.csv")