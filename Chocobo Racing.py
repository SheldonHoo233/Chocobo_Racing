# File: Chocobo Racing.py
# Author: Sheldon Hoo
# Date: 2019/10/2 20:38
# Product: PyCharm

import os
import random
import shutil
import time

import PIL
import keyboard
import numpy
import pyautogui

from picture_match import *

if not os.path.exists('data'):
    os.mkdir('data')
if not os.path.exists('report'):
    os.mkdir('report')
if not os.path.exists('temp'):
    os.mkdir('temp')
time.sleep(1)

# 提示运行状态
SYSTEM_STATE = {
    -1: '已掉线',
    0: '\n使用menu键暂停了脚本……',
    1: '游戏运行中,准备排本',
    2: '副本队列中,等待确认',
    3: '已确认进入副本,等待赛鸟开始',
    4: '比赛进行中……',
    5: '已退出副本,记录比赛数据',
    6: '超时异常,重新判定状态',
}

pyautogui.keyUp('left')
pyautogui.keyUp('up')
pyautogui.press('capslock')
print('按住menu键开始运行脚本')
while True:
    # 按menu键开始运行脚本
    if keyboard.is_pressed('menu'):
        pyautogui.press('capslock')
        break
    time.sleep(1)
print('\n' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
# 获得游戏句柄和左上角坐标
hwnd = win32gui.FindWindow(None, '最终幻想XIV')

fpx = 0
fpy = 0
state = 1
turn = 0
first = True
skip = False
unskilled_x = 0
unskilled_y = 0
unskilled_color = (0, 0, 0)
# 设定陆行鸟技能按键,不使用起步超级冲刺时,二技能填'None'
skill_list = ['q', 'None', 'w']
ranking_list = []
exp_list = []
coin_list = []
star_pos_list = []
images_list = ['main', 'unskilled', 'power', 'attend', 'digit[0]', 'digit[1]', 'digit[2]', 'digit[3]', 'digit[4]',
               'digit[5]', 'digit[6]', 'digit[7]', 'digit[8]', 'digit[9]', 'exit', 'offline', 'result', 'reward[1]',
               'reward[2]', 'select[1]', 'select[2]', 'star', 'stormblood']
scale_list = [0.6, 0.8, 0.9, 1, 1.1, 1.2, 1.4, 1.6, 1.8, 2]


# 获得图片与保存的游戏截图相似度
def compare_handle_without_capture(template, exact=False):
    global fpx, fpy
    template = cv2.imread(template)
    if exact:
        target = cv2.imread('data/screenshot.bmp')
    else:
        target = cv2.imread('data/screenshot.jpg')
    fpx, fpy = find_picture(template, target)
    height, width = template.shape[:2]
    region = get_pic_from_pic(fpx, fpy, width, height, target)
    score = compare_picture(template, region)
    return score


# 获得图片与当前游戏截图相似度
def compare_handle(template, exact=False):
    global hwnd
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')
    if exact:
        window_capture_exact('data/screenshot.bmp')
    else:
        window_capture('data/screenshot.jpg')
    score = compare_handle_without_capture(template, exact)
    return score


# 如果data文件夹没有截图,则把原图放到data文件夹或缩放图放到temp文件夹
for i in range(0, len(images_list)):
    if not os.path.exists('data/%s.png' % images_list[i]):
        if i <= 2:
            for j in range(1, 10):
                img = cv2.imread('original images/%s.png' % images_list[i])
                height, width = img.shape[:2]
                resized = (int(width * scale_list[j - 1]), int(height * scale_list[j - 1]))
                img2 = cv2.resize(img, resized, interpolation=cv2.INTER_CUBIC)
                cv2.imwrite('temp/%s[%s].png' % (images_list[i], str(j)), img2)
        else:
            shutil.copyfile('original images/%s.png' % images_list[i], 'data/%s.png' % images_list[i])
digit_list = [PIL.Image.open('data/digit[%d].png' % i) for i in range(10)]


# 选取匹配玩家的,相似度最高的(≥50%)的图片放进data文件夹
def profiles(template_without_path):
    similar = [0]
    window_capture_exact('data/screenshot.bmp')
    print(template_without_path + '缩放率相似度:')
    for i in range(1, 10):
        similar.append(compare_handle_without_capture('temp/%s[%d].png' % (template_without_path, i), True))
        print('%d%%:' % int(scale_list[i] * 100), '%.2f%%' % (similar[i] * 100))
    if max(similar) >= 0.8:
        shutil.copyfile('temp/%s[%d].png' % (template_without_path, numpy.argmax(similar)),
                        'data/%s.png' % template_without_path)
        for i in range(1, 10):
            os.remove('temp/%s[%d].png' % (template_without_path, i))
        print('选择: %d%%' % int(scale_list[numpy.argmax(similar)] * 100))
        time.sleep(1)


# 获取竞赛名次
# 比赛结果(x, y) 名次n 星星(x - 145, y + 121 + n * 32)
def recognize_ranking():
    ranking = 0
    compare_handle_without_capture('data/star.png', True)
    star_fpx = fpx
    star_fpy = fpy
    try:
        ranking = star_pos_list.index((star_fpx, star_fpy))
    except ValueError:
        compare_handle_without_capture('data/result.png', True)
        result_fpx = fpx
        result_fpy = fpy
        for i in range(0, 9):
            star_pos_list.append((result_fpx - 145, result_fpy + 121 + i * 32))
        ranking = star_pos_list.index((star_fpx, star_fpy))
    finally:
        if ranking != 0:
            ranking_list.append(ranking)
        return ranking


# 获得竞赛奖励
def recognize_rewards():
    global fpx, fpy
    exp1 = 0
    coin = 0
    exp2 = 0
    # 数字图片6px*18px
    width = 6
    height = 18
    # 获得普通奖励与额外奖励的坐标
    template = cv2.imread('data/reward[1].png')
    target = cv2.imread('data/screenshot.bmp')
    fpx, fpy = find_picture(template, target)
    # 相对奖励位置:
    # 普通经验  (x-29, y+23), (x-17, y+23), (x-9, y+23), (x-1, y+23)
    # 普通金蝶币(x+53, y+23), (x+65, y+23), (x+73, y+23), (x+81, y+23)
    # 相对额外奖励位置:
    # 额外经验  (x+16, y+23), (x+28, y+23), (x+36, y+23), (x+44, y+23)
    # 获得个十百千数字坐标
    exp1_pos_list = [(fpx - 1, fpy + 23), (fpx - 9, fpy + 23), (fpx - 17, fpy + 23), (fpx - 29, fpy + 23)]
    coin_pos_list = [(fpx + 81, fpy + 23), (fpx + 73, fpy + 23), (fpx + 65, fpy + 23), (fpx + 53, fpy + 23)]
    if compare_handle_without_capture('data/reward[2].png', True) > 0.6:
        exp2_pos_list = [(fpx + 44, fpy + 23), (fpx + 36, fpy + 23), (fpx + 28, fpy + 23), (fpx + 16, fpy + 23)]
        exp2_exist = True
    else:
        exp2_exist = False
    # 千位只包含1, 2, 3
    arr = numpy.array([1, 2, 3])
    # 判断普通经验个十百千
    for i in range(0, 4):
        fpx, fpy = exp1_pos_list[i]
        region = get_pic_from_pic(fpx, fpy, width, height, target)
        # 判断数字
        for j in range(0, 10):
            template = cv2.imread('data/digit[%d].png' % j)
            score = compare_picture(template, region)
            if score > 0.9:
                exp1 = exp1 + j * pow(10, i)
                break
            elif i == 3 and (arr == j).any() and score > 0.6:
                exp1 = exp1 + j * pow(10, i)
                break
    # 判断金蝶币个十百千
    for i in range(0, 4):
        fpx, fpy = coin_pos_list[i]
        region = get_pic_from_pic(fpx, fpy, width, height, target)
        # 判断数字
        for j in range(0, 10):
            template = cv2.imread('data/digit[%d].png' % j)
            score = compare_picture(template, region)
            if score > 0.9:
                coin = coin + j * pow(10, i)
                break
            elif i == 3 and (arr == j).any() and score > 0.6:
                coin = coin + j * pow(10, i)
                break
    if exp2_exist:
        # 判断额外经验个十百千
        for i in range(0, 4):
            fpx, fpy = exp2_pos_list[i]
            region = get_pic_from_pic(fpx, fpy, width, height, target)
            # 判断数字
            for j in range(0, 10):
                template = cv2.imread('data/digit[%d].png' % j)
                score = compare_picture(template, region)
                if score > 0.9:
                    exp2 = exp2 + j * pow(10, i)
                    break
                elif i == 3 and (arr == j).any() and score > 0.6:
                    exp2 = exp2 + j * pow(10, i)
                    break
    if exp1 != 0:
        exp_list.append(exp1 + exp2)
    if coin != 0:
        coin_list.append(coin)
    return exp1 + exp2, coin, exp2


def my_keypress(key):
    pyautogui.keyDown(key)
    time.sleep(random.random() / 10)
    pyautogui.keyUp(key)
    time.sleep(0.2 + random.random() / 10)


def pause_and_restart():
    global state
    pyautogui.keyUp('left')
    pyautogui.keyUp('up')
    time.sleep(3)
    while True:
        # 按menu键重启
        if keyboard.is_pressed('menu'):
            pyautogui.press('capslock')
            print('重启脚本……')
            print('\n' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
            state = 1
            break
        time.sleep(5)


def ready_to_queue():
    global state, first
    while not os.path.exists('data/main.png'):
        profiles('main')
        time.sleep(5)
    while compare_handle('data/main.png') <= 0.5:
        time.sleep(5)
        # 按menu键暂停
        if keyboard.is_pressed('menu'):
            pyautogui.press('capslock')
            state = 0
            return
    # 首次运行:取消任务选择,判断金蝶币图标,判断任务说明
    my_keypress('num1')
    my_keypress('esc')
    time.sleep(0.5)
    if first:
        my_keypress('u')
        time.sleep(2)
        my_keypress('num8')
        my_keypress('num8')
        my_keypress('num8')
        my_keypress('num8')
        my_keypress('num0')
        my_keypress('num2')
        my_keypress('num2')
        my_keypress('num2')
        my_keypress('num2')
        while compare_handle('data/select[1].png') < 0.8:
            my_keypress('num7')
        while compare_handle('data/select[2].png') < 0.8:
            my_keypress('num2')
            my_keypress('num0')
        my_keypress('num0')
        my_keypress('esc')
        first = False
    my_keypress('u')
    time.sleep(2)
    my_keypress('num8')
    my_keypress('num8')
    my_keypress('num8')
    my_keypress('num8')
    my_keypress('num6')
    my_keypress('num0')
    state = 2


# 排本中
def waiting_for_queue(timeout=35, interval=2):
    global state, skip, hwnd, fpx, fpy, unskilled_x, unskilled_y, unskilled_color
    state_start_time = time.time()
    while compare_handle('data/attend.png') <= 0.7:
        # 超时
        if time.time() - state_start_time > timeout:
            break
        time.sleep(1)
    my_keypress('num4')
    my_keypress('num0')

    time.sleep(8)
    state_start_time = time.time()
    # 获取体力图片
    while not os.path.exists('data/power.png'):
        profiles('power')
        time.sleep(interval)
    # 获取技能格1图片
    while not os.path.exists('data/unskilled.png'):
        profiles('unskilled')
        time.sleep(interval)
        skip = True
    # 识别体力条
    while compare_handle('data/power.png') <= 0.5:
        # 超时
        if time.time() - state_start_time > timeout:
            state = 6
            break
        time.sleep(1)
    # 获取1技能的位置、宽、长
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')
    window_capture_exact('data/screenshot.bmp')
    template = cv2.imread('data/unskilled.png')
    target = cv2.imread('data/screenshot.bmp')
    fpx, fpy = find_picture(template, target)
    height, width = template.shape[:2]
    unskilled_x, unskilled_y = (int(fpx + width / 2), int(fpy + height / 2))
    unskilled_color = pyautogui.pixel(unskilled_x, unskilled_y)
    state = 3


# 进入赛鸟场,等待比赛开始
def waiting_for_race_begin(timeout=100):
    global state, skip, hwnd
    state_start_time = time.time()
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')
    x1, y1 = win32gui.ClientToScreen(hwnd, (0, 0))
    _, _, dx, dy = win32gui.GetClientRect(hwnd)
    dx = int(970 * dx / 1920)
    dy = int(459 * dy / 1080)
    while not skip and not pyautogui.pixelMatchesColor(x1 + dx, y1 + dy, (118, 146, 41), tolerance=10):
        # 超时
        if time.time() - state_start_time > timeout:
            state = 6
            break
    if skip:
        skip = False
    state = 4


# 比赛开始到结束退本
def chocobo_run(timeout=200, interval=2):
    global state, unskilled_x, unskilled_y, unskilled_color
    state_start_time = time.time()
    # 使用2技能,起步冲刺
    if skill_list[1] != 'None':
        while True:
            my_keypress(skill_list[1])
            if time.time() - state_start_time > 3:
                break
    pyautogui.keyDown('up')
    time.sleep(7)
    pyautogui.keyDown('left')
    finished = 0
    # 竞赛过程中
    while compare_handle('data/result.png') <= 0.8:
        # 按menu键暂停
        if keyboard.is_pressed('menu'):
            pyautogui.press('capslock')
            state = 0
            return
        # 第一次松开左键,往右跑一点
        if time.time() - state_start_time > 13 and finished == 0:
            pyautogui.keyUp('left')
            time.sleep(3)
            pyautogui.keyDown('right')
            time.sleep(0.1)
            pyautogui.keyUp('right')
            finished = 1
        # 使用3技能
        if time.time() - state_start_time > 30 and finished == 1:
            if skill_list[2] != 'None':
                my_keypress(skill_list[2])
            finished = 2
        # 往左跑一点
        if time.time() - state_start_time > 38 and finished == 2:
            if skill_list[2] != 'None':
                my_keypress(skill_list[2])
            pyautogui.keyDown('left')
            time.sleep(1)
            pyautogui.keyUp('left')
            finished = 3
            interval = 5
        # 使用1技能
        if not pyautogui.pixelMatchesColor(unskilled_x, unskilled_y, unskilled_color, tolerance=10):
            my_keypress(skill_list[0])
        # 超时
        if time.time() - state_start_time > timeout:
            pyautogui.keyUp('up')
            state = 6
            break
        time.sleep(interval)
    pyautogui.keyUp('up')
    while compare_handle('data/exit.png', True) <= 0.9:
        # 按menu键暂停
        if keyboard.is_pressed('menu'):
            pyautogui.press('capslock')
            state = 0
            return
        # 超时
        if time.time() - state_start_time > timeout:
            break
        time.sleep(2)
    my_keypress('num0')
    my_keypress('num0')
    state = 5


# 退本,记录成绩
def recording_the_results():
    global state, turn
    turn += 1
    ranking = recognize_ranking()
    exp, coin, exp2 = recognize_rewards()
    print('第%d轮赛鸟比赛结果:' % turn)
    if ranking == 0:
        print('获取比赛名次失败!')
    else:
        print('获得了第%d名。(平均:%.2f)' % (ranking, sum(ranking_list) / len(ranking_list)))
    if exp == 0:
        print('获取经验失败!')
    elif exp2 == 0:
        print('获得了%d点经验值。(平均:%d 共计:%d)' % (exp, sum(exp_list) / len(exp_list), sum(exp_list)))
    else:
        print('获得了%d(+%d%%)点经验值!(平均:%d 共计:%d)' % (
            exp, round(100 * exp2 / exp), sum(exp_list) / len(exp_list), sum(exp_list)))
    if coin == 0:
        print('获取金蝶币失败!')
    else:
        print('获得了%d金碟币。(平均:%d 共计:%d)' % (coin, sum(coin_list) / len(coin_list), sum(coin_list)))

    file = open('report/log.txt', 'a')
    try:
        file.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + '[%d]: %d,%d(+%d%%),%d,%d,%d\n' % (
            turn, ranking, exp, round(100 * exp2 / exp), sum(exp_list), coin, sum(coin_list)))
    except ZeroDivisionError:
        file.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + '[%d]: %d,%d(+%d%%),%d,%d,%d\n' % (
            turn, ranking, exp, 0, sum(exp_list), coin, sum(coin_list)))
    file.close()
    # 读取出错截图
    if ranking * exp * coin == 0:
        pyautogui.screenshot().save('report/%s[%d].bmp' % (time.strftime('%Y%m%d_%H%M%S', time.localtime()), turn))
    print('\n' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    state = 1


def timeout():
    global state, first
    time.sleep(100)
    # 不在主界面
    while compare_handle('data/main.png') <= 0.5:
        # 按menu键暂停
        if keyboard.is_pressed('menu'):
            pyautogui.press('capslock')
            state = 0
            return
        # 掉线重连
        if compare_handle('data/offline.png') > 0.5:
            my_keypress('0')
            time.sleep(2)
        # 截图错误,回到标题页面
        else:
            my_keypress('num1')
            my_keypress('esc')
            my_keypress('num8')
            my_keypress('num0')
            my_keypress('num0')
            time.sleep(6)
        # 登录页面
        if compare_handle('data/stormblood.png') > 0.5:
            my_keypress('num0')
            my_keypress('num0')
            time.sleep(8)
            my_keypress('num0')
            time.sleep(8)
            my_keypress('num0')
            my_keypress('num0')
            timeout(8)
            my_keypress('num0')
            my_keypress('num0')
            my_keypress('num0')
            time.sleep(60)
        first = True
    print('\n' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    state = 1


def loop():
    while True:
        print(SYSTEM_STATE[state])
        if state == 0:
            pause_and_restart()
        elif state == 1:
            ready_to_queue()
        elif state == 2:
            waiting_for_queue()
        elif state == 3:
            waiting_for_race_begin()
        elif state == 4:
            chocobo_run()
        elif state == 5:
            recording_the_results()
        elif state == 6:
            timeout()
        else:
            time.sleep(1)


loop()
