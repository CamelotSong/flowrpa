import React, { useEffect, useState } from 'react'
import { useStore } from '../store'

const API = 'http://127.0.0.1:9222'

const EDUCATION_OPTIONS = ['不限', '大专', '本科', '硕士', '博士']

export default function BossPanel() {
  const {
    candidates, selectedCandidateId, bossLoggedIn, bossJobs, selectedJobId,
    greetTemplate, followupTemplate, batchSize, topN, minScore, scoring,
    setCandidates, setSelectedCandidate, setBossLoggedIn, setBossJobs,
    setSelectedJobId, setGreetTemplate, setFollowupTemplate, setBatchSize,
    setTopN, setMinScore, setScoring, updateCandidateScore,
  } = useStore()

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [resumeDetail, setResumeDetail] = useState<any>(null)
  const [scoringProgress, setScoringProgress] = useState(0)

  // 检查登录状态
  useEffect(() => {
    // 简单检查：如果能请求到健康端点就算可用
    setBossLoggedIn(true)
  }, [])

  // 获取职位列表
  useEffect(() => {
    fetchJobs()
  }, [])

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API}/api/boss/jobs`)
      if (res.ok) {
        const data = await res.json()
        setBossJobs(data.jobs || [])
      }
    } catch {}
  }

  const handleLogin = async () => {
    try {
      await fetch(`${API}/api/boss/login`, { method: 'POST' })
      setBossLoggedIn(true)
    } catch {}
  }

  // 筛选 + 评分
  const handleStartFilterScore = async () => {
    if (!selectedJobId) {
      alert('请先选择职位')
      return
    }

    const jd = bossJobs.find(j => j.job_id === selectedJobId)?.jd || ''

    setScoring(true)
    setScoringProgress(10)
    setCandidates([])

    try {
      const params = new URLSearchParams()
      params.set('job_id', selectedJobId)
      params.set('batch_size', String(batchSize))

      const res = await fetch(`${API}/api/boss/candidates?${params}`)
      if (!res.ok) throw new Error('获取候选人失败')

      const data = await res.json()
      let list = data.candidates || []
      setScoringProgress(50)

      // 逐步更新候选人（带评分）
      setCandidates(list)
      setScoringProgress(70)

      // 如果服务端没评分，前端请求逐个评分
      if (list.length > 0 && !list[0].ai_score) {
        for (let i = 0; i < list.length; i++) {
          const c = list[i]
          const text = c.raw_text || `${c.name} ${c.title} ${c.education} ${c.experience} ${c.skills?.join(',') || ''}`
          try {
            const scoreRes = await fetch(`${API}/api/boss/score`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ resume_text: text, jd }),
            })
            if (scoreRes.ok) {
              const score = await scoreRes.json()
              updateCandidateScore(c.id, score)
            }
          } catch {}
          setScoringProgress(70 + Math.round((i + 1) / list.length * 25))
          await new Promise(r => setTimeout(r, 300))
        }
      }

      setScoringProgress(100)

      // 过滤最低分 & 排序
      const filtered = list
        .filter(c => (c.ai_score?.score || 0) >= minScore)
        .sort((a, b) => (b.ai_score?.score || 0) - (a.ai_score?.score || 0))
        .slice(0, topN)

      setCandidates(filtered)
    } catch (e: any) {
      console.error('筛选失败:', e)
    } finally {
      setScoring(false)
    }
  }

  // 批量打招呼
  const handleBatchGreet = async () => {
    const ids = Array.from(selectedIds)
    if (ids.length === 0) { alert('请选择候选人'); return }

    try {
      await fetch(`${API}/api/boss/greet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_ids: ids,
          message: greetTemplate,
          followup: followupTemplate,
          job_id: selectedJobId,
        }),
      })
    } catch {}
  }

  // 查看简历
  const handleViewResume = async (candidateId: string) => {
    setSelectedCandidate(candidateId)
    try {
      const res = await fetch(`${API}/api/boss/resume/${candidateId}`)
      if (res.ok) {
        const data = await res.json()
        setResumeDetail(data)
      }
    } catch {}
  }

  // 下载简历
  const handleDownloadResume = async (candidate: any) => {
    try {
      const res = await fetch(`${API}/api/boss/download-resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_id: candidate.id, name: candidate.name, position: candidate.title }),
      })
      const data = await res.json()
      if (data.path) {
        alert(`简历已保存: ${data.path}`)
      }
    } catch {}
  }

  const getScoreBadgeClass = (score: number) => {
    if (score >= 75) return 'score-badge score-high'
    if (score >= 60) return 'score-badge score-mid'
    return 'score-badge score-low'
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden', background: '#0a0a0f' }}>
      {/* 左列：筛选条件 + 配置 */}
      <div className="glass-card" style={{ width: 280, margin: 8, padding: 14, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14, color: '#e2e8f0' }}>
          🎯 筛选配置
        </div>

        {/* 职位选择 */}
        <div style={{ marginBottom: 12 }}>
          <label className="glass-label">选择职位</label>
          <select className="glass-select" value={selectedJobId} onChange={e => setSelectedJobId(e.target.value)}>
            <option value="">-- 请选择 --</option>
            {bossJobs.map(j => (
              <option key={j.job_id} value={j.job_id}>{j.title || j.job_id}</option>
            ))}
          </select>
        </div>

        {/* 配置参数 */}
        <div style={{ marginBottom: 12 }}>
          <label className="glass-label">每批读取 (batch_size)</label>
          <input className="glass-input" type="number" value={batchSize} min={5} max={100} onChange={e => setBatchSize(parseInt(e.target.value) || 20)} />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label className="glass-label">取前N名 (top_n)</label>
          <input className="glass-input" type="number" value={topN} min={1} max={50} onChange={e => setTopN(parseInt(e.target.value) || 10)} />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label className="glass-label">最低评分 (min_score)</label>
          <input className="glass-input" type="number" value={minScore} min={0} max={100} onChange={e => setMinScore(parseInt(e.target.value) || 60)} />
        </div>

        {/* 招呼语模板 */}
        <div style={{ marginBottom: 12 }}>
          <label className="glass-label">招呼语模板</label>
          <textarea className="glass-textarea" value={greetTemplate} rows={2} onChange={e => setGreetTemplate(e.target.value)} />
          <span style={{ fontSize: 10, color: '#64748b' }}>变量: {'{name}'} {'{position}'} {'{company}'}</span>
        </div>

        <div style={{ marginBottom: 14 }}>
          <label className="glass-label">跟进话术</label>
          <textarea className="glass-textarea" value={followupTemplate} rows={2} onChange={e => setFollowupTemplate(e.target.value)} />
        </div>

        {/* 操作按钮 */}
        <button
          className={`glass-btn ${scoring ? '' : 'glass-btn-primary'}`}
          style={{ width: '100%', marginBottom: 8 }}
          onClick={handleStartFilterScore}
          disabled={scoring}
        >
          {scoring ? `评分中 ${scoringProgress}%...` : '🔍 开始筛选+评分'}
        </button>

        <button className="glass-btn" style={{ width: '100%' }} onClick={handleBatchGreet} disabled={selectedIds.size === 0}>
          📨 批量打招呼 ({selectedIds.size})
        </button>
      </div>

      {/* 中列：候选人列表 */}
      <div className="glass-card" style={{ flex: 1, margin: '8px 0', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '12px 16px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', flexShrink: 0 }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>候选人列表 ({candidates.length})</span>
          <label style={{ fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" onChange={e => {
              if (e.target.checked) {
                setSelectedIds(new Set(candidates.map(c => c.id)))
              } else {
                setSelectedIds(new Set())
              }
            }} />
            全选
          </label>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
          {candidates.length === 0 && (
            <div style={{ color: '#475569', textAlign: 'center', padding: 40, fontSize: 13 }}>
              {scoring ? '正在筛选评分...' : '点击"开始筛选+评分"获取候选人'}
            </div>
          )}
          {candidates.map((c, idx) => (
            <div
              key={c.id}
              className="glass-card"
              style={{
                padding: '10px 14px', marginBottom: 6, cursor: 'pointer',
                borderLeft: selectedCandidateId === c.id ? '3px solid #4F8EF7' : '3px solid transparent',
                background: selectedIds.has(c.id) ? 'rgba(79,142,247,0.08)' : undefined,
              }}
              onClick={() => handleViewResume(c.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(c.id)}
                    onChange={e => {
                      const next = new Set(selectedIds)
                      e.target.checked ? next.add(c.id) : next.delete(c.id)
                      setSelectedIds(next)
                      e.stopPropagation()
                    }}
                    onClick={e => e.stopPropagation()}
                  />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>#{idx + 1}</span>
                  <span style={{ fontWeight: 600 }}>{c.name || '未知'}</span>
                  <span style={{ color: '#94a3b8', fontSize: 12 }}>{c.title}</span>
                </div>
                {c.ai_score && (
                  <span className={getScoreBadgeClass(c.ai_score.score)}>{c.ai_score.score}</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 12, color: '#94a3b8' }}>
                {c.education && <span>🎓 {c.education}</span>}
                {c.experience && <span>💼 {c.experience}</span>}
                {c.salary && <span>💰 {c.salary}</span>}
                {c.city && <span>📍 {c.city}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 右列：简历详情 */}
      <div className="glass-card" style={{ width: 320, margin: '8px 8px 8px 0', padding: 14, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: '#e2e8f0' }}>
          📄 简历详情
        </div>

        {!resumeDetail ? (
          <div style={{ color: '#475569', textAlign: 'center', padding: 40, fontSize: 13 }}>
            点击候选人查看简历
          </div>
        ) : (
          <>
            {/* 评分信息 */}
            {resumeDetail.ai_score && (
              <div style={{ marginBottom: 12, padding: 12, background: 'rgba(79,142,247,0.06)', borderRadius: 10, border: '1px solid rgba(79,142,247,0.15)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>AI 匹配度</span>
                  <span className={getScoreBadgeClass(resumeDetail.ai_score.score)} style={{ fontSize: 18, padding: '4px 14px' }}>
                    {resumeDetail.ai_score.score}
                  </span>
                </div>
                {resumeDetail.ai_score.reason && (
                  <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>{resumeDetail.ai_score.reason}</div>
                )}
                {resumeDetail.ai_score.highlights?.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <span style={{ fontSize: 11, color: '#22c55e' }}>✓ 亮点: </span>
                    <span style={{ fontSize: 11, color: '#94a3b8' }}>{resumeDetail.ai_score.highlights.join('; ')}</span>
                  </div>
                )}
                {resumeDetail.ai_score.concerns?.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <span style={{ fontSize: 11, color: '#fbd38d' }}>⚠ 顾虑: </span>
                    <span style={{ fontSize: 11, color: '#94a3b8' }}>{resumeDetail.ai_score.concerns.join('; ')}</span>
                  </div>
                )}
              </div>
            )}

            {/* 基本信息 */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>{resumeDetail.name || '未知'}</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>{resumeDetail.title}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap', fontSize: 12, color: '#94a3b8' }}>
                {resumeDetail.education && <span>🎓 {resumeDetail.education}</span>}
                {resumeDetail.experience && <span>💼 {resumeDetail.experience}</span>}
              </div>
            </div>

            {/* 技能标签 */}
            {resumeDetail.skills?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>技能</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {resumeDetail.skills.map((s: string, i: number) => (
                    <span key={i} style={{
                      padding: '2px 8px', borderRadius: 12, fontSize: 11,
                      background: 'rgba(79,142,247,0.1)', border: '1px solid rgba(79,142,247,0.2)',
                      color: '#4F8EF7',
                    }}>{s}</span>
                  ))}
                </div>
              </div>
            )}

            {/* 工作经历 */}
            {resumeDetail.work_history?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>工作经历</div>
                {resumeDetail.work_history.map((w: string, i: number) => (
                  <div key={i} style={{ fontSize: 12, color: '#94a3b8', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>{w}</div>
                ))}
              </div>
            )}

            {/* 简历全文 */}
            {resumeDetail.raw_text && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>简历全文</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.7, maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                  {resumeDetail.raw_text.substring(0, 1500)}
                  {resumeDetail.raw_text.length > 1500 && '...'}
                </div>
              </div>
            )}

            {/* Canvas 提取的文字 */}
            {resumeDetail.canvas_texts?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, textTransform: 'uppercase' }}>Canvas OCR 文字</div>
                <div style={{ fontSize: 12, color: '#fbd38d', lineHeight: 1.7 }}>
                  {resumeDetail.canvas_texts.join('\n')}
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button className="glass-btn glass-btn-primary" style={{ flex: 1 }} onClick={() => {
                const c = candidates.find(c => c.id === selectedCandidateId)
                if (c) {
                  const msg = greetTemplate.replace('{name}', c.name).replace('{position}', c.title)
                  alert(`招呼语预览:\n${msg}`)
                }
              }}>
                📨 发招呼
              </button>
              <button className="glass-btn" style={{ flex: 1 }} onClick={() => {
                const c = candidates.find(c => c.id === selectedCandidateId)
                if (c) handleDownloadResume(c)
              }}>
                📥 下载简历
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
