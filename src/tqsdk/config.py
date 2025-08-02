#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TqSDK 量化交易策略配置文件
包含策略运行的各种参数设置
"""

from datetime import date

# ==================== 时间配置 ====================
# K线周期设置 (秒)
timeperiod = 30 * 60

# 回测时间范围
start_dt = date(2025, 4, 1)  # 回测开始日期
end_dt = date(2025, 10, 24)  # 回测结束日期

# ==================== 交易配置 ====================
# 固定仓位数量 (手)
fixed_pos = 5  # 固定持仓n手, 0表示不使用固定仓位

# 风险比例 (账户资金的百分比)
risk_ratio = 0.05  # 单笔交易风险不超过账户资金的5%

# ==================== 技术指标配置 ====================
# 移动平均线周期
ma_short_period = 55  # 短期均线周期
ma_long_period = 144  # 长期均线周期

# RSI指标配置
rsi_period = 21  # RSI计算周期
rsi_oversold = -70  # RSI超卖阈值
rsi_overbought = -30  # RSI超买阈值

# ATR指标配置
atr_period = 21  # ATR计算周期

# ADX指标配置
adx_period = 21  # ADX计算周期
adx_threshold = 25  # ADX趋势强度阈值

# ==================== 交易信号配置 ====================
# 止损设置
stop_loss_atr_multiplier = 3.0  # 止损ATR倍数
take_profit_ratio = 2.0  # 止盈止损比例

# ==================== 账户配置 ====================
# 模拟账户初始资金
sim_init_balance = 100000  # 模拟账户初始资金10万

# ==================== 品种配置 ====================
# 品种列表 (多品种策略使用)
symbols_list = [
    # "SHFE.rb",  # 螺纹钢
    # "CZCE.SA",  # yes
    "CZCE.FG",  # yes
    # "CZCE.MA",  # no
    # "DCE.v",
    # "DCE.l",
    # "DCE.m",
    # "DCE.c",
]

# ==================== 系统配置 ====================
# 日志配置
log_level = "INFO"  # 日志级别: DEBUG, INFO, WARNING, ERROR
log_to_file = False  # 是否将日志输出到文件
log_filename = "strategy.log"  # 日志文件名（当log_to_file=True时使用）

# 每日重启时间配置
restart_hour = 8  # 重启小时 (24小时制)
restart_minute = 0  # 重启分钟

# 天勤认证信息
tq_user = "673973541"  # TqAuth 用户名
tq_password = "Xin940302."  # TqAuth 密码
