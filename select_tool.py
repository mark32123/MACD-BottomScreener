import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import akshare as ak

# --- 强制禁用代理干扰 ---
os.environ['NO_PROXY'] = '*'

# --- 环境设置 ---
plt.rcParams['font.sans-serif'] = ['SimHei'] 
plt.rcParams['axes.unicode_minus'] = False

class StockScanner:
    def __init__(self):
        self.output_dir = "stock_charts"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.results = []

    def fetch_data(self, symbol):
        """获取个股历史数据并计算均线"""
        try:
            # 使用 ak.stock_zh_a_hist 接口
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            
            if df is None or df.empty or len(df) < 25:
                return None

            # 计算常用均线
            df["MA5"] = df["收盘"].rolling(window=5).mean()
            df["MA10"] = df["收盘"].rolling(window=10).mean()
            df["MA20"] = df["收盘"].rolling(window=20).mean()
            return df
        except Exception:
            return None

    def check_trend(self, df):
        """核心筛选逻辑：价格 > MA5 > MA10 > MA20"""
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        price = last_row["收盘"]
        ma5, ma10, ma20 = last_row["MA5"], last_row["MA10"], last_row["MA20"]

        # 条件：严格多头排列 + MA5趋势向上
        return (price > ma5 > ma10 > ma20) and (ma5 > prev_row["MA5"])

    def save_chart(self, df, symbol, name):
        """生成并保存可视化图片"""
        fig, ax = plt.subplots(figsize=(10, 6))
        plot_df = df.tail(40)
        
        ax.plot(plot_df["日期"], plot_df["收盘"], label="价格", color="red", linewidth=2)
        ax.plot(plot_df["日期"], plot_df["MA5"], label="MA5")
        ax.plot(plot_df["日期"], plot_df["MA10"], label="MA10")
        ax.plot(plot_df["日期"], plot_df["MA20"], label="MA20")

        ax.set_title(f"{name} ({symbol}) 趋势分析")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        fig.tight_layout()
        img_path = os.path.join(self.output_dir, f"{symbol}_{name}.png")
        fig.savefig(img_path)
        plt.close(fig)
        return img_path

    def get_stable_symbols(self, limit=50):
        """改用刚才测试成功的稳定接口获取名单"""
        print(f"正在通过基础接口获取全市场名单...")
        try:
            df_all = ak.stock_info_a_code_name()
            # 简单清洗：剔除ST股
            df_all = df_all[~df_all["name"].str.contains("ST")]
            
            # 为了防止全量扫描太慢，默认取前 limit 只进行测试
            # 如果想扫全量，把 head(limit) 去掉即可
            subset = df_all.head(limit)
            return list(zip(subset["code"], subset["name"]))
        except Exception as e:
            print(f"获取名单失败: {e}")
            return []

    def run_scan(self, stock_list):
        print(f"开始扫描 {len(stock_list)} 只股票...")
        for i, (symbol, name) in enumerate(stock_list):
            print(f"\r进度: [{i+1}/{len(stock_list)}] 正在分析 {symbol} {name}", end="")
            
            df = self.fetch_data(symbol)
            if df is not None and self.check_trend(df):
                img_path = self.save_chart(df, symbol, name)
                last_row = df.iloc[-1]
                self.results.append({
                    "代码": symbol, "名称": name, 
                    "当前价": last_row["收盘"], "MA5": round(last_row["MA5"], 2)
                })
            time.sleep(0.1) # 略微延迟，保护接口

        if self.results:
            pd.DataFrame(self.results).to_excel("选股报告.xlsx", index=False)
            print(f"\n\n[成功] 发现 {len(self.results)} 只符合趋势的股票，已生成报告。")
        else:
            print("\n\n[提示] 扫描完成，未发现符合多头排列的股票。")

if __name__ == "__main__":
    scanner = StockScanner()
    # 扫描前 100 只股票
    stocks = scanner.get_stable_symbols(limit=100)
    scanner.run_scan(stocks)