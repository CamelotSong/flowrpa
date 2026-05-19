"""downloader.py - 简历下载

下载候选人简历 PDF，文件命名为 {姓名}_{职位}_{日期}.pdf
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class ResumeDownloader:
    """简历下载器"""

    def __init__(self, download_dir: str = "~/Downloads/boss_resumes"):
        self.download_dir = os.path.expanduser(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)

    async def download(self, page: Any, candidate_id: str,
                       name: str = "",
                       position: str = "") -> str:
        """下载候选人简历

        流程：
        1. 在简历页面找到"下载简历"按钮
        2. 触发下载（或截获下载URL后自行下载）
        3. 按命名规范保存文件

        Args:
            page: DrissionPage 实例
            candidate_id: 候选人 geek_id
            name: 候选人姓名（用于命名）
            position: 候选人职位（用于命名）

        Returns:
            本地文件路径，失败返回空字符串
        """
        resume_url = f"https://www.zhipin.com/web/recruit/geek/resume?geekId={candidate_id}"
        page.get(resume_url)
        await asyncio.sleep(2 + __import__("random").random())

        # 构建输出文件名
        filename = self._build_filename(name, position, candidate_id)
        output_path = os.path.join(self.download_dir, filename)

        # 方案1：通过下载按钮触发浏览器下载
        result = await self._click_download(page, output_path)
        if result:
            return result

        # 方案2：截获下载URL后用 aiohttp 下载
        download_url = await self._get_download_url(page)
        if download_url:
            cookies = self._get_cookies_dict(page)
            result = await self._fetch_pdf(download_url, output_path, cookies)
            if result:
                return result

        # 方案3：打印为PDF（DrissionPage 支持）
        try:
            page.get_screenshot(path=self.download_dir, name=filename.replace(".pdf", ".png"), full_page=True)
            png_path = os.path.join(self.download_dir, filename.replace(".pdf", ".png"))
            if os.path.exists(png_path):
                logger.info(f"截图保存为 {png_path}（PDF下载失败的备选方案）")
                return png_path
        except Exception as e:
            logger.warning(f"截图备选方案失败: {e}")

        logger.error(f"简历下载失败: {candidate_id}")
        return ""

    async def _click_download(self, page: Any, output_path: str) -> str:
        """点击页面上的下载简历按钮"""
        download_selectors = [
            "css:.btn-download",
            "css:.download-resume",
            "css:button[class*='download']",
            "text:下载简历",
            "text:下载PDF",
        ]

        for selector in download_selectors:
            try:
                btn = page.ele(selector, timeout=3)
                if btn:
                    # 设置下载路径
                    download_dir = os.path.dirname(output_path)
                    filename = os.path.basename(output_path)
                    page.set.download_path(download_dir)

                    btn.click()
                    await asyncio.sleep(3)

                    # 等待下载完成
                    downloaded = self._find_downloaded_file(download_dir)
                    if downloaded:
                        final_path = output_path
                        os.rename(downloaded, final_path)
                        logger.info(f"简历下载完成: {final_path}")
                        return final_path
            except Exception:
                continue

        return ""

    async def _get_download_url(self, page: Any) -> str:
        """截获下载 URL"""
        try:
            js = """
            const links = document.querySelectorAll('a[href*=".pdf"], a[href*="download"], a[href*="resume"]');
            for (const link of links) {
                if (link.href && (link.href.includes('.pdf') || link.href.includes('/download'))) {
                    return link.href;
                }
            }
            return '';
            """
            url = page.run_js(js) or ""
            if url:
                return url

            # 尝试从 API 接口获取
            js2 = """
            const matches = document.documentElement.innerHTML.match(/https?:\\/\\/[^"'\\s]+\\.pdf[^"'\\s]*/);
            return matches ? matches[0] : '';
            """
            url = page.run_js(js2) or ""
            return url
        except Exception:
            return ""

    async def _fetch_pdf(self, url: str, output_path: str, cookies: dict) -> str:
        """用 aiohttp 下载 PDF"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://www.zhipin.com/",
            }
            async with aiohttp.ClientSession(cookies=cookies) as session:
                async with session.get(
                    url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        if "pdf" in content_type or url.endswith(".pdf"):
                            data = await resp.read()
                            with open(output_path, "wb") as f:
                                f.write(data)
                            logger.info(f"PDF下载完成: {output_path} ({len(data)} bytes)")
                            return output_path
        except Exception as e:
            logger.error(f"PDF下载失败: {e}")
        return ""

    def _build_filename(self, name: str, position: str, candidate_id: str) -> str:
        """构建文件名: {姓名}_{职位}_{日期}.pdf"""
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = self._sanitize(name or candidate_id[:8])
        safe_pos = self._sanitize(position or "简历")
        return f"{safe_name}_{safe_pos}_{date_str}.pdf"

    def _sanitize(self, text: str) -> str:
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:*?"<>|\s]', "_", text)[:30]

    def _find_downloaded_file(self, directory: str) -> str:
        """在目录中查找最新下载的PDF文件"""
        try:
            files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if f.endswith(".pdf") or f.endswith(".pdf.crdownload")
            ]
            if files:
                # 按修改时间排序，取最新
                files.sort(key=os.path.getmtime, reverse=True)
                latest = files[0]
                if not latest.endswith(".crdownload"):
                    return latest
        except Exception:
            pass
        return ""

    def _get_cookies_dict(self, page: Any) -> dict:
        """从页面获取 cookies 字典"""
        try:
            return page.cookies().as_dict()
        except Exception:
            return {}
