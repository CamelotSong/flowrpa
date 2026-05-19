import React, { useState, useEffect } from 'react'
import WorkflowEditor from './editor/WorkflowEditor'
import Console from './console/Console'
import BossPanel from './boss/BossPanel'
import { useStore } from './store'

type Page = 'editor' | 'console' | 'boss'

const NAV_ITEMS: { id: Page; icon: string; label: string }[] = [
  { id: 'editor',  icon: '⬡', label: '流程编辑' },
  { id: 'console', icon: '⬢', label: '执行控制台' },
  { id: 'boss',    icon: '⬡', label: 'BOSS直聘' },
]

declare global {
  interface Window {
    flowrpa?: {
      minimizeWindow: () => void
      maximizeWindow: () => void
      closeWindow: () => void
      platform?: string
      onEngineLog?: (cb: (data: string) => void) => () => void
      getEngineStatus?: () => Promise<any>
    }
  }
}

export default function App() {
  const [page, setPage] = useState<Page>('editor')
  const { engineConnected, setEngineConnected } = useStore()

  // 检测引擎连接状态
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('http://127.0.0.1:9222/health')
        setEngineConnected(res.ok)
      } catch {
        setEngineConnected(false)
      }
    }
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [setEngineConnected])

  const isMac = window.flowrpa?.platform === 'darwin'

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: '#0a0a0f' }}>
      {/* 标题栏 */}
      <div className="titlebar">
        {/* Mac: 左侧系统按钮已由系统渲染，Windows: 自定义控制按钮 */}
        {!isMac && (
          <div className="titlebar-controls" style={{ order: -1 }}>
            <button className="titlebar-btn close" onClick={() => window.flowrpa?.closeWindow()} />
            <button className="titlebar-btn minimize" onClick={() => window.flowrpa?.minimizeWindow()} />
            <button className="titlebar-btn maximize" onClick={() => window.flowrpa?.maximizeWindow()} />
          </div>
        )}
        <span className="titlebar-title shimmer-text">FlowRPA</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: engineConnected ? '#22c55e' : '#ef4444',
            boxShadow: engineConnected ? '0 0 6px rgba(34,197,94,0.6)' : 'none',
          }} />
          <span style={{ fontSize: 11, color: '#64748b' }}>
            {engineConnected ? '引擎已连接' : '引擎未连接'}
          </span>
          {isMac && (
            <div className="titlebar-controls">
              <button className="titlebar-btn close" onClick={() => window.flowrpa?.closeWindow()} />
              <button className="titlebar-btn minimize" onClick={() => window.flowrpa?.minimizeWindow()} />
              <button className="titlebar-btn maximize" onClick={() => window.flowrpa?.maximizeWindow()} />
            </div>
          )}
        </div>
      </div>

      {/* 主布局 */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 侧边栏 */}
        <div className="sidebar">
          {NAV_ITEMS.map(item => (
            <div
              key={item.id}
              className={`sidebar-item ${page === item.id ? 'active' : ''}`}
              title={item.label}
              onClick={() => setPage(item.id)}
            >
              {item.icon}
            </div>
          ))}
        </div>

        {/* 内容区 */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {page === 'editor'  && <WorkflowEditor />}
          {page === 'console' && <Console />}
          {page === 'boss'    && <BossPanel />}
        </div>
      </div>
    </div>
  )
}
