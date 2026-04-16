import os
import akshare as ak

# 强制禁用代理
os.environ['NO_PROXY'] = '*'

def test_connection():
    print("正在尝试连接基础数据源...")
    try:
        # 尝试换一个更基础的接口获取名单
        df = ak.stock_info_a_code_name()
        if not df.empty:
            print(f"✅ 连接成功！已获取 {len(df)} 只股票名单。")
            print(df.head())
            return
    except Exception as e:
        print(f"❌ 基础接口也失败了: {e}")

    print("\n--- 最终排查方案 ---")
    print("1. 请尝试使用手机热点连接电脑，排除家用路由器屏蔽。")
    print("2. 检查是否有强力杀毒软件（如 360, 火绒）拦截了 Python.exe 的联网。")

if __name__ == "__main__":
    test_connection()