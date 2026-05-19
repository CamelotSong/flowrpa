"""resume.py - BOSS直聘简历读取

支持普通DOM文本、iframe内容、canvas渲染内容的提取。
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional

from anti_detect.behavior import human_delay, human_scroll

logger = logging.getLogger(__name__)


class BossResume:
    """简历读取类"""

    def __init__(self, canvas_ocr=None):
        self.canvas_ocr = canvas_ocr

    async def get_resume(self, page: Any, candidate_id: str) -> Dict[str, Any]:
        """获取完整简历"""
        import random
        resume_url = f"https://www.zhipin.com/web/recruit/geek/resume?geekId={candidate_id}"
        page.get(resume_url)
        await asyncio.sleep(2 + random.random())

        resume = {
            "id": candidate_id,
            "raw_text": "",
            "name": "",
            "title": "",
            "education": "",
            "experience": "",
            "skills": [],
            "work_history": [],
            "education_history": [],
            "canvas_texts": [],
        }

        dom_text = await self._extract_dom_text(page)
        resume["raw_text"] = dom_text
        resume.update(self._parse_structured_info(page, dom_text))

        iframe_text = await self._extract_iframe_content(page, "iframe")
        if iframe_text:
            resume["raw_text"] += "\n" + iframe_text

        if self.canvas_ocr:
            canvas_texts = await self._extract_canvas_contents(page)
            if canvas_texts:
                resume["canvas_texts"] = canvas_texts
                resume["raw_text"] += "\n" + "\n".join(canvas_texts)

        await human_scroll(page, "down", 500, steps=5)
        await asyncio.sleep(0.5)
        logger.info(f"简历提取完成: {candidate_id}, 文本长度: {len(resume['raw_text'])}")
        return resume

    async def _extract_dom_text(self, page: Any) -> str:
        """提取页面主要DOM文本"""
        try:
            selectors = [
                ".resume-detail", ".geek-resume",
                ".resume-content", ".detail-content",
                "#resume-container",
            ]
            for sel in selectors:
                container = page.ele(f"css:{sel}", timeout=3)
                if container:
                    text = container.text or ""
                    if len(text) > 50:
                        return text.strip()

            js = (
                "const body = document.querySelector('.resume-detail')"
                " || document.querySelector('.geek-resume')"
                " || document.querySelector('.resume-content')"
                " || document.querySelector('main')"
                " || document.body;"
                " return body ? body.innerText : '';"
            )
            text = page.run_js(js) or ""
            return text.strip()
        except Exception as e:
            logger.error(f"提取DOM文本失败: {e}")
            return ""

    async def _extract_iframe_content(self, page: Any, iframe_selector: str = "iframe") -> str:
        """提取 iframe 中的内容"""
        try:
            iframe = page.ele(f"css:{iframe_selector}", timeout=3)
            if not iframe:
                return ""

            iframe_page = page.get_frame(iframe_selector)
            if iframe_page:
                text = iframe_page.run_js("return document.body ? document.body.innerText : '';") or ""
                return text.strip()

            esc = iframe_selector.replace("'", "\\'")
            js = (
                f"const f = document.querySelector('{esc}');"
                " if (f && f.contentDocument) { return f.contentDocument.body.innerText || ''; }"
                " return '';"
            )
            text = page.run_js(js) or ""
            return text.strip()
        except Exception as e:
            logger.debug(f"提取iframe内容失败: {e}")
            return ""

    async def _extract_canvas_contents(self, page: Any) -> list:
        """提取页面所有canvas元素中的文字"""
        canvas_texts = []
        try:
            canvases = page.eles("css:canvas")
            for i, _ in enumerate(canvases):
                if self.canvas_ocr:
                    text = await self.canvas_ocr.extract_canvas_text(
                        page, f"canvas:nth-of-type({i + 1})"
                    )
                    if text and text.strip():
                        canvas_texts.append(text.strip())
        except Exception as e:
            logger.debug(f"提取Canvas内容失败: {e}")
        return canvas_texts

    def _parse_structured_info(self, page: Any, dom_text: str) -> Dict[str, Any]:
        """从页面和DOM文本中解析结构化信息"""
        info: Dict[str, Any] = {
            "name": "",
            "title": "",
            "education": "",
            "experience": "",
            "skills": [],
            "work_history": [],
            "education_history": [],
        }

        try:
            name_el = page.ele("css:.geek-name", timeout=2) or page.ele("css:.name-text", timeout=2)
            if name_el:
                info["name"] = name_el.text.strip()

            title_el = page.ele("css:.geek-title", timeout=2) or page.ele("css:.job-title", timeout=2)
            if title_el:
                info["title"] = title_el.text.strip()

            edu_el = page.ele("css:.geek-edu", timeout=2)
            if edu_el:
                info["education"] = edu_el.text.strip()

            exp_el = page.ele("css:.geek-experience", timeout=2)
            if exp_el:
                info["experience"] = exp_el.text.strip()

            if not info["name"]:
                m = re.search(r"姓名[：:]\s*(\S+)", dom_text)
                if m:
                    info["name"] = m.group(1)

            if not info["education"]:
                m = re.search(r"学历[：:]\s*(\S+)", dom_text)
                if m:
                    info["education"] = m.group(1)

            skill_els = page.eles("css:.skill-tag") or page.eles("css:.tag-item")
            info["skills"] = [el.text.strip() for el in skill_els if el.text.strip()]

            work_items = page.eles("css:.work-item") or page.eles("css:.experience-item")
            for item in work_items:
                wt = item.text or ""
                if wt.strip():
                    info["work_history"].append(wt.strip())

            edu_items = page.eles("css:.education-item") or page.eles("css:.edu-item")
            for item in edu_items:
                et = item.text or ""
                if et.strip():
                    info["education_history"].append(et.strip())

        except Exception as e:
            logger.debug(f"解析结构化信息失败: {e}")

        return info
