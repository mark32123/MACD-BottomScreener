import os
import sys

# 彻底禁用所有可能的代理环境变量
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

# 强制设置 NO_PROXY
os.environ['NO_PROXY'] = '*'

import akshare as ak
# 现在再运行测试
df = ak.stock_zh_a_hist(symbol="000001", period="daily", adjust="qfq")
print(df)