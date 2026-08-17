"""Nuclei 解析器单元测试。"""

from __future__ import annotations

from app.plugins.parser.nuclei_parser import NucleiParser

SAMPLE_TEMPLATE = """id: CVE-2017-5638

info:
  name: Apache Struts2 S2-045 RCE
  author: pdteam
  severity: critical
  description: "Apache Struts2 Remote Code Execution via Content-Type header"
  remediation: "Upgrade to Struts 2.3.32 or 2.5.10.1"
  tags: rce,struts,oob
  reference:
    - "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-5638"
    - "https://struts.apache.org/docs/s2-045.html"
  classification:
    cve-id:
      - CVE-2017-5638
    cwe-id:
      - CWE-917
    cvss-metrics: "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    cvss-score: 10.0
  metadata:
    product: struts2
    vendor: apache

http:
  - method: GET
    path:
      - "{{BaseURL}}/struts2-showcase/"
    matchers:
      - type: word
        words:
          - "Struts2"
"""


class TestNucleiParser:
    """Nuclei 解析器测试。"""

    def setup_method(self) -> None:
        self.parser = NucleiParser()

    def test_parse_success(self) -> None:
        """解析标准模板成功。"""
        results = self.parser.parse(SAMPLE_TEMPLATE)
        assert len(results) == 1
        poc = results[0]
        assert poc.name == "cve-2017-5638"
        assert poc.title == "Apache Struts2 S2-045 RCE"
        assert poc.severity == "critical"
        assert poc.author == "pdteam"
        assert "CVE-2017-5638" in poc.cve_ids
        assert "rce" in poc.tags
        assert "struts" in poc.tags
        assert len(poc.references) == 2
        assert poc.extra_meta is not None
        assert poc.extra_meta.get("metadata", {}).get("product") == "struts2"

    def test_parse_invalid_id(self) -> None:
        """非法 id 应跳过。"""
        bad_template = "invalid: {}\n\ninfo:\n  name: test\n"
        results = self.parser.parse(bad_template)
        assert len(results) == 0

    def test_cve_extracted_from_top_level_id(self) -> None:
        """顶层 id 本身即 CVE 编号时，即使无 classification.cve-id 也应提取。"""
        template = """id: CVE-2021-44228

info:
  name: Apache Log4j2 JNDI RCE
  severity: critical

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""
        poc = self.parser.parse(template)[0]
        assert poc.cve_ids == ["CVE-2021-44228"]

    def test_cve_deduped_across_id_and_classification(self) -> None:
        """顶层 id 与 classification.cve-id 指向同一 CVE 时去重。"""
        template = """id: CVE-2021-44228

info:
  name: Apache Log4j2 JNDI RCE
  severity: critical
  classification:
    cve-id:
      - CVE-2021-44228

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""
        poc = self.parser.parse(template)[0]
        assert poc.cve_ids == ["CVE-2021-44228"]

    def test_cve_from_both_sources_distinct(self) -> None:
        """顶层 id 与 classification.cve-id 给出不同 CVE 时应全部保留。"""
        template = """id: CVE-2021-44228

info:
  name: Multi CVE
  severity: high
  classification:
    cve-id:
      - CVE-2021-45046

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"
"""
        poc = self.parser.parse(template)[0]
        assert poc.cve_ids == ["CVE-2021-44228", "CVE-2021-45046"]

    def test_parse_empty(self) -> None:
        """空内容返回空列表。"""
        results = self.parser.parse("")
        assert len(results) == 0

    def test_parse_missing_info(self) -> None:
        """缺少 info 块的模板应跳过。"""
        bad_template = "id: test\n"
        results = self.parser.parse(bad_template)
        assert len(results) == 0

    def test_validate_valid_template(self) -> None:
        """合法模板校验通过。"""
        results = self.parser.parse(SAMPLE_TEMPLATE)
        assert len(results) == 1
        errors = self.parser.validate(results[0])
        assert len(errors) == 0

    def test_validate_missing_http_block(self) -> None:
        """缺少请求块的模板应报错。"""
        from app.plugins.base import NormalizedPoc

        poc = NormalizedPoc(
            name="test-no-http",
            content="id: test-no-http\n\ninfo:\n  name: Test\n  severity: info\n",
            format="nuclei",
        )
        errors = self.parser.validate(poc)
        # 应该报错缺少请求块
        assert any("请求块" in e for e in errors)

    def test_parse_with_forbidden_block(self) -> None:
        """包含 headless 块的模板标记为 v1 禁止。"""
        template_with_headless = """id: test-headless

info:
  name: Test Headless
  severity: info

http:
  - method: GET
    path:
      - "{{BaseURL}}/test"

headless:
  - steps:
      - action: navigate
        args:
          url: "{{BaseURL}}"
"""
        results = self.parser.parse(template_with_headless)
        assert len(results) == 1
        assert results[0].extra_meta.get("v1_blocked") is True


class TestJsonParser:
    """JSON 解析器测试。"""

    def test_parse_success(self) -> None:
        from app.plugins.parser.json_parser import JsonParser

        parser = JsonParser()

        json_data = """{
            "name": "test-json",
            "title": "Test JSON POC",
            "severity": "high",
            "author": "tester",
            "description": "A test",
            "content": "id: test-json\\n\\ninfo:\\n  name: Test\\n  severity: high\\n",
            "cve_ids": ["CVE-2024-0001"],
            "tags": ["rce", "oob"]
        }"""
        results = parser.parse(json_data)
        assert len(results) == 1
        poc = results[0]
        assert poc.name == "test-json"
        assert poc.severity == "high"
        assert "CVE-2024-0001" in poc.cve_ids

    def test_parse_array(self) -> None:
        from app.plugins.parser.json_parser import JsonParser

        parser = JsonParser()

        json_data = """[
            {"name": "poc-1", "severity": "high", "content": "id: poc-1"},
            {"name": "poc-2", "severity": "critical", "content": "id: poc-2"}
        ]"""
        results = parser.parse(json_data)
        assert len(results) == 2

    def test_parse_missing_name(self) -> None:
        from app.plugins.parser.json_parser import JsonParser

        parser = JsonParser()

        import pytest

        with pytest.raises(ValueError, match="缺少 name"):
            parser.parse('{"severity": "high"}')


class TestPluginRegistry:
    """插件注册表测试。"""

    def test_register_and_get(self) -> None:
        from app.plugins.parser.nuclei_parser import NucleiParser
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        parser = NucleiParser()
        reg.register("parser", "nuclei", "1.0.0", parser)

        entry = reg.get("parser", "nuclei")
        assert entry is not None
        assert entry.name == "nuclei"
        assert entry.slot == "parser"
        assert entry.enabled is True

    def test_list_all(self) -> None:
        from app.plugins.parser.nuclei_parser import NucleiParser
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        reg.register("parser", "nuclei", "1.0.0", NucleiParser())
        reg.register("source", "manual", "1.0.0", object())

        entries = reg.list()
        assert len(entries) == 2

    def test_list_by_slot(self) -> None:
        from app.plugins.parser.nuclei_parser import NucleiParser
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        reg.register("parser", "nuclei", "1.0.0", NucleiParser())

        entries = reg.list("parser")
        assert len(entries) == 1
        assert entries[0].slot == "parser"

    def test_set_enabled(self) -> None:
        from app.plugins.parser.nuclei_parser import NucleiParser
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        reg.register("parser", "nuclei", "1.0.0", NucleiParser())
        assert reg.set_enabled("parser", "nuclei", False) is True
        assert reg.get("parser", "nuclei").enabled is False

    def test_get_nonexistent(self) -> None:
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        assert reg.get("parser", "nonexistent") is None
