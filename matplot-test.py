import os
import shutil

import matplotlib as mpl
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# 1. 彻底清理缓存目录
cache_dir = mpl.get_cachedir()
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)
    print(f"已清理 Matplotlib 缓存目录: {cache_dir}")

# 2. 验证字体是否在 Matplotlib 的候选名单中
# 这一步会触发重新扫描，可能需要几秒钟
all_fonts = [f.name for f in fm.fontManager.ttflist]
if any("Microsoft YaHei" in f for f in all_fonts) or any(
    "SimHei" in f for f in all_fonts
):
    print("成功！Matplotlib 已识别到中文字体。")
else:
    print("警告：Matplotlib 仍未找到字体，请检查权限或路径。")


# 必须确保名字和 Windows 下显示的完全一致
# 也可以尝试 'SimHei' (黑体)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

plt.figure(figsize=(6, 4))
plt.plot([1, 2, 3], [4, 5, 6])
plt.title("WSL 环境中文测试", fontsize=15)
plt.show()
