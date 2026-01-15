<template>
  <div class="app-container">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <!-- Logo -->
      <div class="logo" @click="router.push('/chat')">
        <div class="logo-icon">
          <el-icon :size="20"><Document /></el-icon>
        </div>
        <span class="logo-text">标书助手</span>
      </div>

      <!-- 侧边栏选项卡 -->
      <div class="sidebar-tabs">
        <button
          v-for="tab in sidebarTabs"
          :key="tab.key"
          :class="['tab-btn', { active: activeSidebarTab === tab.key }]"
          @click="activeSidebarTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 侧边栏内容 -->
      <div class="sidebar-content">
        <!-- 项目列表 -->
        <div v-show="activeSidebarTab === 'project'" class="panel-content">
          <button class="add-btn">
            <el-icon><Plus /></el-icon>
            新建项目
          </button>
          <div
            v-for="project in projects"
            :key="project.id"
            class="list-item"
          >
            <div class="item-header">
              <span class="item-title">{{ project.name }}</span>
              <span :class="['status-dot', project.status]"></span>
            </div>
            <span class="item-date">{{ project.date }}</span>
          </div>
        </div>

        <!-- 律师列表 -->
        <div v-show="activeSidebarTab === 'lawyer'" class="panel-content">
          <button class="add-btn" @click="router.push('/lawyers')">
            <el-icon><Plus /></el-icon>
            添加律师
          </button>
          <div
            v-for="lawyer in lawyers"
            :key="lawyer.id"
            class="list-item lawyer-item"
          >
            <div class="avatar">{{ lawyer.name.charAt(0) }}</div>
            <div class="lawyer-info">
              <div class="lawyer-name">{{ lawyer.name }}</div>
              <div class="lawyer-license">执业证号: {{ lawyer.license }}</div>
            </div>
          </div>
        </div>

        <!-- 企业列表 -->
        <div v-show="activeSidebarTab === 'enterprise'" class="panel-content">
          <button class="add-btn" @click="router.push('/enterprises')">
            <el-icon><Plus /></el-icon>
            添加企业
          </button>
          <div
            v-for="enterprise in enterprises"
            :key="enterprise.id"
            class="list-item"
          >
            <div class="item-header">
              <span class="item-title">{{ enterprise.name }}</span>
              <span v-if="enterprise.isStateOwned" class="tag state-owned">国企</span>
            </div>
            <span class="item-date">{{ enterprise.creditCode }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-area">
      <!-- 顶部标签栏 -->
      <header class="main-header">
        <div class="main-tabs">
          <button
            v-for="tab in mainTabs"
            :key="tab.path"
            :class="['main-tab-btn', { active: currentRoute === tab.path }]"
            @click="router.push(tab.path)"
          >
            {{ tab.icon }} {{ tab.label }}
          </button>
        </div>

        <div class="header-right">
          <!-- Agent 状态指示器 -->
          <div :class="['agent-status', agentStatus]">
            <span class="status-dot"></span>
            <span class="status-text">{{ agentStatusText }}</span>
          </div>

          <!-- 轨迹面板切换 -->
          <button
            :class="['trace-toggle', { active: showTrace }]"
            @click="showTrace = !showTrace"
            title="显示/隐藏 Agent 轨迹"
          >
            <el-icon :size="18"><List /></el-icon>
          </button>
        </div>
      </header>

      <!-- 内容区域 -->
      <div class="content-wrapper">
        <div class="content-main">
          <router-view />
        </div>

        <!-- Agent 轨迹面板 -->
        <aside v-show="showTrace" class="trace-panel">
          <div class="trace-header">
            <span class="trace-title">🧠 Agent 轨迹</span>
            <button class="clear-btn" @click="clearTrace">清空</button>
          </div>
          <div class="trace-content">
            <div v-if="traceSteps.length === 0" class="trace-empty">
              暂无执行记录
            </div>
            <div v-else class="trace-timeline">
              <div
                v-for="(step, index) in traceSteps"
                :key="index"
                class="trace-item"
              >
                <div class="trace-icon-wrapper">
                  <div :class="['trace-icon', step.type]">
                    {{ step.icon }}
                  </div>
                  <div v-if="index < traceSteps.length - 1" class="trace-line"></div>
                </div>
                <div class="trace-body">
                  <div class="trace-time">{{ step.time }}</div>
                  <div class="trace-message">{{ step.message }}</div>
                  <div v-if="step.params" class="trace-params">
                    {{ JSON.stringify(step.params) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

// 当前路由
const currentRoute = computed(() => route.path)

// 侧边栏选项卡
const sidebarTabs = [
  { key: 'project', label: '项目' },
  { key: 'lawyer', label: '律师' },
  { key: 'enterprise', label: '企业' },
]
const activeSidebarTab = ref('project')

// 主内容选项卡
const mainTabs = [
  { path: '/chat', label: 'AI对话', icon: '💬' },
  { path: '/performances', label: '业绩库', icon: '📊' },
  { path: '/upload', label: '文档', icon: '📄' },
]

// Agent 状态
const agentStatus = computed(() => chatStore.agentStatus)
const agentStatusText = computed(() => {
  const statusMap: Record<string, string> = {
    idle: '就绪',
    thinking: '思考中...',
    executing: '执行中...',
    done: '完成',
    error: '错误',
  }
  return statusMap[agentStatus.value] || '就绪'
})

// 轨迹面板
const showTrace = ref(true)
const traceSteps = computed(() => {
  return chatStore.currentSteps.map(step => ({
    type: step.state === 'thinking' ? 'thinking' 
        : step.state === 'executing' ? 'executing'
        : step.error ? 'error' 
        : 'success',
    icon: step.state === 'thinking' ? '🤔'
        : step.toolName ? '🔧'
        : step.error ? '✗'
        : '✓',
    time: new Date().toLocaleTimeString(),
    message: step.thought || step.toolName || step.error || '',
    params: step.toolParams,
  }))
})

function clearTrace() {
  chatStore.clearSteps()
}

// 模拟数据
const projects = ref([
  { id: 1, name: '深圳燃气集团采购项目', date: '2025-01-10', status: 'active' },
  { id: 2, name: '南方电网法律顾问招标', date: '2025-01-08', status: 'pending' },
  { id: 3, name: '华润置地专项服务', date: '2025-01-05', status: 'done' },
])

const lawyers = ref([
  { id: 1, name: '张三', license: '1440120****' },
  { id: 2, name: '李四', license: '1440120****' },
  { id: 3, name: '王五', license: '1440120****' },
])

const enterprises = ref([
  { id: 1, name: '深圳燃气集团', creditCode: '91440300...', isStateOwned: true },
  { id: 2, name: '南方电网', creditCode: '91440300...', isStateOwned: true },
  { id: 3, name: '华润置地', creditCode: '91440300...', isStateOwned: true },
])
</script>

<style lang="scss" scoped>
.app-container {
  height: 100vh;
  display: flex;
  background-color: #f5f7fa;
}

// ============================================
// 左侧边栏
// ============================================
.sidebar {
  width: 256px;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;

  .logo {
    height: 56px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #e5e7eb;
    cursor: pointer;

    .logo-icon {
      width: 32px;
      height: 32px;
      background: #2563eb;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }

    .logo-text {
      font-size: 16px;
      font-weight: 600;
      color: #1f2937;
    }
  }

  .sidebar-tabs {
    display: flex;
    border-bottom: 1px solid #e5e7eb;

    .tab-btn {
      flex: 1;
      padding: 10px 0;
      font-size: 13px;
      font-weight: 500;
      color: #6b7280;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        color: #374151;
      }

      &.active {
        color: #2563eb;
        border-bottom-color: #2563eb;
      }
    }
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .panel-content {
    .add-btn {
      width: 100%;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: #2563eb;
      background: none;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #eff6ff;
      }
    }

    .list-item {
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #f3f4f6;
      }

      .item-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .item-title {
        font-size: 14px;
        color: #374151;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .item-date {
        font-size: 12px;
        color: #9ca3af;
      }

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;

        &.active { background: #22c55e; }
        &.pending { background: #eab308; }
        &.done { background: #d1d5db; }
      }

      .tag {
        padding: 2px 6px;
        font-size: 11px;
        border-radius: 4px;
        flex-shrink: 0;

        &.state-owned {
          background: #fef2f2;
          color: #dc2626;
        }
      }
    }

    .lawyer-item {
      display: flex;
      align-items: center;
      gap: 10px;

      .avatar {
        width: 32px;
        height: 32px;
        background: #e5e7eb;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        color: #4b5563;
        flex-shrink: 0;
      }

      .lawyer-info {
        overflow: hidden;

        .lawyer-name {
          font-size: 14px;
          color: #374151;
        }

        .lawyer-license {
          font-size: 12px;
          color: #9ca3af;
        }
      }
    }
  }
}

// ============================================
// 主内容区
// ============================================
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .main-header {
    height: 56px;
    padding: 0 16px;
    background: #fff;
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .main-tabs {
      display: flex;
      gap: 8px;

      .main-tab-btn {
        padding: 8px 14px;
        font-size: 14px;
        font-weight: 500;
        color: #4b5563;
        background: none;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: #f3f4f6;
        }

        &.active {
          background: #dbeafe;
          color: #1d4ed8;
        }
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .agent-status {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }

      &.idle {
        background: #f3f4f6;
        color: #4b5563;
        .status-dot { background: #9ca3af; }
      }

      &.thinking {
        background: #fef9c3;
        color: #a16207;
        .status-dot { background: #eab308; animation: pulse 1.5s infinite; }
      }

      &.executing {
        background: #dbeafe;
        color: #1d4ed8;
        .status-dot { background: #3b82f6; animation: pulse 1.5s infinite; }
      }

      &.done {
        background: #dcfce7;
        color: #15803d;
        .status-dot { background: #22c55e; }
      }

      &.error {
        background: #fef2f2;
        color: #dc2626;
        .status-dot { background: #ef4444; }
      }
    }

    .trace-toggle {
      padding: 8px;
      background: none;
      border: none;
      border-radius: 8px;
      color: #9ca3af;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: #f3f4f6;
        color: #4b5563;
      }

      &.active {
        background: #dbeafe;
        color: #2563eb;
      }
    }
  }

  .content-wrapper {
    flex: 1;
    display: flex;
    overflow: hidden;

    .content-main {
      flex: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
  }
}

// ============================================
// Agent 轨迹面板
// ============================================
.trace-panel {
  width: 320px;
  background: #fff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;

  .trace-header {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .trace-title {
      font-size: 14px;
      font-weight: 500;
      color: #374151;
    }

    .clear-btn {
      font-size: 12px;
      color: #9ca3af;
      background: none;
      border: none;
      cursor: pointer;

      &:hover {
        color: #4b5563;
      }
    }
  }

  .trace-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .trace-empty {
      text-align: center;
      color: #9ca3af;
      font-size: 13px;
      padding: 40px 0;
    }

    .trace-timeline {
      .trace-item {
        display: flex;
        gap: 12px;

        .trace-icon-wrapper {
          display: flex;
          flex-direction: column;
          align-items: center;

          .trace-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;

            &.thinking {
              background: #fef9c3;
              color: #a16207;
            }

            &.executing {
              background: #dbeafe;
              color: #1d4ed8;
            }

            &.success {
              background: #dcfce7;
              color: #15803d;
            }

            &.error {
              background: #fef2f2;
              color: #dc2626;
            }
          }

          .trace-line {
            width: 2px;
            flex: 1;
            background: #e5e7eb;
            margin-top: 4px;
          }
        }

        .trace-body {
          flex: 1;
          padding-bottom: 16px;

          .trace-time {
            font-size: 11px;
            color: #9ca3af;
            margin-bottom: 4px;
          }

          .trace-message {
            font-size: 13px;
            color: #374151;
          }

          .trace-params {
            margin-top: 6px;
            padding: 6px 10px;
            background: #f9fafb;
            border-radius: 6px;
            font-size: 11px;
            font-family: monospace;
            color: #6b7280;
            word-break: break-all;
          }
        }
      }
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>