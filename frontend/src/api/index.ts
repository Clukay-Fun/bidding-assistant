import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'

// ============================================
// region 创建 Axios 实例
// ============================================

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 120000, // 2分钟超时（OCR 可能较慢）
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token 等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// endregion
// ============================================


// ============================================
// region 对话 API
// ============================================

export interface ChatRequest {
  message: string
  max_steps?: number
}

export interface ChatResponse {
  answer: string
  steps: number
  tool_calls: Array<{
    tool: string
    params: Record<string, any>
    success: boolean
  }>
}

export interface Tool {
  name: string
  description: string
  category: string
  parameters: Array<{
    name: string
    type: string
    description: string
    required: boolean
  }>
}

// 同步对话
export function chat(data: ChatRequest): Promise<ChatResponse> {
  return request.post('/chat/', data)
}

// 获取可用工具
export function getTools(): Promise<{ count: number; tools: Tool[] }> {
  return request.get('/chat/tools')
}

// endregion
// ============================================


// ============================================
// region 业绩 API
// ============================================

export interface Performance {
  id: number
  file_name: string
  party_a?: string
  party_a_credit_code?: string
  contract_type?: string
  amount?: number
  sign_date?: string
  project_detail?: string
  subject_amount?: number
  opponent?: string
  team_member?: string
  summary?: string
  created_at?: string
}

export interface PerformanceSearchParams {
  party_a?: string
  contract_type?: string
  min_amount?: number
  max_amount?: number
  years?: number
  keyword?: string
}

// 获取业绩列表
export function getPerformances(skip = 0, limit = 20): Promise<Performance[]> {
  return request.get('/performances/', { params: { skip, limit } })
}

// 搜索业绩
export function searchPerformances(params: PerformanceSearchParams): Promise<Performance[]> {
  return request.get('/performances/search', { params })
}

// 获取业绩详情
export function getPerformance(id: number): Promise<Performance> {
  return request.get(`/performances/${id}`)
}

// 创建业绩
export function createPerformance(data: Partial<Performance>): Promise<Performance> {
  return request.post('/performances/', data)
}

// 更新业绩
export function updatePerformance(id: number, data: Partial<Performance>): Promise<Performance> {
  return request.put(`/performances/${id}`, data)
}

// 删除业绩
export function deletePerformance(id: number): Promise<{ message: string }> {
  return request.delete(`/performances/${id}`)
}

// 获取业绩统计
export function getPerformanceStats(): Promise<{
  total_count: number
  total_amount: number
  by_type: Array<{ type: string; count: number; amount: number }>
}> {
  return request.get('/performances/stats/summary')
}

// endregion
// ============================================


// ============================================
// region 企业 API
// ============================================

export interface Enterprise {
  credit_code: string
  company_name: string
  business_scope?: string
  is_state_owned: boolean
  industry?: string
  enterprise_type?: string
  auto_filled: boolean
  data_source?: string
}

// 获取企业列表
export function getEnterprises(skip = 0, limit = 20): Promise<Enterprise[]> {
  return request.get('/enterprises/', { params: { skip, limit } })
}

// 搜索企业
export function searchEnterprises(params: {
  name_keyword?: string
  industry?: string
  is_state_owned?: boolean
}): Promise<Enterprise[]> {
  return request.get('/enterprises/search', { params })
}

// 获取企业详情
export function getEnterpriseByCode(creditCode: string): Promise<Enterprise> {
  return request.get(`/enterprises/by-code/${creditCode}`)
}

// 创建企业
export function createEnterprise(data: Enterprise): Promise<Enterprise> {
  return request.post('/enterprises/', data)
}

// 更新企业
export function updateEnterprise(creditCode: string, data: Partial<Enterprise>): Promise<Enterprise> {
  return request.put(`/enterprises/${creditCode}`, data)
}

// 删除企业
export function deleteEnterprise(creditCode: string): Promise<{ message: string }> {
  return request.delete(`/enterprises/${creditCode}`)
}

// endregion
// ============================================


// ============================================
// region 律师 API
// ============================================

export interface Lawyer {
  id: number
  name: string
  id_card?: string
  license_no?: string
  resume?: string
  id_card_image?: string
  degree_image?: string
  diploma_image?: string
  license_image?: string
}

// 获取律师列表
export function getLawyers(): Promise<Lawyer[]> {
  return request.get('/lawyers/')
}

// 搜索律师
export function searchLawyers(params: { name?: string; license_no?: string }): Promise<Lawyer[]> {
  return request.get('/lawyers/search', { params })
}

// 获取律师详情
export function getLawyer(id: number): Promise<Lawyer> {
  return request.get(`/lawyers/${id}`)
}

// 创建律师
export function createLawyer(data: Partial<Lawyer>): Promise<Lawyer> {
  return request.post('/lawyers/', data)
}

// 更新律师
export function updateLawyer(id: number, data: Partial<Lawyer>): Promise<Lawyer> {
  return request.put(`/lawyers/${id}`, data)
}

// 删除律师
export function deleteLawyer(id: number): Promise<{ message: string }> {
  return request.delete(`/lawyers/${id}`)
}

// endregion
// ============================================


// ============================================
// region 上传 API
// ============================================

export interface UploadResponse {
  success: boolean
  message: string
  file_name: string
  page_count: number
  ocr_text_length: number
  extracted_info?: {
    contract_name?: string
    party_a?: string
    party_a_credit_code?: string
    contract_type?: string
    amount?: number
    sign_date?: string
    project_detail?: string
    summary?: string
  }
  performance_id?: number
}

// 上传合同并解析
export function uploadContract(
  file: File,
  useVision = false,
  saveToDb = true
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('use_vision', String(useVision))
  formData.append('save_to_db', String(saveToDb))

  return request.post('/upload/contract', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 仅 OCR 识别
export function uploadOCR(file: File, filterWatermark = true): Promise<{
  page_count: number
  full_text: string
}> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('filter_watermark', String(filterWatermark))

  return request.post('/upload/ocr', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// endregion
// ============================================


// ============================================
// region 语义搜索 API
// ============================================

export interface SemanticSearchResult {
  id: number
  file_name: string
  party_a?: string
  contract_type?: string
  amount?: number
  sign_date?: string
  project_detail?: string
  summary?: string
  score: number
}

// 语义搜索业绩
export function semanticSearchPerformances(
  query: string,
  topK = 10,
  mode: 'vector' | 'keyword' | 'hybrid' = 'hybrid'
): Promise<{
  success: boolean
  query: string
  mode: string
  total: number
  results: SemanticSearchResult[]
}> {
  return request.post('/search/semantic/performances', { query, top_k: topK, mode })
}

// endregion
// ============================================


export default request