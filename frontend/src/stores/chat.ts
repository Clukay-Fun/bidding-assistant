import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 消息类型
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  // Agent 相关
  thinking?: string
  toolCalls?: ToolCall[]
  status?: 'thinking' | 'executing' | 'done' | 'error'
}

// 工具调用记录
export interface ToolCall {
  tool: string
  params: Record<string, any>
  result?: any
  success?: boolean
}

// Agent 执行步骤
export interface AgentStep {
  step: number
  state: string
  thought?: string
  toolName?: string
  toolParams?: Record<string, any>
  toolResult?: any
  error?: string
}

export const useChatStore = defineStore('chat', () => {
  // ============================================
  // State
  // ============================================
  
  // 消息列表
  const messages = ref<Message[]>([])
  
  // 当前 Agent 状态
  const agentStatus = ref<'idle' | 'thinking' | 'executing' | 'done' | 'error'>('idle')
  
  // 当前执行步骤
  const currentSteps = ref<AgentStep[]>([])
  
  // 是否正在加载
  const isLoading = ref(false)

  // ============================================
  // Getters
  // ============================================
  
  const messageCount = computed(() => messages.value.length)
  
  const lastMessage = computed(() => 
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null
  )

  // ============================================
  // Actions
  // ============================================
  
  // 添加用户消息
  function addUserMessage(content: string) {
    const message: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }
    messages.value.push(message)
    return message
  }
  
  // 添加助手消息
  function addAssistantMessage(content: string, extra?: Partial<Message>) {
    const message: Message = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content,
      timestamp: new Date(),
      ...extra,
    }
    messages.value.push(message)
    return message
  }
  
  // 更新最后一条助手消息
  function updateLastAssistantMessage(updates: Partial<Message>) {
    const lastAssistant = [...messages.value].reverse().find(m => m.role === 'assistant')
    if (lastAssistant) {
      Object.assign(lastAssistant, updates)
    }
  }
  
  // 添加执行步骤
  function addStep(step: AgentStep) {
    currentSteps.value.push(step)
  }
  
  // 清空执行步骤
  function clearSteps() {
    currentSteps.value = []
  }
  
  // 设置 Agent 状态
  function setAgentStatus(status: typeof agentStatus.value) {
    agentStatus.value = status
  }
  
  // 设置加载状态
  function setLoading(loading: boolean) {
    isLoading.value = loading
  }
  
  // 清空所有消息
  function clearMessages() {
    messages.value = []
    currentSteps.value = []
    agentStatus.value = 'idle'
  }

  return {
    // State
    messages,
    agentStatus,
    currentSteps,
    isLoading,
    // Getters
    messageCount,
    lastMessage,
    // Actions
    addUserMessage,
    addAssistantMessage,
    updateLastAssistantMessage,
    addStep,
    clearSteps,
    setAgentStatus,
    setLoading,
    clearMessages,
  }
})