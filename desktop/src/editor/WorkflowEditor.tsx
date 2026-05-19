import React, { useCallback, useMemo, useRef } from 'react'
import ReactFlow, {
  Node, Edge, Controls, Background,
  addEdge, Connection, useNodesState, useEdgesState,
  NodeTypesType, BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useStore } from '../store'

// ── 节点类型定义 ──

const NODE_TYPES_CONFIG = [
  { type: 'open_url',   label: '打开网页', icon: '🌐', color: '#4F8EF7' },
  { type: 'click',      label: '点击元素', icon: '👆', color: '#22c55e' },
  { type: 'input_text', label: '输入文字', icon: '⌨',  color: '#fbd38d' },
  { type: 'scroll',     label: '滚动页面', icon: '↕',  color: '#94a3b8' },
  { type: 'wait',       label: '等待',     icon: '⏳', color: '#7C5CFC' },
  { type: 'screenshot', label: '截图',     icon: '📸', color: '#ef4444' },
  { type: 'get_text',   label: '获取文本', icon: '📝', color: '#f97316' },
  { type: 'condition',  label: '条件判断', icon: '🔀', color: '#06b6d4' },
  { type: 'loop',       label: '循环',     icon: '🔁', color: '#8b5cf6' },
]

// ── 自定义节点组件 ──

function GlassNode({ data, selected }: { data: any; selected: boolean }) {
  const config = NODE_TYPES_CONFIG.find(c => c.type === data.nodeType) || NODE_TYPES_CONFIG[0]
  return (
    <div style={{
      padding: '10px 16px',
      borderRadius: 12,
      background: 'rgba(22,22,30,0.85)',
      backdropFilter: 'blur(20px) saturate(180%)',
      border: `1px solid ${selected ? 'rgba(79,142,247,0.6)' : 'rgba(255,255,255,0.08)'}`,
      boxShadow: selected
        ? '0 0 20px rgba(79,142,247,0.2), 0 8px 32px rgba(0,0,0,0.4)'
        : '0 8px 32px rgba(0,0,0,0.4)',
      color: '#e2e8f0',
      fontSize: 13,
      minWidth: 140,
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 16 }}>{config.icon}</span>
        <span style={{ fontWeight: 600 }}>{data.label || config.label}</span>
      </div>
      {data.url && <div style={{ fontSize: 11, color: '#94a3b8', wordBreak: 'break-all' }}>{data.url}</div>}
      {data.selector && <div style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'monospace' }}>{data.selector}</div>}
      {data.text && <div style={{ fontSize: 11, color: '#fbd38d' }}>"{data.text.substring(0, 30)}"</div>}
    </div>
  )
}

const nodeTypes: NodeTypesType = {
  glassNode: GlassNode as any,
}

// ── 属性面板 ──

function PropertiesPanel({ node, onUpdate }: { node: Node | null; onUpdate: (id: string, data: any) => void }) {
  if (!node) return (
    <div style={{ padding: 16, color: '#64748b', fontSize: 13, textAlign: 'center' }}>
      选择节点以编辑属性
    </div>
  )

  const data = node.data
  const typeConfig = NODE_TYPES_CONFIG.find(c => c.type === data.nodeType)

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>
        {typeConfig?.icon} {data.label || typeConfig?.label}
      </div>

      <div>
        <label className="glass-label">节点名称</label>
        <input className="glass-input" value={data.label || ''} onChange={e => onUpdate(node.id, { label: e.target.value })} />
      </div>

      {data.nodeType === 'open_url' && (
        <div>
          <label className="glass-label">URL</label>
          <input className="glass-input" value={data.url || ''} placeholder="https://..." onChange={e => onUpdate(node.id, { url: e.target.value })} />
        </div>
      )}

      {(data.nodeType === 'click' || data.nodeType === 'input_text' || data.nodeType === 'get_text') && (
        <div>
          <label className="glass-label">选择器</label>
          <input className="glass-input" value={data.selector || ''} placeholder="css:.btn / xpath:... / text:..." onChange={e => onUpdate(node.id, { selector: e.target.value })} />
        </div>
      )}

      {data.nodeType === 'input_text' && (
        <>
          <div>
            <label className="glass-label">输入文本</label>
            <textarea className="glass-textarea" value={data.text || ''} onChange={e => onUpdate(node.id, { text: e.target.value })} />
          </div>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
              <input type="checkbox" checked={data.human_like !== false} onChange={e => onUpdate(node.id, { human_like: e.target.checked })} />
              模拟人工输入
            </label>
          </div>
        </>
      )}

      {data.nodeType === 'wait' && (
        <div>
          <label className="glass-label">等待秒数</label>
          <input className="glass-input" type="number" value={data.seconds || 2} min={0.1} step={0.1} onChange={e => onUpdate(node.id, { seconds: parseFloat(e.target.value) })} />
        </div>
      )}

      {data.nodeType === 'scroll' && (
        <div>
          <label className="glass-label">滚动方向</label>
          <select className="glass-select" value={data.direction || 'down'} onChange={e => onUpdate(node.id, { direction: e.target.value })}>
            <option value="down">向下</option>
            <option value="up">向上</option>
            <option value="bottom">到底部</option>
          </select>
        </div>
      )}

      {data.nodeType === 'condition' && (
        <div>
          <label className="glass-label">条件变量</label>
          <input className="glass-input" value={data.variable || ''} placeholder="变量名" onChange={e => onUpdate(node.id, { variable: e.target.value })} />
        </div>
      )}

      {data.nodeType === 'loop' && (
        <div>
          <label className="glass-label">循环次数</label>
          <input className="glass-input" type="number" value={data.count || 3} min={1} onChange={e => onUpdate(node.id, { count: parseInt(e.target.value) })} />
        </div>
      )}
    </div>
  )
}

// ── 主编辑器 ──

let nodeIdCounter = 0

export default function WorkflowEditor() {
  const { nodes: storeNodes, edges: storeEdges, selectedNodeId, setNodes, setEdges, setSelectedNode, updateNodeData, workflowName, setWorkflowName, executionRunning, addLog } = useStore()

  const [rfNodes, setRfNodes, onRfNodesChange] = useNodesState(storeNodes.map(n => ({
    ...n,
    type: 'glassNode',
    data: { ...n.data, nodeType: n.type },
  })))

  const [rfEdges, setRfEdges, onRfEdgesChange] = useEdgesState(storeEdges)

  const onConnect = useCallback((connection: Connection) => {
    setRfEdges(eds => addEdge({ ...connection, animated: true, style: { stroke: '#4F8EF7', strokeWidth: 2 } }, eds))
  }, [setRfEdges])

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNode(node.id)
  }, [setSelectedNode])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [setSelectedNode])

  const selectedNode = rfNodes.find(n => n.id === selectedNodeId) || null

  const handleUpdateNode = useCallback((id: string, data: any) => {
    setRfNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, ...data } } : n))
    updateNodeData(id, data)
  }, [setRfNodes, updateNodeData])

  // 拖拽添加节点
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    const nodeType = event.dataTransfer.getData('application/reactflow')
    if (!nodeType) return

    const config = NODE_TYPES_CONFIG.find(c => c.type === nodeType)
    if (!config) return

    nodeIdCounter++
    const newNode: Node = {
      id: `node_${nodeIdCounter}`,
      type: 'glassNode',
      position: { x: event.clientX - 280, y: event.clientY - 80 },
      data: { nodeType, label: config.label, ...getDefaultData(nodeType) },
    }
    setRfNodes(nds => [...nds, newNode])
  }, [setRfNodes])

  // 工具栏操作
  const handleRun = async () => {
    const workflow = {
      nodes: rfNodes.map(n => ({ id: n.id, type: n.data.nodeType, ...n.data })),
      edges: rfEdges.map(e => ({ source: e.source, target: e.target })),
    }
    try {
      const res = await fetch('http://127.0.0.1:9222/api/workflow/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow),
      })
      addLog({ level: 'INFO', message: `工作流已提交: ${res.status}`, timestamp: Date.now() })
    } catch (e: any) {
      addLog({ level: 'ERROR', message: `提交失败: ${e.message}`, timestamp: Date.now() })
    }
  }

  const handleStop = async () => {
    await fetch('http://127.0.0.1:9222/api/workflow/stop', { method: 'POST' })
  }

  const handleExport = () => {
    const json = JSON.stringify({ nodes: rfNodes, edges: rfEdges }, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${workflowName || 'workflow'}.json`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* 左侧: 节点面板 */}
      <div className="glass-card" style={{ width: 200, margin: 8, padding: 12, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          节点类型
        </div>
        {NODE_TYPES_CONFIG.map(c => (
          <div
            key={c.type}
            draggable
            onDragStart={e => e.dataTransfer.setData('application/reactflow', c.type)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 10px', marginBottom: 4,
              borderRadius: 8, cursor: 'grab',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              transition: 'all 0.15s',
              fontSize: 13,
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(79,142,247,0.08)'; e.currentTarget.style.borderColor = 'rgba(79,142,247,0.3)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)' }}
          >
            <span style={{ fontSize: 15 }}>{c.icon}</span>
            <span>{c.label}</span>
          </div>
        ))}
      </div>

      {/* 中间: 画布 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* 工具栏 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', background: 'rgba(15,15,20,0.5)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <input className="glass-input" style={{ width: 200, fontSize: 13, fontWeight: 600 }} value={workflowName} onChange={e => setWorkflowName(e.target.value)} />
          <div style={{ flex: 1 }} />
          <button className="glass-btn" onClick={handleExport}>导出 JSON</button>
          {!executionRunning ? (
            <button className="glass-btn glass-btn-primary" onClick={handleRun}>▶ 运行</button>
          ) : (
            <button className="glass-btn glass-btn-danger" onClick={handleStop}>■ 停止</button>
          )}
        </div>

        {/* React Flow */}
        <div ref={reactFlowWrapper} style={{ flex: 1 }}>
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            nodeTypes={nodeTypes}
            onNodesChange={onRfNodesChange}
            onEdgesChange={onRfEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onDragOver={onDragOver}
            onDrop={onDrop}
            fitView
            style={{ background: '#0a0a0f' }}
          >
            <Controls style={{ background: 'rgba(15,15,20,0.8)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }} />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(255,255,255,0.05)" />
          </ReactFlow>
        </div>
      </div>

      {/* 右侧: 属性面板 */}
      <div className="glass-card" style={{ width: 260, margin: 8, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', padding: '12px 16px 4px', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          属性
        </div>
        <PropertiesPanel node={selectedNode} onUpdate={handleUpdateNode} />
      </div>
    </div>
  )
}

function getDefaultData(nodeType: string): Record<string, any> {
  switch (nodeType) {
    case 'open_url': return { url: '' }
    case 'click': return { selector: '' }
    case 'input_text': return { selector: '', text: '', human_like: true }
    case 'scroll': return { direction: 'down', amount: 300 }
    case 'wait': return { seconds: 2 }
    case 'screenshot': return { full_page: false }
    case 'get_text': return { selector: '', variable: 'text_result' }
    case 'condition': return { variable: '', operator: 'eq', value: '' }
    case 'loop': return { count: 3 }
    default: return {}
  }
}
