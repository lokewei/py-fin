import numpy as np


def calculate_cb_value(
    S0, K, r, sigma, T, steps, pure_bond_value, call_price, put_price, redemption_price
):
    """
    S0: 正股当前价格
    K: 当前转股价
    r: 无风险利率 (例如 0.02 表示 2%)
    sigma: 正股年化波动率 (例如 0.25)
    T: 剩余年限 (例如 2.5)
    steps: 二叉树步数 (建议 500-1000)
    pure_bond_value: 纯债价值 (债底，从集思录获取)
    call_price: 强赎触发价 (通常是转股价的 130%)
    put_price: 回售触发价 (通常是转股价的 70%)
    redemption_price: 到期赎回价 (含最后一年利息，如 108)
    """

    # 1. 计算基础参数
    dt = T / steps  # 每一时刻的时间步长
    u = np.exp(sigma * np.sqrt(dt))  # 股价上升因子
    d = 1 / u  # 股价下降因子
    p = (np.exp(r * dt) - d) / (u - d)  # 风险中性概率
    df = np.exp(-r * dt)  # 单步折现因子

    # 2. 初始化末端节点的正股价格
    # 生成 T 时刻所有可能的股价
    st = S0 * d ** (np.arange(steps, -1, -1)) * u ** (np.arange(0, steps + 1, 1))

    # 3. 初始化末端节点的转债价值 (到期时点)
    # 到期时，投资者选择：max(转股价值, 赎回价)
    conversion_ratio = 100 / K  # 每 100 元面值可转股数
    values = np.maximum(st * conversion_ratio, redemption_price)

    # 4. 反向回溯计算
    # 从 T-1 层一层层往回算，直到第 0 层（现在）
    for i in range(steps - 1, -1, -1):
        # 计算基础期望价值 (保持不动的价值)
        values = (p * values[1:] + (1 - p) * values[:-1]) * df

        # 获取当前层的股价
        st = S0 * d ** (np.arange(i, -1, -1)) * u ** (np.arange(0, i + 1, 1))

        # 计算当前时刻的转股价值
        conv_val = st * conversion_ratio

        # --- 条款修正逻辑 ---
        for j in range(len(values)):
            # A. 债底保护：转债价值不低于纯债价值 (简化处理，实际应随时间变动)
            values[j] = max(values[j], pure_bond_value / (steps) * i)

            # B. 考虑转股：如果现在转股更划算，就选转股
            values[j] = max(values[j], conv_val[j])

            # C. 强赎条款：如果股价 > 强赎价，公司强制按赎回价买回
            # 此时投资者通常被迫转股，所以价值取 min(当前价值, max(赎回价, 转股价值))
            if st[j] >= call_price:
                values[j] = min(values[j], max(redemption_price, conv_val[j]))

            # D. 回售条款：如果股价 < 回售价，投资者把债卖给公司
            if st[j] <= put_price:
                values[j] = max(values[j], put_price)

    return values[0]


# --- 案例测试 ---
params = {
    "S0": 15.5,  # 当前股价
    "K": 14.2,  # 转股价
    "r": 0.025,  # 无风险利率
    "sigma": 0.30,  # 波动率 30%
    "T": 3.2,  # 剩余 3.2 年
    "steps": 500,  # 500 步
    "pure_bond_value": 88.5,  # 债底 88.5 元
    "call_price": 14.2 * 1.3,  # 强赎线
    "put_price": 14.2 * 0.7,  # 回售线
    "redemption_price": 108,  # 到期赎回 108
}

result = calculate_cb_value(**params)
print(f"可转债理论估值: {result:.3f}")


def calculate_cb_with_reset(
    S0,
    K,
    r,
    sigma,
    T,
    steps,
    pure_bond_value,
    call_price,
    put_price,
    redemption_price,
    reset_threshold_pct=0.85,  # 下修触发线（通常85%）
    p_reset=0.3,  # 触发后的下修概率（博弈参数）
    net_asset_val=5.0,  # 每股净资产（下修底线）
):
    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(r * dt) - d) / (u - d)
    df = np.exp(-r * dt)

    # 1. 终点价值初始化
    st = S0 * d ** (np.arange(steps, -1, -1)) * u ** (np.arange(0, steps + 1, 1))
    conv_ratio = 100 / K
    values = np.maximum(st * conv_ratio, redemption_price)

    # 2. 反向回溯
    for i in range(steps - 1, -1, -1):
        # 基础期望价
        values = (p * values[1:] + (1 - p) * values[:-1]) * df
        st = S0 * d ** (np.arange(i, -1, -1)) * u ** (np.arange(0, i + 1, 1))

        for j in range(len(values)):
            # --- 核心：下修博弈逻辑 ---
            # 如果股价触及下修线
            if st[j] <= K * reset_threshold_pct:
                # 假设下修后的新转股价 K_new 为当前股价的 1.02 倍（但不低于净资产）
                k_new = max(st[j] * 1.02, net_asset_val)
                # 计算下修后的即时价值 (100 / k_new * st[j])，通常接近 100 元
                v_after_reset = (100 / k_new) * st[j]

                # 概率博弈：当前价值 = (1 - 概率) * 原价值 + 概率 * 下修后价值
                values[j] = (1 - p_reset) * values[j] + p_reset * v_after_reset

            # --- 其他标准条款 ---
            conv_val = (100 / K) * st[j]
            values[j] = max(values[j], pure_bond_value / steps * i)  # 债底
            values[j] = max(values[j], conv_val)  # 转股

            if st[j] >= call_price:  # 强赎
                values[j] = min(values[j], max(redemption_price, conv_val))
            if st[j] <= put_price:  # 回售
                values[j] = max(values[j], put_price)

    return values[0]


# 测试：观察加入下修概率后，理论价值的变化
v_no_reset = calculate_cb_with_reset(
    S0=19.78,
    K=19.34,
    r=0.01628,
    sigma=0.5784,
    T=3.287,
    steps=500,
    pure_bond_value=94.25,
    call_price=25.142,
    put_price=13.538,
    redemption_price=113.00,
    p_reset=0,
)

v_with_reset = calculate_cb_with_reset(
    S0=19.78,
    K=19.34,
    r=0.01628,
    sigma=0.5784,
    T=3.287,
    steps=500,
    pure_bond_value=94.25,
    call_price=25.142,
    put_price=13.538,
    redemption_price=113.00,
    p_reset=0.3,
)

print(f"常规理论价: {v_no_reset:.2f}")
print(f"考虑下修预期的理论价: {v_with_reset:.2f}")
