import numpy as np
from scipy.optimize import newton
from scipy.stats import norm


def calculate_cb_bs_model(S0, K, r, sigma, T, pure_bond_value):
    """
    S0: 正股价格
    K: 转股价
    r: 无风险利率
    sigma: 波动率
    T: 剩余年限
    pure_bond_value: 纯债价值
    """
    # 1. 计算 d1 和 d2
    d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # 2. 计算标准欧式看涨期权价格 (每股)
    call_option_per_share = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    # 3. 换算成 100 元面值对应的转债价值
    # 每 100 元面值包含的股数 = 100 / K
    conversion_ratio = 100 / K
    option_value_total = call_option_per_share * conversion_ratio

    # 4. 总价值 = 纯债价值 + 期权价值
    total_theoretical_value = pure_bond_value + option_value_total

    return total_theoretical_value, option_value_total


# --- 使用你的参数 ---
# 当前股价
S0 = 4.62
# 转股价
K = 5.26
# 无风险利率-5年期
r = 0.01628
# 波动率
sigma = 0.3656
# 剩余年
T = 2.26
# 纯债价值
pure_bond_value = 109.89

# 东财的估值
dc_val = 128.282

theoretical_val, option_val = calculate_cb_bs_model(S0, K, r, sigma, T, pure_bond_value)

print("-" * 30)
print(f"B-S 模型理论总价: {theoretical_val:.3f}")
print(f"其中期权价值部分: {option_val:.3f}")
print(f"东方财富参考值: {dc_val:.3f}")
print(f"差距: {theoretical_val - dc_val:.3f}")
print("-" * 30)


def bs_value(sigma, S0, K, r, T, pure_bond_value):
    d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return pure_bond_value + call * (100 / K)


# 目标：让函数结果等于 东财的估值
target_value = dc_val
# 求解 sigma
implied_vol = newton(
    lambda x: bs_value(x, S0, K, r, T, pure_bond_value) - target_value, sigma
)

print(f"要达到东财的估值，隐含波动率需要达到: {implied_vol*100:.2f}%")
