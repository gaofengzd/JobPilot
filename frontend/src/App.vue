<script setup lang="ts">
import { computed, ref } from 'vue'

type Report = Record<string, any>

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const resumeText = ref('')
const resumeFile = ref<File | null>(null)
const jobText = ref('')
const needAdvice = ref(true)
const loading = ref(false)
const error = ref('')
const report = ref<Report | null>(null)

const selectedMatch = computed(() => {
  const matches = report.value?.match_results || []
  return matches.find((item: any) => item.job_index === report.value?.selected_job_index)
})

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  resumeFile.value = input.files?.[0] || null
}

async function readResume() {
  if (!resumeFile.value) return resumeText.value
  return await resumeFile.value.text()
}

async function analyze() {
  error.value = ''
  report.value = null
  const text = (await readResume()).trim()
  const job = jobText.value.trim()
  if (!text) {
    error.value = '请提供简历文本或上传文本层文件。'
    return
  }
  if (!job) {
    error.value = '请填写目标岗位 JD。'
    return
  }
  loading.value = true
  try {
    const response = await fetch(`${apiBaseUrl}/agent/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_text: text,
        raw_jobs: [job],
        selected_job_index: 0,
        need_advice: needAdvice.value,
      }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = data.detail
      error.value = typeof detail === 'object' ? `${detail.code || 'APIError'}: ${detail.message || '请求失败'}` : String(detail || `HTTP ${response.status}`)
      return
    }
    report.value = data
  } catch (cause) {
    error.value = `无法连接 API：${cause instanceof Error ? cause.message : String(cause)}`
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">JOBPILOT / V1.0</p>
        <h1>岗位分析工作台</h1>
        <p class="subtitle">用简历和岗位描述生成可追溯的匹配、差距与行动建议。</p>
      </div>
      <span class="api-status">API {{ apiBaseUrl }}</span>
    </header>

    <section class="workspace">
      <div class="panel input-panel">
        <div class="section-heading"><span>01</span><h2>候选人简历</h2></div>
        <textarea v-model="resumeText" placeholder="粘贴 Markdown/TXT 简历内容" rows="10" />
        <label class="file-input">或上传文本文件<input type="file" accept=".md,.txt,.pdf" @change="onFileChange" /></label>
        <p v-if="resumeFile" class="muted">已选择：{{ resumeFile.name }}</p>
      </div>

      <div class="panel input-panel jobs-panel">
        <div class="section-heading"><span>02</span><h2>目标岗位</h2></div>
        <p class="muted jobs-hint">填写一个岗位描述，一次分析一个岗位。</p>
        <textarea v-model="jobText" placeholder="粘贴岗位描述（JD）" rows="10" />
      </div>

      <div class="controls">
        <label class="checkbox"><input v-model="needAdvice" type="checkbox" />生成学习与简历建议</label>
        <button class="primary" :disabled="loading" @click="analyze">{{ loading ? '分析中…' : '开始分析' }}</button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <section v-if="report" class="panel report-panel">
        <div class="section-heading"><span>03</span><h2>分析报告</h2><strong>{{ report.status === 'success' ? '成功' : report.status === 'failed' ? '失败' : report.status }}</strong></div>
        <div v-if="selectedMatch" class="score-grid">
          <div><small>匹配分数</small><b>{{ selectedMatch.score ?? '-' }}</b></div>
          <div><small>已匹配必需技能</small><p>{{ (selectedMatch.matched_required_skills || []).join('、') || '无' }}</p></div>
          <div><small>缺失必需技能</small><p>{{ (selectedMatch.missing_required_skills || []).join('、') || '无' }}</p></div>
        </div>
        <div v-if="report.skill_gaps?.length" class="result-block">
          <h3>能力差距</h3>
          <ul class="item-list">
            <li v-for="(gap, gapIndex) in report.skill_gaps" :key="`gap-${gapIndex}`">
              <div class="item-head">
                <b>{{ gap.skill }}</b>
                <span class="tag">{{ gap.requirement_type === 'required' ? '必需' : '加分' }}</span>
              </div>
              <p class="item-text">{{ gap.reason }}</p>
              <p v-if="gap.jd_evidence?.length" class="item-source">
                JD 依据：{{ gap.jd_evidence[0].quote }}（{{ gap.jd_evidence[0].locator }}）
              </p>
            </li>
          </ul>
        </div>
        <div v-if="report.learning_plan?.tasks?.length" class="result-block">
          <h3>学习计划</h3>
          <ul class="item-list">
            <li v-for="(task, taskIndex) in report.learning_plan.tasks" :key="`task-${taskIndex}`">
              <div class="item-head"><b>{{ task.skill }}</b><span class="tag">{{ task.priority }}</span></div>
              <p class="item-text">{{ task.objective }}</p>
              <ol class="sub-list">
                <li v-for="(action, actionIndex) in task.actions || []" :key="actionIndex">{{ action }}</li>
              </ol>
              <p class="item-source">
                产出：{{ task.deliverable }}
                <template v-if="task.source_chunk_ids?.length">（来源：{{ task.source_chunk_ids.join('、') }}）</template>
              </p>
            </li>
          </ul>
        </div>
        <div v-if="report.resume_suggestions?.length" class="result-block">
          <h3>简历建议</h3>
          <ul class="item-list">
            <li v-for="(item, itemIndex) in report.resume_suggestions" :key="`suggestion-${itemIndex}`">
              <p class="item-text">原文：{{ item.original_text }}</p>
              <p class="item-text">建议：{{ item.suggested_text }}</p>
              <ul class="sub-list">
                <li v-for="(question, questionIndex) in item.questions_to_confirm || []" :key="questionIndex">
                  {{ question }}
                </li>
              </ul>
              <p v-if="item.candidate_evidence?.length" class="item-source">
                简历依据：{{ item.candidate_evidence[0].quote }}（{{ item.candidate_evidence[0].locator }}）
              </p>
            </li>
          </ul>
        </div>
        <p v-if="report.warnings?.length" class="warning">{{ report.warnings.join('；') }}</p>
        <p v-if="report.errors?.length" class="error">{{ report.errors.join('；') }}</p>
      </section>
    </section>
  </main>
</template>
