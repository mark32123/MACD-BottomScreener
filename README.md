<div align="center">

# 📈 MACD-BottomScreener

**基于 MACD 绿柱动量衰减 + 低位金叉前夕的全 A 股抄底选股量化工具**

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Data Source](https://img.shields.io/badge/Data_Source-Baostock-FF6F00?style=flat-square)](http://baostock.com/)
[![Export Format](https://img.shields.io/badge/Export-Excel%20%2F%20XLSX-107C41?style=flat-square&logo=microsoft-excel&logoColor=white)](#-效果展示)
[![Code Style](https://img.shields.io/badge/Code%20Style-PEP8-black?style=flat-square)](https://peps.python.org/pep-0008/)

[项目简介](#-项目简介) • [核心特性](#-核心特性) • [策略逻辑](#-策略逻辑与选股模型) • [快速开始](#-快速开始) • [参数配置](#-核心参数配置) • [效果展示](#-效果展示)

</div>

---

## 📖 目录

- [💡 项目简介](#-项目简介)
- [🔥 核心特性](#-核心特性)
- [📐 策略逻辑与选股模型](#-策略逻辑与选股模型)
  - [1. MACD 指标计算公式](#1-macd-指标计算公式)
  - [2. 抄底筛选四重判定法则](#2-抄底筛选四重判定法则)
- [🚀 快速开始](#-快速开始)
  - [1. 环境准备](#1-环境准备)
  - [2. 克隆项目与安装依赖](#2-克隆项目与安装依赖)
  - [3. 运行选股程序](#3-运行选股程序)
  - [4. 单股调试（可选）](#4-单股调试可选)
- [⚙️ 核心参数配置](#-核心参数配置)
- [📊 效果展示](#-效果展示)
- [❓ 常見問題](#-常見問題)
- [⚠️ 免责声明](#-免责声明)
- [🤝 贡献与支持](#-贡献与支持)

---

## 💡 项目简介

**MACD-BottomScreener** 是一款专为 A 股市场设计的**低位抄底量化选股工具**。

当标的经历深度回调后，传统趋势指标往往存在滞后性。本系统通过 **baostock** 数据源自动获取全市场日 K 线，多进程并发计算 MACD 指标，结合**绿柱连续缩小**、**柱值逼近零轴**与**DIF-DEA 金叉前夕收敛**等多重因子，精准捕捉空头力量衰竭、底部拐点初显的标的，并自动导出结构化 Excel 报表供复盘决策。

---

## 🔥 核心特性

- **🔍 全市场自动化扫描**：覆盖沪深主板、科创板与创业板 5000+ 只股票，自动排除 ST/退市/新股。
- **🚀 多进程并发加速**：基于 `ProcessPoolExecutor` 的 8 进程并发拉取 K 线，全市场扫描约 5–7 分钟。
- **📐 动态 MACD 抄底算法**：
  - **绿柱动量衰减**：连续 5 日 MACD 绿柱逐日缩小，识别零轴下方空头动能衰竭拐点。
  - **柱值逼近零轴**：最新柱值 `|HIST| < 0.08`，锁定即将翻红的临界形态。
  - **金叉前夕**：DIF 从下方收敛于 DEA、差距逐日缩小，捕捉低位金叉前夜。
  - **量能验证**：引入近 5 日/前 20 日量比因子，过滤无量死寂股。
- **📁 结构化 Excel 自动导出**：生成包含现价、DIF、DEA、柱值、柱趋势与量比的 `.xlsx` 报表。
- **⚡ 稳定可靠的数据源**：原生集成 **baostock** 独立数据服务器，不受东方财富等平台反爬限制。

---

## 📐 策略逻辑与选股模型

### 1. MACD 指标计算公式

基础指数移动平均线 (EMA) 与 MACD 计算：

$$\text{EMA}_n = \text{EMA}(\text{Close}, n)$$

$$\text{DIF} = \text{EMA}_{12} - \text{EMA}_{26}$$

$$\text{DEA} = \text{EMA}(\text{DIF}, 9)$$

$$\text{MACD 柱值} = 2 \times (\text{DIF} - \text{DEA})$$

### 2. 抄底筛选四重判定法则
选股模型由四个关键条件同时约束，严格保证 **“位置低、空头弱、拐点近、即将反转”**。

#### 条件一：连续绿柱 · 低位确认
近 5 个交易日 MACD 柱全部为负值，确保个股处于持续回调后的低位空头区间，不追高位回落标的。

#### 条件二：空头衰竭 · 动能持续减弱
连续 5 个交易日 MACD 绿柱**越来越短**，柱值持续向上修复，代表市场抛压逐步耗尽，下跌动能枯竭。

#### 条件三：逼近零轴 · 拐点临界形态
最新 MACD 绿柱绝对值极小，收缩至 **0.08 临界值以内**，处于马上由绿翻红、多空切换的关键拐点位置。

#### 条件四：双线收敛 · 低位金叉前夜
DIF 持续处于 DEA 下方，且 DIF 与 DEA 的间距持续缩小，双线逐渐粘合蓄力，即将形成低位金叉反转。

> 同时满足以上四重条件，即为标准**空头衰竭、底部蓄力、即将反弹**的抄底形态。

---

## 🚀 快速开始

### 1. 环境准备

确保开发环境中已安装 **Python 3.8+**：

```bash
python --version
```

### 2. 克隆项目与安装依赖

```bash
# 克隆仓库
git clone https://github.com/mark32123/MACD-BottomScreener.git

# 进入项目目录
cd MACD-BottomScreener

# 安装依赖
pip install -r requirements.txt
```

`requirements.txt` 核心依赖：

```text
pandas>=1.5.0
numpy>=1.22.0
baostock>=0.8.9
openpyxl>=3.0.0
matplotlib>=3.5.0   # 单股调试画图用
```

### 3. 运行选股程序

```bash
python select_tool.py
```

扫描完成后，当前目录将生成 `MACD抄底选股_YYYYMMDD_HHMMSS.xlsx` 结果报表。

### 4. 单股调试（可选）

修改 `test.py` 中的 `TEST_CODE` / `TEST_MARKET` 后运行，可查看单只股票的 MACD 数据与走势图：

```bash
python test.py
```

## ⚙️ 核心参数配置

所有参数集中在 `select_tool.py` 文件顶部的"可调参数"区：

| 参数 | 默认值 | 说明 |
|------|:---:|------|
| `MACD_FAST` | `12` | MACD 快线 EMA 周期 |
| `MACD_SLOW` | `26` | MACD 慢线 EMA 周期 |
| `MACD_SIGNAL` | `9` | DEA 信号线周期 |
| `LOOKBACK_DAYS` | `5` | 绿柱缩小的观察天数 |
| `HIST_NEAR_ZERO` | `0.08` | 柱值逼近零轴的阈值（放宽可提高命中率） |
| `MIN_HISTORY_DAYS` | `60` | 计算 MACD 所需最少 K 线数量 |
| `PROCESS_WORKERS` | `8` | 并发进程数 |

> 💡 **提示**：若扫描结果为空，可适当调大 `HIST_NEAR_ZERO`（如改为 `0.15`）放宽筛选条件。

## 📊 效果展示

<table>
  <tr>
    <td align="center"><img src="images/6eccaf4dd6827a104cc61dc936bb44b2.png" width="100%"><br/><b>运行效果示例</b></td>
    <td align="center"><img src="images/05e3c8c8119589358746d8467ef82744.jpg" width="100%"><br/><b>信号示例 1</b></td>
  </tr>
  <tr>
    <td align="center"><img src="images/1c4dd4510c6521c1c3cb52f82c89d5cc.jpg" width="100%"><br/><b>信号示例 2</b></td>
    <td align="center"><img src="images/6571294c0cd532b6291e66051fa0b7b6.jpg" width="100%"><br/><b>信号示例 3</b></td>
  </tr>
  <tr>
    <td align="center" colspan="2"><img src="images/ca504ce9dbdb503f029a7dc340a8ed00.jpg" width="60%"><br/><b>信号示例 4</b></td>
  </tr>
</table>

---

## ❓ 常見問題
### ip被拉黑名單

#### 联系官方解除

发邮件至 **baostock@163.com**，说明情况请求解除 IP 限制，例如：

```
标题：IP 被加入黑名单，申请解除

您好，
我使用 baostock 调试脚本时因短时高频连接触发了 IP 风控，
现登录返回错误码 10001011（黑名单用户）。
我的公网 IP 是：<你的出口 IP>
请协助解除限制，我将控制访问频率，感谢！
```

> 如何查询公网 IP：`curl ifconfig.me` 或访问 `https://ifconfig.me`

#### 更换出口 IP

##### 方式 A：重启光猫/路由器

宽带为**动态 IP** 时，重启光猫/路由器即可获取新公网 IP，立即解除。
（重启后如 IP 未变，可多试一次或稍等几分钟）

##### 方式 B：VPN / 梯子「全局（TUN）」模式

**关键前提：必须开启梯子的「全局 / TUN / 虚拟网卡」模式**，只开「系统代理」无效！

| 原因 | 说明 |
|---|---|
| baostock 使用 10030 端口**原始 TCP socket** 连接 | 不走 HTTP 代理 |
| 「系统代理/PAC 模式」只接管浏览器等 HTTP 流量 | baostock 流量仍从本机宽带 IP 出去，黑名单照旧生效 |
| 「TUN 模式/全局模式」在网卡层接管**所有流量** | baostock 连接走 VPN 出口 IP，绕过黑名单 |

各客户端开启方式：

| 客户端 | 操作 |
|---|---|
| Clash Verge / Clash for Windows | 主界面开启「**TUN 模式**」（首次需安装服务模式/管理员权限） |
| v2rayN | 开启「**TUN 模式**」，或「路由 → 全局」 |
| 其他梯子 | 找「全局代理 / 虚拟网卡模式」开关，勿用「规则模式」 |

**验证是否生效**（开启后执行）：

```powershell
& "d:/develop/Projectes/A-share selection tools/.venv/Scripts/python.exe" -u -c "import os; [os.environ.pop(k,None) for k in list(os.environ) if 'proxy' in k.lower()]; os.environ['NO_PROXY']='*'; import urllib.request; print('IPv4出口:', urllib.request.urlopen('https://api.ipify.org', timeout=15).read().decode()); import baostock as bs; lg=bs.login(); print('baostock登录:', lg.error_code, lg.error_msg); bs.logout()"
```

判定标准：

- ✅ `IPv4出口` 显示为 VPN 节点 IP（不再是 `2409:895b:` 开头的电信 IP）→ TUN 生效
- ✅ `baostock登录: 0 success` → 黑名单已绕过，可正常跑脚本
- ❌ 若仍报 `10001011` → 该节点 IP 可能也被拉黑（共享 IP，概率较低），**换个节点**再试

#### 等待自动解除

- baostock 官网黑名单页面**每日更新**，理论上限制会随时间解除
- 解除周期不确定（数小时～数天），且**反复尝试登录会刷新/延长封禁**，等待期间请勿运行脚本

## ⚠️ 免责声明

> [!WARNING]
> **免责声明 (Disclaimer)**
>
> 本项目仅供学术研究、量化技术交流及 Python 编程学习使用，**不构成任何投资建议、推荐或买卖依据**。
>
> 股市有风险，投资需谨慎。投资者据此策略及程序操作，风险自担。
>
> 作者及贡献者不对因使用本程序或数据造成的任何直接或间接投资损失承担法律责任。


## 🤝 贡献与支持

欢迎提交 Issue 或 Pull Request 来优化选股因子、提升数据效率或扩充策略功能！如果这个项目对你的量化研究有所帮助，欢迎点个 ⭐ Star 支持一下！

Made with ❤️ for Quant Traders & Developers

