# File: picture_match.py
# Author: Sheldon Hoo
# Date: 2019/10/3 0:43
# Product: PyCharm

import sys

import cv2
import win32api
import win32con
import win32gui
import win32ui
from PyQt5.QtWidgets import QApplication
from skimage.measure import compare_ssim


# 截取指定坐标的图片(低质量)
def window_capture(filename, pos=None):
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')  # 窗口的编号，0号表示当前活跃窗口
    app = QApplication(sys.argv)
    screen = QApplication.primaryScreen()
    screenshot_result = screen.grabWindow(hwnd).toImage()
    screenshot_result.save(filename)
    return app


# 截取指定坐标的图片(高质量)
def window_capture_exact(filename, hwnd=0, pos=None):
    # 窗口的编号，0号表示当前活跃窗口
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')
    # 根据窗口句柄获取窗口的设备上下文DC（Divice Context）
    hwndDC = win32gui.GetWindowDC(hwnd)
    # 根据窗口的DC获取mfcDC
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    # mfcDC创建可兼容的DC
    saveDC = mfcDC.CreateCompatibleDC()
    # 创建bigmap准备保存图片
    saveBitMap = win32ui.CreateBitmap()
    # 获取监控器信息
    MoniterDev = win32api.EnumDisplayMonitors(None, None)
    if pos is None:
        # 截取全屏
        # x1 = 0
        # y1 = 0
        # w = MoniterDev[0][2][2]
        # h = MoniterDev[0][2][3]
        # 截取窗口
        # 获取窗口左上角坐标
        x1, y1 = win32gui.ClientToScreen(hwnd, (0, 0))
        # 获取窗口长宽
        useless1, useless2, w, h = win32gui.GetClientRect(hwnd)
    else:
        x1 = pos[0]
        y1 = pos[1]
        w = pos[2] - pos[0]
        h = pos[3] - pos[1]
    # print w,h　　　#图片大小
    # 为bitmap开辟空间(全屏)
    # saveBitMap.CreateCompatibleBitmap(mfcDC, MoniterDev[0][2][2], MoniterDev[0][2][3])
    # 为bitmap开辟空间(窗口)
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    # 高度saveDC，将截图保存到saveBitmap中
    saveDC.SelectObject(saveBitMap)
    # 截取从左上角（0，0）长宽为（w，h）的图片
    saveDC.BitBlt((x1, y1), (w, h), mfcDC, (x1, y1), win32con.SRCCOPY)
    saveBitMap.SaveBitmapFile(saveDC, filename)
    # 清除图片数据，防止内存泄露
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()


# 判断A在B中的位置
# target：cv2.imread(“图片B”)
# template：cv2.imread(“图片A”)
def find_picture(target, template):
    # 获得模板图片的高宽尺寸
    theight, twidth = template.shape[:2]
    # 执行模板匹配，采用的匹配方式cv2.TM_SQDIFF_NORMED
    result = cv2.matchTemplate(target, template, cv2.TM_SQDIFF_NORMED)
    # 归一化处理
    cv2.normalize(result, result, 0, 1, cv2.NORM_MINMAX, -1)
    # 寻找矩阵（一维数组当做向量，用Mat定义）中的最大值和最小值的匹配结果及其位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    # 匹配值转换为字符串
    # 对于cv2.TM_SQDIFF及cv2.TM_SQDIFF_NORMED方法min_val越趋近与0匹配度越好，匹配位置取min_loc
    # 对于其他方法max_val越趋近于1匹配度越好，匹配位置取max_loc
    strmin_val = str(min_val)
    # 绘制矩形边框，将匹配区域标注出来
    # min_loc：矩形定点
    # (min_loc[0]+twidth,min_loc[1]+theight)：矩形的宽高
    # (0,0,225)：矩形的边框颜色；2：矩形边框宽度
    cv2.rectangle(target, min_loc, (min_loc[0] + twidth, min_loc[1] + theight), (0, 0, 225), 2)
    # 显示结果,并将匹配值显示在标题栏上
    # cv2.imshow("MatchResult----MatchingValue="+strmin_val,target)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    x = min_loc[0]
    y = min_loc[1]
    return x, y


# 返回指定图片的指定位置指定坐标
# target原始图片
# x,y 起始坐标
# w,h 返回的宽长
def get_pic_from_pic(x, y, w, h, target):
    region = target[y:y + h, x:x + w]
    return region


# 比较两个图片的相似度
def compare_picture(imageA, imageB):
    # 灰度图片比较
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    (score, diff) = compare_ssim(grayA, grayB, full=True, multichannel=True)
    return float(score)
