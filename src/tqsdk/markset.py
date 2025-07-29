from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask, TqSim
from tqsdk.ta import MA, ATR, WR, DMI
import talib
import numpy as np


auth = TqAuth("673973541", "Xin940302.")
init_balance = 100000
fixed_pos = 1
risk_ratio = 0.05

timeperiod = 60 * 60
start_dt = date(2025, 1, 1)
end_dt = date(2025, 10, 24)

# SYMBOLS = ["DCE.m", "SHFE.rb"]
# SYMBOLS = ["SHFE.rb"]
# SYMBOLS = ["DCE.c"]
SYMBOLS = [
    "CZCE.SA",  # yes
    "CZCE.FG",  # yes
    #     # "CZCE.MA", # no
    #     "DCE.v",
]


class Strategy:
    def __init__(self, api: TqApi, symbol_base: str, timeperiod: int):
        self.api = api
        self.symbol = None
        self.symbol_base = symbol_base
        self.timeperiod = timeperiod
        self.target_pos = None
        self.klines = None

        self.update_main_contract()

        self.is_buy = False
        self.is_sell = False

        self.entry_price = 0
        self.stop_loss_price = 0
        self.take_profit_price = 0

        self.total_count = 0
        self.stop_loss_count = 0
        self.take_profit_count = 0

    def update_main_contract(self):
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

        print(f"{self.symbol_base} 更新主力合约: {main_symbol}")

        # 更新行情订阅
        self.symbol = main_symbol
        self.klines = self.api.get_kline_serial(main_symbol, self.timeperiod)
        self.target_pos = TargetPosTask(self.api, main_symbol)

    def get_signals(self):
        # 计算指标
        ma20 = MA(self.klines, 21)["ma"].tolist()
        ma144 = MA(self.klines, 144)["ma"].tolist()
        atr = ATR(self.klines, 14)["atr"].tolist()

        high = np.array(self.klines.high)
        low = np.array(self.klines.low)
        close = np.array(self.klines.close)
        wr = talib.WILLR(high, low, close, timeperiod=21)
        adx = talib.ADX(high, low, close, timeperiod=14)

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

        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "long_open": long_open,
            "short_open": short_open,
            "long_exit": long_exit,
            "short_exit": short_exit,
        }

    def on_bar(self):
        if not self.api.is_changing(self.klines):
            return

        signals = self.get_signals()
        current_price = self.klines.close.iloc[-1]

        # 空仓时判断开仓
        if not self.is_buy and not self.is_sell:
            # 开多信号
            if signals["long_open"]:
                self.target_pos.set_target_volume(
                    fixed_pos
                    if fixed_pos
                    else position_size(self.api, self.klines, self.symbol)
                )
                self.is_buy = True
                self.entry_price = current_price
                self.stop_loss_price = self.entry_price - signals["stop_loss"]
                self.take_profit_price = self.entry_price + signals["take_profit"]
                self.total_count += 1
                print(
                    f"{self.symbol} 开多：价格={self.entry_price:.2f}, 止损={self.stop_loss_price:.2f}, 止盈={self.take_profit_price:.2f}"
                )

            # 开空信号
            elif signals["short_open"]:
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
                self.stop_loss_price = self.entry_price + signals["stop_loss"]
                self.take_profit_price = self.entry_price - signals["take_profit"]
                self.total_count += 1
                print(
                    f"{self.symbol} 开空：价格={self.entry_price:.2f}, 止损={self.stop_loss_price:.2f}, 止盈={self.take_profit_price:.2f}"
                )

        # 持多仓时
        elif self.is_buy:
            # 止损
            if current_price <= self.stop_loss_price:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                self.stop_loss_count += 1
                print(f"{self.symbol} 多单止损：价格={current_price:.2f}")
                self.update_main_contract()
            # 止盈
            elif current_price >= self.take_profit_price:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                self.take_profit_count += 1
                print(f"{self.symbol} 多单止盈：价格={current_price:.2f}")
                self.update_main_contract()
            # 信号平仓
            elif signals["long_exit"]:
                self.target_pos.set_target_volume(0)
                self.is_buy = False
                print(f"{self.symbol} 多单信号平仓：价格={current_price:.2f}")
                self.update_main_contract()

        # 持空仓时
        elif self.is_sell:
            # 止损
            if current_price >= self.stop_loss_price:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                self.stop_loss_count += 1
                print(f"{self.symbol} 空单止损：价格={current_price:.2f}")
                self.update_main_contract()
            # 止盈
            elif current_price <= self.take_profit_price:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                self.take_profit_count += 1
                print(f"{self.symbol} 空单止盈：价格={current_price:.2f}")
                self.update_main_contract()
            # 信号平仓
            elif signals["short_exit"]:
                self.target_pos.set_target_volume(0)
                self.is_sell = False
                print(f"{self.symbol} 空单信号平仓：价格={current_price:.2f}")
                self.update_main_contract()

    def get_stats(self):
        return {
            "symbol": self.symbol,
            "total_count": self.total_count,
            "stop_loss_count": self.stop_loss_count,
            "take_profit_count": self.take_profit_count,
        }


# 计算开仓手数
def position_size(api, klines, symbol):
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
    print(
        risk_amount / loss_per_lot,
        risk_amount / loss_per_lot < (balance * 0.8) / margin_per_lot,
    )
    return max(config["min_volume"], round(position))  # 至少开1手


def test():
    try:
        api = TqApi(
            TqSim(init_balance),
            web_gui="127.0.0.1:8080",
            backtest=TqBacktest(start_dt, end_dt),
            auth=auth,
        )

        # 创建多个品种的策略实例
        strategies = []
        for symbol in SYMBOLS:
            strategies.append(Strategy(api, symbol, timeperiod))

        while True:
            api.wait_update()

            # 遍历每个品种执行策略
            for strategy in strategies:
                strategy.on_bar()

    except Exception as e:
        print("error:", e)
    finally:
        api.close()
        # 打印每个品种的统计信息
        for strategy in strategies:
            stats = strategy.get_stats()
            print(
                f"\n{stats['symbol']} 统计:",
                f"总交易次数: {stats['total_count']},",
                f"止损次数: {stats['stop_loss_count']},",
                f"止盈次数: {stats['take_profit_count']}",
            )


def main():
    test()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()
