<template>
  <div class="chat-view">
    <!-- 对话消息区域 -->
    <div ref="messagesRef" class="messages-container">
      <!-- 欢迎消息 -->
      <div v-if="messages.length === 0" class="welcome-message">
        <div class="message assistant">
          <div class="message-content">
            <div class="message-text">
              你好！我是标书助手。请上传招标文件或输入你的需求，我可以帮你：
              <br /><br />
              • 分析招标文件要求<br />
              • 匹配符合条件的业绩<br />
              • 查询企业/律师信息<br />
              • 生成投标材料
            </div>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message', message.role]"
      >
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(message.content)"></div>
          
          <!-- 工具调用卡片 -->
          <div v-if="message.toolCalls && message.toolCalls.length > 0" class="tool-calls">
            <div
              v-for="(tool, index) in message.toolCalls"
              :key="index"
              class="tool-call-card"
            >
              <div class="tool-header">
                <span class="tool-icon">🔧</span>
                <span class="tool-name">{{ tool.tool }}</span>
                <span :class="['tool-status', tool.success ? 'success' : 'error']">
                  {{ tool.success ? '成功' : '失败' }}
                </span>
              </div>
              <div v-if="tool.params && Object.keys(tool.params).length > 0" class="tool-params">
                {{ JSON.stringify(tool.params) }}
              </div>
            </div>
          </div>

          <!-- 业绩卡片 -->
          <div v-if="message.performances && message.performances.length > 0" class="performance-cards">
            <div class="cards-header">📊 匹配业绩详情</div>
            <div
              v-for="perf in message.performances"
              :key="perf.id"
              class="performance-card"
            >
              <div class="perf-main">
                <div class="perf-header">
                  <span class="perf-name">{{ perf.contract_name || perf.file_name }}</span>
                  <span v-if="perf.is_state_owned" class="tag state-owned">国企</span>
                  <span class="tag type">{{ perf.contract_type || '其他' }}</span>
                </div>
                <div class="perf-info">
                  {{ perf.party_a || '未知甲方' }} · 
                  {{ perf.amount ? perf.amount + '万元' : '金额未知' }} · 
                  {{ perf.sign_date || '日期未知' }}
                </div>
              </div>
              <div v-if="perf.score" class="perf-score">
                <div :class="['score-value', getScoreClass(perf.score)]">
                  {{ Math.round(perf.score * 100) }}%
                </div>
                <div class="score-label">匹配度</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载中状态 -->
      <div v-if="isLoading" class="message assistant">
        <div class="message-content">
          <div class="loading-indicator">
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-wrapper">
        <button class="attach-btn" @click="handleAttach" title="上传文件">
          <el-icon :size="20"><Paperclip /></el-icon>
        </button>
        <input
          ref="inputRef"
          v-model="inputText"
          type="text"
          class="message-input"
          placeholder="输入需求，如：帮我找近五年的能源类业绩..."
          :disabled="isLoading"
          @keydown.enter="handleSend"
        />
        <button
          class="send-btn"
          :disabled="!inputText.trim() || isLoading"
          @click="handleSend"
        >
          发送
        </button>
      </div>
    </div>

    <!-- 隐藏的文件上传 -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".pdf"
      style="display: none"
      @change="handleFileChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { chat, uploadContract, semanticSearchPerformances } from '@/api'
import type { Message } from '@/stores/chat'

const chatStore = useChatStore()

// Refs
const messagesRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

// State
const inputText = ref('')
const isLoading = computed(() => chatStore.isLoading)
const messages = computed(() => chatStore.messages)

// 格式化消息（支持简单的 Markdown）
function formatMessage(content: string): string {
  if (!content) return ''
  
  return content
    // 加粗
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 换行
    .replace(/\n/g, '<br />')
}

// 获取分数样式类
function getScoreClass(score: number): string {
  if (score >= 0.9) return 'high'
  if (score >= 0.7) return 'medium'
  return 'low'
}

// 滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

// 发送消息
async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isLoading.value) return

  // 添加用户消息
  chatStore.addUserMessage(text)
  inputText.value = ''
  scrollToBottom()

  // 设置加载状态
  chatStore.setLoading(true)
  chatStore.setAgentStatus('thinking')
  chatStore.clearSteps()

  try {
    // 调用后端 API（使用 SSE 流式）
    await chatWithStream(text)
  } catch (error: any) {
    console.error('Chat error:', error)
    chatStore.addAssistantMessage('抱歉，发生了错误：' + (error.message || '未知错误'))
    chatStore.setAgentStatus('error')
  } finally {
    chatStore.setLoading(false)
    scrollToBottom()
  }
}

// 使用 SSE 流式对话
async function chatWithStream(message: string) {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, max_steps: 10 }),
  })

  if (!response.ok) {
    throw new Error('请求失败')
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('无法获取响应流')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let finalAnswer = ''
  let toolCalls: any[] = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    
    // 解析 SSE 事件
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let eventType = ''
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        const data = JSON.parse(line.slice(5).trim())
        
        // 处理不同事件
        switch (eventType) {
          case 'thinking':
            chatStore.setAgentStatus('thinking')
            chatStore.addStep({
              step: chatStore.currentSteps.length + 1,
              state: 'thinking',
              thought: data.thought,
            })
            break
            
          case 'tool_call':
            chatStore.setAgentStatus('executing')
            chatStore.addStep({
              step: chatStore.currentSteps.length + 1,
              state: 'executing',
              toolName: data.tool,
              toolParams: data.params,
            })
            break
            
          case 'tool_result':
            toolCalls.push({
              tool: data.tool,
              params: {},
              success: data.success,
            })
            chatStore.addStep({
              step: chatStore.currentSteps.length + 1,
              state: data.success ? 'done' : 'error',
              toolName: data.tool,
              toolResult: data.result,
              error: data.error,
            })
            break
            
          case 'answer':
            finalAnswer = data.answer
            chatStore.setAgentStatus('done')
            break
            
          case 'error':
            chatStore.setAgentStatus('error')
            finalAnswer = '抱歉，执行出错：' + data.error
            break
        }
      }
    }
  }

  // 添加助手消息
  if (finalAnswer) {
    // 检查是否包含业绩相关关键词，如果有则尝试获取业绩数据
    let performances: any[] = []
    if (finalAnswer.includes('业绩') || finalAnswer.includes('合同')) {
      try {
        const searchResult = await semanticSearchPerformances(message, 5, 'hybrid')
        if (searchResult.results && searchResult.results.length > 0) {
          performances = searchResult.results.map(r => ({
            ...r,
            score: r.score,
          }))
        }
      } catch (e) {
        // 忽略搜索错误
      }
    }

    const assistantMessage: Partial<Message> = {
      toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
    }
    
    // 如果有业绩数据，附加到消息
    if (performances.length > 0) {
      (assistantMessage as any).performances = performances
    }

    chatStore.addAssistantMessage(finalAnswer, assistantMessage)
  }
}

// 附件按钮
function handleAttach() {
  fileInputRef.value?.click()
}

// 文件选择
async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  // 添加用户消息
  chatStore.addUserMessage(`📎 上传文件: ${file.name}`)
  scrollToBottom()

  chatStore.setLoading(true)
  chatStore.setAgentStatus('executing')

  try {
    const result = await uploadContract(file, false, true)  // use_vision=false
    
    if (result.success) {
      const info = result.extracted_info
      let content = `✅ 合同解析成功！\n\n`
      content += `**文件名**: ${result.file_name}\n`
      content += `**页数**: ${result.page_count} 页\n`
      
      if (info) {
        if (info.contract_name) content += `**合同名称**: ${info.contract_name}\n`
        if (info.party_a) content += `**甲方**: ${info.party_a}\n`
        if (info.contract_type) content += `**类型**: ${info.contract_type}\n`
        if (info.amount) content += `**金额**: ${info.amount} 元\n`
        if (info.sign_date) content += `**签订日期**: ${info.sign_date}\n`
        if (info.summary) content += `\n**摘要**: ${info.summary}`
      }
      
      if (result.performance_id) {
        content += `\n\n已保存到业绩库，ID: ${result.performance_id}`
      }
      
      chatStore.addAssistantMessage(content)
      chatStore.setAgentStatus('done')
    } else {
      chatStore.addAssistantMessage(`❌ 解析失败: ${result.message}`)
      chatStore.setAgentStatus('error')
    }
  } catch (error: any) {
    chatStore.addAssistantMessage(`❌ 上传失败: ${error.message}`)
    chatStore.setAgentStatus('error')
  } finally {
    chatStore.setLoading(false)
    target.value = '' // 清空文件选择
    scrollToBottom()
  }
}

onMounted(() => {
  inputRef.value?.focus()
})
</script>

<style lang="scss" scoped>
.chat-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
}

// ============================================
// 消息区域
// ============================================
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  
  .welcome-message {
    max-width: 800px;
    margin: 0 auto;
  }

  .message {
    display: flex;
    margin-bottom: 16px;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;

    &.user {
      justify-content: flex-end;

      .message-content {
        background: #2563eb;
        color: #fff;
        border-radius: 20px 20px 4px 20px;
      }
    }

    &.assistant {
      justify-content: flex-start;

      .message-content {
        background: #fff;
        color: #374151;
        border: 1px solid #e5e7eb;
        border-radius: 20px 20px 20px 4px;
      }
    }

    .message-content {
      max-width: 85%;
      padding: 14px 18px;

      .message-text {
        font-size: 14px;
        line-height: 1.6;

        :deep(strong) {
          font-weight: 600;
        }
      }
    }
  }
}

// ============================================
// 工具调用卡片
// ============================================
.tool-calls {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;

  .tool-call-card {
    background: #f9fafb;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }

    .tool-header {
      display: flex;
      align-items: center;
      gap: 8px;

      .tool-icon {
        font-size: 14px;
      }

      .tool-name {
        font-size: 13px;
        font-weight: 500;
        color: #374151;
      }

      .tool-status {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: auto;

        &.success {
          background: #dcfce7;
          color: #15803d;
        }

        &.error {
          background: #fef2f2;
          color: #dc2626;
        }
      }
    }

    .tool-params {
      margin-top: 8px;
      font-size: 11px;
      font-family: monospace;
      color: #6b7280;
      background: #fff;
      padding: 6px 10px;
      border-radius: 4px;
      word-break: break-all;
    }
  }
}

// ============================================
// 业绩卡片
// ============================================
.performance-cards {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;

  .cards-header {
    font-size: 14px;
    font-weight: 500;
    color: #374151;
    margin-bottom: 10px;
  }

  .performance-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #f3f4f6;
    }

    &:last-child {
      margin-bottom: 0;
    }

    .perf-main {
      flex: 1;
      overflow: hidden;

      .perf-header {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;

        .perf-name {
          font-size: 14px;
          font-weight: 500;
          color: #1f2937;
        }

        .tag {
          padding: 2px 6px;
          font-size: 11px;
          border-radius: 4px;

          &.state-owned {
            background: #fef2f2;
            color: #dc2626;
          }

          &.type {
            background: #f3f4f6;
            color: #4b5563;
          }
        }
      }

      .perf-info {
        font-size: 12px;
        color: #6b7280;
        margin-top: 4px;
      }
    }

    .perf-score {
      text-align: right;
      margin-left: 16px;

      .score-value {
        font-size: 18px;
        font-weight: 700;

        &.high { color: #16a34a; }
        &.medium { color: #2563eb; }
        &.low { color: #ca8a04; }
      }

      .score-label {
        font-size: 11px;
        color: #9ca3af;
      }
    }
  }
}

// ============================================
// 加载指示器
// ============================================
.loading-indicator {
  display: flex;
  gap: 4px;

  .loading-dot {
    width: 8px;
    height: 8px;
    background: #9ca3af;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

// ============================================
// 输入区域
// ============================================
.input-area {
  padding: 16px 20px;
  background: #fff;
  border-top: 1px solid #e5e7eb;

  .input-wrapper {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 10px;

    .attach-btn {
      padding: 10px;
      background: none;
      border: none;
      color: #9ca3af;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s;

      &:hover {
        background: #f3f4f6;
        color: #4b5563;
      }
    }

    .message-input {
      flex: 1;
      padding: 12px 16px;
      background: #f3f4f6;
      border: none;
      border-radius: 12px;
      font-size: 14px;
      outline: none;
      transition: all 0.2s;

      &:focus {
        background: #fff;
        box-shadow: 0 0 0 2px #2563eb;
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      &::placeholder {
        color: #9ca3af;
      }
    }

    .send-btn {
      padding: 12px 20px;
      background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;

      &:hover:not(:disabled) {
        background: #1d4ed8;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }
}
</style>