#!/usr/bin/env python3
"""测试条款解析功能"""

import pandas as pd

from data_loader import load_cb_data, merge_cb_data, parse_clause

# 加载数据
print("加载数据...")
data = load_cb_data(date="2026-01-09")

# 测试条款解析
print("\n=== 强赎条款解析示例 ===")
for idx, row in data["redeem"].head(3).iterrows():
    parsed = parse_clause(row["强赎条款"], "redeem")
    print(f"\n转债: {row['转债名称']}")
    print(f"原文: {parsed.get('原文', '')[:80]}...")
    print(
        f"解析结果: 连续{parsed.get('连续天数', '?')}天中至少{parsed.get('满足天数', '?')}天, "
        f"{parsed.get('比较方向', '?')}转股价的{parsed.get('触发比例', '?')}%"
    )

print("\n=== 下修条款解析示例 ===")
for idx, row in data["adjust"].head(3).iterrows():
    parsed = parse_clause(row["下修条款"], "adjust")
    print(f"\n转债: {row['转债名称']}")
    print(f"原文: {parsed.get('原文', '')[:80]}...")
    print(
        f"解析结果: 连续{parsed.get('连续天数', '?')}天中至少{parsed.get('满足天数', '?')}天, "
        f"{parsed.get('比较方向', '?')}转股价的{parsed.get('触发比例', '?')}%"
    )

print("\n=== 回售条款解析示例 ===")
for idx, row in data["put"].head(3).iterrows():
    parsed = parse_clause(row["回售条款"], "put")
    print(f"\n转债: {row['转债名称']}")
    print(f"原文: {parsed.get('原文', '')[:80]}...")
    print(
        f"解析结果: {parsed.get('时间限制', '无时间限制')}, "
        f"连续{parsed.get('连续天数', '?')}天, "
        f"{parsed.get('比较方向', '?')}转股价的{parsed.get('触发比例', '?')}%"
    )

# 合并数据
print("\n\n=== 合并数据 ===")
df = merge_cb_data(data)
print(f"总共 {len(df)} 条可转债数据")

# 转换数值类型（处理可能的字符串格式）
df["正股价"] = pd.to_numeric(df["正股价"], errors="coerce")
df["强赎触发价"] = pd.to_numeric(df["强赎触发价"], errors="coerce")
df["下修触发价"] = pd.to_numeric(df["下修触发价"], errors="coerce")
df["回售触发价"] = pd.to_numeric(df["回售触发价"], errors="coerce")

# 计算真正满足条件的转债数量
# 强赎：正股价 >= 强赎触发价
redeem_count = df[
    df["强赎触发价"].notna() & (df["正股价"] >= df["强赎触发价"])
].shape[0]

# 下修：正股价 <= 下修触发价
adjust_count = df[
    df["下修触发价"].notna() & (df["正股价"] <= df["下修触发价"])
].shape[0]

# 回售：正股价 <= 回售触发价
put_count = df[
    df["回售触发价"].notna() & (df["正股价"] <= df["回售触发价"])
].shape[0]

print(f"满足强赎价格条件: {redeem_count} 条 (正股价 >= 强赎触发价)")
print(f"满足下修价格条件: {adjust_count} 条 (正股价 <= 下修触发价)")
print(f"满足回售价格条件: {put_count} 条 (正股价 <= 回售触发价)")

# 显示一个完整示例
print("\n=== 完整数据示例（博23转债）===")
sample = df[df["转债名称"] == "博23转债"].iloc[0]
print(f"代码: {sample['代码']}")
print(f"现价: {sample['现价']}")
print(f"转股价值: {sample['转股价值']}")
print(f"转股溢价率: {sample['转股溢价率']}")
if pd.notna(sample.get("强赎条款_解析")):
    print(f"强赎条款: {sample['强赎条款_解析']}")
