<template>
  <div class="poc-builder">
    <!-- 协议选择 -->
    <div class="builder-section">
      <div class="section-label">协议</div>
      <div class="protocol-grid">
        <button
          v-for="p in PROTOCOL_OPTIONS"
          :key="p.value"
          class="protocol-card"
          :class="{ active: state.protocol === p.value }"
          @click="state.protocol = p.value"
        >
          <span class="protocol-name">{{ p.label }}</span>
          <span class="protocol-desc">{{ p.desc }}</span>
        </button>
      </div>
    </div>

    <!-- HTTP -->
    <div v-if="state.protocol === 'http'" class="builder-section">
      <div class="section-label">HTTP 请求</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item label="请求模式">
          <el-radio-group v-model="state.http.mode" size="small">
            <el-radio-button value="path">结构化（method/path）</el-radio-button>
            <el-radio-button value="raw">原始报文（raw）</el-radio-button>
          </el-radio-group>
          <span class="form-tip">raw 模式可精确控制请求头顺序，支持多请求链</span>
        </el-form-item>

        <template v-if="state.http.mode === 'path'">
          <el-form-item label="请求方法">
            <el-select v-model="state.http.method" filterable allow-create class="w-full">
              <el-option v-for="m in HTTP_METHODS" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="请求路径（每行一个）">
            <div class="multi-list">
              <div v-for="(_, i) in state.http.paths" :key="i" class="multi-row">
                <el-input v-model="state.http.paths[i]" placeholder="{{BaseURL}}/path" size="small" />
                <el-button text type="danger" :icon="Delete" @click="removeItem(state.http.paths, i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="state.http.paths.push('')">添加路径</el-button>
            </div>
          </el-form-item>
          <el-form-item label="请求头">
            <div class="multi-list">
              <div v-for="(kv, i) in state.http.headers" :key="i" class="multi-row">
                <el-input v-model="kv.key" placeholder="Header 名" size="small" class="kv-key" />
                <el-input v-model="kv.value" placeholder="Header 值" size="small" class="kv-val" />
                <el-button text type="danger" :icon="Delete" @click="removeItem(state.http.headers, i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="state.http.headers.push({ key: '', value: '' })">添加请求头</el-button>
            </div>
          </el-form-item>
          <el-form-item label="请求体">
            <el-input
              v-model="state.http.body"
              type="textarea"
              :rows="3"
              placeholder="POST/PUT 请求体，可留空"
            />
          </el-form-item>
          <div class="form-row">
            <el-form-item label="跟随重定向">
              <el-switch v-model="state.http.redirects" />
            </el-form-item>
            <el-form-item v-if="state.http.redirects" label="最大重定向次数">
              <el-input-number v-model="state.http.maxRedirects" :min="0" :max="20" controls-position="right" />
            </el-form-item>
          </div>
        </template>

        <template v-else>
          <el-form-item label="原始报文（每块一条请求，支持多请求链）">
            <div class="multi-list">
              <div v-for="(_, i) in state.http.raw" :key="i" class="multi-row">
                <el-input
                  v-model="state.http.raw[i]"
                  type="textarea"
                  :rows="6"
                  size="small"
                  class="raw-textarea"
                  placeholder="POST /{{path}} HTTP/1.1&#10;Host: {{Hostname}}&#10;Content-Type: application/x-www-form-urlencoded&#10;&#10;username={{randstr_8}}&password={{randstr_8}}"
                />
                <el-button text type="danger" :icon="Delete" size="small" @click="removeItem(state.http.raw, i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="state.http.raw.push('')">添加请求（链式）</el-button>
            </div>
          </el-form-item>
          <div class="form-row">
            <el-form-item label="不自动处理">
              <el-switch v-model="state.http.unsafe" />
              <span class="form-tip">unsafe: true，保留原始报文</span>
            </el-form-item>
            <el-form-item label="Cookie 复用">
              <el-switch v-model="state.http.cookieReuse" />
            </el-form-item>
          </div>
        </template>

        <el-form-item label="请求链响应引用">
          <el-switch v-model="state.http.reqCondition" />
          <span class="form-tip">req-condition: true，DSL 中可用 body_1 / status_code_2 引用各请求响应</span>
        </el-form-item>

        <el-form-item label="模糊测试（attack）">
          <el-select v-model="state.http.attack" class="w-full">
            <el-option label="禁用" value="none" />
            <el-option label="batteringram（各 payload 组逐一组合）" value="batteringram" />
            <el-option label="pitchfork（按索引并行组合）" value="pitchfork" />
            <el-option label="clusterbomb（笛卡尔积）" value="clusterbomb" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="state.http.attack !== 'none'" label="Payload 组">
          <div class="multi-list">
            <div v-for="(pg, i) in state.http.payloads" :key="i" class="payload-group">
              <el-input v-model="pg.name" placeholder="Payload 名，如 injection" size="small" class="pg-name" />
              <el-input
                :model-value="pg.values.join('\n')"
                @update:model-value="(v: string) => (pg.values = v.split('\n'))"
                type="textarea"
                :rows="2"
                size="small"
                class="pg-values"
                placeholder="每行一个 payload"
              />
              <el-button text type="danger" :icon="Delete" size="small" @click="removePayloadGroup(i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="addPayloadGroup">添加 Payload 组</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- TCP -->
    <div v-else-if="state.protocol === 'tcp'" class="builder-section">
      <div class="section-label">TCP 请求</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item label="主机/输入（每行一个）">
          <div class="multi-list">
            <div v-for="(_, i) in state.tcp.inputs" :key="i" class="multi-row">
              <el-input v-model="state.tcp.inputs[i]" placeholder="{{Hostname}}" size="small" />
              <el-button text type="danger" :icon="Delete" @click="removeItem(state.tcp.inputs, i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="state.tcp.inputs.push('')">添加</el-button>
          </div>
        </el-form-item>
        <el-form-item label="端口">
          <el-input v-model="state.tcp.port" placeholder="如 6379" />
        </el-form-item>
        <el-form-item label="发送数据">
          <el-input v-model="state.tcp.data" type="textarea" :rows="3" placeholder="发送的原始数据/命令" />
        </el-form-item>
        <el-form-item label="读取字节数">
          <el-input-number v-model="state.tcp.readBytes" :min="0" :step="16" controls-position="right" />
        </el-form-item>
      </el-form>
    </div>

    <!-- Network -->
    <div v-else-if="state.protocol === 'network'" class="builder-section">
      <div class="section-label">Network 请求</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item label="主机（host，每行一个）">
          <div class="multi-list">
            <div v-for="(_, i) in state.network.host" :key="i" class="multi-row">
              <el-input v-model="state.network.host[i]" placeholder="{{Hostname}}" size="small" />
              <el-button text type="danger" :icon="Delete" @click="removeItem(state.network.host, i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="state.network.host.push('')">添加</el-button>
          </div>
        </el-form-item>
        <el-form-item label="端口">
          <el-input v-model="state.network.port" placeholder="如 443" />
        </el-form-item>
        <el-form-item label="多阶段交互">
          <el-switch v-model="useStages" />
          <span class="form-tip">开启后按 inputs[] 序列发送数据并逐段读取</span>
        </el-form-item>
        <template v-if="useStages">
          <el-form-item label="交互阶段（data + read）">
            <div class="multi-list">
              <div v-for="(st, i) in state.network.stages" :key="i" class="stage-row">
                <el-input
                  :model-value="st.data"
                  @update:model-value="(v: string) => updateStage(i, 'data', v)"
                  placeholder="发送数据（支持 {{hex_decode('...')}}）"
                  size="small"
                  class="stage-data"
                />
                <el-input-number
                  :model-value="st.read"
                  @update:model-value="(v: number | undefined) => updateStage(i, 'read', v ?? 0)"
                  :min="0"
                  :step="16"
                  size="small"
                  controls-position="right"
                  class="stage-read"
                />
                <el-button text type="danger" :icon="Delete" size="small" @click="removeStage(i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="addStage">添加阶段</el-button>
            </div>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="发送数据">
            <el-input v-model="state.network.data" type="textarea" :rows="3" placeholder="发送的原始数据（支持 Hex 编码）" />
          </el-form-item>
          <el-form-item label="读取字节数">
            <el-input-number v-model="state.network.readBytes" :min="0" :step="16" controls-position="right" />
          </el-form-item>
        </template>
        <div class="form-row">
          <el-form-item label="TLS 加密">
            <el-switch v-model="state.network.tls" />
          </el-form-item>
          <el-form-item v-if="state.network.tls" label="TLS SNI">
            <el-input v-model="state.network.tlsSni" placeholder="服务器名称指示，如 example.com" />
          </el-form-item>
        </div>
      </el-form>
    </div>

    <!-- WebSocket -->
    <div v-else-if="state.protocol === 'websocket'" class="builder-section">
      <div class="section-label">WebSocket 请求</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item label="地址（address）">
          <el-input v-model="state.websocket.address" placeholder="ws://{{Hostname}}:{{Port}}/ws" />
        </el-form-item>
        <el-form-item label="消息体（input.data）">
          <el-input v-model="state.websocket.inputData" type="textarea" :rows="3" placeholder="发送的消息内容" />
        </el-form-item>
        <el-form-item label="读取字节数（read-size）">
          <el-input-number v-model="state.websocket.readSize" :min="0" :step="1024" controls-position="right" />
          <span class="form-tip">单次读取响应字节数上限</span>
        </el-form-item>
      </el-form>
    </div>

    <!-- DNS -->
    <div v-else class="builder-section">
      <div class="section-label">DNS 请求</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item label="域名（每行一个）">
          <div class="multi-list">
            <div v-for="(_, i) in state.dns.domains" :key="i" class="multi-row">
              <el-input v-model="state.dns.domains[i]" placeholder="{{Hostname}}" size="small" />
              <el-button text type="danger" :icon="Delete" @click="removeItem(state.dns.domains, i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="state.dns.domains.push('')">添加</el-button>
          </div>
        </el-form-item>
        <el-form-item label="记录类型">
          <el-select v-model="state.dns.queryType" class="w-full">
            <el-option v-for="t in DNS_QUERY_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="DNS 类别">
          <el-input v-model="state.dns.kclass" placeholder="inet" />
        </el-form-item>
        <el-form-item label="递归查询">
          <el-switch v-model="state.dns.recursion" />
        </el-form-item>
      </el-form>
    </div>

    <!-- 匹配器 -->
    <div class="builder-section">
      <div class="section-label">
        匹配器
        <el-button text type="primary" :icon="Plus" size="small" @click="addMatcher">添加</el-button>
      </div>
      <div v-if="state.matchers.length > 1" class="matcher-condition-row">
        <span class="matcher-condition-label">多条匹配规则逻辑（matchers-condition）</span>
        <el-radio-group v-model="state.matchersCondition" size="small">
          <el-radio-button value="and">全部满足（and）</el-radio-button>
          <el-radio-button value="or">任一满足（or）</el-radio-button>
        </el-radio-group>
      </div>
      <div v-for="(m, i) in state.matchers" :key="m.id" class="matcher-card">
        <div class="matcher-head">
          <span class="matcher-title">匹配规则 {{ i + 1 }}</span>
          <el-button text type="danger" :icon="Delete" @click="removeItem(state.matchers, i)" />
        </div>
        <el-form label-position="top" class="builder-form">
          <div class="matcher-row">
            <el-form-item label="类型">
              <el-select v-model="m.type" size="small">
                <el-option v-for="t in MATCHER_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="m.type !== 'status' && m.type !== 'size' && m.type !== 'condition'" label="匹配部位">
              <el-select v-model="m.part" size="small" clearable>
                <el-option v-for="p in getMatcherPartsForProtocol(state.protocol)" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="m.type === 'word' || m.type === 'regex' || m.type === 'dsl'" label="条件">
              <el-radio-group v-model="m.condition" size="small">
                <el-radio-button value="or">或</el-radio-button>
                <el-radio-button value="and">且</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="取反">
              <el-switch v-model="m.negative" size="small" />
            </el-form-item>
          </div>

          <el-form-item v-if="m.type === 'word'" label="关键词（每行一个）">
            <el-input
              :model-value="m.words.join('\n')"
              @update:model-value="(v: string) => (m.words = v.split('\n'))"
              type="textarea"
              :rows="3"
              placeholder="逐行填写关键词"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'regex'" label="正则表达式（每行一个，输出为 regex 键）">
            <el-input
              :model-value="m.words.join('\n')"
              @update:model-value="(v: string) => (m.words = v.split('\n'))"
              type="textarea"
              :rows="3"
              placeholder="如 (uid|gid)=[0-9]+"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'dsl'" label="DSL 表达式（每行一个）">
            <el-input
              :model-value="m.words.join('\n')"
              @update:model-value="(v: string) => (m.words = v.split('\n'))"
              type="textarea"
              :rows="3"
              placeholder="如 status_code == 200 && contains(body, 'ok')"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'status'" label="状态码（逗号分隔）">
            <el-input
              :model-value="m.status.join(',')"
              @update:model-value="(v: string) => (m.status = v.split(',').map((x) => parseInt(x.trim(), 10)).filter((n) => !Number.isNaN(n)))"
              placeholder="如 200, 301, 403"
            />
          </el-form-item>
          <div v-else-if="m.type === 'size'" class="size-row">
            <el-form-item label="响应体小于（lt）">
              <el-input-number v-model="m.lt" :min="0" size="small" controls-position="right" placeholder="可选" />
            </el-form-item>
            <el-form-item label="响应体大于（gt）">
              <el-input-number v-model="m.gt" :min="0" size="small" controls-position="right" placeholder="可选" />
            </el-form-item>
          </div>
          <el-form-item v-else-if="m.type === 'binary'" label="二进制数据（十六进制，每行一个）">
            <el-input
              :model-value="m.binary.join('\n')"
              @update:model-value="(v: string) => (m.binary = v.split('\n'))"
              type="textarea"
              :rows="3"
              placeholder="如 504b0304（ZIP 文件头）"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'condition'" label="条件表达式（condition 匹配器）">
            <el-input
              v-model="m.conditionExpression"
              type="textarea"
              :rows="3"
              placeholder="如 contains(body, '{{token}}') && status_code == 200"
            />
          </el-form-item>
        </el-form>
      </div>
      <div v-if="!state.matchers.length" class="empty-matchers">暂无匹配规则，点击「添加」</div>
    </div>

    <!-- 提取器 -->
    <div class="builder-section">
      <div class="section-label">
        提取器
        <el-button text type="primary" :icon="Plus" size="small" @click="addExtractor">添加</el-button>
      </div>
      <div v-for="(e, i) in state.extractors" :key="e.id" class="matcher-card">
        <div class="matcher-head">
          <span class="matcher-title">提取器 {{ i + 1 }}</span>
          <el-button text type="danger" :icon="Delete" @click="removeItem(state.extractors, i)" />
        </div>
        <el-form label-position="top" class="builder-form">
          <div class="matcher-row">
            <el-form-item label="类型">
              <el-select v-model="e.type" size="small">
                <el-option v-for="t in EXTRACTOR_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item label="名称">
              <el-input v-model="e.name" size="small" placeholder="如 b64 / version" />
            </el-form-item>
            <el-form-item label="匹配部位">
              <el-select v-model="e.part" size="small" clearable>
                <el-option v-for="p in EXTRACTOR_PARTS" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="e.type === 'regex'" label="分组">
              <el-input-number v-model="e.group" :min="0" size="small" controls-position="right" />
            </el-form-item>
            <el-form-item v-if="e.type === 'xpath'" label="属性（attribute）">
              <el-input v-model="e.attribute" size="small" placeholder="如 href" />
            </el-form-item>
          </div>
          <el-form-item label="表达式（每行一个）">
            <el-input
              :model-value="e.expressions.join('\n')"
              @update:model-value="(v: string) => (e.expressions = v.split('\n'))"
              type="textarea"
              :rows="3"
              :placeholder="extractorPlaceholder(e)"
            />
          </el-form-item>
          <el-form-item label="仅内部使用">
            <el-switch v-model="e.internal" size="small" />
            <span class="form-tip">开启后结果不输出，仅供后续 DSL 引用</span>
          </el-form-item>
        </el-form>
      </div>
      <div v-if="!state.extractors.length" class="empty-matchers">暂无提取器，可留空</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import {
  PROTOCOL_OPTIONS, HTTP_METHODS, DNS_QUERY_TYPES, MATCHER_TYPES,
  getMatcherPartsForProtocol,
  EXTRACTOR_TYPES, EXTRACTOR_PARTS,
  genMatcherId, type BuilderState, type Matcher, type Extractor, type NetworkStage,
} from '@/utils/pocBuilder'

const props = defineProps<{ state: BuilderState }>()

// 多阶段模式开关：以 stages 数组是否非空为真实来源，避免与持久化的旧状态脱节
const useStages = computed({
  get: () => props.state.network.stages.length > 0,
  set: (on: boolean) => {
    if (on) {
      if (props.state.network.stages.length === 0) {
        props.state.network.stages.push({ data: '', read: 0 })
      }
    } else {
      props.state.network.stages = []
    }
  },
})

function removeItem<T>(arr: T[], index: number) {
  arr.splice(index, 1)
}

function addStage() {
  props.state.network.stages.push({ data: '', read: 0 })
}

function removeStage(index: number) {
  props.state.network.stages.splice(index, 1)
}

function updateStage(index: number, field: keyof NetworkStage, value: string | number) {
  const st = props.state.network.stages[index]
  if (!st) return
  if (field === 'data') st.data = String(value)
  else st.read = Number(value) || 0
}

function extractorPlaceholder(e: Extractor): string {
  switch (e.type) {
    case 'json':
      return 'JSON 路径，如 .data.token'
    case 'kval':
      return '响应头字段，如 content_type'
    case 'xpath':
      return 'XPath 表达式，如 /html/body/div/a'
    case 'dsl':
      return 'DSL 表达式，如 base64_decode(body)'
    default:
      return '正则表达式，如 version: ([0-9.]+)'
  }
}

function addPayloadGroup() {
  props.state.http.payloads.push({ name: '', values: [''] })
}

function removePayloadGroup(index: number) {
  props.state.http.payloads.splice(index, 1)
}

function addMatcher() {
  const empty: Matcher = {
    id: genMatcherId(),
    type: 'word',
    part: 'body',
    words: [''],
    status: [],
    condition: 'or',
    negative: false,
    lt: null,
    gt: null,
    binary: [],
    conditionExpression: '',
  }
  props.state.matchers.push(empty)
}

function addExtractor() {
  const empty: Extractor = {
    id: genMatcherId(),
    type: 'regex',
    name: '',
    part: '',
    expressions: [''],
    group: 0,
    internal: false,
    attribute: '',
  }
  props.state.extractors.push(empty)
}
</script>


<style scoped lang="scss">
@use '@/styles/variables' as *;

.poc-builder {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  height: 100%;
  overflow-y: auto;
  padding: $spacing-lg;
}

.builder-section {
  background: $bg-tertiary;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-md $spacing-lg;
}

.section-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: $font-body;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: $spacing-md;

  .el-button {
    margin-left: auto;
  }
}

.protocol-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: $spacing-sm;
}

.protocol-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: all $transition-fast;

  &:hover {
    border-color: $accent;
  }

  &.active {
    border-color: $accent;
    background: rgba($accent, 0.08);
  }
}

.protocol-name {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
}

.protocol-desc {
  font-size: $font-caption;
  color: $text-disabled;
  line-height: 1.4;
}

.builder-form {
  :deep(.el-form-item) {
    margin-bottom: $spacing-md;
  }
  :deep(.el-form-item__label) {
    font-size: $font-caption;
    color: $text-secondary;
    padding-bottom: 4px;
  }
}

.multi-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.multi-row {
  display: flex;
  align-items: center;
  gap: 6px;

  .kv-key {
    width: 40%;
    flex-shrink: 0;
  }
}

.matcher-card {
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  padding: $spacing-sm $spacing-md;
  margin-bottom: $spacing-sm;
  background: $bg-secondary;
}

.matcher-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-sm;
}

.matcher-title {
  font-size: $font-body;
  font-weight: 500;
  color: $text-primary;
}

.matcher-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-sm;
  align-items: end;
}

.matcher-condition-row {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm $spacing-md;
  margin-bottom: $spacing-sm;
  background: rgba($accent, 0.05);
  border: 1px solid $border-color;
  border-radius: $radius-sm;
}

.matcher-condition-label {
  font-size: $font-caption;
  color: $text-secondary;
}

.stage-row {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;

  .stage-data {
    flex: 1;
  }

  .stage-read {
    width: 140px;
    flex-shrink: 0;
  }
}

.size-row {
  display: flex;
  gap: $spacing-md;
  align-items: flex-end;

  .el-form-item {
    flex: 1;
  }
}

.payload-group {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  width: 100%;

  .pg-name {
    width: 160px;
    flex-shrink: 0;
  }

  .pg-values {
    flex: 1;
  }
}

.raw-textarea {
  flex: 1;
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
}

.form-row {
  display: flex;
  gap: $spacing-md;

  .el-form-item {
    flex: 1;
  }
}

.form-tip {
  font-size: $font-caption;
  color: $text-disabled;
  margin-left: $spacing-sm;
  line-height: 1.4;
}

.empty-matchers {
  font-size: $font-caption;
  color: $text-disabled;
  padding: $spacing-sm 0;
}
</style>
