# File: Chocobo Racing.py
# Author: Sheldon Hoo
# Date: 2019/10/2 20:38
# Product: PyCharm

import os
import random
import shutil
import time

import PIL
import numpy
import pyautogui

from picture_match import *

if not os.path.exists('data'):
    os.mkdir('data')
if not os.path.exists('report'):
    os.mkdir('report')
if not os.path.exists('temp'):
    os.mkdir('temp')

# 提示运行状态
SYSTEM_STATE = {
    -1: '已掉线',
    0: '已暂停',
    1: '游戏运行中,准备排本',
    2: '副本队列中,等待确认',
    3: '已确认进入副本,等待赛鸟开始',
    4: '比赛进行中……',
    5: '已退出副本,记录比赛数据',
    6: '准备下一轮赛鸟\n',
    7: '超时异常,重新判定状态',
}

print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
time.sleep(2)
# 获得游戏句柄和左上角坐标
hwnd = win32gui.FindWindow(None, '最终幻想XIV')

fpx = 0
fpy = 0
state = 1
turn = 0
first = True
skip = False
unskilled_fpx = 0
unskilled_fpy = 0
unskilled_height = 0
unskilled_width = 0
unskilled_template = None
# 设定陆行鸟技能按键,不使用起步超级冲刺时,二技能填'None'
skill_list = ['q', 'None', 'None']
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
    if compare_handle_without_capture('data/reward[2].png', True) > 0.7:
        exp2_pos_list = [(fpx + 44, fpy + 23), (fpx + 36, fpy + 23), (fpx + 28, fpy + 23), (fpx + 16, fpy + 23)]
        exp2_exist = True
    else:
        exp2_exist = False
    # 千位只包含1, 2, 3
    arr = numpy.array([1, 2, 3])
    # 判断普通经验个十百千
    for i in range(0, 3):
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
    for i in range(0, 3):
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
        for i in range(0, 3):
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
    time.sleep(0.1 + random.random() / 10)


def ready_to_queue():
    global state, first
    while not os.path.exists('data/main.png'):
        profiles('main')
        time.sleep(5)
    while compare_handle('data/main.png') <= 0.5:
        time.sleep(5)
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
def waiting_for_queue(timeout=35, interval=1):
    global state, skip, hwnd, fpx, fpy, unskilled_fpx, unskilled_fpy, unskilled_height, unskilled_width, unskilled_template
    state_start_time = time.time()
    while compare_handle('data/attend.png') <= 0.5:
        # 超时
        if time.time() - state_start_time > timeout:
            break
        time.sleep(interval)
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
            state = 7
            break
        time.sleep(interval)
    # 获取1技能的位置、宽、长
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')
    unskilled_template = cv2.imread('data/unskilled.png')
    target = cv2.imread('data/screenshot.jpg')
    unskilled_fpx, unskilled_fpy = find_picture(unskilled_template, target)
    unskilled_height, unskilled_width = unskilled_template.shape[:2]
    state = 3


# 进入赛鸟场,等待比赛开始
def waiting_for_race_begin(timeout=100, interval=1):
    global state, skip, hwnd
    state_start_time = time.time()
    hwnd = win32gui.FindWindow(None, '最终幻想XIV')
    useless1, useless2, dx, dy = win32gui.GetClientRect(hwnd)
    dx = int(970 * dx / 1920)
    dy = int(459 * dy / 1080)
    while not skip and not pyautogui.pixelMatchesColor(dx, dy, (118, 146, 41), tolerance=10):
        # 超时
        if time.time() - state_start_time > timeout:
            state = 7
            break
    if skip:
        skip = False
    state = 4


# 比赛开始到结束退本
def chocobo_run(timeout=200, interval=1):
    global state, unskilled_fpx, unskilled_fpy, unskilled_height, unskilled_width
    state_start_time = time.time()
    # 使用2技能,起步冲刺
    if skill_list[1] != 'None':
        while True:
            my_keypress(skill_list[1])
            if time.time() - state_start_time > 3:
                break
    else:
        pyautogui.keyDown('up')
    time.sleep(4 + random.random() * 4)
    pyautogui.keyDown('left')
    finished = False
    # 竞赛过程中
    while compare_handle('data/result.png') <= 0.8:
        # 第一次松开左键,并使用3技能
        if time.time() - state_start_time > 12 and not finished:
            pyautogui.keyUp('left')
            if skill_list[2] != 'None':
                my_keypress(skill_list[2])
            finished = True
        # 按Q使用第一个技能
        target = cv2.imread('data/screenshot.jpg')
        region = get_pic_from_pic(unskilled_fpx, unskilled_fpy, unskilled_width, unskilled_height, target)
        if compare_picture(unskilled_template, region) <= 0.15:
            my_keypress(skill_list[0])
        # 超时
        if time.time() - state_start_time > timeout:
            if skill_list[1] == 'None':
                pyautogui.keyUp('up')
            state = 7
            break
        time.sleep(interval)
    if skill_list[1] == 'None':
        pyautogui.keyUp('up')
    while compare_handle('data/exit.png', True) <= 0.9:
        # 超时
        if time.time() - state_start_time > timeout:
            break
        time.sleep(interval)
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
    file.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + '[%d]: %d,%d(%d),%d\n' % (
        turn, ranking, exp, exp2, coin))
    file.close()

    # 读取出错截图
    if ranking * exp * coin == 0:
        pyautogui.screenshot().save('report/%s[%d].bmp' % (time.strftime('%Y%m%d_%H%M%S', time.localtime()), turn))
    state = 6


def waiting_for_return(timeout=60, interval=1):
    global state
    state_start_time = time.time()
    # 返回主界面
    while compare_handle('data/main.png') <= 0.5:
        # 超时
        if time.time() - state_start_time > timeout:
            state = 7
            break
        time.sleep(interval)
    state = 1


def timeout():
    global state, first
    time.sleep(100)
    # 不在主界面
    while compare_handle('data/main.png') <= 0.5:
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
    state = 1


def loop():
    while True:
        print(SYSTEM_STATE[state])
        if state == 1:
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
            waiting_for_return()
            print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        elif state == 7:
            timeout()
        else:
            time.sleep(1)


loop()
