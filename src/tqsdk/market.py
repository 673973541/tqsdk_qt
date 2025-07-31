from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest, TqKq, TqSim
from tqsdk.exceptions import BacktestFinished
import logging
import time
import signal
from strategy import Strategy
from config import (
    timeperiod, start_dt, end_dt, sim_init_balance,
    symbols_list, log_level,tq_user, tq_password
)

# 配置日志记录
logging.basicConfig(
    # filename="strategy.log",
    level=getattr(logging, log_level),
    format="%(levelname)s - %(message)s",
)

# 全局变量用于优雅退出
graceful_exit = False

def signal_handler(signum, frame):
    """信号处理函数"""
    global graceful_exit
    logging.info("接收到退出信号，正在优雅关闭...")
    graceful_exit = True

# 初始化TqAuth
auth = TqAuth(tq_user, tq_password)

# 使用配置文件中的品种列表
SYMBOLS = symbols_list


def test() -> None:
    start_time = time.time()
    try:
        api = TqApi(
            TqSim(sim_init_balance),
            # web_gui="127.0.0.1:8080",
            backtest=TqBacktest(start_dt, end_dt),
            auth=auth,
        )

        # 创建多个品种的策略实例
        strategies: list[Strategy] = []
        for symbol in SYMBOLS:
            strategies.append(Strategy(api, symbol, timeperiod))

        while True:
            api.wait_update()

            # 遍历每个品种执行策略
            for strategy in strategies:
                strategy.on_bar()
    except BacktestFinished:
        if "api" in locals() and api is not None:
            # 打印账户最终状态
            account = api.get_account()
            logging.info(
                f"回测结束 - 最终余额: {account.balance:.2f}, 收益: {account.balance - sim_init_balance:.2f}"
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
    except Exception as e:
        logging.error(f"发生错误: {e}", exc_info=True)
        api.close()

def trader() -> None:
    global graceful_exit
    api = None
    try:
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        api = TqApi(
            TqKq(),
            auth=auth,
        )
        logging.info(f"账户余额: {api.get_account().balance}")

        # 创建多个品种的策略实例
        strategies: list[Strategy] = []
        for symbol in SYMBOLS:
            strategies.append(Strategy(api, symbol, timeperiod))

        while not graceful_exit:
            api.wait_update(deadline=time.time() + 300)
            # 遍历每个品种执行策略
            for strategy in strategies:
                strategy.on_bar()
                
        logging.info("正在退出交易循环...")
        
    except KeyboardInterrupt:
        logging.info("用户中断程序")
    except Exception as e:
        logging.error(f"发生错误: {e}", exc_info=True)
    finally:
        if api is not None:
            try:
                api.close()
                logging.info("API连接已关闭")
            except Exception as e:
                logging.warning(f"关闭API时发生错误: {e}")

def main() -> None:
    test()  # 先测试回测功能
    # trader()  # 注释掉实盘交易


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("程序被用户中断")
    except Exception as e:
        logging.error(f"程序异常退出: {e}", exc_info=True)
    finally:
        logging.info("程序结束")
