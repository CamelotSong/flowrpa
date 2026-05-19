"""filter.py - 候选人过滤器"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

EDUCATION_RANK = {
    "不限": 0,
    "大专": 1,
    "本科": 2,
    "硕士": 3,
    "博士": 4,
}


class CandidateFilter:
    """候选人过滤器

    根据多维度条件过滤候选人列表。
    """

    def filter(self, candidates: List[Dict], criteria: Dict[str, Any]) -> List[Dict]:
        """过滤候选人

        Args:
            candidates: 候选人字典列表
            criteria: 筛选条件，支持：
                - education: 最低学历要求（大专/本科/硕士/博士）
                - experience_min: 最少工作年限
                - experience_max: 最多工作年限
                - salary_min: 最低期望薪资（K/月）
                - salary_max: 最高期望薪资（K/月）
                - city: 城市（支持列表或字符串）
                - keyword: 关键词（在简历文本中匹配）
                - exclude_keywords: 排除关键词列表

        Returns:
            过滤后的候选人列表
        """
        result = []
        for candidate in candidates:
            if self._matches(candidate, criteria):
                result.append(candidate)

        logger.info(f"过滤完成: {len(candidates)} -> {len(result)} 人")
        return result

    def _matches(self, candidate: Dict, criteria: Dict) -> bool:
        """判断单个候选人是否满足条件"""

        # 学历过滤
        min_edu = criteria.get("education", "")
        if min_edu and min_edu != "不限":
            candidate_edu = candidate.get("education", "")
            min_rank = EDUCATION_RANK.get(min_edu, 0)
            cand_rank = EDUCATION_RANK.get(self._normalize_education(candidate_edu), 0)
            if cand_rank < min_rank:
                return False

        # 工作年限过滤
        exp_min = criteria.get("experience_min")
        exp_max = criteria.get("experience_max")
        if exp_min is not None or exp_max is not None:
            years = self._parse_experience_years(candidate.get("experience", ""))
            if exp_min is not None and years < exp_min:
                return False
            if exp_max is not None and years > exp_max:
                return False

        # 薪资过滤（期望薪资）
        sal_min = criteria.get("salary_min")
        sal_max = criteria.get("salary_max")
        if sal_min is not None or sal_max is not None:
            sal_low, sal_high = self._parse_salary(candidate.get("salary", ""))
            if sal_low > 0 or sal_high > 0:
                if sal_min is not None and sal_high > 0 and sal_high < sal_min:
                    return False
                if sal_max is not None and sal_low > 0 and sal_low > sal_max:
                    return False

        # 城市过滤
        city_filter = criteria.get("city")
        if city_filter:
            cities = city_filter if isinstance(city_filter, list) else [city_filter]
            candidate_city = candidate.get("city", "")
            if candidate_city and not any(c in candidate_city or candidate_city in c for c in cities):
                return False

        # 关键词过滤（在简历文本中查找）
        keyword = criteria.get("keyword", "")
        if keyword:
            text_to_search = " ".join([
                candidate.get("title", ""),
                candidate.get("raw_text", ""),
                " ".join(candidate.get("skills", [])),
            ])
            if keyword.lower() not in text_to_search.lower():
                return False

        # 排除关键词
        exclude_keywords = criteria.get("exclude_keywords", [])
        if exclude_keywords:
            text_to_check = " ".join([
                candidate.get("title", ""),
                candidate.get("raw_text", ""),
            ])
            if any(kw.lower() in text_to_check.lower() for kw in exclude_keywords):
                return False

        return True

    def _normalize_education(self, edu_str: str) -> str:
        """标准化学历字符串"""
        edu_map = {
            "专科": "大专", "大专": "大专",
            "本科": "本科", "学士": "本科",
            "硕士": "硕士", "研究生": "硕士", "mba": "硕士", "MBA": "硕士",
            "博士": "博士", "phd": "博士", "PhD": "博士",
        }
        for k, v in edu_map.items():
            if k in edu_str:
                return v
        return "不限"

    def _parse_experience_years(self, exp_str: str) -> float:
        """从经验字符串解析年数，如 '3年' -> 3, '3-5年' -> 4"""
        if not exp_str:
            return 0
        # 匹配 "X年"、"X-Y年"、"应届"
        if "应届" in exp_str:
            return 0
        match = re.search(r"(\d+)\s*[-~]\s*(\d+)\s*年", exp_str)
        if match:
            return (float(match.group(1)) + float(match.group(2))) / 2
        match = re.search(r"(\d+)\s*年", exp_str)
        if match:
            return float(match.group(1))
        # 纯数字
        match = re.search(r"(\d+)", exp_str)
        if match:
            return float(match.group(1))
        return 0

    def _parse_salary(self, salary_str: str) -> tuple:
        """从薪资字符串解析范围（K/月），如 '15K-25K' -> (15, 25)"""
        if not salary_str:
            return (0, 0)
        match = re.search(r"(\d+(?:\.\d+)?)\s*[Kk千]\s*[-~]\s*(\d+(?:\.\d+)?)\s*[Kk千]", salary_str)
        if match:
            return (float(match.group(1)), float(match.group(2)))
        match = re.search(r"(\d+(?:\.\d+)?)\s*[Kk千]", salary_str)
        if match:
            val = float(match.group(1))
            return (val, val)
        return (0, 0)
