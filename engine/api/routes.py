"""routes.py - FastAPI REST 路由"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.deps import (
    get_boss_auth, get_boss_recruiter, get_boss_resume,
    get_candidate_filter, get_downloader, get_runner,
    get_scorer, get_boss_message, get_config,
)
from api.websocket import ws_broadcast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ─── 工作流 ───

@router.post("/workflow/run")
async def run_workflow(workflow: Dict[str, Any], background_tasks: BackgroundTasks):
    """执行工作流

    Body: 工作流 JSON（含 nodes 和 edges）
    """
    runner = get_runner()

    if runner.status.get("running"):
        raise HTTPException(400, "工作流正在执行中，请先停止")

    runner.load_workflow(workflow)
    runner.set_ws_broadcast(ws_broadcast)

    async def _run():
        await runner.run()

    background_tasks.add_task(_run)
    return {"message": "工作流已启动", "status": runner.status}


@router.post("/workflow/stop")
async def stop_workflow():
    """停止当前工作流执行"""
    runner = get_runner()
    runner.stop()
    await ws_broadcast({"type": "log", "data": {"level": "WARN", "message": "用户手动停止工作流"}})
    return {"message": "已停止", "status": runner.status}


@router.get("/workflow/status")
async def get_workflow_status():
    """获取当前工作流执行状态"""
    runner = get_runner()
    return runner.status


# ─── BOSS直聘 ───

@router.post("/boss/login")
async def boss_login(background_tasks: BackgroundTasks):
    """触发 BOSS直聘 登录流程"""
    auth = get_boss_auth()

    # 需要页面实例（从 runner 获取或创建）
    from DrissionPage import ChromiumPage
    from anti_detect.stealth import get_stealth_options

    co = get_stealth_options()
    page = ChromiumPage(co)

    result = await auth.login(page)
    if result:
        # 登录成功后把 page 存到全局供后续操作使用
        from api.deps import get_boss_recruiter
        recruiter = get_boss_recruiter()
        recruiter._page = page
        return {"message": "登录成功"}
    else:
        raise HTTPException(401, "登录失败或超时")


@router.get("/boss/candidates")
async def get_candidates(
    keyword: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    experience: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    salary_max: Optional[int] = Query(None),
    city: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
):
    """获取候选人列表（支持筛选）

    先筛选候选人，然后用 AI 评分，按分数倒序返回。
    """
    recruiter = get_boss_recruiter()
    scorer = get_scorer()
    candidate_filter = get_candidate_filter()
    config = get_config()
    boss_config = config.get("boss", {})

    # 获取页面实例
    page = getattr(recruiter, "_page", None)
    if not page:
        raise HTTPException(400, "请先登录 BOSS直聘")

    filters = {
        "keyword": keyword or "",
        "education": education or "",
        "experience": experience or "",
        "salary_min": salary_min,
        "salary_max": salary_max,
        "city": city or "",
        "job_id": job_id or "",
    }

    # 1. 获取候选人
    candidates = await recruiter.get_candidates(page, filters)
    if not candidates:
        return {"candidates": [], "total": 0}

    # 2. 过滤
    criteria = {k: v for k, v in filters.items() if v}
    filtered = candidate_filter.filter(candidates, criteria)

    # 3. AI 评分
    job_id_val = job_id or ""
    jd = ""
    for job in boss_config.get("jobs", []):
        if job.get("job_id") == job_id_val:
            jd = job.get("jd", "")
            break

    if jd:
        min_score = boss_config.get("min_score", 60)
        top_n = boss_config.get("top_n", 10)

        # 需要先读取简历才能评分
        resume_tool = get_boss_resume()
        scored_candidates = []
        for c in filtered[:boss_config.get("batch_size", 20)]:
            try:
                resume = await resume_tool.get_resume(page, c.get("id", ""))
                c["raw_text"] = resume.get("raw_text", "")
                c.update(resume)
            except Exception:
                pass
            scored_candidates.append(c)

        # 批量评分
        scored = await scorer.batch_score(
            scored_candidates, jd,
            llm_config=config.get("llm", {}),
        )

        # 过滤最低分
        result = [
            c for c in scored
            if c.get("ai_score", {}).get("score", 0) >= min_score
        ][:top_n]
    else:
        result = filtered

    await ws_broadcast({
        "type": "log",
        "data": {"level": "INFO", "message": f"候选人筛选评分完成: {len(result)} 人达标"}
    })

    return {"candidates": result, "total": len(result)}


@router.post("/boss/greet")
async def batch_greet(body: Dict[str, Any], background_tasks: BackgroundTasks):
    """批量发招呼

    Body: {
        candidate_ids: ["id1", "id2", ...],
        message: "招呼语模板",
        followup: "跟进话术模板",
        job_id: "职位ID"
    }
    """
    recruiter = get_boss_recruiter()
    config = get_config()
    boss_config = config.get("boss", {})

    page = getattr(recruiter, "_page", None)
    if not page:
        raise HTTPException(400, "请先登录 BOSS直聘")

    candidate_ids = body.get("candidate_ids", [])
    message = body.get("message", boss_config.get("greet_template", "您好，我们对您的简历很感兴趣！"))
    followup = body.get("followup", boss_config.get("followup_template", ""))
    job_id = body.get("job_id", "")

    if not candidate_ids:
        raise HTTPException(400, "请提供 candidate_ids")

    interval_min = boss_config.get("greet_interval_min", 30)
    interval_max = boss_config.get("greet_interval_max", 120)

    async def _greet():
        results = await recruiter.batch_greet(
            page, candidate_ids, message, followup, job_id,
            interval_range=(interval_min, interval_max),
        )
        await ws_broadcast({
            "type": "complete",
            "data": {"action": "batch_greet", "results": results}
        })

    background_tasks.add_task(_greet)
    return {"message": f"已启动批量招呼: {len(candidate_ids)} 人"}


@router.get("/boss/resume/{candidate_id}")
async def get_resume(candidate_id: str):
    """获取候选人简历"""
    resume_tool = get_boss_resume()
    recruiter = get_boss_recruiter()

    page = getattr(recruiter, "_page", None)
    if not page:
        raise HTTPException(400, "请先登录 BOSS直聘")

    resume = await resume_tool.get_resume(page, candidate_id)
    return resume


@router.post("/boss/score")
async def score_resume(body: Dict[str, Any]):
    """AI 评分简历

    Body: {resume_text: str, jd: str, llm_config?: dict}
    """
    scorer = get_scorer()
    config = get_config()

    resume_text = body.get("resume_text", "")
    jd = body.get("jd", "")
    llm_config = body.get("llm_config", config.get("llm", {}))

    if not resume_text or not jd:
        raise HTTPException(400, "请提供 resume_text 和 jd")

    result = await scorer.score(resume_text, jd, llm_config)
    return result


@router.post("/boss/download-resume")
async def download_resume(body: Dict[str, Any]):
    """下载候选人简历 PDF

    Body: {candidate_id: str, name: str, position: str}
    """
    downloader = get_downloader()
    recruiter = get_boss_recruiter()

    page = getattr(recruiter, "_page", None)
    if not page:
        raise HTTPException(400, "请先登录 BOSS直聘")

    candidate_id = body.get("candidate_id", "")
    name = body.get("name", "")
    position = body.get("position", "")

    if not candidate_id:
        raise HTTPException(400, "请提供 candidate_id")

    path = await downloader.download(page, candidate_id, name, position)
    if path:
        return {"success": True, "path": path}
    else:
        raise HTTPException(500, "简历下载失败")


@router.get("/boss/jobs")
async def get_jobs():
    """获取在招职位列表"""
    recruiter = get_boss_recruiter()
    page = getattr(recruiter, "_page", None)
    if not page:
        raise HTTPException(400, "请先登录 BOSS直聘")
    jobs = await recruiter.get_job_list(page)
    return {"jobs": jobs}


@router.get("/boss/conversations")
async def get_conversations():
    """获取消息列表"""
    msg = get_boss_message()
    recruiter = get_boss_recruiter()
    page = getattr(recruiter, "_page", None)
    if not page:
        raise HTTPException(400, "请先登录 BOSS直聘")
    conversations = await msg.get_conversations(page)
    return {"conversations": conversations}
