"""版本匹配引擎单元测试（开发方案 §5.9）。"""

from __future__ import annotations

import pytest

from app.core.versioning import Version, VersionRange, normalize_version


class TestNormalizeVersion:
    """版本号归一化（§5.9）。"""

    def test_standard(self) -> None:
        assert normalize_version("2.3.15") == (2, 3, 15, 0)

    def test_short_padded(self) -> None:
        assert normalize_version("5.1") == (5, 1, 0, 0)

    def test_long_truncated(self) -> None:
        assert normalize_version("1.2.3.4.5") == (1, 2, 3, 4)

    def test_non_numeric(self) -> None:
        with pytest.raises(ValueError):
            normalize_version("2.beta.1")


class TestVersion:
    """Version 对象比较。"""

    def test_parse_standard(self) -> None:
        v = Version("2.3.15")
        assert v.raw == "2.3.15"
        assert v._key == ((0, 2), (0, 3), (0, 15), (0, 0))

    def test_less_than(self) -> None:
        assert Version("2.3.14") < Version("2.3.15")
        assert Version("2.3") < Version("2.3.1")
        assert Version("1.9") < Version("2.0")

    def test_equal(self) -> None:
        assert Version("2.3.15") == Version("2.3.15")
        assert Version("2.3") == Version("2.3.0")

    def test_greater_than(self) -> None:
        assert Version("2.3.16") > Version("2.3.15")
        assert Version("2.3.15.1") > Version("2.3.15")

    def test_hashable(self) -> None:
        assert hash(Version("1.2")) == hash(Version("1.2.0"))

    def test_from_normalized(self) -> None:
        v = Version.from_normalized((2, 3, 15, 0))
        assert v.raw == "2.3.15.0"
        assert Version("2.3.15") == v


class TestVersionRange:
    """版本区间匹配。"""

    # ── 标准区间 ──

    def test_exact_version(self) -> None:
        r = VersionRange("2.3.0", None, "2.3.5", None)
        assert r.matches(Version("2.3.3"))

    def test_below_range(self) -> None:
        r = VersionRange("2.3.0", ">=", "2.3.5", "<=")
        assert not r.matches(Version("2.2.9"))

    def test_above_range(self) -> None:
        r = VersionRange("2.3.0", ">=", "2.3.5", "<=")
        assert not r.matches(Version("2.3.6"))

    def test_lower_boundary(self) -> None:
        r = VersionRange("2.3.0", ">=", "2.3.5", "<=")
        assert r.matches(Version("2.3.0"))

    def test_upper_boundary(self) -> None:
        r = VersionRange("2.3.0", ">=", "2.3.5", "<=")
        assert r.matches(Version("2.3.5"))

    # ── 操作符别名 ──

    def test_operator_gte(self) -> None:
        r = VersionRange("2.3.0", ">=", None, None)
        assert r.matches(Version("2.3.0"))
        assert r.matches(Version("2.3.5"))
        assert not r.matches(Version("2.2.9"))

    def test_operator_gt(self) -> None:
        r = VersionRange("2.3.0", ">", None, None)
        assert not r.matches(Version("2.3.0"))
        assert r.matches(Version("2.3.1"))

    def test_operator_lte(self) -> None:
        r = VersionRange(None, None, "2.3.5", "<=")
        assert r.matches(Version("2.3.5"))
        assert r.matches(Version("2.3.0"))
        assert not r.matches(Version("2.3.6"))

    def test_operator_lt(self) -> None:
        r = VersionRange(None, None, "2.3.5", "<")
        assert not r.matches(Version("2.3.5"))
        assert r.matches(Version("2.3.4"))

    def test_operator_alias_doc_style(self) -> None:
        """文档风格操作符别名（gte/gt/lte/lt）与 Python 风格等价。"""
        for py_style, doc_style in [(">=", "gte"), (">", "gt"), ("<=", "lte"), ("<", "lt")]:
            r1 = VersionRange("2.0", py_style, "3.0", py_style)
            r2 = VersionRange("2.0", doc_style, "3.0", doc_style)
            assert r1.matches(Version("2.5")) == r2.matches(Version("2.5"))

    # ── 区间精度 ──

    def test_patch_precision(self) -> None:
        """2.3.0~2.3.5 的区间应命中 2.3.4 但不命中 2.3.15。"""
        r = VersionRange("2.3.0", ">=", "2.3.5", "<=")
        assert r.matches(Version("2.3.4"))
        assert not r.matches(Version("2.3.15"))

    # ── 全版本（哑元） ──

    def test_any_version(self) -> None:
        r = VersionRange(None, None, None, None)
        assert r.matches(Version("1.0"))
        assert r.matches(Version("99.99.99"))
        assert r.matches(Version("0.0.1"))

    # ── 表达式 ──

    def test_expression_left_side(self) -> None:
        r = VersionRange("2.3.0", ">=", "2.3.5", "<=")
        assert r.matches(Version("2.3.3"))
        assert not r.matches(Version("2.2.0"))

    def test_expression_unparseable_ignored(self) -> None:
        """不可解析的表达式不阻断匹配。"""
        r = VersionRange("2.0.0", ">=", None, None, expression="nonsense data")
        assert r.matches(Version("2.3.0"))
        assert r.matches(Version("2.0.0"))

    # ── 子组件前缀 ──

    def test_version_with_prefix(self) -> None:
        """非数字段（如beta）降级为字符串比较，数字在前非数字在后。"""
        v = Version("2.3.0beta")
        assert v.raw == "2.3.0beta"

    # ── 版本号边界 ──

    def test_single_component(self) -> None:
        assert Version("5") == Version("5.0")
        assert Version("5") < Version("5.1")

    def test_large_numbers(self) -> None:
        assert Version("999.999.999") > Version("998.999.999")

    @pytest.mark.parametrize(
        "start, s_type, end, e_type, good, bad",
        [
            ("1.0", "gte", "2.0", "lt", ["1.0", "1.9", "1.999"], ["0.9", "2.0", "2.1"]),
            ("1.0", "gt", "2.0", "lte", ["1.1", "1.999", "2.0"], ["0.9", "1.0", "2.1"]),
        ],
    )
    def test_various_boundaries(self, start, s_type, end, e_type, good, bad) -> None:
        r = VersionRange(start, s_type, end, e_type)
        for v in good:
            assert r.matches(Version(v)), f"{v} should match {r}"
        for v in bad:
            assert not r.matches(Version(v)), f"{v} should not match {r}"


class TestVersionRangeOverlaps:
    """区间重叠检测。"""

    def test_identical_range(self) -> None:
        a = VersionRange("2.0", "gte", "3.0", "lte")
        b = VersionRange("2.0", "gte", "3.0", "lte")
        assert a.overlaps(b)

    def test_adjacent_ranges(self) -> None:
        a = VersionRange("2.0", "gte", "2.5", "lte")
        b = VersionRange("2.5", "gt", "3.0", "lte")
        assert not a.overlaps(b)

    def test_overlap_lower_boundary(self) -> None:
        a = VersionRange("2.0", "gte", "2.5", "lte")
        b = VersionRange("2.5", "gte", "3.0", "lte")
        assert a.overlaps(b)

    def test_subset_range(self) -> None:
        a = VersionRange("1.0", "gte", "5.0", "lte")
        b = VersionRange("2.0", "gte", "3.0", "lte")
        assert a.overlaps(b)

    def test_no_overlap(self) -> None:
        a = VersionRange("1.0", "gte", "2.0", "lte")
        b = VersionRange("3.0", "gte", "4.0", "lte")
        assert not a.overlaps(b)

    def test_unbounded_start(self) -> None:
        a = VersionRange(None, None, "2.0", "lte")
        b = VersionRange("1.0", "gte", "3.0", "lte")
        assert a.overlaps(b)

    def test_unbounded_end(self) -> None:
        a = VersionRange("2.0", "gte", None, None)
        b = VersionRange("1.0", "gte", "3.0", "lte")
        assert a.overlaps(b)

    def test_both_unbounded(self) -> None:
        a = VersionRange(None, None, None, None)
        b = VersionRange("1.0", "gte", "2.0", "lte")
        assert a.overlaps(b)

    def test_eq_point_range(self) -> None:
        a = VersionRange("2.5", "eq", "2.5", "eq")
        b = VersionRange("2.0", "gte", "3.0", "lte")
        assert a.overlaps(b)

    def test_eq_point_no_overlap(self) -> None:
        a = VersionRange("4.0", "eq", "4.0", "eq")
        b = VersionRange("2.0", "gte", "3.0", "lte")
        assert not a.overlaps(b)
