from datetime import date, datetime, time as dt_time
from tqsdk import TqApi, TqAuth, TqBacktest, TqKq, TqSim
from tqsdk.exceptions import BacktestFinished
import logging
import time
import signal
from strategy import Strategy
from config import (
    timeperiod, start_dt, end_dt, sim_init_balance,
    symbols_list, log_level, tq_user, tq_password,
    restart_hour, restart_minute, log_to_file, log_filename
)

# 配置日志记录
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
        format="%(levelname)s - %(message)s",
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
    """带每日重启功能的交易函数"""
    global graceful_exit
    last_restart_date = None
    
    def should_restart_today():
        """检查今天是否还需要重启"""
        current_date = datetime.now().date()
        current_time = datetime.now().time()
        restart_time = dt_time(restart_hour, restart_minute)  # 使用配置的重启时间
        
        # 如果今天还没重启过，且当前时间已过重启时间
        return (last_restart_date != current_date and 
                current_time >= restart_time)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.info(f"=== 交易程序启动，配置的每日重启时间: {restart_hour:02d}:{restart_minute:02d} ===")
    
    while not graceful_exit:  # 外层循环：处理每日重启和优雅退出
        api = None
        strategies: list[Strategy] = []
        
        try:
            current_date = datetime.now().date()
            
            # 如果需要重启，更新重启日期
            if should_restart_today():
                last_restart_date = current_date
                logging.info(f"=== {current_date} 每日API重启开始 ({restart_hour:02d}:{restart_minute:02d}) ===")
            
            # 创建API连接
            api = TqApi(
                TqKq(),
                auth=auth,
            )
            logging.info(f"API连接已建立，账户余额: {api.get_account().balance}")

            # 创建多个品种的策略实例
            for symbol in SYMBOLS:
                strategies.append(Strategy(api, symbol, timeperiod))
            
            logging.info(f"已创建 {len(strategies)} 个策略实例")

            # 交易主循环
            while not graceful_exit:
                # 检查是否到了第二天需要重启的时间
                now = datetime.now()
                if (now.date() != current_date and 
                    now.time() >= dt_time(restart_hour, restart_minute)):
                    logging.info(f"到达新一天的重启时间 ({now.date()} {restart_hour:02d}:{restart_minute:02d})，准备重启API连接...")
                    break
                
                try:
                    api.wait_update(deadline=time.time() + 300)
                    
                    # 遍历每个品种执行策略
                    for strategy in strategies:
                        strategy.on_bar()
                        
                except Exception as e:
                    logging.error(f"策略执行过程中发生错误: {e}", exc_info=True)
                    time.sleep(5)  # 短暂等待后继续
                    
        except KeyboardInterrupt:
            logging.info("用户中断程序")
            graceful_exit = True
            
        except Exception as e:
            logging.error(f"API连接或初始化错误: {e}", exc_info=True)
            if not graceful_exit:
                logging.info("30秒后重新尝试连接...")
                time.sleep(30)
            
        finally:
            # 清理资源
            if api is not None:
                try:
                    api.close()
                    logging.info("API连接已关闭")
                except Exception as e:
                    logging.warning(f"关闭API时发生错误: {e}")
        
        # 如果不是优雅退出，短暂等待后重新开始循环
        if not graceful_exit:
            logging.info("等待2秒后重新建立连接...")
            time.sleep(2)
            
    logging.info("正在退出交易循环...")

def main() -> None:
    """主函数"""
    logging.info("=== 程序启动 ===")
    logging.info(f"配置的每日重启时间: {restart_hour:02d}:{restart_minute:02d}")
    
    # test()  # 回测功能
    trader()  # 实盘交易（带每日重启功能）


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("程序被用户中断")
    except Exception as e:
        logging.error(f"程序异常退出: {e}", exc_info=True)
    finally:
        logging.info("程序结束")
