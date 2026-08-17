/** CVSS 向量解析：把 "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" 拆成可渲染的标签片段。 */

export interface CvssMetric {
  /** 原始键，如 "AV" */
  key: string
  /** 键的中文标签，如 "攻击向量" */
  label: string
  /** 原始值，如 "N" */
  value: string
  /** 值的中文标签，如 "网络" */
  valueLabel: string
}

export interface CvssVector {
  /** CVSS 版本，如 "3.1"；无法识别时为空 */
  version: string
  /** 分解后的指标片段 */
  metrics: CvssMetric[]
  /** 是否成功解析出至少一个指标 */
  valid: boolean
}

// 键 → 中文标签
const KEY_LABELS: Record<string, string> = {
  AV: '攻击向量',
  AC: '攻击复杂度',
  PR: '所需权限',
  UI: '用户交互',
  S: '影响范围',
  C: '机密性',
  I: '完整性',
  A: '可用性',
  E: '利用代码成熟度',
  RL: '修复级别',
  RC: '报告可信度',
}

// 按 key 分组的「值 → 中文标签」映射：同一字母在不同指标下含义不同
// （如 L 在 AV=本地、在 AC=低），故以 key 为前缀避免冲突。
const VALUE_LABELS: Record<string, Record<string, string>> = {
  AV: { N: '网络', A: '相邻', L: '本地', P: '物理' },
  AC: { L: '低', H: '高' },
  PR: { N: '无', L: '低', H: '高' },
  UI: { N: '无需', R: '需要' },
  S: { U: '不变', C: '改变' },
  C: { H: '高', L: '低', N: '无' },
  I: { H: '高', L: '低', N: '无' },
  A: { H: '高', L: '低', N: '无' },
  E: { U: '未定义', P: '概念验证', F: '功能级', H: '高级' },
  RL: { O: '官方修复', T: '临时修复', W: '变通方案', U: '不可用' },
  RC: { U: '未知', R: '合理', C: '已确认' },
}

/** 解析 CVSS 向量字符串。无法识别时返回 valid=false 的空结果（调用方可回退展示原文）。 */
export function parseCvssVector(raw: string | null | undefined): CvssVector {
  if (!raw || typeof raw !== 'string') {
    return { version: '', metrics: [], valid: false }
  }

  const text = raw.trim()
  // 形如 CVSS:3.1/AV:N/... 或直接 AV:N/...
  const versionMatch = text.match(/^CVSS:([\d.]+)\//i)
  const version = versionMatch ? versionMatch[1] : ''
  const body = versionMatch ? text.slice(versionMatch[0].length) : text

  const metrics: CvssMetric[] = []
  for (const seg of body.split('/')) {
    const part = seg.trim()
    if (!part || !part.includes(':')) continue
    const idx = part.indexOf(':')
    const key = part.slice(0, idx).toUpperCase()
    const value = part.slice(idx + 1).trim()
    if (!key || !value) continue
    metrics.push({
      key,
      label: KEY_LABELS[key] || key,
      value,
      valueLabel: VALUE_LABELS[key]?.[value] || value,
    })
  }

  return { version, metrics, valid: metrics.length > 0 }
}
