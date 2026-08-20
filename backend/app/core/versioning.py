"""版本号归一化与版本区间匹配引擎（开发方案 §5.9）。

核心操作：给定产品 X 与版本号 Y，命中哪些 POC —— 将 PocAffected 记录的
版本区间 ``(version_start, start_type, version_end, end_type)`` 与目标版本逐条比对。

操作符兼容：
    - 存储层 / API 层使用 Python 风格（``>=  >  <=  <``，空 = 任意）
    - 设计文档使用 ``gte / gt / lte / lt / any``
两者在本模块归一化为同一语义。

执行模型（对齐 §5.9）：
```python
class VersionRange:
    def __init__(self, start, start_type, end, end_type):
        self.start = Version(start) if start else None
        self.end = Version(end) if end else None

    def matches(self, v: Version) -> bool:
        if self.start_type == "gte" and not (self.start <= v):
            return False
        ...
```
"""

from __future__ import annotations

import re

# 操作符别名 → 语义键。
_OPERATOR_ALIASES: dict[str, str] = {
    "gte": "gte",
    ">=": "gte",
    "gt": "gt",
    ">": "gt",
    "lte": "lte",
    "<=": "lte",
    "lt": "lt",
    "<": "lt",
}
_ANY_VALUES = {"any", "", None}

# 归一化段数：2.3.15 → (2, 3, 15, 0)，补 0 便于比较。
_SEGMENTS = 4
# 段起始数字匹配：leading digits 转 int，无法解析的段按字符串降级比较。
_NUM_SEGMENT = re.compile(r"(?P<num>\d+)")

# ── 归一化 ───────────────────────────────────────────────────────────────


def normalize_version(v: str, segments: int = _SEGMENTS) -> tuple[int, ...]:
    """版本号归一化为整数元组（§5.9）：2.3.15 → (2, 3, 15, 0)。

    无法解析的数字段抛 ValueError，由调用方决定跳过或返回 400。
    """
    parts = [int(p) for p in v.split(".")]
    while len(parts) < segments:
        parts.append(0)
    return tuple(parts[:segments])


def _segment_key(part: str) -> tuple[int, int | str]:
    """单段比较键：数字段 (0, 数字)，非数字段 (1, 原串)。

    首位标记保证数字段恒小于非数字段（数字比较优先），同标段再比实际值。
    """
    m = _NUM_SEGMENT.match(part.strip())
    if m:
        return (0, int(m.group(1)))
    return (1, part)


class Version:
    """版本号对象：归一化为 4 段比较键，元组原生支持 <、<=，可哈希。"""

    __slots__ = ("_key", "raw")

    def __init__(self, raw: str) -> None:
        self.raw = raw.strip()
        parts = self.raw.split(".")
        seg_keys = [_segment_key(p) for p in parts[:_SEGMENTS]]
        while len(seg_keys) < _SEGMENTS:
            seg_keys.append((0, 0))  # 缺段补 0，等价于 normalize_version
        self._key: tuple[tuple[int, int | str], ...] = tuple(seg_keys)

    @classmethod
    def from_normalized(cls, parts: tuple[int, ...]) -> Version:
        """从归一化整数元组构造。"""
        return cls(".".join(str(p) for p in parts))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Version) and self._key == other._key

    def __lt__(self, other: Version) -> bool:
        return self._key < other._key

    def __le__(self, other: Version) -> bool:
        return self._key <= other._key

    def __hash__(self) -> int:
        return hash(self._key)

    def __repr__(self) -> str:
        return f"Version({self.raw!r})"


# ── 版本区间 ───────────────────────────────────────────────────────────────
# version_expression 支持两种写法（CVE human 格式，VERSION 大小写不限）：
#   - 单边：  2.3.0 <= VERSION   |  VERSION <= 2.3.5   |  = 2.3.4
#   - 双边：  2.3.0 <= VERSION < 2.3.5
# 值与运算符可带引号；多表达式以逗号分隔，任一命中即通过（OR 语义）。
_VERSION_VALUE = r'"?[\w.\-~+]+"?'
_REL_OP = r"<=|>=|<|>|="
_EXPR_RE = re.compile(
    rf"^\s*(?:(?P<a>{_VERSION_VALUE})\s*(?P<op1>{_REL_OP})\s*VERSION"
    rf"\s*(?P<op2>{_REL_OP})\s*(?P<b>{_VERSION_VALUE})"
    rf"|(?P<c>{_VERSION_VALUE})\s*(?P<op3>{_REL_OP})\s*VERSION"
    rf"|VERSION\s*(?P<op4>{_REL_OP})\s*(?P<d>{_VERSION_VALUE}))\s*$",
    re.IGNORECASE,
)

# 运算符 → 语义键（含 "eq"）。
_OP_TO_KEY: dict[str, str] = {**_OPERATOR_ALIASES, "=": "eq", "==": "eq"}


class VersionRange:
    """版本区间：上界/下界各自可为空，操作符归一化为 gte/gt/lte/lt/eq/any。

    可选 ``expression``（version_expression 字段）：解析 CVE 格式表达式，
    与区间约束为 AND 关系；表达式整体不可解析时视为「不约束」，
    避免脏数据阻断匹配。
    """

    __slots__ = ("start", "start_type", "end", "end_type", "_expressions")

    def __init__(
        self,
        start: str | None,
        start_type: str | None,
        end: str | None,
        end_type: str | None,
        expression: str | None = None,
    ) -> None:
        self.start = Version(start) if start else None
        self.start_type = self._resolve(start_type)
        self.end = Version(end) if end else None
        self.end_type = self._resolve(end_type)
        self._expressions: list[VersionRange] | None = None
        if expression:
            subs = [r for r in (self._parse_expression(e) for e in expression.split(",")) if r is not None]
            self._expressions = subs if subs else []

    @staticmethod
    def _resolve(value: str | None) -> str:
        """操作符映射：Python 风格与文档风格统一到语义键。"""
        if value in _ANY_VALUES or value is None:
            return "any"
        return _OP_TO_KEY.get(value, "any")  # 未知写法按「不约束」安全降级

    def matches(self, v: Version) -> bool:
        """目标版本是否落在区间内（§5.9 匹配算法）。"""
        if self.start_type == "eq" or self.end_type == "eq":
            # eq = 精确版本匹配：start == end == v
            eq = self.start if self.start_type == "eq" else self.end
            return eq is not None and eq == v
        s = self.start
        e = self.end
        if self.start_type == "gte" and (s is None or not (s <= v)):
            return False
        if self.start_type == "gt" and (s is None or not (s < v)):
            return False
        if self.end_type == "lte" and (e is None or not (v <= e)):
            return False
        if self.end_type == "lt" and (e is None or not (v < e)):
            return False
        if self._expressions is not None:
            # 多条表达式视为同一漏洞的不同版本分支，任一命中即受该 POC 影响（OR）。
            return any(eq.matches(v) for eq in self._expressions) if self._expressions else True
        return True

    @classmethod
    def _parse_expression(cls, expr: str) -> VersionRange | None:
        """解析单条 version_expression → 派生态（仅含子区间约束，无嵌套表达式）。

        返回的 VersionRange.start/_end 直接复用 matches() 的边界判定；
        解析失败返回 None。
        """
        m = _EXPR_RE.fullmatch(expr.strip())
        if not m:
            return None

        def to_key(op: str) -> str:
            return _OP_TO_KEY.get(op, "any")

        def to_version(raw: str) -> str:
            return raw.strip().strip('"')

        # 双边：a op1 VERSION op2 b，需先做方向镜像
        if m.group("a") is not None:
            start = to_version(m.group("a"))
            start_type = _mirror(to_key(m.group("op1")))
            end = to_version(m.group("b"))
            end_type = to_key(m.group("op2"))
            return cls(start, start_type, end, end_type)
        # 单边（值在前）：c op3 VERSION → 下界
        if m.group("c") is not None:
            return cls(to_version(m.group("c")), _mirror(to_key(m.group("op3"))), None, None)
        # 单边（VERSION 在前）：VERSION op4 d → 上界
        return cls(None, None, to_version(m.group("d")), to_key(m.group("op4")))

    def __repr__(self) -> str:
        lo = f"{self.start.raw} {self.start_type}" if self.start else "any"
        hi = f"{self.end.raw} {self.end_type}" if self.end else "any"
        return f"VersionRange({lo} → {hi})"

    def overlaps(self, other: VersionRange) -> bool:
        """两个区间是否存在重叠（存在至少一个版本同时满足双方约束）。

        用于产品查询面板的版本范围搜索：给定搜索区间 [start, end]，
        找出所有 poc_affected 区间与之有交集的 POC。
        """
        # 若一方无有效边界，则默认有重叠（无约束侧覆盖一切）。
        # 对于 "eq" 类型，起止版本相同，分别检查即可。
        a_lo = self.start
        b_hi = other.end
        if a_lo and b_hi:
            if a_lo > b_hi:
                return False
            if a_lo == b_hi and (self.start_type in ("gt", "eq") or other.end_type in ("lt", "eq")):
                # 相等边界下，若任一侧是严格比较（gt/lt）则该点不满足交叉
                if self.start_type == "gt" or other.end_type == "lt":
                    return False
        b_lo = other.start
        a_hi = self.end
        if b_lo and a_hi:
            if b_lo > a_hi:
                return False
            if b_lo == a_hi and (other.start_type in ("gt", "eq") or self.end_type in ("lt", "eq")):
                if other.start_type == "gt" or self.end_type == "lt":
                    return False
        return True


def _mirror(op: str) -> str:
    """镜像比较方向：用于「值 在前」表达式（a <= VERSION 等价于 VERSION >= a）。"""
    if op == "gt":
        return "lt"
    if op == "gte":
        return "lte"
    if op == "lt":
        return "gt"
    if op == "lte":
        return "gte"
    if op == "eq":
        return "eq"
    return "any"
