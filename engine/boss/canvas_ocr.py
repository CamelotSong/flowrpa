"""canvas_ocr.py - Canvas 内容 OCR 提取

方案1：注入 JS hook canvas.toDataURL()，截获图片数据
方案2：直接截图 canvas 区域
然后用 easyocr 或 pytesseract 识别文字
"""

import asyncio
import base64
import io
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CanvasOCR:
    """Canvas 内容 OCR 提取"""

    def __init__(self, engine: str = "easyocr", languages: list = None):
        """
        Args:
            engine: OCR 引擎，'easyocr' 或 'tesseract'
            languages: 语言列表，默认 ['ch_sim', 'en']（简中+英文）
        """
        self.engine = engine
        self.languages = languages or ["ch_sim", "en"]
        self._ocr_reader = None

    def _get_reader(self):
        """延迟初始化 OCR 引擎（加载较慢）"""
        if self._ocr_reader is not None:
            return self._ocr_reader

        if self.engine == "easyocr":
            try:
                import easyocr
                self._ocr_reader = easyocr.Reader(
                    self.languages,
                    gpu=False,
                    verbose=False,
                )
                return self._ocr_reader
            except ImportError:
                logger.warning("easyocr 未安装，尝试 tesseract")
                self.engine = "tesseract"

        if self.engine == "tesseract":
            try:
                import pytesseract
                self._ocr_reader = pytesseract
                return self._ocr_reader
            except ImportError:
                logger.error("easyocr 和 pytesseract 均未安装，Canvas OCR 不可用")
                return None

        return None

    async def extract_canvas_text(self, page: Any, canvas_selector: str) -> str:
        """从 Canvas 元素提取文字

        首先尝试 JS hook 截获 toDataURL，失败则截图后 OCR。

        Args:
            page: DrissionPage 实例
            canvas_selector: Canvas 元素的 CSS 选择器

        Returns:
            识别出的文字
        """
        # 方案1：通过 JS 获取 canvas 内容（最准确）
        image_data = await self._get_canvas_data_via_js(page, canvas_selector)

        if not image_data:
            # 方案2：截图
            image_data = await self._get_canvas_data_via_screenshot(page, canvas_selector)

        if not image_data:
            return ""

        # OCR 识别
        text = self._image_to_text(image_data)
        return text

    async def _get_canvas_data_via_js(self, page: Any, canvas_selector: str) -> Optional[bytes]:
        """通过 JS 获取 Canvas 图片数据

        注入脚本劫持 toDataURL 方法，或直接调用获取当前内容。
        """
        try:
            esc = canvas_selector.replace("'", "\\'")
            js = f"""
            const canvas = document.querySelector('{esc}');
            if (!canvas) return null;
            try {{
                return canvas.toDataURL('image/png');
            }} catch(e) {{
                return null;
            }}
            """
            data_url = page.run_js(js)
            if data_url and data_url.startswith("data:image"):
                # 去除 data:image/png;base64, 前缀
                b64 = data_url.split(",", 1)[-1]
                return base64.b64decode(b64)
        except Exception as e:
            logger.debug(f"JS获取Canvas数据失败: {e}")
        return None

    async def _get_canvas_data_via_screenshot(self, page: Any, canvas_selector: str) -> Optional[bytes]:
        """通过截图获取 Canvas 内容"""
        try:
            element = page.ele(f"css:{canvas_selector}", timeout=3)
            if not element:
                return None

            # 截取元素截图
            tmp_path = f"/tmp/flowrpa_canvas_{hash(canvas_selector) & 0xFFFF}.png"
            element.get_screenshot(path="/tmp", name=f"flowrpa_canvas_{hash(canvas_selector) & 0xFFFF}.png")

            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    data = f.read()
                os.remove(tmp_path)
                return data
        except Exception as e:
            logger.debug(f"截图获取Canvas数据失败: {e}")
        return None

    def _image_to_text(self, image_data: bytes) -> str:
        """OCR 识别图片中的文字

        Args:
            image_data: 图片的二进制数据（PNG/JPEG格式）

        Returns:
            识别出的文字
        """
        reader = self._get_reader()
        if not reader:
            return ""

        try:
            if self.engine == "easyocr":
                import numpy as np
                from PIL import Image

                img = Image.open(io.BytesIO(image_data)).convert("RGB")
                img_array = np.array(img)
                results = reader.readtext(img_array)
                # 按垂直位置排序，拼接文字
                results.sort(key=lambda r: r[0][0][1])  # 按 y 坐标排序
                texts = [r[1] for r in results if r[2] > 0.3]  # 置信度 > 0.3
                return " ".join(texts)

            elif self.engine == "tesseract":
                from PIL import Image
                img = Image.open(io.BytesIO(image_data))
                # 简体中文+英文
                text = reader.image_to_string(img, lang="chi_sim+eng")
                return text.strip()

        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")

        return ""
