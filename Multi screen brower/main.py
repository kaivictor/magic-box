import mss.tools
# # from mss.windows import MSS as mss
from win32api import GetSystemMetrics
from win32con import SM_CMONITORS
import tkinter
from PIL import Image, ImageTk
import threading
import time
import cv2
import numpy
import win32gui
import win32ui


last_execution_time = time.time()


# 获取鼠标样式
def add_cursor(screenImg, bbox):
    global last_execution_time
    is_sucess = 0
    hcursor = win32gui.GetCursorInfo()[1]
    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc, 36, 36)
    hdc = hdc.CreateCompatibleDC()
    hdc.SelectObject(hbmp)
    try:  # 刚好鼠标被隐藏
        hdc.DrawIcon((0, 0), hcursor)
        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        cursor = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1).convert("RGBA")
    except Exception:
        print("鼠标获取失败")
        is_sucess = 1
    try:
        win32gui.DestroyIcon(hcursor)
    except Exception:
        print("句柄清除失败")
        is_sucess = 2
    win32gui.DeleteObject(hbmp.GetHandle())
    hdc.DeleteDC()
    if not is_sucess:
        pixdata = cursor.load()
        width, height = cursor.size
        for y in range(height):
            for x in range(width):
                if pixdata[x, y] == (0, 0, 0, 255):
                    pixdata[x, y] = (0, 0, 0, 0)
        hotspotx, hotspoty = win32gui.GetIconInfo(hcursor)[1:3]
        # return (cursor, hotspot)
    else:
        # 使用默认鼠标样式
        default_mouse_model = Image.open(r"D:\Studio\PyProgram\Project\desktopCopy\default_mouse_model.png")
        cursor = default_mouse_model.resize((36, 36))
    # ratio = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
    pos_win = win32gui.GetCursorPos()
    # pos = (round(pos_win[0] * ratio - hotspotx), round(pos_win[1] * ratio - hotspoty))
    if (pos_win[0] >= bbox['left']) and (pos_win[0] <= (bbox['left'] + bbox['width'])) and (pos_win[1] >= bbox['top']) and (pos_win[1] <= (bbox['top'] + bbox['height'])):
        true_cursorPos = (pos_win[0] - bbox['left'], pos_win[1] - bbox['top'])
        pos_win = true_cursorPos
        screenImg.paste(cursor, pos_win, cursor)
    current_time = time.time()
    if current_time - last_execution_time >= 1:
        print("鼠标位置: ", pos_win, "要求: ", bbox)
        last_execution_time = current_time
    return screenImg


class viewApp():
    def __init__(self) -> None:
        # 窗口准备
        self.screenWin = tkinter.Tk()
        self.screenWin.pack_propagate(0)
        self.screenWin.title("分屏监看程序")
        # 主屏幕尺寸 用于设置软件大小
        MajorScreenWidth = GetSystemMetrics(0)  # 主屏幕宽
        MajorScreenHeight = GetSystemMetrics(1)  # 主屏幕高
        self.screenWin.geometry(f'{MajorScreenWidth}x{MajorScreenHeight}')
        print(f"窗口初始大小: {MajorScreenWidth}x{MajorScreenHeight}")
        self.screenWin.minsize(600, 240)
        self.video_lost_img = Image.open(r"D:\Studio\PyProgram\Project\desktopCopy\video_lost.png")
        self.screenWin.bind('<Configure>', self.window_resize)
        # 添加右键菜单
        self.context_menu = tkinter.Menu(self.screenWin, tearoff=0)
        self.context_menu.add_command(label="多视图", command=self.defaultScreenViewing)
        self.context_menu.add_command(label="全屏", command=self.toggle_fullscreen)
        self.context_menu.add_command(label="退出", command=self.app_quit)
        # 绑定窗口关闭事件处理函数
        self.screenWin.protocol("WM_DELETE_WINDOW", self.app_quit)
        # 窗口标签列表
        self.screenWinLabelInfoList = {}
        # 判断当前是不是单个窗口
        self.viewingScreen_single = False
        # 是否全屏 标记
        self.fullscreen = False
        # 是否继续运行
        self.exit_flag = threading.Event()

    def window_resize(self, event=None):
        # 显示器数量检测
        monitor_number = GetSystemMetrics(SM_CMONITORS)
        print("显示器数量: ", monitor_number)
        # 每个窗口的大小
        widthProportion = 0.8 / monitor_number / 1.2
        offsetWidth = self.windows_width() * widthProportion
        offsetHeight = offsetWidth / 1.7
        video_lost_img = self.video_lost_img.resize((int(offsetWidth), int(offsetHeight)))
        video_lost_img = ImageTk.PhotoImage(video_lost_img)
        # 计算窗口位置（中心）
        screenWinLabelCenterX = []
        screenWinLabelCenterY = self.windows_height() * 0.5
        screenWinLabelCenterX_base = self.windows_width() * 0.1
        print("预览窗口左边界: ", screenWinLabelCenterX_base)
        for i in range(0, monitor_number):
            screenWinLabelCenterX.append(screenWinLabelCenterX_base + (i * 1.2 * offsetWidth) + (offsetWidth / 2) + (1.2 * offsetWidth * 0.083))
            self.screenWinLabelInfoList[i]['baseSize'] = (int(offsetWidth), int(offsetHeight))
            self.screenWinLabelInfoList[i]['basePos'] = (int(screenWinLabelCenterX[i] - (offsetWidth / 2)), int(screenWinLabelCenterY - (offsetHeight / 2)))
        self.isViewingScreen_single()

        if self.viewingScreen_single:
            for i in self.screenWinLabelInfoList.keys():
                if self.screenWinLabelInfoList[i]['update'] is True:
                    self.fullScreenViewing(i)
        else:
            for i in self.screenWinLabelInfoList.keys():
                self.screenWinLabelInfoList[i]['label']['width'] = self.screenWinLabelInfoList[i]['baseSize'][0]
                self.screenWinLabelInfoList[i]['label']['height'] = self.screenWinLabelInfoList[i]['baseSize'][1]
                self.screenWinLabelInfoList[i]['label'].place_configure(x=self.screenWinLabelInfoList[i]['basePos'][0], y=self.screenWinLabelInfoList[i]['basePos'][1])

    def windows_width(self):  # 主要是为了处理窗口未生成前无法正确获取窗口大小的问题
        if self.screenWin.winfo_width() <= 100:
            return GetSystemMetrics(0)  # 主屏幕宽
        return self.screenWin.winfo_width()

    def windows_height(self):  # 主要是为了处理窗口未生成前无法正确获取窗口大小的问题
        if self.screenWin.winfo_height() <= 50:
            return GetSystemMetrics(1)  # 主屏幕高
        return self.screenWin.winfo_height()

    def addViewScreen(self):
        # 显示器数量检测
        monitor_number = GetSystemMetrics(SM_CMONITORS)
        print("显示器数量: ", monitor_number)
        # 每个窗口的大小
        widthProportion = 0.8 / monitor_number / 1.2
        offsetWidth = self.windows_width() * widthProportion
        offsetHeight = offsetWidth / 1.7

        video_lost_img = self.video_lost_img.resize((int(offsetWidth), int(offsetHeight)))
        video_lost_img = ImageTk.PhotoImage(video_lost_img)

        # 计算窗口位置（中心）
        screenWinLabelCenterX = []
        screenWinLabelCenterY = self.windows_height() * 0.5
        screenWinLabelCenterX_base = self.windows_width() * 0.1
        print("预览窗口左边界: ", screenWinLabelCenterX_base)
        for i in range(0, monitor_number):
            screenWinLabelCenterX.append(screenWinLabelCenterX_base + (i * 1.2 * offsetWidth) + (offsetWidth / 2) + (1.2 * offsetWidth * 0.083))
        print(screenWinLabelCenterX)

        self.screenWinLabelInfoList = {}

        for i in range(0, monitor_number):
            # 添加显示空间
            self.screenWinLabelInfoList[i] = {'id': i, 'img': video_lost_img, 'baseSize': (int(offsetWidth), int(offsetHeight)),
                                              'basePos': (int(screenWinLabelCenterX[i] - (offsetWidth / 2)), int(screenWinLabelCenterY - (offsetHeight / 2))),
                                              'update': True}

            new_label = tkinter.Label(self.screenWin, image=self.screenWinLabelInfoList[i]['img'], bg="gray",
                                      width=self.screenWinLabelInfoList[i]['baseSize'][0],
                                      height=self.screenWinLabelInfoList[i]['baseSize'][1])
            print("预览大小: ", int(offsetWidth), int(offsetHeight))
            new_label.place(x=self.screenWinLabelInfoList[i]['basePos'][0], y=self.screenWinLabelInfoList[i]['basePos'][1])
            self.screenWinLabelInfoList[i]['label'] = new_label
            new_label.bind("<Button-1>", lambda e, labelId=self.screenWinLabelInfoList[i]['id']: self.fullScreenViewing(labelId))
            print("放置位置: ", int(screenWinLabelCenterX[i] - (offsetWidth / 2)), int(screenWinLabelCenterY - (offsetHeight / 2)), int(screenWinLabelCenterY - (offsetHeight / 2)))

            # 添加菜单点击
            new_label.bind("<Button-3>", self.show_context_menu)

    def fullScreenViewing(self, screenId):
        print("全屏显示屏幕: ", screenId)
        # 将label设置为全屏
        self.screenWinLabelInfoList[screenId]['label']['width'] = int(self.windows_width() * 1)
        self.screenWinLabelInfoList[screenId]['label']['height'] = int(self.windows_height() * 1)
        self.screenWinLabelInfoList[screenId]['label'].place_configure(x=int(self.windows_width() * 0), y=int(self.windows_height() * 0))

        for i in self.screenWinLabelInfoList.keys():
            if (i != screenId):
                self.screenWinLabelInfoList[i]['update'] = False
                self.screenWinLabelInfoList[i]['label'].place_forget()
            elif (i == screenId):
                self.screenWinLabelInfoList[i]['update'] = True
                # screenWinLabelInfoList[i]['label'].pack_forget()
        self.isViewingScreen_single()

    def defaultScreenViewing(self):
        for i in self.screenWinLabelInfoList.keys():
            self.screenWinLabelInfoList[i]['label']['width'] = self.screenWinLabelInfoList[i]['baseSize'][0]
            self.screenWinLabelInfoList[i]['label']['height'] = self.screenWinLabelInfoList[i]['baseSize'][1]
            self.screenWinLabelInfoList[i]['label'].place_configure(x=self.screenWinLabelInfoList[i]['basePos'][0], y=self.screenWinLabelInfoList[i]['basePos'][1])
            self.screenWinLabelInfoList[i]['update'] = True
        self.isViewingScreen_single()
        # 防止全屏
        self.fullscreen = True
        self.toggle_fullscreen()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.screenWin.attributes("-fullscreen", self.fullscreen)
        # 更新右键菜单文本
        menu_label = "窗口" if self.fullscreen else "全屏"
        self.context_menu.entryconfigure(1, label=menu_label)

    def isViewingScreen_single(self):
        # 判断当前是不是单个窗口
        self.viewingScreen_single = False
        viewingScreen = 0
        for screenId in self.screenWinLabelInfoList.keys():
            if self.screenWinLabelInfoList[screenId]['update'] is True:
                viewingScreen += 1

        if viewingScreen == 1:
            self.viewingScreen_single = True

    def show_context_menu(self, event):  # 显示菜单
        if self.viewingScreen_single:
            self.context_menu.post(event.x_root, event.y_root)

    def getScreenImg(self):
        # thisLabel['image'] = screenWinLabelInfoList[screenId]['img']
        print("结束标志: ", self.exit_flag)
        with mss.mss() as sct:
            while (not self.exit_flag.is_set()):
                for screenId in self.screenWinLabelInfoList.keys():
                    monitor_number = screenId + 1
                    thisLabel = self.screenWinLabelInfoList[screenId]['label']
                    if (self.screenWinLabelInfoList[screenId]['update'] is True):
                        mon = sct.monitors[monitor_number]
                        # print(mon)
                        # The screen part to capture
                        monitor = {
                            "top": mon["top"],  # 100px from the top
                            "left": mon["left"],  # 100px from the left
                            "width": mon["width"],
                            "height": mon["height"],
                            "mon": monitor_number,
                        }
                        img = numpy.array(sct.grab(monitor))
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(img)

                        # 判断窗口是否被关闭
                        if (self.exit_flag.is_set()):
                            return
                        # video_live_img = Image.open(video_live_img)
                        if self.viewingScreen_single:  # 添加鼠标样式
                            img = add_cursor(img, monitor)
                        img = img.resize((thisLabel['width'], thisLabel['height']))
                        # thisLabel['image'] = screenWinLabelInfoList[screenId]['img']
                        new_img = ImageTk.PhotoImage(img)
                        thisLabel.imgtk = new_img
                        thisLabel.config(image=new_img)
                        self.screenWinLabelInfoList[screenId]['img'] = new_img
                        thisLabel['image'] = self.screenWinLabelInfoList[screenId]['img']
                        # thisLabel['image'] = ImageTk.PhotoImage(new_img)

    def screeWin_mainloop(self):
        self.screenWin.mainloop()

    def app_quit(self):
        self.exit_flag.set()
        self.screenWin.destroy()


if __name__ == '__main__':
    testApp = viewApp()
    testApp.addViewScreen()

    # t1 = threading.Thread(target=simpleViewing, args=['id'])
    t1 = threading.Thread(target=testApp.getScreenImg, args=[])
    testApp.screenWin.after(200, t1.start())
    testApp.screeWin_mainloop()
