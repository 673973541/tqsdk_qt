# TqSDK 量化交易库深度理解指南

## 库概述

**TqSDK** 是由信易科技开发的Python量化交易库，专为期货、期权、股票量化交易设计。它提供从历史数据、实时数据、策略开发、回测、模拟交易到实盘交易的完整解决方案。

- **最新版本**: 3.8.3
- **Python要求**: >= 3.7  
- **开发商**: 信易科技 (Shinny Tech)
- **安装方式**: `pip install tqsdk`
- **开源协议**: Apache License 2.0

## 核心架构设计

### 系统架构
```
行情网关 ←→ TqSDK ←→ 交易中继网关
    ↑        ↓         ↑
实时数据   策略程序    期货公司
历史数据              交易系统
```

### 设计模式
1. **事件驱动架构**: 通过 `wait_update()` 驱动所有数据更新
2. **策略模式**: 多种账户实现统一接口（实盘/模拟/回测）
3. **实体框架模式**: 业务对象自动更新，实时响应数据变化
4. **异步编程**: 完整的 asyncio 支持

## 核心导入和模块组织

### 主要导入类
```python
from tqsdk import (
    # 核心类
    TqApi,                    # 主API接口
    TqAuth,                   # 认证类
    TqChan,                   # 通道类
    
    # 账户类型
    TqAccount,                # 实盘期货账户
    TqSim, TqSimStock,       # 模拟账户
    TqKq, TqKqStock,         # 快期账户
    TqZq,                    # 众期账户
    TqCtp,                   # CTP直连
    TqRohon, TqJees, TqYida, # 其他账户类型
    TqTradingUnit,           # 交易单元
    TqMultiAccount,          # 多账户管理
    
    # 回测和重放
    TqBacktest, TqReplay,    # 回测和重放
    
    # 工具类  
    TargetPosScheduler,      # 仓位调度器
    TargetPosTask,           # 目标仓位任务
    InsertOrderTask,         # 订单插入任务
    InsertOrderUntilAllTradedTask,  # 持续下单任务
    TqNotify,                # 通知系统
    
    # 异常类
    BacktestFinished,        # 回测完成异常
    TqBacktestPermissionError, # 回测权限异常
    TqTimeoutError,          # 超时异常
    TqRiskRuleError,         # 风控异常
)
```

### 库内部结构理解
- **api.py**: 核心TqApi类，所有功能的统一入口
- **auth.py**: 身份认证和权限管理
- **objs.py**: 数据对象定义（Quote, Order, Position等）
- **tradeable/**: 各种交易账户的实现
- **backtest/**: 历史回测功能
- **lib/**: 高级工具和任务管理
- **ta.py**: 技术分析指标库

## 核心模块详解

### 1. TqApi - 核心接口类

**主要职责**:
- 统一的数据和交易接口
- 网络连接管理  
- 内存数据库维护
- 事件循环驱动

**关键方法**:
```python
class TqApi:
    # 构造函数
    def __init__(self, account=None, auth=None, backtest=None, web_gui=False)
    
    # 行情数据
    def get_quote(self, symbol: str) -> Quote
    def get_kline_serial(self, symbol: str, duration_seconds: int) -> pd.DataFrame
    def get_tick_serial(self, symbol: str) -> pd.DataFrame
    
    # 交易操作
    def insert_order(self, symbol: str, direction: str, offset: str, volume: int) -> Order
    def cancel_order(self, order_or_order_id: Union[str, Order]) -> None
    
    # 账户信息
    def get_account(self) -> Union[Account, SecurityAccount]
    def get_position(self, symbol: str = None) -> Union[Position, Entity]
    
    # 核心事件循环
    def wait_update(self, deadline=None) -> bool
    def is_changing(self, obj, keys=None) -> bool
```

### 2. 交易账户体系

**接口设计**:
- `IFuture`: 期货交易接口
- `IStock`: 股票交易接口

**账户类型**:
- **实盘账户**: TqAccount, TqCtp, TqKq, TqZq, TqRohon, TqJees, TqYida
- **模拟账户**: TqSim, TqSimStock
- **多账户**: TqMultiAccount

### 3. 数据对象模型

**行情数据**:
- `Quote`: 实时行情（5档深度，包含买卖价格、成交价、成交量等）
- `Kline`: K线数据（OHLCV格式）
- `Tick`: 逐笔成交数据

**交易数据**:
- `Account`: 账户资金信息（余额、可用资金、浮动盈亏等）
- `Position`: 持仓信息（多空持仓、今昨仓等）
- `Order`: 委托订单（订单状态、价格、数量等）
- `Trade`: 成交记录（成交价格、数量、时间等）

### 4. 目标仓位管理 - TargetPosTask

```python
class TargetPosTask:
    def __init__(self, api, symbol, price="ACTIVE", 
                 offset_priority="今昨,开", account=None)
    
    def set_target_volume(self, volume: int) -> None  # 设置目标仓位
    def cancel(self) -> None                         # 取消任务
    def is_finished(self) -> bool                    # 检查是否完成
```

**核心特性**:
- 自动调仓到目标位置（无需手动计算开平仓）
- 智能价格跟踪（支持对价、排队、限价等策略）
- 大单拆分执行（避免冲击成本）
- 支持复杂的开平仓优先级（今昨仓控制）

### 5. 技术分析模块

**主要指标分类**:
- **趋势类**: MA, EMA, BOLL, DMI, MACD
- **震荡类**: RSI, KDJ, WR, CCI, ROC
- **成交量**: OBV, VR, AD, MFI
- **其他**: ATR, BIAS, TRIX, SAR

```python
from tqsdk.ta import MA, ATR, RSI, BOLL
# 所有指标都返回pandas DataFrame，可直接用于策略计算
```

### 6. 回测系统

```python
# 回测配置示例
from datetime import date
api = TqApi(
    TqSim(init_balance=100000),          # 模拟账户
    backtest=TqBacktest(                 # 回测参数
        start_dt=date(2023, 1, 1), 
        end_dt=date(2023, 12, 31)
    ),
    auth=TqAuth("user", "pass")          # 认证信息
)
```

**回测特性**:
- 支持Tick级和K线级回测
- 真实的撮合机制模拟
- 完整的交易费用计算
- 自动生成回测报告

## 核心开发模式

### 1. 事件驱动策略开发

```python
from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask

# 初始化
api = TqApi(TqSim(), auth=TqAuth("user", "pass"))
quote = api.get_quote("SHFE.rb2309")
target_pos = TargetPosTask(api, "SHFE.rb2309")

# 主循环
while True:
    api.wait_update()
    
    # 只在价格变化时执行逻辑
    if api.is_changing(quote, "last_price"):
        if quote.last_price > some_threshold:
            target_pos.set_target_volume(1)  # 做多1手
        else:
            target_pos.set_target_volume(0)  # 平仓
```

### 2. 多品种策略

```python
symbols = ["SHFE.rb2309", "DCE.m2309", "CZCE.MA309"]
quotes = {symbol: api.get_quote(symbol) for symbol in symbols}
target_positions = {symbol: TargetPosTask(api, symbol) for symbol in symbols}

while True:
    api.wait_update()
    
    for symbol in symbols:
        if api.is_changing(quotes[symbol]):
            # 为每个品种执行独立策略逻辑
            strategy_logic(symbol, quotes[symbol], target_positions[symbol])
```

### 3. 技术指标使用

```python
from tqsdk.ta import MA, ATR, RSI

# 获取K线数据
klines = api.get_kline_serial("SHFE.rb2309", 60)  # 1分钟K线

# 计算技术指标
ma20 = MA(klines, 20)["ma"]
atr = ATR(klines, 14)["atr"] 
rsi = RSI(klines, 14)["rsi"]

# 策略逻辑
if rsi.iloc[-1] < 30 and quote.last_price > ma20.iloc[-1]:
    target_pos.set_target_volume(1)  # RSI超卖且价格在均线上方：做多
```

## 实际应用场景

### 1. 日内高频策略

```python
# 适用于需要快速响应的日内策略
class HighFrequencyStrategy:
    def __init__(self, api, symbol):
        self.api = api
        self.quote = api.get_quote(symbol)
        self.target_pos = TargetPosTask(api, symbol)
        
    def on_tick(self):
        if self.api.is_changing(self.quote, "last_price"):
            # 毫秒级响应的策略逻辑
            self.execute_strategy()
```

### 2. 多时间框架分析

```python
# 结合多个时间周期的分析
klines_1m = api.get_kline_serial("SHFE.rb2309", 60)      # 1分钟
klines_5m = api.get_kline_serial("SHFE.rb2309", 300)     # 5分钟  
klines_1h = api.get_kline_serial("SHFE.rb2309", 3600)    # 1小时

# 多时间框架技术分析
def multi_timeframe_analysis():
    trend_1h = MA(klines_1h, 20)["ma"].iloc[-1]  # 小时级趋势
    signal_5m = RSI(klines_5m, 14)["rsi"].iloc[-1]  # 5分钟信号
    entry_1m = quote.last_price  # 1分钟入场
```

### 3. 跨品种套利

```python
# 螺纹钢-热卷价差套利示例
rb_quote = api.get_quote("SHFE.rb2309")  # 螺纹钢
hc_quote = api.get_quote("SHFE.hc2309")  # 热卷
rb_pos = TargetPosTask(api, "SHFE.rb2309")
hc_pos = TargetPosTask(api, "SHFE.hc2309") 

while True:
    api.wait_update()
    spread = rb_quote.last_price - hc_quote.last_price
    
    if spread > 500:  # 价差过高
        rb_pos.set_target_volume(-1)  # 空螺纹钢
        hc_pos.set_target_volume(1)   # 多热卷
    elif spread < 200:  # 价差回归
        rb_pos.set_target_volume(0)   # 平仓
        hc_pos.set_target_volume(0)
```

## 重要配置和最佳实践

### 1. 认证和连接

```python
# 生产环境认证
auth = TqAuth("tianqin_user", "password")

# 实盘交易
api = TqApi(
    TqAccount("期货公司", "账户", "密码"),
    auth=auth
)

# 回测
api = TqApi(
    TqSim(init_balance=100000),
    backtest=TqBacktest(start_dt, end_dt),
    auth=auth
)
```

### 2. 风险管理

```python
# 仓位大小计算
def calculate_position_size(api, symbol, risk_ratio=0.02):
    account = api.get_account()
    klines = api.get_kline_serial(symbol, 3600)
    atr = ATR(klines, 14)["atr"].iloc[-1]
    
    risk_amount = account.balance * risk_ratio
    price_per_tick = 10  # 根据品种调整
    stop_loss_ticks = atr * 2 / price_per_tick
    
    position_size = risk_amount / (stop_loss_ticks * price_per_tick)
    return int(position_size)
```

### 3. 日志和监控

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strategy.log'),
        logging.StreamHandler()
    ]
)

# 在策略中使用
logger = logging.getLogger(__name__)
logger.info(f"开仓: {symbol} 价格: {price} 手数: {volume}")
```

## 性能优化建议

### 1. 数据订阅优化
- 只订阅需要的合约
- 合理设置K线数据长度
- 避免频繁的数据查询

### 2. 策略逻辑优化
- 使用 `is_changing()` 避免不必要的计算
- 缓存计算结果
- 合理使用pandas操作

### 3. 网络和连接优化
- 选择合适的服务器地址
- 配置合理的超时设置
- 使用连接池管理

## 常见问题和解决方案

### 1. 数据延迟问题
- 检查网络连接
- 确认服务器地址
- 优化策略逻辑减少计算时间

### 2. 回测准确性
- 使用Tick级回测获得更高精度
- 考虑滑点和手续费
- 验证历史数据质量

### 3. 实盘交易差异
- 模拟交易与实盘的撮合差异
- 网络延迟和滑点影响
- 资金和风控限制

## 扩展开发

### 1. 自定义指标
```python
def custom_indicator(klines, period=20):
    """自定义技术指标"""
    close = klines.close
    return close.rolling(period).mean()  # 简单移动平均
```

### 2. 事件通知
```python
from tqsdk.lib import TqNotify

notify = TqNotify(api)
notify.send_message("策略信号", f"开仓 {symbol}")
```

### 3. 数据导出
```python
# 导出回测结果
klines.to_csv("backtest_data.csv")
trades = api.get_trade()  # 获取所有交易记录
```

## 依赖库说明

**核心依赖**:
- `websockets>=8.1`: WebSocket通信
- `pandas>=1.1.0`: 数据处理
- `numpy`: 数值计算
- `aiohttp`: 异步HTTP客户端
- `requests`: HTTP请求
- `psutil>=5.9.6`: 系统资源监控

**专用依赖**:
- `tqsdk_ctpse`: CTP交易接口
- `tqsdk_sm`: 加密模块
- `shinny_structlog`: 结构化日志
- `sgqlc`: GraphQL客户端

## 开发建议

1. **从基础开始**: 先熟悉基本的行情订阅和事件循环机制
2. **渐进式开发**: 从简单策略开始，逐步增加复杂度
3. **充分测试**: 先模拟交易，再实盘运行
4. **风险控制**: 始终设置止损和仓位管理
5. **持续监控**: 实盘运行时保持监控和日志记录

## 总结

TqSDK是一个功能完整、设计良好的量化交易库，通过事件驱动架构和统一的API接口，为量化交易提供了从数据获取到策略执行的完整解决方案。其核心特点是：

- **统一接口**: 一套API同时支持实盘、模拟、回测
- **事件驱动**: 高效的数据更新和策略执行机制  
- **专业工具**: TargetPosTask等高级工具简化策略开发
- **完整生态**: 从数据、指标到交易的全套功能

理解这些核心概念和使用模式，就能快速上手并构建出稳定可靠的量化交易策略。