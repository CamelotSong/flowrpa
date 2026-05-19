"""deps.py - FastAPI 依赖注入"""

from executor.runner import WorkflowRunner
from boss.auth import BossAuth
from boss.recruiter import BossRecruiter
from boss.scorer import ResumeScorer
from boss.downloader import ResumeDownloader
from boss.canvas_ocr import CanvasOCR
from boss.filter import CandidateFilter
from boss.message import BossMessage
from boss.resume import BossResume
from utils.config import load_config

_config = load_config()

# 全局单例
_runner: WorkflowRunner = None
_boss_auth: BossAuth = None
_boss_recruiter: BossRecruiter = None
_scorer: ResumeScorer = None
_downloader: ResumeDownloader = None


def get_config():
    return _config


def get_runner() -> WorkflowRunner:
    global _runner
    if _runner is None:
        _runner = WorkflowRunner()
    return _runner


def get_boss_auth() -> BossAuth:
    global _boss_auth
    if _boss_auth is None:
        _boss_auth = BossAuth()
    return _boss_auth


def get_boss_recruiter() -> BossRecruiter:
    global _boss_recruiter
    if _boss_recruiter is None:
        boss_config = _config.get("boss", {})
        _boss_recruiter = BossRecruiter(config=boss_config)
    return _boss_recruiter


def get_scorer() -> ResumeScorer:
    global _scorer
    if _scorer is None:
        llm_config = _config.get("llm", {})
        _scorer = ResumeScorer(llm_config=llm_config)
    return _scorer


def get_downloader() -> ResumeDownloader:
    global _downloader
    if _downloader is None:
        boss_config = _config.get("boss", {})
        _downloader = ResumeDownloader(
            download_dir=boss_config.get("download_dir", "~/Downloads/boss_resumes")
        )
    return _downloader


def get_canvas_ocr() -> CanvasOCR:
    return CanvasOCR(engine="easyocr")


def get_candidate_filter() -> CandidateFilter:
    return CandidateFilter()


def get_boss_message() -> BossMessage:
    return BossMessage()


def get_boss_resume() -> BossResume:
    return BossResume(canvas_ocr=get_canvas_ocr())
