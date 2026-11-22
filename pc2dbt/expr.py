"""Translate Informatica expressions into DuckDB SQL with the same results.

A small precedence-climbing parser turns the expression into a tree; each node becomes SQL.
Only functions this module knows are translated; anything else raises UnsupportedFunction,
so nothing is guessed. Ports are looked up case-insensitively in a symbol table that maps
each port to its SQL reference and PowerCenter datatype.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Symbol:
    sql: str        # how to refer to the port in SQL, e.g. "subtotal_in"
    pc_type: str    # PowerCenter datatype: string, decimal, double, integer, date/time, ...


class UnsupportedFunction(Exception):
    """An Informatica function (or format) this converter does not translate."""

    def __init__(self, name: str):
        super().__init__(f"unsupported Informatica function or format: {name}")
        self.name = name


class ExpressionError(Exception):
    pass


# ---------------------------------------------------------------- tokens

TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<num>\d+\.\d*|\.\d+|\d+)
  | (?P<str>'(?:[^']|'')*')
  | (?P<op><=|>=|<>|!=|\^=|\|\||[-+*/%=<>(),])
  | (?P<name>\$\$?[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)
""", re.VERBOSE)


def tokenize(text: str) -> list[tuple[str, str]]:
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ExpressionError(f"cannot read expression at {text[pos:pos + 20]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        value = m.group(kind)
        if kind == "name" and value.upper() in ("AND", "OR", "NOT"):
            kind, value = "op", value.upper()
        out.append((kind, value))
    out.append(("end", ""))
    return out


# ---------------------------------------------------------------- tree

@dataclass
class Expr:
    sql: str
    pc_type: str


# binary operators: precedence (higher binds tighter), per Informatica's operator table
BINARY = {"OR": 1, "AND": 2,
          "=": 4, "<>": 4, "!=": 4, "^=": 4,
          "<": 5, "<=": 5, ">": 5, ">=": 5,
          "||": 6, "+": 7, "-": 7, "*": 8, "/": 8, "%": 8}
COMPARISON = {"=", "<>", "!=", "^=", "<", "<=", ">", ">="}
NUMERIC = {"decimal", "double", "integer", "small integer", "bigint", "real"}
# Aggregate functions: same NULL rules as SQL (NULLs skipped; all-NULL gives NULL; COUNT(*) counts rows).
AGGREGATES = {"COUNT", "SUM", "MIN", "MAX"}


class Parser:
    def __init__(self, text: str, symbols: dict[str, Symbol], aggregates: bool = False):
        self.tokens = tokenize(text)
        self.i = 0
        self.symbols = {k.upper(): v for k, v in symbols.items()}
        self.aggregates = aggregates
        self.self_compares: list[str] = []  # comparisons with the same value on both sides

    def peek(self):
        return self.tokens[self.i]

    def take(self, value=None):
        tok = self.tokens[self.i]
        if value is not None and tok[1] != value:
            raise ExpressionError(f"expected {value!r}, found {tok[1]!r}")
        self.i += 1
        return tok

    def parse(self) -> Expr:
        e = self.expression(0)
        if self.peek()[0] != "end":
            raise ExpressionError(f"unexpected {self.peek()[1]!r}")
        return e

    def expression(self, min_prec: int) -> Expr:
        left = self.unary()
        while True:
            kind, op = self.peek()
            if kind != "op" or op not in BINARY or BINARY[op] < min_prec:
                return left
            self.take()
            right = self.expression(BINARY[op] + 1)
            if op in COMPARISON and bare(left.sql) == bare(right.sql):
                self.self_compares.append(bare(left.sql))
            left = binary(op, left, right)

    def unary(self) -> Expr:
        kind, value = self.peek()
        if kind == "op" and value == "NOT":
            self.take()
            e = self.expression(3)
            return Expr(f"(not {e.sql})", "boolean")
        if kind == "op" and value in ("-", "+"):
            self.take()
            e = self.unary()
            return Expr(f"({value}{e.sql})", e.pc_type)
        return self.primary()

    def primary(self) -> Expr:
        kind, value = self.take()
        if kind == "num":
            return Expr(value, "decimal")
        if kind == "str":
            return Expr(value, "string")
        if kind == "op" and value == "(":
            e = self.expression(0)
            self.take(")")
            return Expr(f"({e.sql})", e.pc_type)
        if kind == "name":
            upper = value.upper()
            if self.peek()[1] == "(":
                self.take("(")
                if upper in AGGREGATES:
                    return self.aggregate(upper)
                args = []
                if self.peek()[1] != ")":
                    args.append(self.expression(0))
                    while self.peek()[1] == ",":
                        self.take(",")
                        args.append(self.expression(0))
                self.take(")")
                return function(upper, args)
            if upper == "NULL":
                return Expr("null", "null")
            if upper in ("TRUE", "FALSE"):
                return Expr(upper.lower(), "boolean")
            sym = self.symbols[upper]  # KeyError: the expression uses a port we don't have
            return Expr(sym.sql, sym.pc_type)
        raise ExpressionError(f"unexpected {value!r}")


    def aggregate(self, name: str) -> Expr:
        """COUNT(*) / COUNT(x) / SUM(x) / MIN(x) / MAX(x); only inside an Aggregator."""
        if not self.aggregates:
            raise UnsupportedFunction(name)
        if name == "COUNT" and self.peek()[1] == "*":
            self.take("*")
            self.take(")")
            return Expr("count(*)", "decimal")
        arg = self.expression(0)
        self.take(")")
        return Expr(f"{name.lower()}({arg.sql})", "decimal" if name == "COUNT" else arg.pc_type)


def bare(sql: str) -> str:
    """SQL without comments, spaces or wrapping brackets, to tell whether two sides are the same value."""
    sql = re.sub(r"\s+", "", re.sub(r"/\*.*?\*/", "", sql))
    while sql.startswith("(") and sql.endswith(")") and depth_never_zero(sql[1:-1]):
        sql = sql[1:-1]
    return sql


def depth_never_zero(inner: str) -> bool:
    depth = 0
    for ch in inner:
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if depth < 0:
            return False
    return depth == 0


def binary(op: str, a: Expr, b: Expr) -> Expr:
    if op in ("AND", "OR"):
        return Expr(f"({a.sql} {op.lower()} {b.sql})", "boolean")
    if op in COMPARISON:
        sql_op = "<>" if op in ("!=", "^=") else op
        return Expr(f"{a.sql} {sql_op} {b.sql}", "boolean")
    if op == "||":
        # Informatica ignores a NULL side when concatenating; both NULL gives NULL.
        return Expr(f"case when {a.sql} is null and {b.sql} is null then null else concat({a.sql}, {b.sql}) end", "string")
    pc_type = "double" if op == "/" else ("integer" if a.pc_type == b.pc_type == "integer" else "decimal")
    return Expr(f"{a.sql} {op} {b.sql}", pc_type)


# Informatica date format tokens -> strftime, longest first
FORMAT_TOKENS = [("YYYY", "%Y"), ("HH24", "%H"), ("HH12", "%I"), ("MONTH", "%B"), ("MON", "%b"), ("DAY", "%A"),
                 ("YY", "%y"), ("MM", "%m"), ("DD", "%d"), ("DY", "%a"), ("HH", "%I"), ("MI", "%M"),
                 ("SS", "%S"), ("AM", "%p"), ("PM", "%p")]


def strftime_format(literal: str) -> str:
    text = literal[1:-1].replace("''", "'")
    out, i = [], 0
    while i < len(text):
        for tok, rep in FORMAT_TOKENS:
            if text[i:i + len(tok)].upper() == tok:
                out.append(rep)
                i += len(tok)
                break
        else:
            ch = text[i]
            if ch.isalpha():
                raise UnsupportedFunction(f"date format {text!r}")
            out.append(ch)
            i += 1
    return "'" + "".join(out) + "'"


def function(name: str, args: list[Expr]) -> Expr:
    n = len(args)
    if name == "IIF" and n == 3:
        return Expr(f"case when {args[0].sql} then {args[1].sql} else {args[2].sql} end", args[1].pc_type)
    if name == "ISNULL" and n == 1:
        return Expr(f"({args[0].sql} is null)", "boolean")
    if name in ("UPPER", "LOWER") and n == 1:
        return Expr(f"{name.lower()}({args[0].sql})", "string")
    if name in ("LTRIM", "RTRIM") and n in (1, 2):
        return Expr(f"{name.lower()}({', '.join(a.sql for a in args)})", "string")
    if name == "TO_CHAR" and n == 2 and args[0].pc_type == "date/time" and args[1].pc_type == "string":
        return Expr(f"strftime({args[0].sql}, {strftime_format(args[1].sql)})", "string")
    if name == "TO_DATE" and n == 2 and args[1].pc_type == "string":
        return Expr(f"strptime({args[0].sql}, {strftime_format(args[1].sql)})", "date/time")
    if name == "TRUNC" and n == 1 and args[0].pc_type == "date/time":
        return Expr(f"date_trunc('day', {args[0].sql})", "date/time")
    if name == "DATE_DIFF" and n == 3 and args[2].pc_type == "string":
        # date1 - date2 in the unit asked for, with fractions (Informatica), not calendar boundaries.
        if args[2].sql.upper() not in ("'D'", "'DD'", "'DDD'", "'DY'", "'DAY'"):
            raise UnsupportedFunction(f"DATE_DIFF with format {args[2].sql}")
        return Expr(f"((epoch({args[0].sql}) - epoch({args[1].sql})) / 86400)", "double")
    if name == "TRUNC" and n == 1 and args[0].pc_type in NUMERIC:
        return Expr(f"trunc({args[0].sql})", args[0].pc_type)
    raise UnsupportedFunction(name)


def translate(text: str, symbols: dict[str, Symbol], aggregates: bool = False, self_compares: list | None = None) -> str:
    """Informatica expression -> SQL. If `self_compares` is given, every comparison of a value with itself
    (say v_PREV = X where v_PREV already holds this row's X) is appended to it."""
    parser = Parser(text, symbols, aggregates)
    sql = parser.parse().sql
    if self_compares is not None:
        self_compares.extend(parser.self_compares)
    return sql


def uses_aggregate(text: str) -> bool:
    toks = tokenize(text)
    return any(k == "name" and v.upper() in AGGREGATES and toks[i + 1][1] == "(" for i, (k, v) in enumerate(toks[:-1]))
