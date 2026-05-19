"""auth.py - BOSS直聘 登录和会话管理"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

BOSS_LOGIN_URL = "https://www.zhipin.com/web/user/?ka=header-login"
BOSS_HOME_URL = "https://www.zhipin.com/"
BOSS_GEEK_HOME = "https://www.zhipin.com/web/geek/job"

# 判断是否已登录的选择器（头像/用户名）
LOGGED_IN_SELECTORS = [
    ".user-nav",
    ".nav-figure",
    "[class*='header-username']",
    "a[href*='/web/user/account']",
]


class BossAuth:
    """BOSS直聘 登录和会话管理"""

    def __init__(self, cookies_path: str = "~/.flowrpa/boss_cookies.json"):
        self.cookies_path = os.path.expanduser(cookies_path)
        os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)

    def load_cookies(self, path: Optional[str] = None) -> Optional[list]:
        """加载保存的 cookie

        Args:
            path: cookie 文件路径，默认使用初始化时的路径

        Returns:
            cookie 列表，若文件不存在则返回 None
        """
        p = path or self.cookies_path
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                cookies = json.load(f)
                logger.info(f"已加载 {len(cookies)} 个 cookie")
                return cookies
        except Exception as e:
            logger.error(f"加载 cookie 失败: {e}")
            return None

    def save_cookies(self, page: Any, path: Optional[str] = None) -> None:
        """保存当前页面的 cookie

        Args:
            page: DrissionPage 实例
            path: 保存路径，默认使用初始化时的路径
        """
        p = path or self.cookies_path
        try:
            cookies = page.cookies().as_dict()
            # 转换为列表格式
            cookie_list = [{"name": k, "value": v} for k, v in cookies.items()]
            with open(p, "w", encoding="utf-8") as f:
                json.dump(cookie_list, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(cookie_list)} 个 cookie 到 {p}")
        except Exception as e:
            logger.error(f"保存 cookie 失败: {e}")

    def set_cookies(self, page: Any, cookies: list) -> None:
        """将 cookie 设置到页面

        Args:
            page: DrissionPage 实例
            cookies: cookie 列表
        """
        try:
            for cookie in cookies:
                if isinstance(cookie, dict):
                    page.set.cookies(cookie)
            logger.info(f"已设置 {len(cookies)} 个 cookie")
        except Exception as e:
            logger.error(f"设置 cookie 失败: {e}")

    async def login(self, page: Any, timeout: int = 180) -> bool:
        """跳转到登录页，等待用户扫码/手动登录，然后保存 cookie

        Args:
            page: DrissionPage 实例
            timeout: 等待登录的最长秒数

        Returns:
            True 表示登录成功
        """
        logger.info("跳转到 BOSS直聘 登录页...")
        page.get(BOSS_LOGIN_URL)
        await asyncio.sleep(2)

        logger.info(f"请在 {timeout} 秒内完成登录（扫码或账号密码）...")
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            if await self.is_logged_in(page):
                logger.info("检测到登录成功！")
                self.save_cookies(page)
                return True
            await asyncio.sleep(3)

        logger.error(f"登录超时（{timeout}秒）")
        return False

    async def is_logged_in(self, page: Any) -> bool:
        """检查当前页面是否已登录

        Args:
            page: DrissionPage 实例

        Returns:
            True 表示已登录
        """
        try:
            # 检查登录相关选择器是否存在
            for selector in LOGGED_IN_SELECTORS:
                el = page.ele(f"css:{selector}", timeout=2)
                if el:
                    return True

            # 通过 JS 检查 cookie 中是否有登录 token
            js_check = """
            const cookies = document.cookie;
            return cookies.includes('bst=') || cookies.includes('geek_zp_token=') || cookies.includes('__uid=');
            """
            result = page.run_js(js_check)
            if result:
                return True

            # 检查当前 URL 是否在用户个人页面（非登录页）
            url = page.url
            if "web/user/?ka=header-login" not in url and (
                "zhipin.com" in url and "/login" not in url
            ):
                # 尝试访问需要登录的页面
                page.get("https://www.zhipin.com/web/geek/job")
                await asyncio.sleep(1.5)
                current_url = page.url
                if "/user/" not in current_url or "ka=header-login" not in current_url:
                    return True

            return False
        except Exception as e:
            logger.debug(f"登录检查异常: {e}")
            return False

    async def ensure_logged_in(self, page: Any) -> bool:
        """确保已登录，若未登录则触发登录流程

        Args:
            page: DrissionPage 实例

        Returns:
            True 表示最终已登录
        """
        # 先尝试加载保存的 cookie
        cookies = self.load_cookies()
        if cookies:
            page.get(BOSS_HOME_URL)
            await asyncio.sleep(1.5)
            self.set_cookies(page, cookies)
            page.refresh()
            await asyncio.sleep(2)
            if await self.is_logged_in(page):
                logger.info("Cookie 登录成功")
                return True
            logger.info("Cookie 已失效，需要重新登录")

        # 触发手动登录
        return await self.login(page)
