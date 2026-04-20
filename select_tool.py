import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import akshare as ak
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# --- 强制禁用代理 ---
os.environ['NO_PROXY'] = '*'

# --- 环境设置 ---
plt.rcParams['font.sans-serif'] = ['SimHei'] 
plt.rcParams['axes.unicode_minus'] = False

class FastStockScanner:
    def __init__(self, max_workers=20):
        self.output_dir = "stock_charts"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.results = []
        self.lock = Lock() # 线程锁
        self.max_workers = max_workers # 并发线程数

    def fetch_and_check(self, stock_tuple):
            symbol, name = stock_tuple
            try:
                # 增加 timeout，防止个别请求卡死整个线程池
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                
                if df is None or df.empty or len(df) < 25:
                    return None

                # --- 强制重命名列，防止有的接口返回 '收盘价' 有的返回 '收盘' ---
                # 打印 df.columns 可以发现有的版本返回的是中文，有的是英文
                # 我们统一处理
                rename_dict = {"收盘": "close", "开盘": "open", "日期": "date"}
                df.rename(columns=rename_dict, inplace=True)
                
                # 如果重命名没成功（即原始列名不叫'收盘'），我们按索引取
                # 历史数据接口通常第5列是收盘价
                if "close" not in df.columns:
                    df["close"] = df.iloc[:, 4] 

                # 强制转类型
                df["close"] = pd.to_numeric(df["close"], errors='coerce')
                df = df.dropna(subset=["close"])

                # 计算均线
                df["MA20"] = df["close"].rolling(window=20).mean()

                # 获取最后一行
                last_row = df.iloc[-1]
                
                # --- 关键：检查是否为 NaN ---
                price = float(last_row["close"])
                ma20 = float(last_row["MA20"])

                if pd.isna(price) or pd.isna(ma20):
                    return None

                # 只要价格大于20日均线就记录
                if price > ma20:
                    # 为了速度，我们可以先不画图，只记录结果
                    # img_path = self.save_chart(df, symbol, name) 
                    img_path = "Skipped" 
                    
                    with self.lock:
                        self.results.append({
                            "代码": symbol, 
                            "名称": name, 
                            "最新价": price,
                            "MA20": round(ma20, 2)
                        })
                    return True
            except Exception as e:
                # 如果还是 0 只，取消下面这行的注释，看看到底报什么错
                # print(f"\n[DEBUG] {symbol} {name} Error: {e}")
                pass
            return None

    def save_chart(self, df, symbol, name):
        """保存图片（注意：plt在多线程下有时不稳定，如果崩溃请关闭此功能）"""
        try:
            fig, ax = plt.subplots(figsize=(8, 5))
            plot_df = df.tail(30)
            ax.plot(plot_df["日期"], plot_df["收盘"], label="Price", color="red")
            ax.plot(plot_df["日期"], plot_df["MA5"], label="MA5")
            ax.plot(plot_df["日期"], plot_df["MA10"], label="MA10")
            ax.set_title(f"{name} {symbol}")
            ax.grid(True, alpha=0.2)
            img_path = os.path.join(self.output_dir, f"{symbol}.png")
            fig.savefig(img_path)
            plt.close(fig)
            return img_path
        except:
            return "绘图失败"

    def run_fast_scan(self, stock_list):
        total = len(stock_list)
        print(f"🚀 启动多线程扫描，总数: {total}，并发数: {self.max_workers}")
        
        start_time = time.time()
        
        # 使用线程池
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = [executor.submit(self.fetch_and_check, s) for s in stock_list]
            
            count = 0
            for future in as_completed(futures):
                count += 1
                if count % 10 == 0 or count == total:
                    print(f"\r进度: {count}/{total} ({(count/total*100):.1f}%)", end="")

        end_time = time.time()
        print(f"\n\n✅ 扫描完成！耗时: {int(end_time - start_time)} 秒")
        
        if self.results:
            df_res = pd.DataFrame(self.results)
            df_res.to_excel("全市场筛选结果.xlsx", index=False)
            print(f"找到符合条件的股票: {len(self.results)} 只，报告已生成。")
        else:
            print("未发现符合条件的股票。")

# --- 执行 ---
if __name__ == "__main__":
    scanner = FastStockScanner(max_workers=30) # 提速到30线程
    
    print("正在加载全量名单...")
    try:
        raw_data = ak.stock_info_a_code_name()
        # 排除 ST，避免扫描垃圾股
        raw_data = raw_data[~raw_data["name"].str.contains("ST")]
        all_stocks = list(zip(raw_data["code"], raw_data["name"]))
        
        print(f"名单加载完成，准备全速扫描全市场 {len(all_stocks)} 只股票...")
        
        scanner.run_fast_scan(all_stocks[:10]) 
        
    except Exception as e:
        print(f"名单获取失败: {e}")