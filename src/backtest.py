from tqsdk import TqApi, TqAuth, TqBacktest, TqSim
from tqsdk.exceptions import BacktestFinished
import logging
import time
import signal
import sys
from strategy import Strategy
from config import (
    timeperiod,
    start_dt,
    end_dt,
    sim_init_balance,
    symbols_list,
    log_level,
    tq_user,
    tq_password,
    log_filename,
)


def logging_setup(log_to_file: bool) -> None:
    """设置日志记录"""
    if log_to_file:
        # 输出到文件
        logging.basicConfig(
            filename=log_filename,
            level=getattr(logging, log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        print(f"日志将输出到文件: {log_filename}")
    else:
        # 输出到控制台
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        print("日志将输出到控制台")


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


def backtest() -> None:
    global graceful_exit
    start_time = time.time()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

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
        while graceful_exit is False:
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
    finally:
        api.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "file":
        log_to_file = True
    else:
        log_to_file = False
    logging_setup(log_to_file)
    logging.info("=== 回测程序启动 ===")
    backtest()  # 启动回测
    logging.info("=== 回测程序结束 ===")
