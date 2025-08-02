from tqsdk import TqApi, TqAuth, TqKq
import logging
import time
import signal
import sys
from strategy import Strategy
from config import (
    timeperiod,
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


def trader() -> None:
    """交易函数"""
    global graceful_exit

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 创建API连接
        api = TqApi(
            TqKq(),
            auth=auth,
        )
        logging.info(f"API连接已建立,账户余额: {api.get_account().balance}")
        strategies: list[Strategy] = []
        # 创建多个品种的策略实例
        for symbol in SYMBOLS:
            strategies.append(Strategy(api, symbol, timeperiod))

        logging.info(f"已创建 {len(strategies)} 个策略实例")

        # 交易主循环
        while not graceful_exit:
            api.wait_update(deadline=time.time() + 5)

            # 遍历每个品种执行策略
            for strategy in strategies:
                strategy.on_bar()

    except Exception as e:
        logging.error(f"程序发生错误: {e}", exc_info=True)
    finally:
        # 在这里安全地关闭API连接
        if api is not None:
            logging.info("正在关闭API连接...")
            api.close()
            logging.info("API连接已关闭")


def main() -> None:
    """主函数"""
    logging.info("=== 程序启动 ===")
    trader()  # 实盘交易


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "file":
        log_to_file = True
    else:
        log_to_file = False
    logging_setup(log_to_file)
    main()
