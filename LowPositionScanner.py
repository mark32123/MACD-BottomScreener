"""
低位扫描工具 - 已整合至 select_tool.py（MACD 抄底选股扫描器）
本文件保留作为工具库扩展入口，核心功能请使用 select_tool.py
"""
from select_tool import calc_macd, check_macd_signal, fetch_one_stock

__all__ = ["calc_macd", "check_macd_signal", "fetch_one_stock"]
