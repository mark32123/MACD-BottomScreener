"""
MACD 单股测试 —— 验证 MACD 计算和抄底信号（baostock 库）
用法：修改 TEST_CODE / TEST_MARKET 后运行
"""
import os, sys

for k in list(os.environ.keys()):
    if 'proxy' in k.lower():
        del os.environ[k]
os.environ['NO_PROXY'] = '*'

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import baostock as bs
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from select_tool import calc_macd, check_macd_signal

TEST_CODE = "000001"      # 6位代码
TEST_MARKET = 0           # 0=深圳, 1=上海


def test(code_6, market):
    prefix_market = '上海' if market == 1 else '深圳'
    bs_code = ('sh.' if market == 1 else 'sz.') + code_6
    print(f"测试: {code_6} ({prefix_market})  →  {bs_code}")
    print("-" * 60)

    lg = bs.login()
    if lg.error_code != '0':
        print(f"X 登录失败: {lg.error_msg}")
        return

    try:
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')

        rs = bs.query_history_k_data_plus(
            bs_code, 'date,close,volume',
            start_date=start, end_date=end,
            frequency='d', adjustflag='2',
        )

        klines = []
        while (rs.error_code == '0') & rs.next():
            klines.append(rs.get_row_data())

        if len(klines) < 60:
            print(f"X 数据不足 ({len(klines)} 条)")
            return

        dates = [r[0] for r in klines]
        closes = np.array([float(r[1]) for r in klines if r[1] != ''])
        volumes = np.array([float(r[2]) for r in klines if r[2] != ''])

        print(f"共 {len(closes)} 根K线 ({dates[0]} ~ {dates[-1]})")

        dif, dea, hist = calc_macd(closes)
        ok = check_macd_signal(dif, dea, hist)
        print(f"{'V 符合' if ok else 'X 不符合'} MACD 抄底条件\n")

        n_show = 15
        print(f"最近 {n_show} 天 MACD:")
        print(f"{'#':>3} {'日期':>12} {'收盘':>8} {'DIF':>10} {'DEA':>10} {'柱值':>10}  {'信号'}")
        print("-" * 72)
        s = max(0, len(closes) - n_show)
        for i in range(s, len(closes)):
            sig = ""
            if i >= len(closes) - 5:
                if hist[i] < 0:
                    sig = "up" if (i > s and hist[i] > hist[i-1]) else "green"
                else:
                    sig = "red"
            print(f"{i+1:>3} {dates[i]:>12} {closes[i]:>8.2f} {dif[i]:>10.4f} "
                  f"{dea[i]:>10.4f} {hist[i]:>10.4f}  {sig:>8}")

        # 画图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
        x = range(len(closes))
        ax1.plot(x, closes, 'b-', lw=1, label='close')
        ax1.legend(loc='upper left'); ax1.grid(alpha=0.3)
        ax1.set_title(f'{code_6} MACD')

        ax2.plot(x, dif, 'b-', lw=0.8, label='DIF')
        ax2.plot(x, dea, 'r-', lw=0.8, label='DEA')
        colors = ['#ff4444' if v >= 0 else '#00aa00' for v in hist]
        ax2.bar(x, hist, width=0.8, color=colors, alpha=0.6, label='MACD')
        ax2.axhline(y=0, color='black', lw=0.5)
        ax2.legend(loc='upper left'); ax2.grid(alpha=0.3)

        plt.tight_layout()
        out = f"MACD_{code_6}.png"
        plt.savefig(out, dpi=150)
        print(f"\n图表: {os.path.abspath(out)}")

    finally:
        bs.logout()


if __name__ == '__main__':
    test(TEST_CODE, TEST_MARKET)
