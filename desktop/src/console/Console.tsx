import React, { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'

const LOG_COLORS: Record<string, string> = {
  INFO: '#4F8EF7',
  WARN: '#fbd38d',
  ERROR: '#ef4444',
}

export default function Console() {
  const {
    executionLogs, executionRunning, nodeStatus, clearLogs,
    setExecutionRunning, addLog, setNodeStatus, resetNodeStatus,
    nodes,
  } = useStore()

  const [ws, setWs] = useState<WebSocket | null>(null)
  const [progress, setProgress] = useState(0)
  const logEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [executionLogs])

  // WebSocket 连接
  useEffect(() => {
    const connect = () => {
      const socket = new WebSocket('ws://127.0.0.1:9222/ws')
      wsRef.current = socket

      socket.onopen = () => {
        addLog({ level: 'INFO', message: '已连接到引擎 WebSocket', timestamp: Date.now() })
      }

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          handleWsMessage(msg)
        } catch {
          addLog({ level: 'WARN', message: event.data, timestamp: Date.now() })
        }
      }

      socket.onclose = () => {
        addLog({ level: 'WARN', message: '与引擎断开连接，5s后重试', timestamp: Date.now() })
        setExecutionRunning(false)
        setTimeout(connect, 5000)
      }

      socket.onerror = () => {
        addLog({ level: 'ERROR', message: '引擎连接错误', timestamp: Date.now() })
      }

      setWs(socket)
    }

    connect()

    return () => {
      wsRef.current?.close()
    }
  }, [])

  const handleWsMessage = (msg: any) => {
    const { type, data } = msg

    if (type === 'log') {
      addLog({
        level: data.level || 'INFO',
        message: data.message || '',
        timestamp: Date.now(),
        nodeId: data.node_id,
      })
    } else if (type === 'node_status') {
      setNodeStatus(data.node_id, data.status)
      if (data.status === 'running') {
        setExecutionRunning(true)
      }
    } else if (type === 'complete') {
      setExecutionRunning(false)
      addLog({ level: 'INFO', message: `工作流执行完成 (共${data.total || 0}个节点)`, timestamp: Date.now() })
      setProgress(100)
    } else if (type === 'error') {
      addLog({ level: 'ERROR', message: data.message || '发生错误', timestamp: Date.now() })
    }

    // 更新进度
    const total = nodes.length || 1
    const done = Object.values(nodeStatus).filter(s => s === 'success' || s === 'error').length
    setProgress(Math.round((done / total) * 100))
  }

  const handleStop = async () => {
    try {
      await fetch('http://127.0.0.1:9222/api/workflow/stop', { method: 'POST' })
    } catch {}
  }

  const totalNodes = nodes.length
  const doneNodes = Object.values(nodeStatus).filter(s => s === 'success' || s === 'error').length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0, padding: 12, background: '#0a0a0f', overflow: 'hidden' }}>
      {/* 顶部：状态和控制 */}
      <div className="glass-card" style={{ padding: '12px 16px', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: executionRunning ? '#4F8EF7' : '#64748b' }}>
              {executionRunning ? '🔄 执行中...' : '⏸ 就绪'}
            </span>
            <span style={{ fontSize: 12, color: '#64748b' }}>
              {doneNodes}/{totalNodes} 节点
            </span>
          </div>
          <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 4,
              background: `linear-gradient(90deg, #4F8EF7, #7C5CFC)`,
              width: `${progress}%`,
              transition: 'width 0.4s ease',
            }} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          {executionRunning && (
            <button className="glass-btn glass-btn-danger" onClick={handleStop} style={{ padding: '6px 16px', fontSize: 12 }}>
              ■ 停止
            </button>
          )}
          <button className="glass-btn" onClick={clearLogs} style={{ padding: '6px 16px', fontSize: 12 }}>
            清除日志
          </button>
          <button className="glass-btn" onClick={resetNodeStatus} style={{ padding: '6px 16px', fontSize: 12 }}>
            重置状态
          </button>
        </div>
      </div>

      {/* 中部：节点状态可视化 */}
      {nodes.length > 0 && (
        <div className="glass-card" style={{ padding: '10px 14px', marginBottom: 10, maxHeight: 120, overflowX: 'auto', flexShrink: 0 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>节点状态</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'nowrap', overflowX: 'auto' }}>
            {nodes.map((node: any) => {
              const status = nodeStatus[node.id] || 'pending'
              const colorMap: Record<string, string> = {
                pending: '#64748b',
                running: '#4F8EF7',
                success: '#22c55e',
                error: '#ef4444',
              }
              return (
                <div key={node.id} style={{
                  padding: '4px 10px', borderRadius: 20, fontSize: 11, flexShrink: 0,
                  background: `${colorMap[status]}22`,
                  border: `1px solid ${colorMap[status]}44`,
                  color: colorMap[status],
                  transition: 'all 0.3s',
                  boxShadow: status === 'running' ? `0 0 8px ${colorMap[status]}44` : 'none',
                }}>
                  {node.data?.label || node.type || node.id}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 底部：日志流 */}
      <div className="glass-card" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: '10px 14px 6px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5, flexShrink: 0 }}>
          实时日志 · {executionLogs.length} 条
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 14px', fontFamily: "'SF Mono', 'Fira Code', monospace", fontSize: 12, lineHeight: 1.7 }}>
          {executionLogs.map((log, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, padding: '2px 0' }}>
              <span style={{ color: '#475569', flexShrink: 0 }}>
                {new Date(log.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
              </span>
              <span style={{ color: LOG_COLORS[log.level] || '#94a3b8', fontWeight: 600, flexShrink: 0 }}>
                [{log.level}]
              </span>
              <span style={{ color: '#e2e8f0', wordBreak: 'break-word' }}>{log.message}</span>
            </div>
          ))}
          {executionLogs.length === 0 && (
            <div style={{ color: '#475569', textAlign: 'center', padding: 24 }}>暂无日志，运行工作流后查看</div>
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}
