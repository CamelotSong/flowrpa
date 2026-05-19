"""scorer.py - AI 简历评分

将简历文本与 JD 进行匹配，调用 LLM API 给出 0-100 分和评分理由。
支持 OpenAI / Claude / 自定义 baseURL。
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

SCORE_PROMPT_TEMPLATE = """你是一位专业的招聘评估专家。请对以下候选人简历与职位JD的匹配程度进行评分。

## 职位描述（JD）
{jd}

## 候选人简历
{resume}

## 评分要求
请从以下维度综合评分（总分100分）：
1. 技能匹配度（30分）：候选人技能与JD要求的契合程度
2. 工作经验（25分）：经验年限、行业背景、工作内容相关性
3. 学历背景（15分）：学历层次与专业是否符合要求
4. 成就亮点（20分）：过往工作中的量化成果、项目经历
5. 综合印象（10分）：简历完整性、表达专业度

## 输出格式（严格JSON）
{{
  "score": <0-100的整数>,
  "reason": "<3-5句话的综合评价>",
  "highlights": ["<亮点1>", "<亮点2>", "<亮点3>"],
  "concerns": ["<顾虑1>", "<顾虑2>"],
  "dimensions": {{
    "skills": <0-30>,
    "experience": <0-25>,
    "education": <0-15>,
    "achievements": <0-20>,
    "overall": <0-10>
  }}
}}

只输出JSON，不要有任何其他文字。"""


class ResumeScorer:
    """AI 简历评分类"""

    def __init__(self, llm_config: Dict[str, Any] = None):
        """
        Args:
            llm_config: LLM 配置字典
                - provider: 'openai' / 'claude' / 'custom'
                - model: 模型名称
                - api_key: API 密钥
                - base_url: 自定义 API base URL（可选）
        """
        self.llm_config = llm_config or {}

    async def score(self, resume_text: str, jd: str,
                    llm_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """对简历与 JD 进行匹配评分

        Args:
            resume_text: 简历全文（含canvas提取的文字）
            jd: 职位描述文本
            llm_config: 临时覆盖 LLM 配置（可选）

        Returns:
            评分结果字典：
            {
                score: int,          # 0-100
                reason: str,         # 评分理由
                highlights: list,    # 亮点列表
                concerns: list,      # 顾虑列表
                dimensions: dict,    # 各维度得分
                error: str           # 错误信息（若有）
            }
        """
        cfg = llm_config or self.llm_config
        if not cfg:
            return self._default_error("未配置 LLM")

        provider = cfg.get("provider", "openai").lower()
        model = cfg.get("model", "gpt-3.5-turbo")
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "")

        if not api_key:
            return self._default_error("缺少 API Key")

        prompt = SCORE_PROMPT_TEMPLATE.format(
            jd=jd[:3000],
            resume=resume_text[:4000],
        )

        try:
            if provider == "claude":
                raw = await self._call_claude(api_key, model, prompt)
            else:
                # OpenAI 兼容格式（含 custom）
                raw = await self._call_openai(api_key, model, prompt, base_url)

            return self._parse_response(raw)

        except asyncio.TimeoutError:
            return self._default_error("LLM API 请求超时")
        except Exception as e:
            logger.error(f"LLM 评分失败: {e}")
            return self._default_error(str(e))

    async def batch_score(self, resumes: List[Dict], jd: str,
                          llm_config: Dict[str, Any] = None,
                          concurrency: int = 3) -> List[Dict]:
        """批量评分（并发控制）

        Args:
            resumes: 候选人简历列表，每个字典需包含 'id' 和 'raw_text'
            jd: 职位描述
            llm_config: LLM 配置
            concurrency: 并发请求数（默认3，避免频率限制）

        Returns:
            带评分的候选人列表（倒序排列）
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def score_one(candidate: Dict) -> Dict:
            async with semaphore:
                resume_text = candidate.get("raw_text", "")
                if not resume_text:
                    resume_text = f"姓名:{candidate.get('name','')} 职位:{candidate.get('title','')} 学历:{candidate.get('education','')} 经验:{candidate.get('experience','')} 技能:{','.join(candidate.get('skills',[]))}"

                result = await self.score(resume_text, jd, llm_config)
                # 避免频率限制
                await asyncio.sleep(0.5)
                return {**candidate, "ai_score": result}

        tasks = [score_one(r) for r in resumes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常，按分数倒序
        scored = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"评分任务异常: {r}")
                continue
            scored.append(r)

        scored.sort(key=lambda x: x.get("ai_score", {}).get("score", 0), reverse=True)
        return scored

    async def _call_openai(self, api_key: str, model: str, prompt: str,
                           base_url: str = "") -> str:
        """调用 OpenAI 兼容 API"""
        url = (base_url.rstrip("/") + "/chat/completions") if base_url else "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一位专业的招聘评估专家，专注于技术岗位的简历评估。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"OpenAI API 返回 {resp.status}: {text[:200]}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _call_claude(self, api_key: str, model: str, prompt: str) -> str:
        """调用 Claude API"""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": model or "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Claude API 返回 {resp.status}: {text[:200]}")
                data = await resp.json()
                return data["content"][0]["text"]

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON"""
        try:
            # 提取 JSON 块（防止模型输出多余文字）
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"解析评分JSON失败: {e}, 原始内容: {raw[:200]}")

        # 尝试提取分数
        score_match = re.search(r'"score"\s*:\s*(\d+)', raw)
        score = int(score_match.group(1)) if score_match else 50

        return {
            "score": score,
            "reason": raw[:200],
            "highlights": [],
            "concerns": [],
            "dimensions": {},
        }

    def _default_error(self, msg: str) -> Dict[str, Any]:
        return {
            "score": 0,
            "reason": "",
            "highlights": [],
            "concerns": [],
            "dimensions": {},
            "error": msg,
        }
