import os
import time
import pandas as pd
import akshare as ak

def get_hot_stocks():
    print("🚀 正在抓取今日涨幅前 50 的强势个股...")
    try:
        # 获取实时行情快照
        df = ak.stock_zh_a_spot_em()
        
        # 过滤掉 ST 和 退市股
        df = df[~df["名称"].str.contains("ST|退")]
        
        # 按照涨跌幅降序排列
        df_sorted = df.sort_values(by="涨跌幅", ascending=False).head(50).copy()
        
        # 选择需要的字段
        # 注意：EM 接口通常自带“板块”或“行业”字段
        result_columns = {
            "代码": "股票代码",
            "名称": "股票名称",
            "最新价": "最新价",
            "涨跌幅": "涨幅%",
            "成交额": "成交额",
            "换手率": "换手率%",
            "板块": "所属板块"
        }
        
        # 兼容性处理：如果不存在“板块”列，尝试获取行业信息
        if "板块" not in df_sorted.columns:
            df_sorted["板块"] = "详见行情软件"

        final_df = df_sorted[list(result_columns.keys())].rename(columns=result_columns)
        
        # 格式化成交额为亿元
        final_df["成交额"] = (pd.to_numeric(final_df["成交额"]) / 100000000).round(2).astype(str) + " 亿"
        
        output_file = f"今日涨幅前50_{time.strftime('%Y%m%d')}.xlsx"
        final_df.to_excel(output_file, index=False)
        print(f"✅ 强势股列表已生成: {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")

if __name__ == "__main__":
    get_hot_stocks()