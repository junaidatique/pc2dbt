"""Graph, walk and translate: one dbt model per PC Target.

For each target, walk back along the connectors to the sources, then emit one CTE per box
in dependency order. Connectors are the only truth about where a value comes from
(decision D1): names are never matched. Behaviour that looks wrong is copied and flagged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from .expr import ExpressionError, Symbol, UnknownPort, UnsupportedFunction, translate, uses_aggregate
from .parse import Connector, Folder, Mapping, Transformation
from .types import duck_type, scale_of


@dataclass
class Flag:
    kind: str       # crossed, rounds, error_default, router_default, century, master_outer, sort_order, counter,
                    # self_compare, parameter
    line: int
    message: str


@dataclass
class Block:
    """One box of the mapping and the SQL it became ("" when the box is dropped)."""
    box: str
    kind: str
    start: int
    end: int
    sql: str
    note: str = ""


@dataclass
class Model:
    name: str
    folder: str
    target: str
    sql: str
    flags: list[Flag]
    blocks: list[Block]


class UnsupportedElement(Exception):
    """Something in the XML this converter does not translate. Never guessed."""

    def __init__(self, what: str, line: int):
        super().__init__(f"{what} (L{line})")
        self.what, self.line = what, line


@dataclass
class NotConverted:
    """A target the converter could not translate (decision Q18)."""
    model: str
    folder: str
    what: str
    line: int


JOIN_SQL = {"Normal Join": "inner join", "Master Outer Join": "left join",
            "Detail Outer Join": "right join", "Full Outer Join": "full join"}
TWO_DIGIT_YEAR = re.compile(r"'[^']*(?<![Yy])[Yy]{2}(?![Yy])[^']*'")


def lines(a: int, b: int) -> str:
    return f"L{a}" if a == b else f"L{a}–{b}"


def cte_name(instance: str) -> str:
    return instance.lower()


def division(t: Transformation, p, seen: tuple = ()):
    """The port whose expression divides, if p's value comes from a division: in p itself or in a
    variable port it reads (pasted in, decision of prompt 12). None otherwise."""
    if "/" in p.expression:
        return p
    for v in t.ports.values():
        if v.port_type == "LOCAL VARIABLE" and v.name not in seen and mentions(v.name, p.expression):
            found = division(t, v, seen + (p.name,))
            if found is not None:
                return found
    return None


def written_tables(folder: Folder) -> set[str]:
    """Tables some mapping in this XML writes. A PC Source reading one becomes ref() (decision Q5)."""
    return {i.definition for m in folder.mappings.values() for i in m.instances.values() if i.type == "TARGET"}


def mentions(name: str, text: str) -> bool:
    return re.search(rf"(?<![\w$]){re.escape(name)}(?!\w)", text, re.I) is not None


def stateful_variables(variables) -> list:
    """Variable ports that read a previous row's value. PowerCenter evaluates input ports, then variable
    ports top to bottom, then output ports, so a variable that reads itself or a variable below it gets
    that variable's value from the previous row. Everything else uses this row only."""
    return [v for i, v in enumerate(variables) if any(mentions(w.name, v.expression) for w in variables[i:])]


def has_stateful(t: Transformation | None) -> bool:
    return t is not None and bool(stateful_variables([p for p in t.ports.values() if p.port_type == "LOCAL VARIABLE"]))


def var_value(v) -> tuple[str, str]:
    """(dbt var name, default) for a $$ mapping parameter; dates in the XML look like 12/31/2025 00:00:00."""
    default = v.default.strip()
    if v.datatype == "date/time" and default:
        d = datetime.strptime(default, "%m/%d/%Y %H:%M:%S")
        default = d.strftime("%Y-%m-%d") if d.time() == datetime.min.time() else d.strftime("%Y-%m-%d %H:%M:%S")
    return v.name.lstrip("$").lower(), default


class MappingGraph:
    def __init__(self, folder: Folder, mapping: Mapping):
        self.folder, self.m = folder, mapping
        self.into: dict[tuple[str, str], Connector] = {}
        self.incoming: dict[str, list[Connector]] = {}
        for c in mapping.connectors:
            self.into[(c.to_instance, c.to_field)] = c
            self.incoming.setdefault(c.to_instance, []).append(c)
        self.written = written_tables(folder)
        self.param_file_line = 0  # the session's parameter file, which can override $$ parameters
        for session in folder.root.iter("SESSION"):
            if session.get("MAPPINGNAME") == mapping.name:
                for a in session.iter("ATTRIBUTE"):
                    if a.get("NAME") == "Parameter Filename" and (a.get("VALUE") or "").strip():
                        self.param_file_line = a.line
        # A Sorter whose rows go straight into an Expression with variable ports is kept: that
        # Expression reads rows one by one, so their order matters (decisions Q12, Q13).
        self.kept_sorters: dict[str, str] = {}
        for c in mapping.connectors:
            src, dst = self.transformation(c.from_instance), self.transformation(c.to_instance)
            if src is not None and src.type == "Sorter" and dst is not None and dst.type == "Expression" and has_stateful(dst):
                self.kept_sorters[c.from_instance] = c.to_instance

    def transformation(self, instance: str) -> Transformation | None:
        inst = self.m.instances.get(instance)
        if inst is None:
            return None
        return self.m.transformations.get(inst.definition) if inst.type == "TRANSFORMATION" else None

    def upstream(self, target: str) -> list[str]:
        """Instances feeding `target`, sources first (depth-first post-order)."""
        order, seen = [], set()

        def visit(n):
            for c in self.incoming.get(n, []):
                if c.from_instance not in seen:
                    seen.add(c.from_instance)
                    visit(c.from_instance)
                    order.append(c.from_instance)
        visit(target)
        return order

    def ref(self, instance: str, port: str) -> tuple[str, str]:
        """Where the value of an output port lives: (cte, column). Sorters are looked through."""
        t = self.transformation(instance)
        if t is not None and t.type == "Sorter" and instance not in self.kept_sorters:
            c = self.into[(instance, port)]
            return self.ref(c.from_instance, c.from_field)
        if t is not None and t.type == "Router":
            return f"{cte_name(instance)}__{t.ports[port].group.lower()}", port.lower()
        return cte_name(instance), port.lower()

    def origins(self, instance: str, port: str) -> list:
        """The (box, port) pairs where a value was last computed, following pass-through ports back along
        connectors, through Router groups and through every branch of a Union."""
        t = self.transformation(instance)
        p = t.ports.get(port) if t else None
        if p is None:
            return []
        if t.type == "Router" and p.ref_field:
            back = [self.into.get((instance, p.ref_field))]
        elif t.type == "Custom Transformation" and t.template == "Union Transformation" and not p.is_input:
            back = [self.into.get((instance, i)) for i, o in t.dependencies if o == port]
        elif p.is_input and p.is_output and p.expression.strip().upper() in ("", port.upper()):
            back = [self.into.get((instance, port))]
        else:
            return [(t, p)]
        found = []
        for c in back:
            if c is not None and self.transformation(c.from_instance) is not None:
                found += self.origins(c.from_instance, c.from_field)
        return found or [(t, p)]

    def input_ref(self, instance: str, port: str):
        c = self.into.get((instance, port))
        return None if c is None else self.ref(c.from_instance, c.from_field)


def qualified(r) -> str:
    """A column read with the name of the step it comes from, so it can never mean an output
    of the same select (see tests/test_sql_names.py)."""
    return "null" if r is None else f"{r[0]}.{r[1]}"


def one_source(refs, what: str, line: int) -> str:
    ctes = {r[0] for r in refs if r is not None}
    if len(ctes) != 1:
        raise UnsupportedElement(f"{what} takes inputs from {len(ctes)} pipelines", line)
    return ctes.pop()


def column(sql: str, alias: str, comment: str = "") -> str:
    text = sql if sql == alias or sql.endswith(f".{alias}") else f"{sql} as {alias}"
    return text, comment


def select_list(cols: list[tuple[str, str]], indent: int = 8) -> str:
    out = []
    for i, (text, comment) in enumerate(cols):
        sep = "," if i < len(cols) - 1 else ""
        out.append(" " * indent + f"{text}{sep}" + (f"  -- {comment}" if comment else ""))
    return "\n".join(out)


class ModelBuilder:
    def __init__(self, graph: MappingGraph, target_instance: str):
        self.g, self.target = graph, target_instance
        self.order = graph.upstream(target_instance)
        members = set(self.order) | {target_instance}
        self.needed: dict[str, list[str]] = {}
        for c in graph.m.connectors:
            if c.from_instance in members and c.to_instance in members:
                self.needed.setdefault(c.from_instance, [])
                if c.from_field not in self.needed[c.from_instance]:
                    self.needed[c.from_instance].append(c.from_field)
        self.flags: list[Flag] = []
        self.blocks: list[Block] = []
        self.ctes: list[str] = []
        self.params_flagged: set[str] = set()

    def translate(self, text: str, symbols: dict, at: tuple[str, int] | None = None, **kw) -> str:
        """translate(), plus $$ mapping parameters as dbt vars (decision Q15). With `at` = (where, line),
        anything it can't translate becomes an UnsupportedElement naming that place (decision Q18)."""
        if at is not None:
            where, line = at
            try:
                return self.translate(text, symbols, **kw)
            except UnsupportedFunction as e:
                raise UnsupportedElement(f"{where}: {e.name}", line) from None
            except UnknownPort as e:
                raise UnsupportedElement(f"{where}: unknown port {e.name}", line) from None
            except ExpressionError as e:
                raise UnsupportedElement(f"{where}: cannot read the expression ({e})", line) from None
        params = {}
        for name in {n.upper() for n in re.findall(r"\$\$\w+", text)}:
            v = self.g.m.variables.get(name)
            if v is None or not v.is_param or v.datatype not in ("date/time", "string"):
                raise UnsupportedElement(f"mapping variable {name}", v.line if v else self.g.m.line)
            var, default = var_value(v)
            jinja = f"'{{{{ var('{var}', '{default}') }}}}'"
            params[name] = Symbol(f"/* {v.name} L{v.line} */ " + (f"cast({jinja} as timestamp)" if v.datatype == "date/time" else jinja),
                                  v.datatype)
            if name not in self.params_flagged:
                self.params_flagged.add(name)
                where = (f"; the session's parameter file (L{self.g.param_file_line}) can override it in PowerCenter, "
                         f"so pass the same value with dbt --vars") if self.g.param_file_line else ""
                self.flag("parameter", v.line, f"{v.name} becomes the dbt var {var}, default {default} from the XML "
                                               f"(decision Q15){where}")
        return translate(text, {**symbols, **params}, **kw)

    def flag(self, kind: str, line: int, message: str) -> str:
        self.flags.append(Flag(kind, line, message))
        return f"FLAG {kind} L{line}: {message}"

    def needed_ports(self, t: Transformation, instance: str):
        wanted = set(self.needed.get(instance, []))
        return [p for p in t.ports.values() if p.name in wanted]

    def add(self, instance: str, t: Transformation, kind: str, ctes: list[tuple[str, str]], note: str = ""):
        header = f"-- {instance} · {kind} · {lines(t.line, t.end)}" + (f" · {note}" if note else "")
        chunks = [(f"{header}\n" if i == 0 else "") + f"{name} as (\n{body}\n)" for i, (name, body) in enumerate(ctes)]
        sql = ",\n\n".join(chunks)
        self.ctes.extend(chunks)
        self.blocks.append(Block(instance, kind, t.line, t.end, sql, note))

    # ------------------------------------------------------------ boxes

    def source_qualifier(self, instance: str, t: Transformation):
        for a in ("Sql Query", "Source Filter", "User Defined Join", "Pre SQL", "Post SQL"):
            if t.attr(a).strip():
                raise UnsupportedElement(f"{instance}: Source Qualifier with {a}", t.attributes[a][1])
        if t.attr("Select Distinct") == "YES":
            raise UnsupportedElement(f"{instance}: Source Qualifier with Select Distinct", t.attributes["Select Distinct"][1])
        feeds = {c.from_instance for c in self.g.incoming.get(instance, [])}
        if len(feeds) != 1:
            raise UnsupportedElement(f"{instance}: Source Qualifier over {len(feeds)} sources", t.line)
        src_inst = self.g.m.instances[feeds.pop()]
        table = self.g.folder.sources[(src_inst.dbd, src_inst.definition)]
        cols = []
        for p in self.needed_ports(t, instance):
            c = self.g.into[(instance, p.name)]
            cols.append(column(f"{table.name.lower()}.{c.from_field.lower()}", p.name.lower()))
        note = f"reads {table.name} ({lines(table.line, table.end)})"
        if table.name in self.g.written:
            relation = f"{{{{ ref('{table.name.lower()}') }}}}"
            note += ", which another mapping writes: ref() (decision Q5)"
        else:
            relation = f"{{{{ source('{table.owner.lower()}', '{table.name.lower()}') }}}}"
        body = f"    select\n{select_list(cols)}\n    from {relation} as {table.name.lower()}"
        self.add(instance, t, "Source Qualifier", [(cte_name(instance), body)], note)

    def expression(self, instance: str, t: Transformation):
        symbols, refs, where = {}, [], []
        for p in t.ports.values():
            if not p.is_input:
                continue
            r = self.g.input_ref(instance, p.name)
            refs.append(r)
            symbols[p.name] = Symbol(qualified(r), p.datatype)
            default = p.default.strip()
            if default.upper().startswith("ERROR(") and r is not None:
                where.append((f"{qualified(r)} is not null", self.flag(
                    "error_default", p.line, f"{p.name} has an ERROR() default: a row with an empty {p.name} is skipped")))
            elif default and default.upper() != "NULL":
                raise UnsupportedElement(f"{instance}.{p.name}: input port default value {default!r}", p.line)
        source = one_source(refs, instance, t.line)
        # Variable ports, top to bottom (prompt 12). One that uses this row only is pasted into the ports
        # that read it, marked /* name line */; one that reads a previous row must be the counter.
        variables = [p for p in t.ports.values() if p.port_type == "LOCAL VARIABLE"]
        stateful = stateful_variables(variables)
        var_notes: dict[str, list[str]] = {}
        for v in variables:
            if v in stateful:
                sql, note = self.counter(instance, t, v, variables, symbols)
                symbols[v.name] = Symbol(sql, v.datatype)
                var_notes[v.name] = [note]
                continue
            notes = self.notes_from(v.expression, variables, var_notes)
            sql = self.port_sql(instance, v, symbols, notes)
            var_notes[v.name] = notes
            symbols[v.name] = Symbol(f"/* {v.name} L{v.line} */ ({sql})", v.datatype)
        cols = []
        for p in self.needed_ports(t, instance):
            if p.is_input:
                cols.append(column(symbols[p.name].sql, p.name.lower()))
                continue
            notes = self.notes_from(p.expression, variables, var_notes)
            sql = self.port_sql(instance, p, symbols, notes) if p.expression.strip() else "null"
            if re.search(r"TO_DATE\s*\(", p.expression, re.I) and TWO_DIGIT_YEAR.search(p.expression):
                notes.append(self.flag("century", p.line,
                                       "two-digit year: DuckDB reads 00-68 as 20xx and 69-99 as 19xx; PowerCenter's rule may differ"))
            cols.append(column(sql, p.name.lower(), "; ".join(notes)))
        body = f"    select\n{select_list(cols)}\n    from {source}"
        if where:
            body += "\n    where " + "\n      and ".join(f"{w}  -- {c}" for w, c in where)
        self.add(instance, t, "Expression", [(cte_name(instance), body)])

    @staticmethod
    def notes_from(text: str, variables, var_notes: dict) -> list[str]:
        """Flags of the variables an expression reads, so each output carries them as a comment."""
        out = []
        for v in variables:
            if mentions(v.name, text):
                out += [n for n in var_notes.get(v.name, []) if n not in out]
        return out

    def port_sql(self, instance: str, p, symbols: dict, notes: list[str]) -> str:
        same: list[str] = []
        sql = self.translate(p.expression, symbols, at=(f"{instance}.{p.name}", p.line), self_compares=same)
        if same:
            notes.append(self.flag("self_compare", p.line,
                                   f"{p.name} compares {', '.join(dict.fromkeys(same))} with itself: the variables it reads "
                                   f"already hold this row's values (they come earlier in port order), so each comparison "
                                   f"is true unless the value is NULL"))
        return sql

    def sorter(self, instance: str, t: Transformation):
        if t.attr("Distinct") == "YES":
            raise UnsupportedElement(f"{instance}: Sorter with Distinct", t.attributes["Distinct"][1])
        if instance in self.g.kept_sorters:
            return self.sorted_rows(instance, t)
        note = "dropped: row order means nothing in a table (decision Q12)"
        self.blocks.append(Block(instance, "Sorter", t.line, t.end, "", note))
        self.ctes.append(f"-- {instance} · Sorter · {lines(t.line, t.end)} · {note}")

    def counter(self, instance: str, t: Transformation, seq, variables, symbols: dict) -> tuple[str, str]:
        """The one pattern that reads a previous row (decision Q13): v_SEQ = IIF(v_PREV = X, v_SEQ + 1, 1)
        where v_PREV, above it, is X. Anything else that reads a previous row stops."""
        above = {v.name.upper(): v for v in variables[:variables.index(seq)]}
        m = re.fullmatch(rf"IIF\((\w+)=(\w+),{re.escape(seq.name)}\+1,1\)", re.sub(r"\s+", "", seq.expression), re.I)
        prev = x = None
        for a, b in ((m.group(1), m.group(2)), (m.group(2), m.group(1))) if m else ():
            v, port = above.get(a.upper()), t.ports.get(b) or t.ports.get(b.upper())
            if v is not None and port is not None and port.is_input and v.expression.strip().upper() == port.name.upper():
                prev, x = v, port.name
        if prev is None:
            raise UnsupportedElement(f"{instance}.{seq.name}: reads a previous row's value in a pattern this converter "
                                     f"does not translate (decision Q13)", seq.line)
        feeders = {c.from_instance for c in self.g.incoming.get(instance, [])}
        srt = feeders.pop() if len(feeders) == 1 else None
        if srt not in self.g.kept_sorters:
            raise UnsupportedElement(f"{instance}: variable ports need a Sorter right before them, "
                                     f"otherwise the row order is unknown", t.line)
        pos, xs = f"{cte_name(srt)}.sort_position", symbols[x].sql
        sql = f"{pos}\n            - coalesce(max(case when {xs} is null then {pos} end) over (order by {pos}) - 1, 0)"
        note = self.flag("counter", seq.line,
                         f"{prev.name} is set to this row's {x} ({lines(prev.line, prev.line)}) before {seq.name} compares them, "
                         f"so the comparison is true on every row where {x} is not NULL: one running number over all rows "
                         f"in {srt}'s order that never restarts per {x}, back to 1 on a row whose {x} is NULL")
        return sql, note

    def sorted_rows(self, instance: str, t: Transformation):
        """A Sorter kept because an Expression with variable ports reads its rows in order."""
        consumer = self.g.kept_sorters[instance]
        keys = [p for p in t.ports.values() if p.sort_key]
        if not keys:
            raise UnsupportedElement(f"{instance}: Sorter with no sort key", t.line)
        refs = {p.name: self.g.input_ref(instance, p.name) for p in t.ports.values()}
        source = one_source(refs.values(), instance, t.line)
        ignore_case = t.attr("Case Sensitive") == "NO"
        nulls_low = t.attr("Null Treated Low") == "YES"
        order = []
        for p in keys:
            sql = qualified(refs[p.name])
            if ignore_case and p.datatype.lower() in ("string", "nstring", "text", "ntext"):
                sql = f"lower({sql})"
            desc = p.sort_direction == "DESCENDING"
            order.append(f"{sql} {'desc' if desc else 'asc'} nulls {'first' if nulls_low != desc else 'last'}")
        case_line, null_line = t.attributes.get("Case Sensitive", ("", t.line))[1], t.attributes.get("Null Treated Low", ("", t.line))[1]
        note = self.flag("sort_order", t.line,
                         f"{instance} is kept only to put rows in order for {consumer} (decisions Q12, Q13): sort keys "
                         f"{', '.join(p.name for p in keys)}; "
                         + (f"case is ignored (Case Sensitive = NO, L{case_line}), so strings sort by lower(); " if ignore_case else "")
                         + f"NULLs sort {'low' if nulls_low else 'high'} (Null Treated Low = {'YES' if nulls_low else 'NO'}, L{null_line})")
        cols = [column(qualified(refs[p.name]), p.name.lower()) for p in self.needed_ports(t, instance)]
        cols.append(("row_number() over (\n            order by " + ",\n                     ".join(order)
                     + "\n        ) as sort_position", note))
        body = f"    select\n{select_list(cols)}\n    from {source}"
        self.add(instance, t, "Sorter", [(cte_name(instance), body)], f"kept: its order numbers the rows for {consumer} (decision Q12)")

    def aggregator(self, instance: str, t: Transformation):
        symbols, refs = {}, []
        for p in t.ports.values():
            if not p.is_input:
                continue
            r = self.g.input_ref(instance, p.name)
            refs.append(r)
            symbols[p.name] = Symbol(qualified(r), p.datatype)
            if p.default.strip() and p.default.strip().upper() != "NULL":
                raise UnsupportedElement(f"{instance}.{p.name}: input port default value {p.default.strip()!r}", p.line)
        source = one_source(refs, instance, t.line)
        group = [p for p in t.ports.values() if p.expression_type == "GROUPBY"]
        for p in group:
            if not p.is_input:
                raise UnsupportedElement(f"{instance}.{p.name}: group-by port that is not an input", p.line)
        cols = []
        for p in self.needed_ports(t, instance):
            if p.expression_type == "GROUPBY":
                cols.append(column(symbols[p.name].sql, p.name.lower()))
                continue
            if not uses_aggregate(p.expression):
                raise UnsupportedElement(f"{instance}.{p.name}: Aggregator port without an aggregate function "
                                         f"(PowerCenter would return the last row's value)", p.line)
            cols.append(column(self.translate(p.expression, symbols, at=(f"{instance}.{p.name}", p.line), aggregates=True),
                               p.name.lower()))
        body = f"    select\n{select_list(cols)}\n    from {source}"
        if group:
            body += "\n    group by " + ", ".join(symbols[p.name].sql for p in group)
        self.add(instance, t, "Aggregator", [(cte_name(instance), body)])

    def filter(self, instance: str, t: Transformation):
        symbols, refs = {}, []
        for p in t.ports.values():
            if p.is_input:
                r = self.g.input_ref(instance, p.name)
                refs.append(r)
                symbols[p.name] = Symbol(qualified(r), p.datatype)
        source = one_source(refs, instance, t.line)
        text = t.attr("Filter Condition").strip() or "TRUE"
        line = t.attributes.get("Filter Condition", ("", t.line))[1]
        cond = self.translate(text, symbols, at=(f"{instance} filter condition", line))
        cols = [column(symbols[p.name].sql, p.name.lower()) for p in self.needed_ports(t, instance)]
        body = (f"    select\n{select_list(cols)}\n    from {source}\n    where coalesce({cond}, false)"
                f"  -- {' '.join(text.split())} (L{line}); a row whose condition is NULL is dropped, as in PowerCenter")
        self.add(instance, t, "Filter", [(cte_name(instance), body)])

    def joiner(self, instance: str, t: Transformation):
        jt = t.attr("Join Type")
        if jt not in JOIN_SQL:
            raise UnsupportedElement(f"{instance}: join type {jt!r}", t.line)
        if t.attr("Case Sensitive String Comparison") == "NO":
            raise UnsupportedElement(f"{instance}: case-insensitive join", t.attributes["Case Sensitive String Comparison"][1])
        sides = {"master": [], "detail": []}
        boxes = {"master": set(), "detail": set()}
        symbols = {}
        for p in t.ports.values():
            side = "master" if p.is_master else "detail"
            r = self.g.input_ref(instance, p.name)
            sides[side].append(r)
            if (instance, p.name) in self.g.into:
                boxes[side].add(self.g.into[(instance, p.name)].from_instance)
            symbols[p.name] = Symbol("null" if r is None else f"{side}.{r[1]}", p.datatype)
        master = one_source(sides["master"], f"{instance} (master side)", t.line)
        detail = one_source(sides["detail"], f"{instance} (detail side)", t.line)
        cond = self.translate(t.attr("Join Condition"), symbols,
                              at=(f"{instance} join condition", t.attributes.get("Join Condition", ("", t.line))[1]))
        cols = [column(symbols[p.name].sql, p.name.lower()) for p in self.needed_ports(t, instance)]
        flag = ""
        if jt == "Master Outer Join":
            m_box, d_box = ", ".join(sorted(boxes["master"])), ", ".join(sorted(boxes["detail"]))
            flag = "  -- " + self.flag("master_outer", t.attributes["Join Type"][1],
                                      f"{instance} is a Master Outer Join: it keeps every row from {d_box} (detail) and only "
                                      f"the rows from {m_box} (master) that match; {m_box} rows with no match are dropped")
        body = (f"    select\n{select_list(cols)}\n    from {detail} as detail\n"
                f"    {JOIN_SQL[jt]} {master} as master{flag}\n        on {cond}")
        self.add(instance, t, "Joiner", [(cte_name(instance), body)], jt)

    def router(self, instance: str, t: Transformation):
        inputs = {p.name: p for p in t.ports.values() if p.group == "INPUT" or p.port_type == "INPUT"}
        refs = {n: self.g.input_ref(instance, n) for n in inputs}
        source = one_source(refs.values(), instance, t.line)
        symbols = {n: Symbol(qualified(r), inputs[n].datatype) for n, r in refs.items()}
        wanted = set(self.needed.get(instance, []))
        conditions = [(g, self.translate(g.expression.strip(), symbols, at=(f"{instance} group {g.name}", g.line)))
                      for g in sorted(t.groups, key=lambda g: g.order)
                      if g.group_type == "OUTPUT"]
        ctes = []
        for g in sorted(t.groups, key=lambda g: g.order):
            if g.group_type not in ("OUTPUT", "OUTPUT/DEFAULT"):
                continue
            ports = [p for p in t.ports.values() if p.group == g.name and p.name in wanted]
            if g.group_type == "OUTPUT/DEFAULT" and not ports:
                self.ctes.append(f"-- {self.flag('router_default', g.line, f'{instance}: the default group is not connected, so rows that match no group are dropped')}")
                continue
            if not ports:
                continue
            if g.group_type == "OUTPUT":
                where = f"coalesce({dict((x.name, c) for x, c in conditions)[g.name]}, false)"
            else:
                where = " and ".join(f"not coalesce({c}, false)" for _, c in conditions)
            cols = [column(symbols[p.ref_field].sql, p.name.lower()) for p in ports]
            body = f"    -- group {g.name} ({lines(g.line, g.line)})\n    select\n{select_list(cols)}\n    from {source}\n    where {where}"
            ctes.append((f"{cte_name(instance)}__{g.name.lower()}", body))
        self.add(instance, t, "Router", ctes)

    def union(self, instance: str, t: Transformation):
        outputs = [p for p in t.ports.values() if p.group == "OUTPUT" and p.name in set(self.needed.get(instance, []))]
        by_output = {}
        for inp, out in t.dependencies:
            by_output.setdefault(out, {})[t.ports[inp].group] = inp
        branches = []
        for g in sorted((g for g in t.groups if g.group_type == "INPUT"), key=lambda g: g.order):
            refs, cols = [], []
            for o in outputs:
                inp = by_output.get(o.name, {}).get(g.name)
                r = self.g.input_ref(instance, inp) if inp else None
                refs.append(r)
                cols.append(column(qualified(r), o.name.lower()))
            src = one_source(refs, f"{instance} group {g.name}", t.line)
            branches.append(f"    -- group {g.name}\n    select\n{select_list(cols)}\n    from {src}")
        self.add(instance, t, "Union", [(cte_name(instance), "\n    union all\n".join(branches))])

    # ------------------------------------------------------------ target

    def final_select(self) -> str:
        inst = self.g.m.instances[self.target]
        table = self.g.folder.targets[inst.definition]
        refs, cols = [], []
        names = set(table.fields)
        for f in table.fields.values():
            c = self.g.into.get((self.target, f.name))
            dtype = duck_type(f.datatype, f.precision, f.scale)
            if c is None:
                cols.append(column(f"cast(null as {dtype})", f.name.lower()))
                continue
            r = self.g.ref(c.from_instance, c.from_field)
            refs.append(r)
            notes = []
            if c.from_field != f.name and c.from_field in names:
                notes.append(self.flag("crossed", c.line,
                                       f"{c.from_instance}.{c.from_field} goes into {table.name}.{f.name}, as the connector says"))
            found = self.g.origins(c.from_instance, c.from_field)
            if found and scale_of(f.datatype, f.scale) not in (-1, None):
                # With high precision off a computed decimal is a double at run time, so a division
                # can carry more decimals than the port declares (decision Q11). A Union has one
                # origin per branch; any branch that rounds is flagged.
                divided = [(p, division(t, p)) for t, p in found if division(t, p) is not None]
                scales = [scale_of(p.datatype, p.scale) for _, p in found]
                incoming = None if divided or None in scales else max(scales)
                target_scale = scale_of(f.datatype, f.scale)
                src_port, div = divided[0] if divided else (found[0][1], None)
                computed = div is not None
                if incoming is None or (incoming not in (-1,) and incoming > target_scale):
                    inner = "" if div in (None, src_port) else f", which divides in {div.name} ({lines(div.line, div.line)})"
                    what = (f"{c.from_field} is computed as {src_port.expression} ({lines(src_port.line, src_port.line)}){inner}, "
                            f"a double at run time because high precision is off, and" if computed
                            else f"{c.from_field} ({src_port.datatype})")
                    notes.append(self.flag("rounds", c.line, f"{what} is rounded to {target_scale} decimal places "
                                                             f"by the target column {f.name} {dtype} (decision Q11)"))
            cols.append(column(f"cast({qualified(r)} as {dtype})", f.name.lower(), "; ".join(notes)))
        source = one_source(refs, self.target, inst.line)
        body = f"select\n{select_list(cols, 4)}\nfrom {source}"
        self.blocks.append(Block(self.target, "Target", table.line, table.end, body, f"writes {table.name}"))
        return body

    def build(self) -> Model:
        boxes = {"Source Qualifier": self.source_qualifier, "Expression": self.expression, "Sorter": self.sorter,
                 "Joiner": self.joiner, "Router": self.router, "Aggregator": self.aggregator, "Filter": self.filter}
        for instance in self.order:
            inst = self.g.m.instances[instance]
            if inst.type == "SOURCE":
                continue
            t = self.g.transformation(instance)
            if t.type == "Custom Transformation" and t.template == "Union Transformation":
                self.union(instance, t)
            elif t.type in boxes:
                boxes[t.type](instance, t)
            else:
                raise UnsupportedElement(f"{instance}: {t.type}", t.line)
        final = self.final_select()
        inst = self.g.m.instances[self.target]
        table = self.g.folder.targets[inst.definition]
        head = (f"-- Generated by pc2dbt from mapping {self.g.m.name} ({lines(self.g.m.line, self.g.m.end)}), "
                f"target {table.name} ({lines(table.line, table.end)}).\n-- Lines refer to the PowerCenter XML. "
                f"FLAG comments mark behaviour copied as-is (decision D1); see flags.md.\n")
        with_part = ""
        if self.ctes:
            parts, pending = [], []
            for chunk in self.ctes:
                if " as (\n" in chunk:
                    parts.append("\n".join(pending + [chunk]))
                    pending = []
                else:
                    pending.append(chunk)
            with_part = "with\n" + ",\n\n".join(parts) + ("\n" + "\n".join(pending) if pending else "") + "\n\n"
        sql = head + "\n" + with_part + final + "\n"
        return Model(table.name.lower(), self.g.m.name.lower(), table.name, sql, self.flags, self.blocks)


def convert_mapping(folder: Folder, mapping_name: str) -> list[Model]:
    """Every target as a model; stops on the first thing it can't translate (used by the tests)."""
    graph = MappingGraph(folder, folder.mappings[mapping_name])
    targets = [i.name for i in graph.m.instances.values() if i.type == "TARGET"]
    return [ModelBuilder(graph, t).build() for t in targets]


def convert_mapping_keep_going(folder: Folder, mapping_name: str) -> tuple[list[Model], list[NotConverted]]:
    """Every target as a model, converting all it can (decision Q18). A target that can't be translated
    becomes a model that makes dbt stop on it, naming the element and its XML line."""
    graph = MappingGraph(folder, folder.mappings[mapping_name])
    models, failed = [], []
    for inst in (i for i in graph.m.instances.values() if i.type == "TARGET"):
        try:
            models.append(ModelBuilder(graph, inst.name).build())
        except UnsupportedElement as e:
            failed.append(NotConverted(inst.definition.lower(), mapping_name.lower(), e.what, e.line))
        except Exception as e:  # a converter bug: still report it and convert the rest
            failed.append(NotConverted(inst.definition.lower(), mapping_name.lower(),
                                       f"{inst.name}: converter error {type(e).__name__}: {e}", inst.line))
        else:
            continue
        n = failed[-1]
        message = (f"pc2dbt could not convert {n.model} (mapping {mapping_name}): {n.what} (L{n.line})"
                   .replace("\\", "/").replace('"', "'").replace("{", "(").replace("}", ")"))
        sql = ("-- pc2dbt could not convert this model (decision Q18). dbt stops on it with the reason below; "
               "see flags.md.\n"
               f'{{% if execute %}}{{{{ exceptions.raise_compiler_error("{message}") }}}}{{% endif %}}\n')
        models.append(Model(n.model, n.folder, inst.definition, sql, [], []))
    return models, failed
