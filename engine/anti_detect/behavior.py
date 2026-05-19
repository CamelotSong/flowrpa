"""behavior.py - 人工行为模拟

模拟真实用户的延迟、打字习惯、滚动方式和鼠标移动。
"""

import asyncio
import random
import math
from typing import Any


async def human_delay(min: float = 0.5, max: float = 2.0) -> None:
    """随机等待，模拟人工操作间隔

    Args:
        min: 最小等待秒数
        max: 最大等待秒数
    """
    delay = min + random.random() * (max - min)
    # 偶尔出现较长停顿（思考时间）
    if random.random() < 0.08:
        delay += random.uniform(1.0, 3.0)
    await asyncio.sleep(delay)


async def human_type(element: Any, text: str,
                     char_delay_min: float = 0.04,
                     char_delay_max: float = 0.16,
                     mistake_rate: float = 0.02) -> None:
    """逐字符输入，随机延迟，偶尔模拟打错字再删除

    Args:
        element: DrissionPage 元素对象
        text: 要输入的文本
        char_delay_min: 每字符最小延迟（秒）
        char_delay_max: 每字符最大延迟（秒）
        mistake_rate: 打错字概率（0.0-1.0）
    """
    for i, char in enumerate(text):
        # 随机打错字
        if mistake_rate > 0 and random.random() < mistake_rate and char.isalpha():
            wrong_chars = "qwertyuiopasdfghjklzxcvbnm"
            wrong = random.choice(wrong_chars)
            element.input(wrong, clear=False)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            # 删除错误字符
            element.input("\ue003", clear=False)  # Backspace
            await asyncio.sleep(random.uniform(0.1, 0.2))

        element.input(char, clear=False)

        delay = char_delay_min + random.random() * (char_delay_max - char_delay_min)

        # 单词边界处稍微停顿
        if char in (' ', '，', '。', '？', '！', ',', '.', '?', '!'):
            delay += random.uniform(0.05, 0.2)

        # 每隔若干字符有较长停顿（模拟思考）
        if i % random.randint(8, 20) == 0 and i > 0:
            delay += random.uniform(0.3, 0.8)

        await asyncio.sleep(delay)


async def human_scroll(page: Any, direction: str = "down",
                       amount: int = 300,
                       steps: int = 5) -> None:
    """随机分段滚动，模拟人工阅读

    Args:
        page: DrissionPage 页面对象
        direction: 滚动方向 (down/up/left/right)
        amount: 目标总滚动量（像素）
        steps: 分几步完成滚动
    """
    # 随机化总量 ±20%
    total = int(amount * (0.8 + random.random() * 0.4))
    per_step = total // steps

    for step in range(steps):
        # 每步随机偏差
        step_amount = per_step + random.randint(-20, 20)
        step_amount = max(10, step_amount)

        if direction == "down":
            page.scroll.down(step_amount)
        elif direction == "up":
            page.scroll.up(step_amount)
        elif direction == "left":
            page.scroll.left(step_amount)
        elif direction == "right":
            page.scroll.right(step_amount)

        # 步间随机延迟，模拟阅读
        await asyncio.sleep(0.1 + random.random() * 0.3)

    # 最终停顿
    await asyncio.sleep(0.2 + random.random() * 0.5)


async def random_mouse_move(page: Any, move_count: int = 3) -> None:
    """随机鼠标移动轨迹，模拟人工操作间歇性移动

    使用贝塞尔曲线插值生成自然轨迹。

    Args:
        page: DrissionPage 页面对象
        move_count: 随机移动次数
    """
    try:
        # 获取当前视口大小
        viewport = page.run_js("return {w: window.innerWidth, h: window.innerHeight};")
        vw = viewport.get("w", 1280) if viewport else 1280
        vh = viewport.get("h", 720) if viewport else 720

        for _ in range(move_count):
            # 随机目标位置（避免边角，留 100px 边距）
            tx = random.randint(100, max(200, vw - 100))
            ty = random.randint(100, max(200, vh - 100))

            # 贝塞尔曲线控制点
            points = _bezier_points(
                random.randint(0, vw), random.randint(0, vh),
                tx, ty,
                steps=random.randint(8, 20)
            )

            for px, py in points:
                js = f"document.dispatchEvent(new MouseEvent('mousemove', {{clientX:{px}, clientY:{py}, bubbles:true}}));"
                page.run_js(js)
                await asyncio.sleep(random.uniform(0.01, 0.04))

            await asyncio.sleep(random.uniform(0.1, 0.4))

    except Exception:
        # 鼠标移动失败不影响主流程
        pass


def _bezier_points(x0: float, y0: float, x1: float, y1: float,
                   steps: int = 10):
    """生成贝塞尔曲线插值点（模拟人工鼠标轨迹）"""
    # 随机控制点
    cx = (x0 + x1) / 2 + random.uniform(-100, 100)
    cy = (y0 + y1) / 2 + random.uniform(-100, 100)

    points = []
    for i in range(steps + 1):
        t = i / steps
        # 二阶贝塞尔公式
        px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        points.append((int(px), int(py)))
    return points
