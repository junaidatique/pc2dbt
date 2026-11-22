"""Parse: read a PowerCenter XML export into objects that keep their line numbers.

Every object remembers the line it starts on, so generated SQL and flags can point back
to the XML. VALUEPAIR elements are kept as empty nodes: in exports, a Command task keeps
its command (often with credentials) in them, and nothing here needs their content.
"""
from __future__ import annotations

import xml.parsers.expat
from dataclasses import dataclass, field
from pathlib import Path

SECRET_TAGS = {"VALUEPAIR"}


@dataclass
class Node:
    tag: str
    attrs: dict
    line: int
    end: int = 0
    children: list = field(default_factory=list)

    def kids(self, tag: str) -> list["Node"]:
        return [c for c in self.children if c.tag == tag]

    def iter(self, tag: str):
        if self.tag == tag:
            yield self
        for c in self.children:
            yield from c.iter(tag)

    def get(self, key: str, default=None):
        return self.attrs.get(key, default)


def read_tree(path: str | Path) -> Node:
    parser = xml.parsers.expat.ParserCreate()
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)  # powrmart.dtd is not shipped
    root = Node("#document", {}, 1)
    stack = [root]

    def start(tag, attrs):
        node = Node(tag, {} if tag in SECRET_TAGS else dict(attrs), parser.CurrentLineNumber)
        stack[-1].children.append(node)
        stack.append(node)

    def end(_tag):
        stack.pop().end = parser.CurrentLineNumber

    parser.StartElementHandler, parser.EndElementHandler = start, end
    parser.Parse(Path(path).read_bytes(), True)
    return root


# ---------------------------------------------------------------- domain objects

@dataclass
class Field:
    """A column of a PC Source or PC Target."""
    name: str
    datatype: str
    precision: int
    scale: int
    line: int


@dataclass
class Table:
    """A PC Source (owner and dbd set) or a PC Target."""
    name: str
    fields: dict[str, Field]
    line: int
    end: int
    owner: str = ""
    dbd: str = ""


@dataclass
class Port:
    name: str
    port_type: str          # INPUT, OUTPUT, INPUT/OUTPUT, LOCAL VARIABLE, ... /MASTER
    datatype: str
    precision: int
    scale: int
    expression: str
    default: str
    line: int
    group: str = ""
    ref_field: str = ""
    expression_type: str = ""   # GENERAL, or GROUPBY for an Aggregator's group-by port
    sort_key: bool = False      # Sorter: this port is a sort key (keys rank in port order)
    sort_direction: str = ""    # Sorter: ASCENDING or DESCENDING

    @property
    def is_input(self) -> bool:
        return "INPUT" in self.port_type

    @property
    def is_output(self) -> bool:
        return "OUTPUT" in self.port_type

    @property
    def is_master(self) -> bool:
        return "MASTER" in self.port_type


@dataclass
class Group:
    name: str
    group_type: str         # INPUT, OUTPUT, OUTPUT/DEFAULT
    expression: str
    order: int
    line: int


@dataclass
class Transformation:
    name: str
    type: str
    ports: dict[str, Port]
    groups: list[Group]
    attributes: dict[str, tuple[str, int]]   # name -> (value, line)
    line: int
    end: int
    template: str = ""                        # e.g. "Union Transformation" for a Custom Transformation
    dependencies: list[tuple[str, str]] = field(default_factory=list)  # (input port, output port)

    def attr(self, name: str, default: str = "") -> str:
        return self.attributes.get(name, (default, 0))[0]


@dataclass
class Instance:
    name: str
    type: str                # SOURCE, TARGET, TRANSFORMATION
    definition: str          # TRANSFORMATION_NAME
    dbd: str
    attributes: dict[str, tuple[str, int]]
    line: int


@dataclass
class Connector:
    from_instance: str
    from_field: str
    to_instance: str
    to_field: str
    line: int


@dataclass
class MappingVariable:
    """A $$ mapping variable or parameter (MAPPINGVARIABLE)."""
    name: str               # e.g. $$RUN_DATE
    datatype: str
    default: str
    is_param: bool
    line: int


@dataclass
class Mapping:
    name: str
    transformations: dict[str, Transformation]
    instances: dict[str, Instance]
    connectors: list[Connector]
    line: int
    end: int
    variables: dict[str, MappingVariable] = field(default_factory=dict)


@dataclass
class Folder:
    name: str
    sources: dict[tuple[str, str], Table]   # (dbd, name) -> table
    targets: dict[str, Table]
    mappings: dict[str, Mapping]
    root: Node


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _table(node: Node, field_tag: str) -> Table:
    fields = {f.get("NAME"): Field(f.get("NAME"), f.get("DATATYPE"), _int(f.get("PRECISION")), _int(f.get("SCALE")), f.line)
              for f in node.kids(field_tag)}
    return Table(node.get("NAME"), fields, node.line, node.end, node.get("OWNERNAME", ""), node.get("DBDNAME", ""))


def _attributes(node: Node) -> dict[str, tuple[str, int]]:
    return {a.get("NAME"): (a.get("VALUE", ""), a.line) for a in node.kids("TABLEATTRIBUTE")}


def _transformation(node: Node) -> Transformation:
    ports = {}
    for p in node.kids("TRANSFORMFIELD"):
        ports[p.get("NAME")] = Port(
            p.get("NAME"), p.get("PORTTYPE", ""), p.get("DATATYPE", ""), _int(p.get("PRECISION")), _int(p.get("SCALE")),
            p.get("EXPRESSION", "") or "", p.get("DEFAULTVALUE", "") or "", p.line, p.get("GROUP", "") or "",
            p.get("REF_FIELD", "") or "", p.get("EXPRESSIONTYPE", "") or "", p.get("ISSORTKEY") == "YES",
            p.get("SORTDIRECTION", "") or "")
    groups = [Group(g.get("NAME"), g.get("TYPE", ""), g.get("EXPRESSION", "") or "", _int(g.get("ORDER")), g.line)
              for g in node.kids("GROUP")]
    deps = [(d.get("INPUTFIELD"), d.get("OUTPUTFIELD")) for d in node.kids("FIELDDEPENDENCY")]
    return Transformation(node.get("NAME"), node.get("TYPE"), ports, groups, _attributes(node), node.line, node.end,
                          node.get("TEMPLATENAME", "") or "", deps)


def _mapping(node: Node) -> Mapping:
    transformations = {t.get("NAME"): _transformation(t) for t in node.kids("TRANSFORMATION")}
    instances = {i.get("NAME"): Instance(i.get("NAME"), i.get("TYPE"), i.get("TRANSFORMATION_NAME"), i.get("DBDNAME", ""),
                                         _attributes(i), i.line)
                 for i in node.kids("INSTANCE")}
    connectors = [Connector(c.get("FROMINSTANCE"), c.get("FROMFIELD"), c.get("TOINSTANCE"), c.get("TOFIELD"), c.line)
                  for c in node.kids("CONNECTOR")]
    variables = {v.get("NAME").upper(): MappingVariable(v.get("NAME"), v.get("DATATYPE", ""), v.get("DEFAULTVALUE", "") or "",
                                                       v.get("ISPARAM") == "YES", v.line)
                 for v in node.kids("MAPPINGVARIABLE")}
    return Mapping(node.get("NAME"), transformations, instances, connectors, node.line, node.end, variables)


def parse_file(path: str | Path) -> Folder:
    root = read_tree(path)
    folder = next(root.iter("FOLDER"))
    sources = {(s.get("DBDNAME", ""), s.get("NAME")): _table(s, "SOURCEFIELD") for s in folder.kids("SOURCE")}
    targets = {t.get("NAME"): _table(t, "TARGETFIELD") for t in folder.kids("TARGET")}
    mappings = {m.get("NAME"): _mapping(m) for m in folder.kids("MAPPING")}
    return Folder(folder.get("NAME"), sources, targets, mappings, root)
