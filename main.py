import io
import time
import csv
import os
import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler
import pyautogui
import cv2
import win32gui, win32con
import ctypes

r'''
pip install pyperclip pyautogui opencv-python pywin32
pywin32_postinstall -install
'''

# 常量定义
DEFAULT_CONFIDENCE = 0.9
DEFAULT_MAX_WAITING = 30  # 默认最大等待时间
LOG_FILE = "sequenceTask.log"
log_path = os.path.join(os.path.dirname(sys.argv[0]), LOG_FILE)

# 支持的操作类型
SUPPORTED_OPERATIONS = {
    "单击",
    "双击",
    "右键",
    "上页",
    "下页",
    "页顶",
    "页底",
    "滚轮",
    "等待目标",
    "无操作",
    "输入",
}

# 设置PyAutoGUI安全措施
pyautogui.FAILSAFE = True  # 将鼠标移到屏幕左上角将中断程序
pyautogui.PAUSE = 0.1  # 操作之间的短暂暂停

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            filename=log_path,
            maxBytes=100 * 1024,
            backupCount=1,
            encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

def minimize_window():
    """最小化当前窗口"""

    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        logging.info("已最小化当前窗口")
    else:
        logging.error("无法获取当前窗口句柄")
        sys.exit(1)


def find_image(sequence_dir: str, image_fileName: str, max_waiting: int):
    """
    尝试在屏幕上定位图像
    返回图像的中心坐标或者None
    """
    # 确保图像路径存在
    image_path = os.path.join(sequence_dir, image_fileName)
    if not os.path.exists(image_path):
        logging.error(f"找不到图像: {image_path}")
        return None

    image = cv2.imread(image_path)

    time_count = 0
    while time_count < max_waiting:
        try:
            location = pyautogui.locateCenterOnScreen(image=image, confidence=DEFAULT_CONFIDENCE)  # type: ignore
            if location:
                logging.info(
                    f"在坐标 x, y=({location.x}, {location.y}) 找到图像 {image_path}"
                )
                return location
        except Exception:
            pass

        time_count += 1
        logging.warning(f"第{time_count}/{max_waiting}次找不到图像")
        if time_count < max_waiting:
            time.sleep(1)

    logging.error(f"达到最大等待时间 {max_waiting}, 无法找到图像 {image_path}")
    return None


def type_text_via_win32(text: str):
    """通过 Windows WM_CHAR 消息直接向目标窗口输入 Unicode 文本"""
    hwnd = win32gui.GetForegroundWindow()
    for char in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)


def execute_operation(sequence_dir: str, wait_time: float, operation: str, param: str, max_waiting: int):
    """执行指定的操作"""

    if wait_time > 0:
        logging.info(f"先等待 {wait_time} 秒")
        time.sleep(wait_time)

    # 根据操作类型执行相应动作
    match operation:
        case "单击":
            location = find_image(sequence_dir, param, max_waiting)
            if location:
                logging.info(f"左键点击坐标 x, y=({location.x}, {location.y})")
                pyautogui.click(location.x, location.y)
            else:
                logging.error("无法执行左键点击, 终止程序")
                return False

        case "双击":
            location = find_image(sequence_dir, param, max_waiting)
            if location:
                logging.info(f"左键双击坐标 x, y=({location.x}, {location.y})")
                pyautogui.doubleClick(location.x, location.y)
            else:
                logging.error("无法执行左键双击, 终止程序")
                return False

        case "右键":
            location = find_image(sequence_dir, param, max_waiting)
            if location:
                logging.info(f"右键点击坐标 x, y=({location.x}, {location.y})")
                pyautogui.rightClick(location.x, location.y)
            else:
                logging.error("无法执行右键点击, 终止程序")
                return False

        case "上页":
            logging.info(f"执行 {operation} 操作")
            pyautogui.press("pageup")

        case "下页":
            logging.info(f"执行 {operation} 操作")
            pyautogui.press("pagedown")

        case "页顶":
            logging.info(f"执行 {operation} 操作")
            pyautogui.press("home")

        case "页底":
            logging.info(f"执行 {operation} 操作")
            pyautogui.press("end")

        case "滚轮":
            logging.info(f"执行 {operation} {param} 操作")
            try:
                pyautogui.scroll(int(param))
            except:
                logging.error(f"滚轮参数错误: {param}")

        case "等待目标":
            location = find_image(sequence_dir, param, max_waiting)
            if location:
                logging.info(f"目标出现坐标 x, y=({location.x}, {location.y})")
            else:
                logging.error("无法找到目标图像, 终止程序")
                return False

        case "无操作":
            logging.info(f"执行 {operation} 操作")

        case "输入":
            # 去除引号（如果有的话）
            text = param
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            elif text.startswith("'") and text.endswith("'"):
                text = text[1:-1]

            if text == "签到":
                text = datetime.datetime.now().strftime(
                    "[%Y-%m-%d %H:%M:%S] 每日签到"
                )
            type_text_via_win32(text)
            logging.info(f"输入文本: {text}")

        case _:
            logging.warning(f"未知操作类型: {operation}")

    return True


def run_automation():
    """运行自动化操作序列"""

    if len(sys.argv) == 1:
        return

    raw = sys.argv[1]
    # 1. 直接作为路径尝试（支持绝对路径和相对路径）
    if os.path.exists(os.path.join(raw, "sequence.csv")):
        sequence_dir = raw
    else:
        # 2. 兼容旧行为：作为脚本同级子目录
        sequence_dir = os.path.join(os.path.dirname(sys.argv[0]), raw)
    csv_path = os.path.join(sequence_dir, "sequence.csv")

    if not os.path.exists(csv_path):
        logging.error(f"找不到CSV文件: {csv_path}")
        return

    logging.info(f"开始执行操作序列, 文件: {csv_path}")

    # 读取并执行CSV中的操作
    try:
        with open(csv_path, "r", encoding="utf-8") as file:
            fileStr = file.read()
    except:
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as file:
                fileStr = file.read()
        except:
            logging.error(f"无法打开CSV文件, 非UTF8编码: {csv_path}")
            return

    operationList: list[tuple[float, str, str, int]] = []

    reader = csv.reader(io.StringIO(fileStr))
    for row in reader:
        if not row or len(row) < 2:  # 跳过空行或格式不正确的行
            continue

        wait_timeStr = row[0].strip()
        operation = row[1].strip()
        param = "" if (len(row) < 3 or len(row[2].strip()) <= 0) else row[2].strip()
        max_waitingStr = (
            "0" if (len(row) < 4 or len(row[3].strip()) <= 0) else row[3].strip()
        )

        try:
            wait_time = float(wait_timeStr)
            if wait_time < 0:
                logging.warning(f"等待时间不能为负数: {wait_timeStr}, 设置为1")
                wait_time = 1
        except ValueError:
            logging.error(f"无效的等待时间: {wait_timeStr}")
            wait_time = 1

        try:
            max_waiting = int(max_waitingStr)
            if max_waiting < 0:
                logging.warning(
                    f"最大等待时间不能为负数: {max_waitingStr}, 设置为默认值: {DEFAULT_MAX_WAITING}"
                )
                max_waiting = DEFAULT_MAX_WAITING
        except ValueError:
            logging.error(
                f"无效的最大等待时间: {max_waitingStr}, 设置为默认值: {DEFAULT_MAX_WAITING}"
            )
            max_waiting = DEFAULT_MAX_WAITING

        if operation not in SUPPORTED_OPERATIONS:
            logging.warning(f"不支持的操作类型: [{row}] [{operation}]")
            sys.exit(-1)

        operationList.append((wait_time, operation, param, max_waiting))

    logging.info(f"操作序列数量:{len(operationList)}")
    cnt:int = 0
    for wait_time, operation, param, max_waiting in operationList:
        cnt += 1
        logging.info(
            f"执行步骤{cnt}: 先等待={wait_time}秒, 操作={operation}, 参数={param}, 最大等待时间={max_waiting}"
        )

        # 执行操作, 如果失败则终止程序
        if not execute_operation(sequence_dir, wait_time, operation, param, max_waiting):
            logging.error(f"执行步骤{cnt}失败, 终止程序")
            sys.exit(-1)

    logging.info("操作序列执行完成")


if __name__ == "__main__":
    logging.info("=" * 50)
    
    # 告诉操作系统使用程序自身的dpi适配
    ctypes.windll.shcore.SetProcessDpiAwareness(2)

    try:
        run_automation()
    except KeyboardInterrupt:
        logging.info("用户中断操作")
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
