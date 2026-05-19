"""message.py - BOSS直聘消息管理"""

import asyncio
import logging
import re
from typing import Any, Dict, List

from anti_detect.behavior import human_delay, human_type

logger = logging.getLogger(__name__)


class BossMessage:
    """消息管理类"""

    async def get_conversations(self, page: Any) -> List[Dict]:
        """获取消息列表

        Args:
            page: DrissionPage 实例

        Returns:
            对话列表
        """
        page.get("https://www.zhipin.com/web/recruit/chat")
        await asyncio.sleep(2 + __import__("random").random())

        conversations = []
        items = (
            page.eles("css:.chat-list-item")
            or page.eles("css:.conversation-item")
            or page.eles("css:.im-list-item")
        )

        for item in items:
            try:
                name_el = item.ele("css:.name", timeout=2) or item.ele("css:.user-name", timeout=2)
                name = name_el.text.strip() if name_el else ""

                preview_el = item.ele("css:.msg-preview", timeout=2) or item.ele("css:.last-msg", timeout=2)
                preview = preview_el.text.strip() if preview_el else ""

                time_el = item.ele("css:.msg-time", timeout=2) or item.ele("css:.time", timeout=2)
                time_str = time_el.text.strip() if time_el else ""

                # 对话ID
                conv_id = item.attr("data-geek-id") or item.attr("data-conv-id") or ""
                link = item.ele("css:a", timeout=2)
                if not conv_id and link:
                    href = link.attr("href") or ""
                    m = re.search(r"geekId=(\w+)", href)
                    if m:
                        conv_id = m.group(1)

                unread_el = item.ele("css:.unread-count", timeout=2)
                unread_count = 0
                if unread_el:
                    try:
                        unread_count = int(unread_el.text.strip())
                    except ValueError:
                        unread_count = 1

                conversations.append({
                    "id": conv_id,
                    "name": name,
                    "preview": preview,
                    "time": time_str,
                    "unread": unread_count,
                })
            except Exception:
                continue

        logger.info(f"获取到 {len(conversations)} 个对话")
        return conversations

    async def get_messages(self, page: Any, conversation_id: str) -> List[Dict]:
        """获取指定对话的消息历史

        Args:
            page: DrissionPage 实例
            conversation_id: 对话 ID（geek_id）

        Returns:
            消息列表
        """
        chat_url = f"https://www.zhipin.com/web/recruit/chat?geekId={conversation_id}"
        page.get(chat_url)
        await asyncio.sleep(2 + __import__("random").random())

        messages = []
        msg_items = (
            page.eles("css:.chat-message-item")
            or page.eles("css:.message-item")
            or page.eles("css:.im-message")
        )

        for item in msg_items:
            try:
                is_mine = bool(
                    item.ele("css:.message-right", timeout=1)
                    or item.attr("class") and "self" in (item.attr("class") or "")
                )

                text_el = (
                    item.ele("css:.message-text", timeout=2)
                    or item.ele("css:.msg-content", timeout=2)
                    or item.ele("css:.text", timeout=2)
                )
                text = text_el.text.strip() if text_el else ""

                time_el = item.ele("css:.msg-time", timeout=2) or item.ele("css:.time", timeout=2)
                time_str = time_el.text.strip() if time_el else ""

                messages.append({
                    "is_mine": is_mine,
                    "text": text,
                    "time": time_str,
                })
            except Exception:
                continue

        return messages

    async def send_message(self, page: Any, conversation_id: str, text: str) -> bool:
        """发送消息

        Args:
            page: DrissionPage 实例
            conversation_id: 对话 ID
            text: 消息文本

        Returns:
            True 表示发送成功
        """
        chat_url = f"https://www.zhipin.com/web/recruit/chat?geekId={conversation_id}"
        page.get(chat_url)
        await asyncio.sleep(1.5 + __import__("random").random())

        # 找到消息输入框
        input_box = (
            page.ele("css:.chat-input", timeout=5)
            or page.ele("css:.msg-input", timeout=5)
            or page.ele("css:textarea.input", timeout=5)
            or page.ele("css:[contenteditable='true']", timeout=5)
        )

        if not input_box:
            logger.error(f"未找到消息输入框: {conversation_id}")
            return False

        await human_delay(0.3, 0.8)
        input_box.click()
        await asyncio.sleep(0.3)

        await human_type(input_box, text)
        await asyncio.sleep(0.2 + __import__("random").random() * 0.3)

        # 点击发送
        send_btn = (
            page.ele("css:.send-btn", timeout=3)
            or page.ele("css:.btn-send", timeout=3)
            or page.ele("css:button.send", timeout=3)
        )
        if send_btn:
            send_btn.click()
        else:
            # 尝试 Enter 键发送
            input_box.input("\n")

        await asyncio.sleep(0.5 + __import__("random").random() * 0.5)

        logger.info(f"已向 {conversation_id} 发送消息，长度: {len(text)}")
        return True

    def render_template(self, template: str, variables: Dict[str, str]) -> str:
        """招呼语模板变量替换

        支持 {name}, {position}, {company} 等变量。

        Args:
            template: 含变量占位符的模板文本
            variables: 变量字典

        Returns:
            替换后的文本
        """
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        # 清理未替换的占位符
        result = re.sub(r"\{[^}]+\}", "", result)
        return result
