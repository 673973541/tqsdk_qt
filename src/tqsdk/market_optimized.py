from datetime import date
from dataclasses import dataclass
from typing import Optional, Dict, Any
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask, TqKq, TqSim
from tqsdk.ta import MA, ATR
import talib
import numpy as np
import logging
import pandas as pd
import time

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
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


auth = TqAuth("673973541", "Xin940302.")
init_balance = 100000
fixed_pos = 10
risk_ratio = 0.05

timeperiod = 60 * 60
start_dt = date(2025, 1, 1)
end_dt = date(2025, 10, 24)

SYMBOLS = [
    "CZCE.SA",  # yes
    # "CZCE.FG",  # yes
    # "CZCE.MA", # no
    # "DCE.v",
    # "DCE.l",
]


class SimpleOptimizedStrategy:
    def __init__(self, api: TqApi, symbol_base: str, timeperiod: int) -> None:
        self.api: TqApi = api
        self.symbol: Optional[str] = None
        self.symbol_base: str = symbol_base
        self.timeperiod: int = timeperiod
        self.target_pos: Optional[TargetPosTask] = None
        self.klines: Optional[pd.DataFrame] = None

        # 预转换的numpy数组缓存（仅用于避免重复转换）
        self.high_array: Optional[np.ndarray] = None
        self.low_array: Optional[np.ndarray] = None
        self.close_array: Optional[np.ndarray] = None
        self.last_klines_len: int = -1

        self.update_main_contract()

        self.is_buy: bool = False
        self.is_sell: bool = False

        self.entry_price: float = 0.0
        self.stop_loss_price: float = 0.0
        self.take_profit_price: float = 0.0

        self.total_count: int = 0
        self.stop_loss_count: int = 0
        self.take_profit_count: int = 0

        # 主力合约更新控制
        self.bar_count: int = 0
        self.contract_check_interval: int = 100  # 每100个bar检查一次主力合约

    def update_main_contract(self) -> None:
        """更新主力合约"""
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

        # 清空数组缓存
        self.high_array = None
        self.low_array = None
        self.close_array = None
        self.last_klines_len = -1

    def _update_array_cache_if_needed(self) -> None:
        """仅在需要时更新numpy数组缓存"""
        current_len = len(self.klines)
        if self.last_klines_len != current_len:
            self.high_array = self.klines.high.values
            self.low_array = self.klines.low.values
            self.close_array = self.klines.close.values
            self.last_klines_len = current_len

    def get_signals(self) -> TradingSignals:
        """获取交易信号（保持原版逻辑，仅优化数组转换）"""
        # 计算指标（保持原版逻辑）
        ma20 = MA(self.klines, 21)["ma"].tolist()
        ma144 = MA(self.klines, 144)["ma"].tolist()
        atr = ATR(self.klines, 14)["atr"].tolist()

        # 使用缓存的numpy数组
        self._update_array_cache_if_needed()
        wr = talib.WILLR(
            self.high_array, self.low_array, self.close_array, timeperiod=21
        )
        adx = talib.ADX(
            self.high_array, self.low_array, self.close_array, timeperiod=14
        )

        adx_signal = adx[-1] > 25
        # 趋势信号
        ma_buy = ma20[-1] > ma144[-1]
        ma_sell = ma20[-1] < ma144[-1]
        wr_sell = wr[-1] < -70
        wr_buy = wr[-1] > -30

        # 计算止损止盈
        stop_loss = atr[-1] * 4  # n倍ATR止损
        take_profit = atr[-1] * 8  # n倍ATR止盈

        # 使用WR超买超卖 + MA趋势 作为开平仓信号
        long_open = wr_buy and adx_signal and ma_buy
        short_open = wr_sell and adx_signal and ma_sell
        long_exit = wr_sell
        short_exit = wr_buy

        logging.debug(
            f"adx: {adx[-1]}, ma20: {ma20[-1]}, ma144: {ma144[-1]}, wr: {wr[-1]}"
        )
        logging.debug(
            f"long_open: {long_open}, short_open: {short_open}, long_exit: {long_exit}, short_exit: {short_exit}"
        )

        return TradingSignals(
            stop_loss=stop_loss,
            take_profit=take_profit,
            long_open=long_open,
            short_open=short_open,
            long_exit=long_exit,
            short_exit=short_exit,
        )

    def _should_check_main_contract(self) -> bool:
        """控制主力合约检查频率"""
        self.bar_count += 1
        if self.bar_count >= self.contract_check_interval:
            self.bar_count = 0
            return True
        return False

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
                    else position_size(self.api, self.klines, self.symbol)
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
                        else position_size(self.api, self.klines, self.symbol)
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
                if self._should_check_main_contract():
                    self.update_main_contract()
            # 止盈
            elif current_price >= self.take_profit_price:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                self.take_profit_count += 1
                logging.info(f"{self.symbol} 多单止盈：价格={current_price:.2f}")
                if self._should_check_main_contract():
                    self.update_main_contract()
            # 信号平仓
            elif signals.long_exit:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                logging.info(f"{self.symbol} 多单信号平仓：价格={current_price:.2f}")
                if self._should_check_main_contract():
                    self.update_main_contract()

        # 持空仓时
        elif self.is_sell:
            # 止损
            if current_price >= self.stop_loss_price:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                self.stop_loss_count += 1
                logging.info(f"{self.symbol} 空单止损：价格={current_price:.2f}")
                if self._should_check_main_contract():
                    self.update_main_contract()
            # 止盈
            elif current_price <= self.take_profit_price:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                self.take_profit_count += 1
                logging.info(f"{self.symbol} 空单止盈：价格={current_price:.2f}")
                if self._should_check_main_contract():
                    self.update_main_contract()
            # 信号平仓
            elif signals.short_exit:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                logging.info(f"{self.symbol} 空单信号平仓：价格={current_price:.2f}")
                if self._should_check_main_contract():
                    self.update_main_contract()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "total_count": self.total_count,
            "stop_loss_count": self.stop_loss_count,
            "take_profit_count": self.take_profit_count,
        }


# 计算开仓手数（保持原版逻辑）
def position_size(api: TqApi, klines: pd.DataFrame, symbol: str) -> int:
    atr = ATR(klines, 21)["atr"].tolist()[-1]
    # 设置ATR的最小值，防止除以0或极小值
    MIN_ATR = 0.001
    atr = max(atr, MIN_ATR)

    account = api.get_account()
    balance = account.balance / len(SYMBOLS)
    current_price = klines.close.iloc[-1]

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
    parts = symbol.split(".")
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


def test() -> None:
    start_time = time.time()
    try:
        api = TqApi(
            TqSim(init_balance),
            web_gui="127.0.0.1:8080",
            backtest=TqBacktest(start_dt, end_dt),
            auth=auth,
        )

        # 创建多个品种的简单优化策略实例
        strategies: list[SimpleOptimizedStrategy] = []
        for symbol in SYMBOLS:
            strategies.append(SimpleOptimizedStrategy(api, symbol, timeperiod))

        while True:
            api.wait_update()

            # 遍历每个品种执行策略
            for strategy in strategies:
                strategy.on_bar()

    except Exception as e:
        logging.error(f"发生错误: {e}", exc_info=True)
    finally:
        if "api" in locals() and api is not None:
            # 打印账户最终状态
            account = api.get_account()
            logging.info(
                f"回测结束 - 最终余额: {account.balance:.2f}, 收益: {account.balance - init_balance:.2f}"
            )
            api.close()
        # 打印每个品种的统计信息
        if "strategies" in locals():
            for strategy in strategies:
                stats = strategy.get_stats()
                logging.info(
                    f"{stats['symbol']} 统计: 总交易次数: {stats['total_count']}, "
                    f"止损次数: {stats['stop_loss_count']}, 止盈次数: {stats['take_profit_count']}"
                )
        logging.info(f"总耗时: {time.time() - start_time:.2f} 秒")


def trader() -> None:
    api = TqApi(
        TqKq(),
        auth=auth,
    )
    logging.info(f"账户余额: {api.get_account().balance}")

    # 创建多个品种的简单优化策略实例
    strategies: list[SimpleOptimizedStrategy] = []
    for symbol in SYMBOLS:
        strategies.append(SimpleOptimizedStrategy(api, symbol, timeperiod))

    while True:
        api.wait_update()
        # 遍历每个品种执行策略
        for strategy in strategies:
            strategy.on_bar()


def main() -> None:
    test()
    # trader()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()
