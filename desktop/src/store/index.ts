import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ── Types ──

export interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, any>
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
}

export interface ExecutionLog {
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
  timestamp: number
  nodeId?: string
}

export interface Candidate {
  id: string
  name: string
  title: string
  education: string
  experience: string
  salary: string
  city: string
  raw_text?: string
  skills?: string[]
  ai_score?: {
    score: number
    reason: string
    highlights: string[]
    concerns: string[]
    dimensions?: Record<string, number>
  }
}

export interface BossJob {
  job_id: string
  title: string
  jd: string
}

export interface LLMConfig {
  provider: 'openai' | 'claude' | 'custom'
  model: string
  api_key: string
  base_url: string
}

// ── Store ──

interface AppStore {
  // Workflow
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  selectedNodeId: string | null
  workflowName: string
  setNodes: (nodes: WorkflowNode[]) => void
  setEdges: (edges: WorkflowEdge[]) => void
  setSelectedNode: (id: string | null) => void
  updateNodeData: (id: string, data: Partial<Record<string, any>>) => void
  setWorkflowName: (name: string) => void

  // Execution
  executionRunning: boolean
  executionLogs: ExecutionLog[]
  nodeStatus: Record<string, 'pending' | 'running' | 'success' | 'error'>
  setExecutionRunning: (v: boolean) => void
  addLog: (log: ExecutionLog) => void
  clearLogs: () => void
  setNodeStatus: (id: string, status: 'pending' | 'running' | 'success' | 'error') => void
  resetNodeStatus: () => void

  // Boss
  candidates: Candidate[]
  selectedCandidateId: string | null
  filterParams: Record<string, any>
  bossLoggedIn: boolean
  bossJobs: BossJob[]
  selectedJobId: string
  scoring: boolean
  greetTemplate: string
  followupTemplate: string
  batchSize: number
  topN: number
  minScore: number
  setCandidates: (c: Candidate[]) => void
  setSelectedCandidate: (id: string | null) => void
  setFilterParams: (p: Record<string, any>) => void
  setBossLoggedIn: (v: boolean) => void
  setBossJobs: (jobs: BossJob[]) => void
  setSelectedJobId: (id: string) => void
  setScoring: (v: boolean) => void
  setGreetTemplate: (s: string) => void
  setFollowupTemplate: (s: string) => void
  setBatchSize: (n: number) => void
  setTopN: (n: number) => void
  setMinScore: (n: number) => void
  updateCandidateScore: (id: string, score: any) => void

  // Settings
  llmConfig: LLMConfig
  engineUrl: string
  engineConnected: boolean
  setLLMConfig: (c: Partial<LLMConfig>) => void
  setEngineUrl: (url: string) => void
  setEngineConnected: (v: boolean) => void
}

export const useStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // Workflow
      nodes: [],
      edges: [],
      selectedNodeId: null,
      workflowName: '未命名工作流',
      setNodes: (nodes) => set({ nodes }),
      setEdges: (edges) => set({ edges }),
      setSelectedNode: (id) => set({ selectedNodeId: id }),
      updateNodeData: (id, data) => set((state) => ({
        nodes: state.nodes.map(n =>
          n.id === id ? { ...n, data: { ...n.data, ...data } } : n
        ),
      })),
      setWorkflowName: (name) => set({ workflowName: name }),

      // Execution
      executionRunning: false,
      executionLogs: [],
      nodeStatus: {},
      setExecutionRunning: (v) => set({ executionRunning: v }),
      addLog: (log) => set((state) => ({
        executionLogs: [...state.executionLogs.slice(-499), log],
      })),
      clearLogs: () => set({ executionLogs: [] }),
      setNodeStatus: (id, status) => set((state) => ({
        nodeStatus: { ...state.nodeStatus, [id]: status },
      })),
      resetNodeStatus: () => set({ nodeStatus: {} }),

      // Boss
      candidates: [],
      selectedCandidateId: null,
      filterParams: {},
      bossLoggedIn: false,
      bossJobs: [],
      selectedJobId: '',
      scoring: false,
      greetTemplate: '您好{name}，我们看了您的简历很感兴趣！',
      followupTemplate: '请问方便发一份完整简历和联系方式给我吗？期待进一步沟通～',
      batchSize: 20,
      topN: 10,
      minScore: 60,
      setCandidates: (c) => set({ candidates: c }),
      setSelectedCandidate: (id) => set({ selectedCandidateId: id }),
      setFilterParams: (p) => set({ filterParams: p }),
      setBossLoggedIn: (v) => set({ bossLoggedIn: v }),
      setBossJobs: (jobs) => set({ bossJobs: jobs }),
      setSelectedJobId: (id) => set({ selectedJobId: id }),
      setScoring: (v) => set({ scoring: v }),
      setGreetTemplate: (s) => set({ greetTemplate: s }),
      setFollowupTemplate: (s) => set({ followupTemplate: s }),
      setBatchSize: (n) => set({ batchSize: n }),
      setTopN: (n) => set({ topN: n }),
      setMinScore: (n) => set({ minScore: n }),
      updateCandidateScore: (id, score) => set((state) => ({
        candidates: state.candidates.map(c =>
          c.id === id ? { ...c, ai_score: score } : c
        ),
      })),

      // Settings
      llmConfig: {
        provider: 'openai',
        model: 'gpt-4o-mini',
        api_key: '',
        base_url: 'https://api.openai.com/v1',
      },
      engineUrl: 'http://127.0.0.1:9222',
      engineConnected: false,
      setLLMConfig: (c) => set((state) => ({ llmConfig: { ...state.llmConfig, ...c } })),
      setEngineUrl: (url) => set({ engineUrl: url }),
      setEngineConnected: (v) => set({ engineConnected: v }),
    }),
    {
      name: 'flowrpa-store',
      partialize: (state) => ({
        workflowName: state.workflowName,
        nodes: state.nodes,
        edges: state.edges,
        greetTemplate: state.greetTemplate,
        followupTemplate: state.followupTemplate,
        batchSize: state.batchSize,
        topN: state.topN,
        minScore: state.minScore,
        llmConfig: state.llmConfig,
        engineUrl: state.engineUrl,
        bossJobs: state.bossJobs,
      }),
    }
  )
)
