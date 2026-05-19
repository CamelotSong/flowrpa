import React, { useState } from 'react'
import { Button, Input, Select, Form, Card, List, Tag, Divider, message, Spin } from 'antd'
import { RobotOutlined, ThunderboltOutlined, ImportOutlined, SettingOutlined } from '@ant-design/icons'
import { useStore } from '../store'

const { TextArea } = Input
const { Option } = Select

const PROVIDERS = [
  { label: 'OpenAI', value: 'openai', models: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  { label: 'Anthropic Claude', value: 'claude', models: ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'] },
  { label: '自定义', value: 'custom', models: [] },
]

const NODE_TYPE_LABELS: Record<string, string> = {
  open_url: '🌐 打开网页',
  click: '🖱️ 点击元素',
  input_text: '⌨️ 输入文字',
  wait: '⏱️ 等待',
  scroll: '📜 滚动页面',
  screenshot: '📸 截图',
  get_text: '📝 获取文本',
  condition: '🔀 条件判断',
  loop: '🔁 循环',
}

interface GeneratedNode {
  id: string
  type: string
  label: string
  data: Record<string, any>
}

export default function AIGenerator() {
  const { setWorkflowNodes, setWorkflowEdges } = useStore()
  const [form] = Form.useForm()

  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-4o')
  const [customModel, setCustomModel] = useState('')
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('llm_api_key') || '')
  const [baseUrl, setBaseUrl] = useState(() => localStorage.getItem('llm_base_url') || '')
  const [prompt, setPrompt] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generatedNodes, setGeneratedNodes] = useState<GeneratedNode[]>([])
  const [showSettings, setShowSettings] = useState(false)

  const selectedProvider = PROVIDERS.find(p => p.value === provider)

  const handleProviderChange = (v: string) => {
    setProvider(v)
    const p = PROVIDERS.find(x => x.value === v)
    if (p && p.models.length > 0) setModel(p.models[0])
  }

  const saveSettings = () => {
    localStorage.setItem('llm_api_key', apiKey)
    localStorage.setItem('llm_base_url', baseUrl)
    message.success('配置已保存')
    setShowSettings(false)
  }

  const callLLM = async (userPrompt: string): Promise<string> => {
    const url = provider === 'claude'
      ? 'https://api.anthropic.com/v1/messages'
      : (baseUrl || 'https://api.openai.com/v1') + '/chat/completions'

    const systemPrompt = `你是一个RPA工作流生成器。根据用户描述，生成一个JSON格式的工作流。

工作流格式：
{
  "nodes": [
    {
      "id": "node_1",
      "type": "open_url",  // 节点类型
      "label": "打开百度",  // 节点名称
      "data": {
        "url": "https://www.baidu.com"  // 节点参数
      }
    }
  ],
  "edges": [
    {"id": "e1", "source": "node_1", "target": "node_2"}
  ]
}

可用节点类型及参数：
- open_url: {url: string}
- click: {selector: string, selector_type: "css"|"xpath"|"text", description: string}
- input_text: {selector: string, text: string, selector_type: "css"|"xpath"|"text"}
- wait: {wait_type: "time"|"element", seconds?: number, selector?: string}
- scroll: {direction: "down"|"up", amount: number}
- screenshot: {filename: string}
- get_text: {selector: string, variable_name: string}
- condition: {condition_type: "element_exists"|"text_contains", selector?: string, text?: string, value?: string}
- loop: {loop_type: "count"|"while", count?: number, selector?: string}

只返回JSON，不要有其他文字。`

    if (provider === 'claude') {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: model,
          max_tokens: 4096,
          system: systemPrompt,
          messages: [{ role: 'user', content: userPrompt }],
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error?.message || '请求失败')
      return data.content[0].text
    } else {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: customModel || model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt },
          ],
          max_tokens: 4096,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error?.message || '请求失败')
      return data.choices[0].message.content
    }
  }

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      message.warning('请输入任务描述')
      return
    }
    if (!apiKey) {
      message.warning('请先配置 API Key')
      setShowSettings(true)
      return
    }

    setGenerating(true)
    setGeneratedNodes([])

    try {
      const raw = await callLLM(prompt)
      // 提取JSON
      const jsonMatch = raw.match(/\{[\s\S]*\}/)
      if (!jsonMatch) throw new Error('AI返回格式异常')
      const workflow = JSON.parse(jsonMatch[0])
      setGeneratedNodes(workflow.nodes || [])
      message.success(`生成了 ${workflow.nodes?.length || 0} 个节点`)
      // 暂存 edges 供导入用
      ;(window as any).__pendingEdges = workflow.edges || []
    } catch (e: any) {
      message.error('生成失败：' + (e.message || '未知错误'))
    } finally {
      setGenerating(false)
    }
  }

  const handleImport = () => {
    if (!generatedNodes.length) return
    // 转成 React Flow 格式
    const rfNodes = generatedNodes.map((n, i) => ({
      id: n.id,
      type: 'customNode',
      position: { x: 250, y: i * 120 },
      data: { label: n.label, nodeType: n.type, ...n.data },
    }))
    const rfEdges = ((window as any).__pendingEdges || []).map((e: any) => ({
      ...e,
      animated: true,
      style: { stroke: '#4F8EF7' },
    }))
    setWorkflowNodes(rfNodes)
    setWorkflowEdges(rfEdges)
    message.success('已导入到编辑器，切换到"工作流编辑器"查看')
  }

  return (
    <div style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      {/* 标题 */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24, gap: 12 }}>
        <RobotOutlined style={{ fontSize: 28, color: '#4F8EF7' }} />
        <div>
          <h2 style={{ margin: 0, color: '#fff' }}>AI 工作流生成</h2>
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
            用自然语言描述任务，AI 自动生成工作流节点
          </span>
        </div>
        <Button
          icon={<SettingOutlined />}
          style={{ marginLeft: 'auto' }}
          onClick={() => setShowSettings(!showSettings)}
          className="glass-btn"
        >
          API 配置
        </Button>
      </div>

      {/* API 配置面板 */}
      {showSettings && (
        <Card className="glass-card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label className="form-label">Provider</label>
              <Select value={provider} onChange={handleProviderChange} style={{ width: '100%' }} className="glass-select">
                {PROVIDERS.map(p => <Option key={p.value} value={p.value}>{p.label}</Option>)}
              </Select>
            </div>
            <div>
              <label className="form-label">Model</label>
              {provider === 'custom' ? (
                <Input
                  value={customModel}
                  onChange={e => setCustomModel(e.target.value)}
                  placeholder="输入模型名称"
                  className="glass-input"
                />
              ) : (
                <Select value={model} onChange={setModel} style={{ width: '100%' }} className="glass-select">
                  {selectedProvider?.models.map(m => <Option key={m} value={m}>{m}</Option>)}
                </Select>
              )}
            </div>
            <div>
              <label className="form-label">API Key</label>
              <Input.Password
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="glass-input"
              />
            </div>
            <div>
              <label className="form-label">Base URL（可选，自定义端点）</label>
              <Input
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="glass-input"
              />
            </div>
          </div>
          <Button type="primary" onClick={saveSettings} style={{ marginTop: 12 }}>
            保存配置
          </Button>
        </Card>
      )}

      {/* 输入区域 */}
      <Card className="glass-card" style={{ marginBottom: 20 }}>
        <label className="form-label" style={{ display: 'block', marginBottom: 8 }}>
          用自然语言描述你要自动化的任务
        </label>
        <TextArea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder={`示例：
打开 BOSS直聘，搜索"前端工程师"，筛选北京地区本科及以上学历，读取前20条简历，给评分高于70分的候选人发送招呼语"您好，我们对您很感兴趣"，然后要求对方发简历和联系方式。`}
          rows={6}
          className="glass-input"
          style={{ resize: 'none' }}
        />
        <div style={{ marginTop: 12, display: 'flex', gap: 12 }}>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleGenerate}
            loading={generating}
            size="large"
            style={{ background: 'linear-gradient(135deg, #4F8EF7, #7B5EFB)' }}
          >
            {generating ? '生成中...' : '生成工作流'}
          </Button>
          {generatedNodes.length > 0 && (
            <Button
              icon={<ImportOutlined />}
              onClick={handleImport}
              size="large"
              className="glass-btn"
            >
              导入到编辑器
            </Button>
          )}
        </div>
      </Card>

      {/* 生成中 loading */}
      {generating && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <p style={{ color: 'rgba(255,255,255,0.6)', marginTop: 16 }}>
            AI 正在分析任务并生成工作流节点...
          </p>
        </div>
      )}

      {/* 生成结果预览 */}
      {generatedNodes.length > 0 && !generating && (
        <Card className="glass-card">
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
            <span style={{ color: '#fff', fontWeight: 600 }}>
              预览 — 共 {generatedNodes.length} 个节点
            </span>
            <Tag color="green" style={{ marginLeft: 12 }}>生成成功</Tag>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {generatedNodes.map((node, idx) => (
              <div
                key={node.id}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  padding: '12px 16px',
                  background: 'rgba(79,142,247,0.08)',
                  borderRadius: 8,
                  border: '1px solid rgba(79,142,247,0.2)',
                }}
              >
                <span style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: 'rgba(79,142,247,0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#4F8EF7', fontSize: 12, fontWeight: 700, flexShrink: 0,
                }}>
                  {idx + 1}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ color: '#fff', fontWeight: 500 }}>{node.label}</span>
                    <Tag style={{ margin: 0, fontSize: 11 }}>
                      {NODE_TYPE_LABELS[node.type] || node.type}
                    </Tag>
                  </div>
                  <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
                    {JSON.stringify(node.data, null, 0)}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Divider style={{ borderColor: 'rgba(255,255,255,0.1)' }} />
          <Button
            type="primary"
            icon={<ImportOutlined />}
            onClick={handleImport}
            block
            size="large"
          >
            导入到编辑器
          </Button>
        </Card>
      )}
    </div>
  )
}
