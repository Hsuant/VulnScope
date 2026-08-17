/**
 * CVE 导入模板集合。
 *
 * 各格式模板独立维护，新增格式只需追加条目并扩展 CVE_TEMPLATE_LIST。
 */

export interface CveTemplate {
  /** 格式标识 */
  key: 'json' | 'jsonl' | 'yaml' | 'markdown'
  /** 展示名称 */
  label: string
  /** 文件扩展名 */
  ext: string
  /** 模板原文 */
  content: string
}

const JSON_TEMPLATE = `[
  {
    "cve_id": "CVE-2021-44228",
    "vendor": "apache",
    "title": "Apache Log4j2 JNDI 注入远程代码执行",
    "description": "Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，可触发远程代码执行。",
    "cvss": 9.8,
    "severity": "critical",
    "cvss_metrics": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "product": [
      {
        "vendor": "apache",
        "product": "log4j",
        "version_start": "2.0",
        "version_start_type": "including",
        "version_end": "2.14.1",
        "version_end_type": "including"
      }
    ],
    "remediation": {
      "mitigation": "升级到 Apache Log4j 2.15.0 或更高版本。",
      "workaround": "设置环境变量 LOG4J_FORMAT_MSG_NO_LOOKUPS=true。"
    },
    "reference": [
      { "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228", "label": "NVD" }
    ]
  }
]
`

const JSONL_TEMPLATE = `{"cve_id":"CVE-2021-44228","vendor":"apache","title":"Apache Log4j2 JNDI RCE","cvss":9.8,"severity":"critical","cvss_metrics":"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}
{"cve_id":"CVE-2021-45046","vendor":"apache","cvss":9.0,"severity":"critical"}
{"cve_id":"CVE-2022-22222","vendor":"nginx","title":"示例漏洞","cvss":7.5,"severity":"high"}
`

const YAML_TEMPLATE = `- cve_id: CVE-2021-44228
  vendor: apache
  title: Apache Log4j2 JNDI 注入远程代码执行
  description: |
    Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，可触发远程代码执行。
  cvss: 9.8
  severity: critical
  cvss_metrics: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
  product:
    - vendor: apache
      product: log4j
      version_start: "2.0"
      version_start_type: including
      version_end: "2.14.1"
      version_end_type: including
  remediation:
    mitigation: 升级到 Apache Log4j 2.15.0 或更高版本。
    workaround: 设置环境变量 LOG4J_FORMAT_MSG_NO_LOOKUPS=true。
  reference:
    - url: https://nvd.nist.gov/vuln/detail/CVE-2021-44228
      label: NVD

- cve_id: CVE-2021-45046
  vendor: apache
  cvss: 9.0
  severity: critical
`

const MARKDOWN_TEMPLATE = `---
cve_id: CVE-2021-44228
vendor: apache
title: Apache Log4j2 JNDI 注入远程代码执行
cvss: 9.8
severity: critical
cvss_metrics: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
remediation:
  mitigation: 升级到 Apache Log4j 2.15.0 或更高版本。
  workaround: 设置 LOG4J_FORMAT_MSG_NO_LOOKUPS=true。
reference:
  - url: https://nvd.nist.gov/vuln/detail/CVE-2021-44228
    label: NVD
---

# 漏洞概述

Apache Log4j2 的 JNDI 特性未限制 LDAP/RMI 查找，可触发远程代码执行。
正文内容将作为描述（front-matter 未填 description 时）。
`

/** 全部导入模板，按格式顺序展示。 */
export const CVE_TEMPLATE_LIST: CveTemplate[] = [
  { key: 'json', label: 'JSON', ext: '.json', content: JSON_TEMPLATE },
  { key: 'jsonl', label: 'JSONL', ext: '.jsonl', content: JSONL_TEMPLATE },
  { key: 'yaml', label: 'YAML', ext: '.yaml / .yml', content: YAML_TEMPLATE },
  { key: 'markdown', label: 'Markdown', ext: '.md', content: MARKDOWN_TEMPLATE },
]
