"""recruiter.py - BOSS直聘招聘者操作

核心业务：VIP筛选简历 → AI评分 → 打招呼+跟进话术 → 下载简历
"""

import asyncio
import json
import logging
import random
from typing import Any, Dict, List, Optional

from anti_detect.behavior import human_delay, human_type, human_scroll

logger = logging.getLogger(__name__)

BOSS_RECRUITER_URL = "https://www.zhipin.com/web/recruit/geek/recommend?scene=1"
BOSS_CHAT_URL = "https://www.zhipin.com/web/recruit/chat"


class BossRecruiter:
    """BOSS直聘招聘者操作类"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.daily_greet_count = 0

    async def get_candidates(self, page: Any, filters: Dict[str, Any] = None) -> List[Dict]:
        """获取候选人列表（VIP筛选条件）

        Args:
            page: DrissionPage 实例
            filters: 筛选条件字典
                - education: 学历要求 (不限/大专/本科/硕士/博士)
                - experience: 工作年限范围 (如 "1-3")
                - salary_min: 最低月薪(K)
                - salary_max: 最高月薪(K)
                - city: 城市
                - keyword: 关键词
                - job_id: 职位ID（从哪个职位视角筛选）

        Returns:
            候选人信息列表
        """
        filters = filters or {}
        job_id = filters.get("job_id", "")
        keyword = filters.get("keyword", "")
        city = filters.get("city", "")
        batch_size = self.config.get("batch_size", filters.get("batch_size", 20))

        # 构建筛选URL
        url = BOSS_RECRUITER_URL
        if job_id:
            url = f"https://www.zhipin.com/web/recruit/geek/recommend?scene=1&jobId={job_id}"

        page.get(url)
        await asyncio.sleep(2 + random.random())

        # 设置筛选条件
        if keyword:
            search_box = page.ele("css:.search-input", timeout=5) or page.ele("css:input[placeholder*='搜索']", timeout=5)
            if search_box:
                await human_type(search_box, keyword)
                search_btn = page.ele("css:.search-btn", timeout=3) or page.ele("css:button.search", timeout=3)
                if search_btn:
                    search_btn.click()
                    await asyncio.sleep(1.5 + random.random())

        # 设置学历筛选
        education = filters.get("education", "")
        if education and education != "不限":
            edu_selectors = {
                "大专": "101",
                "本科": "102",
                "硕士": "103",
                "博士": "104",
            }
            edu_code = edu_selectors.get(education)
            if edu_code:
                edu_btn = page.ele(f"css:[data-degree='{edu_code}']", timeout=3)
                if edu_btn:
                    edu_btn.click()
                    await asyncio.sleep(0.8 + random.random())

        # 设置经验筛选
        experience = filters.get("experience", "")
        if experience:
            exp_btn = page.ele(f"css:[data-experience='{experience}']", timeout=3)
            if exp_btn:
                exp_btn.click()
                await asyncio.sleep(0.8 + random.random())

        # 设置薪资筛选
        salary_min = filters.get("salary_min", 0)
        salary_max = filters.get("salary_max", 0)
        if salary_min > 0 or salary_max > 0:
            salary_range = f"{salary_min}K-{salary_max}K"
            salary_btn = page.ele(f"css:[data-salary='{salary_range}']", timeout=3)
            if salary_btn:
                salary_btn.click()
                await asyncio.sleep(0.8 + random.random())

        # 设置城市筛选
        if city:
            city_filter = page.ele("css:.city-select", timeout=3)
            if city_filter:
                city_filter.click()
                await asyncio.sleep(0.5)
                city_option = page.ele(f"text:{city}", timeout=5)
                if city_option:
                    city_option.click()
                    await asyncio.sleep(0.8 + random.random())

        await asyncio.sleep(1.0 + random.random())

        # 滚动加载更多候选人
        candidates = []
        scrolls_needed = max(1, batch_size // 10)
        for scroll_idx in range(scrolls_needed):
            await human_scroll(page, "down", 300, steps=3)

            # 解析候选人列表
            geek_items = page.eles("css:.geek-item") or page.eles("css:.recommend-list-item") or page.eles("css:.card-inner")
            for item in geek_items:
                try:
                    candidate = self._parse_candidate_item(item)
                    if candidate and candidate not in candidates:
                        candidates.append(candidate)
                except Exception as e:
                    logger.debug(f"解析候选人失败: {e}")
                    continue

            await asyncio.sleep(0.5 + random.random() * 0.5)

            if len(candidates) >= batch_size:
                break

        logger.info(f"获取到 {len(candidates)} 个候选人")
        return candidates[:batch_size]

    def _parse_candidate_item(self, item: Any) -> Optional[Dict]:
        """解析单个候选人卡片元素"""
        try:
            # 基础信息
            name_el = item.ele("css:.geek-name", timeout=1) or item.ele("css:.name-text", timeout=1)
            name = name_el.text.strip() if name_el else ""

            title_el = item.ele("css:.geek-title", timeout=1) or item.ele("css:.job-title", timeout=1)
            title = title_el.text.strip() if title_el else ""

            # 学历
            edu_el = item.ele("css:.geek-edu", timeout=1) or item.ele("css:[class*='edu']", timeout=1)
            education = edu_el.text.strip() if edu_el else ""

            # 工作年限
            exp_el = item.ele("css:.geek-experience", timeout=1) or item.ele("css:[class*='experience']", timeout=1)
            experience = exp_el.text.strip() if exp_el else ""

            # 期望薪资
            salary_el = item.ele("css:.geek-salary", timeout=1) or item.ele("css:[class*='salary']", timeout=1)
            salary = salary_el.text.strip() if salary_el else ""

            # 城市
            city_el = item.ele("css:.geek-city", timeout=1) or item.ele("css:[class*='city']", timeout=1)
            city = city_el.text.strip() if city_el else ""

            # 候选人ID（从链接提取）
            link_el = item.ele("css:a[href*='geek']", timeout=1) or item.ele("css:.geek-link", timeout=1)
            geek_id = ""
            if link_el:
                href = link_el.attr("href") or ""
                if "geekId=" in href:
                    geek_id = href.split("geekId=")[-1].split("&")[0]
                elif "/geek/" in href:
                    geek_id = href.split("/geek/")[-1].split("?")[0]

            return {
                "id": geek_id,
                "name": name,
                "title": title,
                "education": education,
                "experience": experience,
                "salary": salary,
                "city": city,
            }
        except Exception:
            return None

    async def greet_candidate(self, page: Any, candidate_id: str,
                              message: str = "",
                              followup: str = "",
                              job_id: str = "") -> Dict[str, Any]:
        """发送招呼语给单个候选人

        Args:
            page: DrissionPage 实例
            candidate_id: 候选人 geek_id
            message: 招呼语内容
            followup: 打招呼后的跟进话术
            job_id: 职位ID（招呼时需要指定职位）

        Returns:
            操作结果字典
        """
        greet_url = f"https://www.zhipin.com/web/recruit/geek/recommend?scene=1"
        if job_id:
            greet_url += f"&jobId={job_id}"

        page.get(greet_url)
        await asyncio.sleep(2 + random.random())

        # 查找候选人并点击"打招呼"按钮
        greet_btn = page.ele(f"css:.greet-btn[data-geek-id='{candidate_id}']", timeout=5)
        if not greet_btn:
            greet_btn = page.ele(f"css:.btn-greet[data-geek-id='{candidate_id}']", timeout=5)
        if not greet_btn:
            # 尝试通过候选人卡片内查找
            geek_card = page.ele(f"css:.geek-item[data-geek-id='{candidate_id}']", timeout=5)
            if geek_card:
                greet_btn = geek_card.ele("css:.greet-btn", timeout=3) or geek_card.ele("css:.btn-greet", timeout=3)

        if greet_btn:
            await human_delay(0.5, 1.5)
            greet_btn.click()
            await asyncio.sleep(1.0 + random.random())

            # 如果有招呼语输入框
            msg_input = page.ele("css:.greet-msg-input", timeout=3) or page.ele("css:.chat-input", timeout=3)
            if msg_input and message:
                await human_type(msg_input, message)
                send_btn = page.ele("css:.send-btn", timeout=3) or page.ele("css:.btn-send", timeout=3)
                if send_btn:
                    send_btn.click()
                    await asyncio.sleep(0.5 + random.random())

            # 发送跟进话术
            if followup:
                # 切换到聊天页面发送
                page.get(BOSS_CHAT_URL)
                await asyncio.sleep(2 + random.random())

                # 找到与该候选人的对话
                chat_item = page.ele(f"css:[data-geek-id='{candidate_id}']", timeout=5)
                if chat_item:
                    chat_item.click()
                    await asyncio.sleep(1.0 + random.random())

                    chat_input = page.ele("css:.chat-input", timeout=3) or page.ele("css:.msg-input", timeout=3)
                    if chat_input:
                        await human_type(chat_input, followup)
                        send_btn = page.ele("css:.send-btn", timeout=3)
                        if send_btn:
                            send_btn.click()
                            await asyncio.sleep(0.5 + random.random())

            self.daily_greet_count += 1
            return {"success": True, "candidate_id": candidate_id}

        return {"success": False, "error": f"未找到打招呼按钮: {candidate_id}"}

    async def batch_greet(self, page: Any, candidate_ids: List[str],
                         message_template: str = "",
                         followup_template: str = "",
                         job_id: str = "",
                         interval_range: tuple = (30, 120)) -> List[Dict]:
        """批量发招呼，随机间隔防止被检测

        Args:
            page: DrissionPage 实例
            candidate_ids: 候选人 ID 列表
            message_template: 招呼语模板
            followup_template: 跟进话术模板
            job_id: 职位ID
            interval_range: (最小间隔秒, 最大间隔秒)

        Returns:
            每个候选人的操作结果列表
        """
        results = []
        daily_limit = self.config.get("daily_greet_limit", 100)

        for idx, cid in enumerate(candidate_ids):
            if self.daily_greet_count >= daily_limit:
                logger.warning(f"已达到每日招呼上限 {daily_limit}")
                break

            # 变量替换
            msg = message_template.replace("{name}", str(cid))
            followup = followup_template.replace("{name}", str(cid))

            result = await self.greet_candidate(page, cid, msg, followup, job_id)
            results.append(result)

            if result.get("success"):
                # 随机间隔
                interval = random.uniform(interval_range[0], interval_range[1])
                logger.info(f"已招呼 {cid}，等待 {interval:.1f} 秒...")
                await asyncio.sleep(interval)

        logger.info(f"批量招呼完成: 成功 {sum(1 for r in results if r.get('success'))} / {len(results)}")
        return results

    async def get_job_list(self, page: Any) -> List[Dict]:
        """获取在招职位列表

        Args:
            page: DrissionPage 实例

        Returns:
            职位信息列表 [{job_id, title, status}]
        """
        page.get("https://www.zhipin.com/web/recruit/job")
        await asyncio.sleep(2 + random.random())

        jobs = []
        job_items = page.eles("css:.job-item") or page.eles("css:.job-card") or page.eles("css:.job-list-item")

        for item in job_items:
            try:
                title_el = item.ele("css:.job-name", timeout=2) or item.ele("css:.job-title", timeout=2)
                title = title_el.text.strip() if title_el else ""

                # 从链接获取 job_id
                link = item.ele("css:a", timeout=2)
                job_id = ""
                if link:
                    href = link.attr("href") or ""
                    if "jobId=" in href:
                        job_id = href.split("jobId=")[-1].split("&")[0]
                    elif "/job/" in href:
                        job_id = href.split("/job/")[-1].split("?")[0]

                status_el = item.ele("css:.job-status", timeout=2)
                status = status_el.text.strip() if status_el else "在招"

                jobs.append({
                    "job_id": job_id,
                    "title": title,
                    "status": status,
                })
            except Exception:
                continue

        logger.info(f"获取到 {len(jobs)} 个职位")
        return jobs