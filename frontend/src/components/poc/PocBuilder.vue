<template>
  <div class="poc-builder">
    <!-- 协议选择 -->
    <div class="builder-section">
      <div class="section-label">{{ $t('pocBuilder.section.protocol') }}</div>
      <div class="protocol-grid">
        <button
          v-for="p in PROTOCOL_OPTIONS"
          :key="p.value"
          class="protocol-card"
          :class="{ active: state.protocol === p.value }"
          @click="state.protocol = p.value"
        >
          <span class="protocol-name">{{ $t('pocBuilder.proto.' + p.value) }}</span>
          <span class="protocol-desc">{{ $t('pocBuilder.protoDesc.' + p.value) }}</span>
        </button>
      </div>
    </div>

    <!-- HTTP -->
    <div v-if="state.protocol === 'http'" class="builder-section">
      <div class="section-label">{{ $t('pocBuilder.section.http') }}</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item :label="$t('pocBuilder.http.mode.label')">
          <el-radio-group v-model="state.http.mode" size="small">
            <el-radio-button value="path">{{ $t('pocBuilder.http.mode.path') }}</el-radio-button>
            <el-radio-button value="raw">{{ $t('pocBuilder.http.mode.raw') }}</el-radio-button>
          </el-radio-group>
          <span class="form-tip">{{ $t('pocBuilder.http.mode.tip') }}</span>
        </el-form-item>

        <template v-if="state.http.mode === 'path'">
          <el-form-item :label="$t('pocBuilder.http.method')">
            <el-select v-model="state.http.method" filterable allow-create class="w-full">
              <el-option v-for="m in HTTP_METHODS" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('pocBuilder.http.paths')">
            <div class="multi-list">
              <div v-for="(_, i) in state.http.paths" :key="i" class="multi-row">
                <el-input v-model="state.http.paths[i]" :placeholder="$t('pocBuilder.http.pathsPlaceholder')" size="small" />
                <el-button text type="danger" :icon="Delete" @click="removeItem(state.http.paths, i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="state.http.paths.push('')">{{ $t('pocBuilder.add') }}</el-button>
            </div>
          </el-form-item>
          <el-form-item :label="$t('pocBuilder.http.headers')">
            <div class="multi-list">
              <div v-for="(kv, i) in state.http.headers" :key="i" class="multi-row">
                <el-input v-model="kv.key" :placeholder="$t('pocBuilder.http.headerKeyPlaceholder')" size="small" class="kv-key" />
                <el-input v-model="kv.value" :placeholder="$t('pocBuilder.http.headerValPlaceholder')" size="small" class="kv-val" />
                <el-button text type="danger" :icon="Delete" @click="removeItem(state.http.headers, i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="state.http.headers.push({ key: '', value: '' })">{{ $t('pocBuilder.http.addHeader') }}</el-button>
            </div>
          </el-form-item>
          <el-form-item :label="$t('pocBuilder.http.body')">
            <el-input
              v-model="state.http.body"
              type="textarea"
              :rows="3"
              :placeholder="$t('pocBuilder.http.bodyPlaceholder')"
            />
          </el-form-item>
          <div class="form-row">
            <el-form-item :label="$t('pocBuilder.http.redirects')">
              <el-switch v-model="state.http.redirects" />
            </el-form-item>
            <el-form-item v-if="state.http.redirects" :label="$t('pocBuilder.http.maxRedirects')">
              <el-input-number v-model="state.http.maxRedirects" :min="0" :max="20" controls-position="right" />
            </el-form-item>
          </div>
        </template>

        <template v-else>
          <el-form-item :label="$t('pocBuilder.http.raw')">
            <div class="multi-list">
              <div v-for="(_, i) in state.http.raw" :key="i" class="multi-row">
                <el-input
                  v-model="state.http.raw[i]"
                  type="textarea"
                  :rows="6"
                  size="small"
                  class="raw-textarea"
                  :placeholder="$t('pocBuilder.http.rawPlaceholder')"
                />
                <el-button text type="danger" :icon="Delete" size="small" @click="removeItem(state.http.raw, i)" />
              </div>
              <el-button text type="primary" :icon="Plus" size="small" @click="state.http.raw.push('')">{{ $t('pocBuilder.http.addRequest') }}</el-button>
            </div>
          </el-form-item>
          <div class="form-row">
            <el-form-item :label="$t('pocBuilder.http.unsafe')">
              <el-switch v-model="state.http.unsafe" />
              <span class="form-tip">{{ $t('pocBuilder.http.unsafeTip') }}</span>
            </el-form-item>
            <el-form-item :label="$t('pocBuilder.http.cookieReuse')">
              <el-switch v-model="state.http.cookieReuse" />
            </el-form-item>
          </div>
        </template>

        <el-form-item :label="$t('pocBuilder.http.reqCondition')">
          <el-switch v-model="state.http.reqCondition" />
          <span class="form-tip">{{ $t('pocBuilder.http.reqConditionTip') }}</span>
        </el-form-item>

        <el-form-item :label="$t('pocBuilder.http.attack')">
          <el-select v-model="state.http.attack" class="w-full">
            <el-option :label="$t('pocBuilder.http.attackOptions.none')" value="none" />
            <el-option :label="$t('pocBuilder.http.attackOptions.batteringram')" value="batteringram" />
            <el-option :label="$t('pocBuilder.http.attackOptions.pitchfork')" value="pitchfork" />
            <el-option :label="$t('pocBuilder.http.attackOptions.clusterbomb')" value="clusterbomb" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="state.http.attack !== 'none'" :label="$t('pocBuilder.http.payloads')">
          <div class="multi-list">
            <div v-for="(pg, i) in state.http.payloads" :key="i" class="payload-group">
              <el-input v-model="pg.name" :placeholder="$t('pocBuilder.http.payloadNamePlaceholder')" size="small" class="pg-name" />
              <el-input
                :model-value="pg.values.join('\n')"
                @update:model-value="(v: string) => (pg.values = v.split('\n'))"
                type="textarea"
                :rows="2"
                size="small"
                class="pg-values"
                :placeholder="$t('pocBuilder.http.payloadValuesPlaceholder')"
              />
              <el-button text type="danger" :icon="Delete" size="small" @click="removePayloadGroup(i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="addPayloadGroup">{{ $t('pocBuilder.http.addPayloadGroup') }}</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- TCP -->
    <div v-else-if="state.protocol === 'tcp'" class="builder-section">
      <div class="section-label">{{ $t('pocBuilder.section.tcp') }}</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item :label="$t('pocBuilder.tcp.inputs')">
          <div class="multi-list">
            <div v-for="(_, i) in state.tcp.inputs" :key="i" class="multi-row">
              <el-input v-model="state.tcp.inputs[i]" :placeholder="$t('pocBuilder.tcp.inputsPlaceholder')" size="small" />
              <el-button text type="danger" :icon="Delete" @click="removeItem(state.tcp.inputs, i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="state.tcp.inputs.push('')">{{ $t('pocBuilder.add') }}</el-button>
          </div>
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.tcp.port')">
          <el-input v-model="state.tcp.port" :placeholder="$t('pocBuilder.tcp.portPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.tcp.data')">
          <el-input v-model="state.tcp.data" type="textarea" :rows="3" :placeholder="$t('pocBuilder.tcp.dataPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.tcp.readBytes')">
          <el-input-number v-model="state.tcp.readBytes" :min="0" :step="16" controls-position="right" />
        </el-form-item>
      </el-form>
    </div>

    <!-- Network -->
    <div v-else-if="state.protocol === 'network'" class="builder-section">
      <div class="section-label">{{ $t('pocBuilder.section.network') }}</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item :label="$t('pocBuilder.network.host')">
          <div class="multi-list">
            <div v-for="(_, i) in state.network.host" :key="i" class="multi-row">
              <el-input v-model="state.network.host[i]" :placeholder="$t('pocBuilder.network.hostPlaceholder')" size="small" />
              <el-button text type="danger" :icon="Delete" @click="removeItem(state.network.host, i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="state.network.host.push('')">{{ $t('pocBuilder.add') }}</el-button>
          </div>
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.network.port')">
          <el-input v-model="state.network.port" :placeholder="$t('pocBuilder.network.portPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.network.stages')">
          <el-switch v-model="useStages" />
          <span class="form-tip">{{ $t('pocBuilder.network.stagesTip') }}</span>
        </el-form-item>
        <template v-if="useStages">
          <el-form-item :label="$t('pocBuilder.network.stageLabel')">
            <div class="multi-list">
              <div v-for="(st, i) in state.network.stages" :key="i" class="stage-row">
                <el-input
                  :model-value="st.data"
                  @update:model-value="(v: string) => updateStage(i, 'data', v)"
                  :placeholder="$t('pocBuilder.network.stageDataPlaceholder')"
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
              <el-button text type="primary" :icon="Plus" size="small" @click="addStage">{{ $t('pocBuilder.network.addStage') }}</el-button>
            </div>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item :label="$t('pocBuilder.network.data')">
            <el-input v-model="state.network.data" type="textarea" :rows="3" :placeholder="$t('pocBuilder.network.dataPlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('pocBuilder.network.readBytes')">
            <el-input-number v-model="state.network.readBytes" :min="0" :step="16" controls-position="right" />
          </el-form-item>
        </template>
        <div class="form-row">
          <el-form-item :label="$t('pocBuilder.network.tls')">
            <el-switch v-model="state.network.tls" />
          </el-form-item>
          <el-form-item v-if="state.network.tls" :label="$t('pocBuilder.network.tlsSni')">
            <el-input v-model="state.network.tlsSni" :placeholder="$t('pocBuilder.network.tlsSniPlaceholder')" />
          </el-form-item>
        </div>
      </el-form>
    </div>

    <!-- WebSocket -->
    <div v-else-if="state.protocol === 'websocket'" class="builder-section">
      <div class="section-label">{{ $t('pocBuilder.section.websocket') }}</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item :label="$t('pocBuilder.websocket.address')">
          <el-input v-model="state.websocket.address" :placeholder="$t('pocBuilder.websocket.addressPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.websocket.inputData')">
          <el-input v-model="state.websocket.inputData" type="textarea" :rows="3" :placeholder="$t('pocBuilder.websocket.inputDataPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.websocket.readSize')">
          <el-input-number v-model="state.websocket.readSize" :min="0" :step="1024" controls-position="right" />
          <span class="form-tip">{{ $t('pocBuilder.websocket.readSizeTip') }}</span>
        </el-form-item>
      </el-form>
    </div>

    <!-- DNS -->
    <div v-else class="builder-section">
      <div class="section-label">{{ $t('pocBuilder.section.dns') }}</div>
      <el-form label-position="top" class="builder-form">
        <el-form-item :label="$t('pocBuilder.dns.domains')">
          <div class="multi-list">
            <div v-for="(_, i) in state.dns.domains" :key="i" class="multi-row">
              <el-input v-model="state.dns.domains[i]" :placeholder="$t('pocBuilder.dns.domainsPlaceholder')" size="small" />
              <el-button text type="danger" :icon="Delete" @click="removeItem(state.dns.domains, i)" />
            </div>
            <el-button text type="primary" :icon="Plus" size="small" @click="state.dns.domains.push('')">{{ $t('pocBuilder.add') }}</el-button>
          </div>
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.dns.queryType')">
          <el-select v-model="state.dns.queryType" class="w-full">
            <el-option v-for="t in DNS_QUERY_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.dns.kclass')">
          <el-input v-model="state.dns.kclass" :placeholder="$t('pocBuilder.dns.kclassPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('pocBuilder.dns.recursion')">
          <el-switch v-model="state.dns.recursion" />
        </el-form-item>
      </el-form>
    </div>

    <!-- 匹配器 -->
    <div class="builder-section">
      <div class="section-label">
        {{ $t('pocBuilder.section.matchers') }}
        <el-button text type="primary" :icon="Plus" size="small" @click="addMatcher">{{ $t('pocBuilder.add') }}</el-button>
      </div>
      <div v-if="state.matchers.length > 1" class="matcher-condition-row">
        <span class="matcher-condition-label">{{ $t('pocBuilder.matchers.conditionLabel') }}</span>
        <el-radio-group v-model="state.matchersCondition" size="small">
          <el-radio-button value="and">{{ $t('pocBuilder.matchers.and') }}</el-radio-button>
          <el-radio-button value="or">{{ $t('pocBuilder.matchers.or') }}</el-radio-button>
        </el-radio-group>
      </div>
      <div v-for="(m, i) in state.matchers" :key="m.id" class="matcher-card">
        <div class="matcher-head">
          <span class="matcher-title">{{ $t('pocBuilder.matchers.title', { n: i + 1 }) }}</span>
          <el-button text type="danger" :icon="Delete" @click="removeItem(state.matchers, i)" />
        </div>
        <el-form label-position="top" class="builder-form">
          <div class="matcher-row">
            <el-form-item :label="$t('pocBuilder.matchers.type')">
              <el-select v-model="m.type" size="small">
                <el-option v-for="t in MATCHER_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="m.type !== 'status' && m.type !== 'size' && m.type !== 'condition'" :label="$t('pocBuilder.matchers.part')">
              <el-select v-model="m.part" size="small" clearable>
                <el-option v-for="p in getMatcherPartsForProtocol(state.protocol)" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="m.type === 'word' || m.type === 'regex' || m.type === 'dsl'" :label="$t('pocBuilder.matchers.condition')">
              <el-radio-group v-model="m.condition" size="small">
                <el-radio-button value="or">{{ $t('pocBuilder.matchers.conditionOr') }}</el-radio-button>
                <el-radio-button value="and">{{ $t('pocBuilder.matchers.conditionAnd') }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="$t('pocBuilder.matchers.negative')">
              <el-switch v-model="m.negative" size="small" />
            </el-form-item>
          </div>

          <el-form-item v-if="m.type === 'word'" :label="$t('pocBuilder.matchers.words')">
            <el-input
              :model-value="m.words.join('\n')"
              @update:model-value="(v: string) => (m.words = v.split('\n'))"
              type="textarea"
              :rows="3"
              :placeholder="$t('pocBuilder.matchers.wordsPlaceholder')"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'regex'" :label="$t('pocBuilder.matchers.regex')">
            <el-input
              :model-value="m.words.join('\n')"
              @update:model-value="(v: string) => (m.words = v.split('\n'))"
              type="textarea"
              :rows="3"
              :placeholder="$t('pocBuilder.matchers.regexPlaceholder')"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'dsl'" :label="$t('pocBuilder.matchers.dsl')">
            <el-input
              :model-value="m.words.join('\n')"
              @update:model-value="(v: string) => (m.words = v.split('\n'))"
              type="textarea"
              :rows="3"
              :placeholder="$t('pocBuilder.matchers.dslPlaceholder')"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'status'" :label="$t('pocBuilder.matchers.status')">
            <el-input
              :model-value="m.status.join(',')"
              @update:model-value="(v: string) => (m.status = v.split(',').map((x) => parseInt(x.trim(), 10)).filter((n) => !Number.isNaN(n)))"
              :placeholder="$t('pocBuilder.matchers.statusPlaceholder')"
            />
          </el-form-item>
          <div v-else-if="m.type === 'size'" class="size-row">
            <el-form-item :label="$t('pocBuilder.matchers.sizeLt')">
              <el-input-number v-model="m.lt" :min="0" size="small" controls-position="right" :placeholder="$t('pocBuilder.matchers.sizePlaceholder')" />
            </el-form-item>
            <el-form-item :label="$t('pocBuilder.matchers.sizeGt')">
              <el-input-number v-model="m.gt" :min="0" size="small" controls-position="right" :placeholder="$t('pocBuilder.matchers.sizePlaceholder')" />
            </el-form-item>
          </div>
          <el-form-item v-else-if="m.type === 'binary'" :label="$t('pocBuilder.matchers.binary')">
            <el-input
              :model-value="m.binary.join('\n')"
              @update:model-value="(v: string) => (m.binary = v.split('\n'))"
              type="textarea"
              :rows="3"
              :placeholder="$t('pocBuilder.matchers.binaryPlaceholder')"
            />
          </el-form-item>
          <el-form-item v-else-if="m.type === 'condition'" :label="$t('pocBuilder.matchers.conditionExpr')">
            <el-input
              v-model="m.conditionExpression"
              type="textarea"
              :rows="3"
              :placeholder="$t('pocBuilder.matchers.conditionExprPlaceholder')"
            />
          </el-form-item>
        </el-form>
      </div>
      <div v-if="!state.matchers.length" class="empty-matchers">{{ $t('pocBuilder.emptyMatchers') }}</div>
    </div>

    <!-- 提取器 -->
    <div class="builder-section">
      <div class="section-label">
        {{ $t('pocBuilder.section.extractors') }}
        <el-button text type="primary" :icon="Plus" size="small" @click="addExtractor">{{ $t('pocBuilder.add') }}</el-button>
      </div>
      <div v-for="(e, i) in state.extractors" :key="e.id" class="matcher-card">
        <div class="matcher-head">
          <span class="matcher-title">{{ $t('pocBuilder.extractors.title', { n: i + 1 }) }}</span>
          <el-button text type="danger" :icon="Delete" @click="removeItem(state.extractors, i)" />
        </div>
        <el-form label-position="top" class="builder-form">
          <div class="matcher-row">
            <el-form-item :label="$t('pocBuilder.extractors.type')">
              <el-select v-model="e.type" size="small">
                <el-option v-for="t in EXTRACTOR_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('pocBuilder.extractors.name')">
              <el-input v-model="e.name" size="small" :placeholder="$t('pocBuilder.extractors.namePlaceholder')" />
            </el-form-item>
            <el-form-item :label="$t('pocBuilder.extractors.part')">
              <el-select v-model="e.part" size="small" clearable>
                <el-option v-for="p in EXTRACTOR_PARTS" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="e.type === 'regex'" :label="$t('pocBuilder.extractors.group')">
              <el-input-number v-model="e.group" :min="0" size="small" controls-position="right" />
            </el-form-item>
            <el-form-item v-if="e.type === 'xpath'" :label="$t('pocBuilder.extractors.attribute')">
              <el-input v-model="e.attribute" size="small" :placeholder="$t('pocBuilder.extractors.attributePlaceholder')" />
            </el-form-item>
          </div>
          <el-form-item :label="$t('pocBuilder.extractors.expressions')">
            <el-input
              :model-value="e.expressions.join('\n')"
              @update:model-value="(v: string) => (e.expressions = v.split('\n'))"
              type="textarea"
              :rows="3"
              :placeholder="extractorPlaceholder(e)"
            />
          </el-form-item>
          <el-form-item :label="$t('pocBuilder.extractors.internal')">
            <el-switch v-model="e.internal" size="small" />
            <span class="form-tip">{{ $t('pocBuilder.extractors.internalTip') }}</span>
          </el-form-item>
        </el-form>
      </div>
      <div v-if="!state.extractors.length" class="empty-matchers">{{ $t('pocBuilder.emptyExtractors') }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Delete, Plus } from '@element-plus/icons-vue'
import {
  PROTOCOL_OPTIONS, HTTP_METHODS, DNS_QUERY_TYPES, MATCHER_TYPES,
  getMatcherPartsForProtocol,
  EXTRACTOR_TYPES, EXTRACTOR_PARTS,
  genMatcherId, type BuilderState, type Matcher, type Extractor, type NetworkStage,
} from '@/utils/pocBuilder'

const { t } = useI18n()

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
      return t('pocBuilder.extractors.placeholder.json')
    case 'kval':
      return t('pocBuilder.extractors.placeholder.kval')
    case 'xpath':
      return t('pocBuilder.extractors.placeholder.xpath')
    case 'dsl':
      return t('pocBuilder.extractors.placeholder.dsl')
    default:
      return t('pocBuilder.extractors.placeholder.default')
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
