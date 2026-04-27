import os
import time
import random
import pandas as pd
import numpy as np
import akshare as ak
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class LowPositionScanner:
    def __init__(self, sample_size=50):
        self.sample_size = sample_size
        self.results = []
        self.lock = Lock()
        self.output_file = f"随机抽样低位机会_{time.strftime('%Y%m%d')}.xlsx"

    def calculate_macd_status(self, df):
        """计算 MACD 并判断金叉或贴合度"""
        try:
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            
            last_m, last_s = macd_line.iloc[-1], signal_line.iloc[-1]
            prev_m, prev_s = macd_line.iloc[-2], signal_line.iloc[-2]
            
            # 状态 1: 黄金交叉 (快线上穿慢线)
            is_golden_cross = prev_m <= prev_s and last_m > last_s
            
            # 状态 2: 极度贴合 (快线在下但距离慢线极近，准备金叉)
            diff = last_s - last_m
            is_closing_in = 0 < diff < (df['close'].iloc[-1] * 0.005) # 差值小于股价的0.5%
            
            if is_golden_cross:
                return "今日黄金交叉"
            elif is_closing_in:
                return "即将金叉(贴合)"
            return None
        except:
            return None

    def process_stock(self, stock_info):
        symbol = stock_info['code']
        try:
            # 获取历史数据
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            if df is None or len(df) < 40: return
            
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
            status = self.calculate_macd_status(df)
            
            if status:
                with self.lock:
                    self.results.append({
                        "代码": symbol,
                        "名称": stock_info['name'],
                        "技术状态": status,
                        "最新价": df['close'].iloc[-1],
                        "今日涨幅%": df['pct_chg'].iloc[-1]
                    })
                    print(f"🎯 发现信号: {stock_info['name']} ({status})")
        except:
            pass

    def run(self):
        print(f"🔍 正在从全市场随机抽取 {self.sample_size} 只股票进行体检...")
        try:
            # 获取全市场名单
            all_stocks = ak.stock_zh_a_spot_em()
            # 过滤
            all_stocks = all_stocks[~all_stocks["名称"].str.contains("ST|退")]
            
            # 随机抽样
            sample_list = all_stocks.sample(n=min(self.sample_size, len(all_stocks))).to_dict('records')
            
            task_list = [{'code': str(row['代码']), 'name': str(row['名称'])} for row in sample_list]
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(self.process_stock, task_list)
            
            if self.results:
                final_df = pd.DataFrame(self.results)
                final_df.to_excel(self.output_file, index=False)
                print(f"\n✅ 扫描结束！结果已保存至: {os.path.abspath(self.output_file)}")
            else:
                print("\n本次抽样中未发现符合 MACD 低位信号的个股，可以尝试再次运行。")
                
        except Exception as e:
            print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    scanner = LowPositionScanner(sample_size=50) # 你可以手动修改这里的 50
    scanner.run()