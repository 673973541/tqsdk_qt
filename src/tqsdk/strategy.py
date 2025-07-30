from tqsdk import TqApi,TargetPosTask
import talib
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging
import pandas as pd
from config import (
    fixed_pos, risk_ratio, ma_short_period, ma_long_period,
    atr_period, adx_period, stop_loss_atr_multiplier,
    take_profit_ratio
)


@dataclass
class TradingSignals:
    """交易信号结构体"""

    stop_loss: float
    take_profit: float
    long_open: bool
    short_open: bool
    long_exit: bool
    short_exit: bool

class Strategy:
    def __init__(self, api: TqApi, symbol_base: str, timeperiod: int) -> None:
        self.api: TqApi = api
        self.symbol: Optional[str] = None
        self.symbol_base: str = symbol_base
        self.timeperiod: int = timeperiod
        self.target_pos: Optional[TargetPosTask] = None
        self.klines: Optional[pd.DataFrame] = None

        self.update_main_contract()

        self.is_buy: bool = False
        self.is_sell: bool = False

        self.entry_price: float = 0.0
        self.stop_loss_price: float = 0.0
        self.take_profit_price: float = 0.0

        self.total_count: int = 0
        self.stop_loss_count: int = 0
        self.take_profit_count: int = 0

    def update_main_contract(self) -> None:
        """更新主力合约"""
        # 判断是否为期权合约（包含-C-或-P-）
        if "-C-" in self.symbol_base or "-P-" in self.symbol_base:
            # 期权合约直接使用指定的合约，不查询主力合约
            if self.symbol is None:
                self.symbol = self.symbol_base
                self.klines = self.api.get_kline_serial(self.symbol, self.timeperiod)
                self.target_pos = TargetPosTask(self.api, self.symbol)
                logging.info(f"使用期权合约: {self.symbol}")
            return
        
        # 期货合约查询主力合约
        exchange = self.symbol_base.split(".")[0]
        product = self.symbol_base.split(".")[1]
        main_symbols = self.api.query_cont_quotes(
            exchange_id=exchange,
            product_id=product,
        )
        main_symbol = main_symbols[0]
        if main_symbol == self.symbol:
            return

        logging.info(f"{self.symbol_base} 更新主力合约: {main_symbol}")

        # 更新行情订阅
        self.symbol = main_symbol
        self.klines = self.api.get_kline_serial(main_symbol, self.timeperiod)
        self.target_pos = TargetPosTask(self.api, main_symbol)

    def get_signals(self) -> TradingSignals:
        # 数据转换
        high = self.klines.high.values
        low = self.klines.low.values
        close = self.klines.close.values
        
        # 使用配置文件中的参数计算指标
        ma_short = talib.SMA(close, timeperiod=ma_short_period)[-1]
        ma_long = talib.SMA(close, timeperiod=ma_long_period)[-1]
        atr = talib.ATR(high, low, close, timeperiod=atr_period)[-1]
        wr = talib.WILLR(high, low, close, timeperiod=ma_short_period)[-1]
        adx = talib.ADX(high, low, close, timeperiod=adx_period)[-1]
        
        # 信号判断
        adx_signal = adx > 25
        ma_buy = ma_short > ma_long
        ma_sell = ma_short < ma_long
        wr_sell = wr < -70
        wr_buy = wr > -30

        # 使用配置文件中的参数计算止损止盈
        stop_loss = atr * stop_loss_atr_multiplier
        take_profit = atr * stop_loss_atr_multiplier * take_profit_ratio

        # 信号逻辑
        long_open = wr_buy and adx_signal and ma_buy
        short_open = wr_sell and adx_signal and ma_sell
        long_exit = wr_sell
        short_exit = wr_buy
        # logging.debug(
        #     f"adx: {adx}, ma20: {ma20}, ma144: {ma144}, wr: {wr}"
        # )
        # logging.debug(
        #     f"long_open: {long_open}, short_open: {short_open}, long_exit: {long_exit}, short_exit: {short_exit}"
        # )
        return TradingSignals(
            stop_loss=stop_loss,
            take_profit=take_profit,
            long_open=long_open,
            short_open=short_open,
            long_exit=long_exit,
            short_exit=short_exit,
        )

    def on_bar(self) -> None:
        if not self.api.is_changing(self.klines):
            return

        signals = self.get_signals()
        current_price = self.klines.close.iloc[-1]

        # 空仓时判断开仓
        if not self.is_buy and not self.is_sell:
            # 开多信号
            if signals.long_open:
                self.target_pos.set_target_volume(
                    fixed_pos
                    if fixed_pos
                    else self.position_size()
                )
                self.is_buy = True
                self.entry_price = current_price
                self.stop_loss_price = self.entry_price - signals.stop_loss
                self.take_profit_price = self.entry_price + signals.take_profit
                self.total_count += 1
                logging.info(
                    f"{self.symbol} 开多：价格={self.entry_price:.2f}, 止损={self.stop_loss_price:.2f}, 止盈={self.take_profit_price:.2f}"
                )

            # 开空信号
            elif signals.short_open:
                self.target_pos.set_target_volume(
                    -1
                    * (
                        fixed_pos
                        if fixed_pos
                        else self.position_size()
                    )
                )
                self.is_sell = True
                self.entry_price = current_price
                self.stop_loss_price = self.entry_price + signals.stop_loss
                self.take_profit_price = self.entry_price - signals.take_profit
                self.total_count += 1
                logging.info(
                    f"{self.symbol} 开空：价格={self.entry_price:.2f}, 止损={self.stop_loss_price:.2f}, 止盈={self.take_profit_price:.2f}"
                )

        # 持多仓时
        elif self.is_buy:
            # 止损
            if current_price <= self.stop_loss_price:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                self.stop_loss_count += 1
                logging.info(f"{self.symbol} 多单止损：价格={current_price:.2f}")
                self.update_main_contract()
            # 止盈
            elif current_price >= self.take_profit_price:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                self.take_profit_count += 1
                logging.info(f"{self.symbol} 多单止盈：价格={current_price:.2f}")
                self.update_main_contract()
            # 信号平仓
            elif signals.long_exit:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                logging.info(f"{self.symbol} 多单信号平仓：价格={current_price:.2f}")
                self.update_main_contract()

        # 持空仓时
        elif self.is_sell:
            # 止损
            if current_price >= self.stop_loss_price:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                self.stop_loss_count += 1
                logging.info(f"{self.symbol} 空单止损：价格={current_price:.2f}")
                self.update_main_contract()
            # 止盈
            elif current_price <= self.take_profit_price:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                self.take_profit_count += 1
                logging.info(f"{self.symbol} 空单止盈：价格={current_price:.2f}")
                self.update_main_contract()
            # 信号平仓
            elif signals.short_exit:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                logging.info(f"{self.symbol} 空单信号平仓：价格={current_price:.2f}")
                self.update_main_contract()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "total_count": self.total_count,
            "stop_loss_count": self.stop_loss_count,
            "take_profit_count": self.take_profit_count,
        }
    # 计算开仓手数
    def position_size(self) -> int:
        # 期权合约
        if "-C-" in parts[1] or "-P-" in parts[1]:
            return 1  # 期权合约通常最小开仓1手
        

        # 使用TA-Lib计算ATR，性能更好
        close = self.klines.close.values
        high = self.klines.high.values
        low = self.klines.low.values
        atr = talib.ATR(high, low, close, timeperiod=atr_period)[-1]
        # 设置ATR的最小值，防止除以0或极小值
        MIN_ATR = 0.001
        atr = max(atr, MIN_ATR)

        account = self.api.get_account()
        balance = account.balance
        current_price = self.klines.close.iloc[-1]

        # 合约规格配置
        contract_config = {
            "SHFE.rb": {  # 螺纹钢
                "price_unit": 10,  # 每点价格变动对应的资金变动
                "min_volume": 1,  # 最小交易量
            },
            "SHFE.hc": {
                "price_unit": 10,  # 每点价格变动对应的资金变动
                "min_volume": 1,  # 最小交易量
            },
            "DCE.m": {  # 豆粕
                "price_unit": 10,
                "min_volume": 1,
            },
            "CZCE.FG": {  # 玻璃
                "price_unit": 20,
                "min_volume": 1,
            },
            "CZCE.SA": {  # 纯碱
                "price_unit": 20,
                "min_volume": 1,
            },
            "DCE.c": {  # 玉米
                "price_unit": 10,
                "min_volume": 1,
            },
        }

        # 提取合约基础代码
        parts = self.symbol.split(".")
        import re

        symbol_letters = re.match(r"([A-Za-z]+)", parts[1]).group()
        symbol_base = f"{parts[0]}.{symbol_letters}"
        config = contract_config.get(symbol_base)

        if not config:
            raise ValueError(f"未找到合约 {symbol_base} 的配置信息")

        # 使用固定保守的保证金比例 15%
        MARGIN_RATIO = 0.15

        # 风险金额为账户的1%
        risk_amount = balance * risk_ratio

        # 计算每手所需保证金
        margin_per_lot = current_price * config["price_unit"] * MARGIN_RATIO

        # 计算止损点数（以价格为单位）
        stop_loss_points = atr * 6

        # 计算每手止损金额
        loss_per_lot = stop_loss_points * config["price_unit"]

        # 计算可开仓位
        position = min(
            risk_amount / loss_per_lot,  # 基于风险计算的仓位
            (balance * 0.8) / margin_per_lot,  # 基于保证金计算的仓位（留20%余量）
        )
        logging.info(
            f"基于风险计算的仓位: {risk_amount / loss_per_lot}, 是否小于基于保证金计算的仓位: {risk_amount / loss_per_lot < (balance * 0.8) / margin_per_lot}"
        )
        return max(config["min_volume"], round(position))  # 至少开1手