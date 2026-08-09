"""
MACD 抄底选股扫描器
策略：MACD 绿柱近5日逐日缩小 + 柱状图接近0 + DIF即将上穿DEA（金叉前夕）
数据源：baostock（多进程并发拉取 K 线）
"""
import os
import sys

for k in list(os.environ.keys()):
    if 'proxy' in k.lower():
        del os.environ[k]
os.environ['NO_PROXY'] = '*'

import time
import threading
import pandas as pd
import numpy as np
import baostock as bs
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass  # 子进程中 stdout 可能不可用

# ==================== 可调参数 ====================
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
LOOKBACK_DAYS = 5
HIST_NEAR_ZERO = 0.08
MIN_HISTORY_DAYS = 60
PROCESS_WORKERS = 8            # 进程数（建议 4-12，视 CPU 核数调整）
KLINE_TIMEOUT = 15             # 单只股票 K 线请求超时（秒），超时则跳过该股
LOGIN_TIMEOUT = 15             # baostock 登录超时（秒）
# =================================================


# ---------- MACD 计算（无状态，可跨进程）----------

def calc_macd(close_arr):
    s = pd.Series(close_arr)
    ema_f = s.ewm(span=MACD_FAST, adjust=False).mean()
    ema_s = s.ewm(span=MACD_SLOW, adjust=False).mean()
    dif = ema_f - ema_s
    dea = dif.ewm(span=MACD_SIGNAL, adjust=False).mean()
    hist = 2.0 * (dif - dea)
    return dif.values, dea.values, hist.values


def check_macd_signal(dif_arr, dea_arr, hist_arr):
    n = LOOKBACK_DAYS
    if len(hist_arr) < n + 1:
        return False
    h, d, e = hist_arr[-n:], dif_arr[-n:], dea_arr[-n:]
    if not all(v < 0 for v in h):
        return False
    for i in range(1, n):
        if h[i] <= h[i - 1]:
            return False
    if abs(h[-1]) > HIST_NEAR_ZERO:
        return False
    for i in range(n):
        if d[i] >= e[i]:
            return False
    gaps = e - d
    for i in range(1, n):
        if gaps[i] >= gaps[i - 1]:
            return False
    return True


# ---------- 带超时的网络封装（防卡死）----------

def _run_with_timeout(timeout, fn):
    """
    在线程中执行 fn，最多等 timeout 秒。
    返回 (结果, None)；超时返回 (None, 错误信息)。
    daemon 线程即使卡在 socket 上也绝不会阻塞主流程。
    """
    box = {}

    def _do():
        try:
            box['result'] = fn()
        except Exception as e:
            box['error'] = f"{type(e).__name__}: {e}"

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, f"请求超时(>{timeout}s)，已跳过"
    if 'error' in box:
        return None, box['error']
    return box.get('result'), None


def fetch_one_stock(bs_code, start_date, end_date, timeout=KLINE_TIMEOUT):
    """
    带超时地拉取单只股票日K（前复权）。
    成功返回 (klines, None)；超时/失败返回 (None, 错误信息字符串)。
    本函数最多阻塞 timeout 秒，网络异常也不会卡死扫描。
    """
    def _query():
        rs = bs.query_history_k_data_plus(
            bs_code, 'close,volume',
            start_date=start_date, end_date=end_date,
            frequency='d', adjustflag='2',
        )
        if rs.error_code != '0':
            raise RuntimeError(f"baostock error: {rs.error_msg}")
        klines = []
        while (rs.error_code == '0') and rs.next():
            klines.append(rs.get_row_data())
        return klines

    return _run_with_timeout(timeout, _query)


def _login_with_timeout(timeout=LOGIN_TIMEOUT):
    """带超时的 baostock 登录，成功返回 (lg, None)，失败返回 (None, 错误信息)"""
    def _login():
        lg = bs.login()
        if lg.error_code != '0':
            raise RuntimeError(f"登录失败: {lg.error_msg}")
        return lg

    lg, err = _run_with_timeout(timeout, _login)
    if err is not None:
        return None, err
    return lg, None


# ---------- 子进程工作函数 ----------

def _worker_process(batch):
    """
    单个子进程：登录 → 拉 K 线 → 算 MACD → 筛选 → 返回命中结果
    每个子进程有独立的 baostock 连接；
    返回 (results, errors)：errors 记录被跳过的股票及原因（超时/网络错误）。
    """
    results = []
    errors = []

    lg, err = _login_with_timeout()
    if lg is None:
        errors.append(('*登录*', err))
        return results, errors

    try:
        end_d = datetime.now().strftime('%Y-%m-%d')
        start_d = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')

        for item in batch:
            bs_code = item['bs_code']
            # 带超时拉取：网络卡住也会在 KLINE_TIMEOUT 秒后返回 None+错误，跳过该股
            klines, err = fetch_one_stock(bs_code, start_d, end_d)
            if err is not None:
                errors.append((item['code_6'], err))
                continue
            if len(klines) < MIN_HISTORY_DAYS:
                continue

            try:
                closes = np.array([float(r[0]) for r in klines if r[0] != ''])
                volumes = np.array([float(r[1]) for r in klines if r[1] != ''])

                if len(closes) < MIN_HISTORY_DAYS:
                    continue

                dif, dea, hist = calc_macd(closes)
                if not check_macd_signal(dif, dea, hist):
                    continue

                vol_ratio = None
                if len(volumes) >= 25:
                    a5 = volumes[-5:].mean()
                    a20 = volumes[-25:-5].mean()
                    if a20 > 0:
                        vol_ratio = round(float(a5 / a20), 2)

                recent = [float(v) for v in hist[-LOOKBACK_DAYS:]]
                trend = " -> ".join([f"{v:.4f}" for v in recent])

                results.append({
                    "股票代码": item['code_6'],
                    "股票名称": item['name'],
                    "最新价": round(float(closes[-1]), 2),
                    "DIF": round(float(dif[-1]), 4),
                    "DEA": round(float(dea[-1]), 4),
                    "DIF-DEA差": round(float(dif[-1] - dea[-1]), 4),
                    "MACD柱值": round(float(hist[-1]), 4),
                    "近5日柱趋势": trend,
                    "量比": vol_ratio,
                })
            except Exception as e:
                errors.append((item['code_6'], f"{type(e).__name__}: {e}"))
                continue
    finally:
        try:
            bs.logout()
        except Exception:
            pass

    return results, errors


# ---------- 主流程 ----------

def main():
    print("=" * 55)
    print("   MACD 抄底选股扫描器 (baostock 多进程)")
    print(f"   绿柱缩窄 + 柱近零 + 金叉前夕 | {PROCESS_WORKERS} 进程")
    print("=" * 55)

    # ── 登录主进程（仅获取股票列表）──
    print("\n[0] 登录 baostock ...")
    lg, err = _login_with_timeout()
    if lg is None:
        print(f"  X {err}")
        print(f"  X 无法登录，请检查网络后重试。")
        return
    print("  OK 登录成功")

    try:
        # ── 获取股票列表（同样带超时，防止网络卡住导致程序跑不完）──
        print("\n[1/3] 获取全 A 股列表...")

        def _fetch_stock_list():
            rs = bs.query_stock_basic()
            if rs.error_code != '0':
                raise RuntimeError(f"query_stock_basic 失败: {rs.error_msg}")
            records = []
            while (rs.error_code == '0') and rs.next():
                records.append(rs.get_row_data())
            return records, rs.fields

        records, err = _run_with_timeout(30, _fetch_stock_list)
        if err is not None:
            print(f"  X 获取股票列表失败: {err}")
            return
        stock_records, stock_fields = records

        df = pd.DataFrame(stock_records, columns=stock_fields)
        df = df[df['type'] == '1']
        df = df[df['status'] == '1']
        df = df[~df['code'].str.contains(r'bj\.', na=False)]
        df['code_6'] = df['code'].str.split('.').str[1]

        # 预过滤
        df = df[~df['code_name'].str.contains('ST|退|N|C', na=False)]
        df = df[df['code_6'].str.match(r'^\d{6}$')]

        # 构建任务列表
        tasks = [
            {'bs_code': row['code'], 'code_6': row['code_6'], 'name': row['code_name']}
            for _, row in df.iterrows()
        ]

        print(f"  OK {len(tasks)} 只候选（已排除 ST/新股）")

        # ── 分发给子进程 ──
        print(f"\n[2/3] {PROCESS_WORKERS} 进程并发扫描...")

        # 按进程数均匀分片
        chunk_size = max(1, len(tasks) // PROCESS_WORKERS)
        chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
        # 合并尾部小块（避免进程数过多）
        if len(chunks) > PROCESS_WORKERS:
            while len(chunks) > PROCESS_WORKERS:
                chunks[-2].extend(chunks[-1])
                chunks.pop()

        all_results = []
        all_errors = []            # [(股票代码, 错误原因), ...] 被跳过的记录
        t0 = time.time()
        done_chunks = 0

        with ProcessPoolExecutor(max_workers=PROCESS_WORKERS) as ex:
            fmap = {ex.submit(_worker_process, chunk): i for i, chunk in enumerate(chunks)}
            for f in as_completed(fmap):
                done_chunks += 1
                try:
                    chunk_results, chunk_errors = f.result(timeout=900)  # 单个 chunk 最多 15 分钟
                    all_results.extend(chunk_results)
                    all_errors.extend(chunk_errors)
                except Exception as e:
                    print(f"  ! 某批次出错: {type(e).__name__}: {e}")

                elapsed = time.time() - t0
                rate = done_chunks / elapsed if elapsed > 0 else 0
                eta = (len(chunks) - done_chunks) / rate if rate > 0 else 0
                print(f"  {done_chunks}/{len(chunks)} 批次 | {elapsed:.0f}s | "
                      f"~{eta:.0f}s 剩余 | hit {len(all_results)}")

        elapsed = time.time() - t0
        print(f"\n[3/3] 完成 | {elapsed:.0f}s | 扫描 {len(tasks)} 只 | 命中 {len(all_results)} 只")

        # ── 汇总网络异常（超时/错误）被跳过的股票，不静默吞掉 ──
        if all_errors:
            print(f"\n  ! {len(all_errors)} 只因网络超时/错误被跳过，原因如下:")
            for code, msg in all_errors[:20]:
                print(f"    - {code}: {msg}")
            if len(all_errors) > 20:
                print(f"    ... 其余 {len(all_errors) - 20} 只省略（可稍后重跑补扫）")

    finally:
        try:
            bs.logout()
        except Exception:
            pass

    if not all_results:
        print("  无结果。可放宽 HIST_NEAR_ZERO 参数重试。")
        return

    # ── 输出 xlsx ──
    df = pd.DataFrame(all_results)
    cols = ["股票代码", "股票名称", "最新价",
            "DIF", "DEA", "DIF-DEA差", "MACD柱值", "近5日柱趋势", "量比"]
    df = df[[c for c in cols if c in df.columns]]
    df = df.sort_values("MACD柱值", ascending=False)

    fname = f"MACD抄底选股_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(fname, index=False)

    print(f"  OK 结果: {os.path.abspath(fname)}")
    print(f"\n  前 10 预览:\n")
    print(df.head(10).to_string(index=False))


if __name__ == '__main__':
    # Windows 下必须加这个保护，否则子进程会递归启动
    main()
