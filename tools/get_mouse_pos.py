import pyautogui
import time

print("按 Ctrl+C 退出")
while True:
    x, y = pyautogui.position()
    print(f"鼠标坐标：X={x:4d}  Y={y:4d}", end="\r")
    time.sleep(0.1)