"""Line-aware reader for a PowerCenter XML export.

Every element keeps its start and end line, so facts can cite real line numbers.
VALUEPAIR elements (where the demo's command task keeps a plaintext credential)
are kept as empty nodes: their attributes are dropped at parse time and never
reach any caller.
"""
import re
import xml.parsers.expat

REDACT_TAGS = {"VALUEPAIR"}


class Node:
    __slots__ = ("tag", "a", "start", "end", "children", "parent")

    def __init__(self, tag, a, start, parent):
        self.tag, self.a, self.start, self.end = tag, a, start, start
        self.children, self.parent = [], parent

    def get(self, k, d=None):
        return self.a.get(k, d)

    def kids(self, tag=None):
        return [c for c in self.children if tag is None or c.tag == tag]

    def iter(self, tag=None):
        if tag is None or self.tag == tag:
            yield self
        for c in self.children:
            yield from c.iter(tag)

    def attrs_table(self, child="TABLEATTRIBUTE"):
        return {c.get("NAME"): (c.get("VALUE"), c.start) for c in self.kids(child)}

    def __repr__(self):
        return f"<{self.tag} {self.get('NAME', '')} L{self.start}-{self.end}>"


def parse(path):
    data = open(path, "rb").read()
    p = xml.parsers.expat.ParserCreate()
    root = Node("#doc", {}, 1, None)
    stack = [root]

    def start(tag, attrs):
        line = p.CurrentLineNumber
        n = Node(tag, {} if tag in REDACT_TAGS else dict(attrs), line, stack[-1])
        stack[-1].children.append(n)
        stack.append(n)

    def end(tag):
        stack.pop().end = p.CurrentLineNumber

    p.StartElementHandler, p.EndElementHandler = start, end
    # The export declares a DTD (powrmart.dtd) that is not shipped; ignore it.
    p.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    p.Parse(data, True)
    return root.children[0]


def secret_tokens(path):
    """Tokens that appear only on credential lines, for output guards. Never print these."""
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    sec = [l for l in lines if "VALUEPAIR" in l]
    rest = "\n".join(l for l in lines if "VALUEPAIR" not in l)
    return {t for l in sec for t in re.findall(r"[^\s\"'=;&]{6,}", l) if t not in rest}
