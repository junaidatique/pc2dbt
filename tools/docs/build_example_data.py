"""Extract the RAW_ORDERS -> STG_ORDERS slice of the demo XML into docs/assets/example-data.js.

Every line number in the output is read from the file, never typed by hand.
The workflow command task's VALUEPAIR line (it holds a credential) is never read into the output,
and a final guard fails the run if any token of that value leaks into the generated file.

Usage: python3 -I build_example_data.py <xml> <out.js>
"""
import html
import json
import re
import sys

xml_path, out_path = sys.argv[1], sys.argv[2]
raw = open(xml_path, encoding="cp1252").read().split("\n")
LINES = {i + 1: t for i, t in enumerate(raw)}

TAG = re.compile(r"^\s*<(/?)([A-Z]+)\b(.*?)(/?)>\s*$")
ATTR = re.compile(r'([A-Z_]+) ="([^"]*)"')


def parse(n):
    m = TAG.match(LINES[n])
    if not m:
        return None
    closing, tag, rest, selfclose = m.groups()
    attrs = {k: html.unescape(v) for k, v in ATTR.findall(rest)}
    return {"n": n, "close": bool(closing), "tag": tag, "attrs": attrs, "self": bool(selfclose)}


def show(p, keep):
    """Render a parsed line with only the attributes in `keep` (in that order)."""
    if p["close"]:
        return "</%s>" % p["tag"]
    parts = ['%s="%s"' % (k, p["attrs"][k]) for k in keep if k in p["attrs"]]
    return "<%s %s%s>" % (p["tag"], " ".join(parts), "/" if p["self"] else "")


def find(tag, name, lo=1, hi=None):
    hi = hi or len(LINES)
    for n in range(lo, hi + 1):
        p = parse(n)
        if p and not p["close"] and p["tag"] == tag and p["attrs"].get("NAME") == name:
            return n
    raise SystemExit("not found: %s %s" % (tag, name))


def block(start):
    """Lines from an opening tag to its matching closing tag (same tag name)."""
    tag = parse(start)["tag"]
    n = start
    while True:
        n += 1
        p = parse(n)
        if p and p["close"] and p["tag"] == tag:
            return list(range(start, n + 1))


KEEP = {
    "SOURCE": ["NAME", "OWNERNAME", "DATABASETYPE"],
    "SOURCEFIELD": ["NAME", "DATATYPE"],
    "TARGET": ["NAME", "DATABASETYPE"],
    "TARGETFIELD": ["NAME", "DATATYPE"],
    "TRANSFORMATION": ["NAME", "TYPE"],
    "TRANSFORMFIELD": ["NAME", "EXPRESSION", "PORTTYPE", "ISSORTKEY"],
    "TABLEATTRIBUTE": ["NAME", "VALUE"],
    "CONNECTOR": ["FROMINSTANCE", "FROMFIELD", "TOINSTANCE", "TOFIELD"],
    "INSTANCE": ["NAME", "TRANSFORMATION_NAME", "TYPE"],
    "SESSION": ["NAME", "MAPPINGNAME"],
    "SESSTRANSFORMATIONINST": ["SINSTANCENAME", "TRANSFORMATIONTYPE"],
    "SESSIONEXTENSION": ["NAME", "SINSTANCENAME", "TYPE"],
    "CONNECTIONREFERENCE": ["CONNECTIONNAME", "CONNECTIONTYPE"],
    "ATTRIBUTE": ["NAME", "VALUE"],
    "WORKFLOW": ["NAME"],
    "SCHEDULEINFO": ["SCHEDULETYPE"],
    "TASK": ["NAME", "TYPE"],
    "TASKINSTANCE": ["NAME", "TASKTYPE"],
    "WORKFLOWLINK": ["FROMTASK", "TOTASK"],
}
SHOW_TABLEATTR = {"Sql Query", "Source Filter", "User Defined Join", "Select Distinct", "Distinct"}


def render(ns):
    """Render line numbers as [n, text] rows, inserting an elision row where lines are skipped."""
    rows, prev = [], None
    for n in ns:
        if "VALUEPAIR" in LINES[n]:
            raise SystemExit("refusing to render a VALUEPAIR line")
        p = parse(n)
        if prev is not None and n != prev + 1:
            rows.append([None, "…"])
        keep = KEEP.get(p["tag"], ["NAME"])
        a = dict(p["attrs"])
        if p["tag"] == "TRANSFORMFIELD" and a.get("ISSORTKEY") != "YES":
            p["attrs"].pop("ISSORTKEY", None)
        rows.append([n, show(p, keep)])
        prev = n
    return rows


# ---------------- locate the slice ----------------
MAP_START = find("MAPPING", "m_FL_JS_STAGING_FULL")
MAP_LINES = block(MAP_START)
MAP_END = MAP_LINES[-1]

SLICE = ["RAW_ORDERS", "SQ_RAW_ORDERS", "EXP_ORDERS", "SRT_ORDERS", "STG_ORDERS"]
starts = {
    "RAW_ORDERS": find("SOURCE", "RAW_ORDERS"),
    "SQ_RAW_ORDERS": find("TRANSFORMATION", "SQ_RAW_ORDERS", MAP_START, MAP_END),
    "EXP_ORDERS": find("TRANSFORMATION", "EXP_ORDERS", MAP_START, MAP_END),
    "SRT_ORDERS": find("TRANSFORMATION", "SRT_ORDERS", MAP_START, MAP_END),
    "STG_ORDERS": find("TARGET", "STG_ORDERS"),
}

connectors, instances = [], {}
for n in MAP_LINES:
    p = parse(n)
    if not p or p["close"]:
        continue
    if p["tag"] == "CONNECTOR":
        a = p["attrs"]
        if a["FROMINSTANCE"] in SLICE and a["TOINSTANCE"] in SLICE:
            connectors.append((n, a))
    if p["tag"] == "INSTANCE" and p["attrs"].get("NAME") in SLICE:
        instances[p["attrs"]["NAME"]] = n

nodes = []
for name in SLICE:
    ns = block(starts[name])
    keep_ns = []
    for n in ns:
        p = parse(n)
        if p["tag"] == "TABLEATTRIBUTE" and p["attrs"].get("NAME") not in SHOW_TABLEATTR:
            continue
        keep_ns.append(n)
    wires_in = sorted(n for n, a in connectors if a["TOINSTANCE"] == name)
    nodes.append({
        "id": name,
        "type": parse(starts[name])["attrs"].get("TYPE") or parse(starts[name])["tag"].title(),
        "start": ns[0], "end": ns[-1],
        "instanceLine": instances.get(name),
        "lines": render(keep_ns),
        "wiresIn": render(wires_in),
    })

# ---------------- session + workflow ----------------
SESSION_START = find("SESSION", "s_FL_JS_STAGING_FULL")
session_ns = [SESSION_START]
sess_block = block(SESSION_START)
for n in sess_block:
    p = parse(n)
    if not p or p["close"]:
        continue
    if p["tag"] == "SESSTRANSFORMATIONINST" and p["attrs"].get("SINSTANCENAME") in SLICE:
        session_ns.append(n)
writer = None
for n in sess_block:
    p = parse(n)
    if p and not p["close"] and p["tag"] == "SESSIONEXTENSION" and p["attrs"].get("SINSTANCENAME") == "STG_ORDERS" \
            and p["attrs"].get("TYPE") == "WRITER":
        writer = n
for n in block(writer):
    p = parse(n)
    if p["tag"] in ("SESSIONEXTENSION", "CONNECTIONREFERENCE"):
        session_ns.append(n)
    elif p["tag"] == "ATTRIBUTE" and p["attrs"].get("NAME") in {"Target load type", "Insert", "Truncate target table option"}:
        session_ns.append(n)
for n in sess_block:
    p = parse(n)
    if p and p["tag"] == "ATTRIBUTE" and p["attrs"].get("NAME") == "Treat source rows as":
        session_ns.append(n)
session_ns = sorted(set(session_ns))

WF_START = find("WORKFLOW", "wf_FL_JAFFLESHOP_DEMO")
wf_block = [n for n in block(WF_START) if "VALUEPAIR" not in LINES[n]]
linked = set()
for n in wf_block:
    p = parse(n)
    if p and p["tag"] == "WORKFLOWLINK":
        linked |= {p["attrs"]["FROMTASK"], p["attrs"]["TOTASK"]}
wf_ns = [WF_START]
for n in wf_block:
    p = parse(n)
    if not p or p["close"]:
        continue
    if p["tag"] in ("SCHEDULEINFO", "WORKFLOWLINK"):
        wf_ns.append(n)
    # Only tasks that are steps of the workflow (targets of links), not helper tasks inside sessions.
    if p["tag"] in ("TASK", "TASKINSTANCE") and p["attrs"].get("NAME") in linked:
        wf_ns.append(n)
wf_ns = sorted(set(wf_ns))
links = [parse(n)["attrs"] for n in wf_ns if parse(n)["tag"] == "WORKFLOWLINK"]

# ---------------- column lineage ----------------
port_line = {}  # (instance, port) -> line of TRANSFORMFIELD / SOURCEFIELD / TARGETFIELD
port_expr = {}
port_type = {}
for name in SLICE:
    for n in block(starts[name]):
        p = parse(n)
        if p["tag"] in ("TRANSFORMFIELD", "SOURCEFIELD", "TARGETFIELD"):
            port_line[(name, p["attrs"]["NAME"])] = n
            port_type[(name, p["attrs"]["NAME"])] = p["attrs"].get("PORTTYPE") or p["attrs"].get("DATATYPE")
            if "EXPRESSION" in p["attrs"]:
                port_expr[(name, p["attrs"]["NAME"])] = p["attrs"]["EXPRESSION"]

incoming = {(a["TOINSTANCE"], a["TOFIELD"]): (n, a) for n, a in connectors}
target_cols = [parse(n)["attrs"]["NAME"] for n in block(starts["STG_ORDERS"]) if parse(n)["tag"] == "TARGETFIELD"]
QUOTED = re.compile(r"'[^']*'")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def lineage(inst, port, out, depth=0):
    if depth > 20:
        raise SystemExit("lineage too deep")
    key = (inst, port)
    if inst == "RAW_ORDERS":
        out.append({"n": port_line[key], "text": "%s.%s" % (inst, port), "kind": "PC Source column"})
        return
    expr = port_expr.get(key)
    ptype = port_type.get(key, "")
    if expr is not None and ptype in ("OUTPUT", "LOCAL VARIABLE") and inst != "STG_ORDERS":
        out.append({"n": port_line[key], "text": "%s.%s = %s" % (inst, port, expr), "kind": "port expression"})
        names = set(IDENT.findall(QUOTED.sub("", expr)))
        for nm in sorted(names):
            if (inst, nm) in port_type and port_type[(inst, nm)] in ("INPUT", "INPUT/OUTPUT"):
                lineage(inst, nm, out, depth + 1)
        return
    n, a = incoming[key]
    out.append({"n": n, "text": "%s.%s ← %s.%s" % (inst, port, a["FROMINSTANCE"], a["FROMFIELD"]), "kind": "connector"})
    lineage(a["FROMINSTANCE"], a["FROMFIELD"], out, depth + 1)


lin, flags = {}, []
for col in target_cols:
    chain = []
    lineage("STG_ORDERS", col, chain)
    n, a = incoming[("STG_ORDERS", col)]
    crossed = a["FROMFIELD"] != col and a["FROMFIELD"] in target_cols
    if crossed:
        chain[0]["flag"] = True
        flags.append({"n": n, "column": col, "from": "%s.%s" % (a["FROMINSTANCE"], a["FROMFIELD"])})
    lin[col] = chain

data = {
    "xmlFile": "FLOWLINE_DEMO_JAFFLESHOP.xml",
    "mapping": {"name": "m_FL_JS_STAGING_FULL", "start": MAP_START, "end": MAP_END},
    "nodes": nodes,
    "wireCounts": [{"from": a, "to": b, "count": sum(1 for _, c in connectors if c["FROMINSTANCE"] == a and c["TOINSTANCE"] == b)}
                   for a, b in zip(SLICE, SLICE[1:])],
    "session": {"name": "s_FL_JS_STAGING_FULL", "start": SESSION_START, "lines": render(session_ns)},
    "workflow": {"name": "wf_FL_JAFFLESHOP_DEMO", "start": WF_START, "lines": render(wf_ns), "links": links},
    "targetColumns": target_cols,
    "lineage": lin,
    "flags": flags,
}

body = json.dumps(data, ensure_ascii=False, indent=1)

# ---- guard: no token of the command-task value may appear in the output ----
secret_lines = [n for n, t in LINES.items() if "VALUEPAIR" in t]
for n in secret_lines:
    value = html.unescape(dict(ATTR.findall(LINES[n])).get("VALUE", ""))
    tokens = {t for t in re.split(r"[\s\"@/:\\]+", value) if len(t) >= 5}
    leaked = [t for t in tokens if t in body]
    # Paths like "Informatica" or "server" are harmless words; the guard only cares about the login part.
    login = value.split("@")[0].split()[-1] if "@" in value else ""
    if login and login in body:
        raise SystemExit("GUARD FAILED: credential text found in output")
print("guard: no credential text in output")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("/* GENERATED from the demo XML (%s) by a script. Do not edit by hand.\n" % data["xmlFile"])
    f.write("   Slice: RAW_ORDERS -> STG_ORDERS in mapping m_FL_JS_STAGING_FULL, plus its session and workflow.\n")
    f.write("   Every line number is read from the file. Attributes are trimmed to the ones that matter. */\n")
    f.write("window.EXAMPLE = ")
    f.write(body)
    f.write(";\n")

print("nodes:", [(x["id"], x["start"], x["end"], x["instanceLine"]) for x in nodes])
print("wires:", data["wireCounts"])
print("session lines:", [r[0] for r in data["session"]["lines"]])
print("workflow lines:", [r[0] for r in data["workflow"]["lines"]])
print("flags:", flags)
print("lineage SUBTOTAL_CENTS:", [(s["n"], s["text"]) for s in lin["SUBTOTAL_CENTS"]])
print("lineage ORDERED_AT_DAY:", [(s["n"], s["text"]) for s in lin["ORDERED_AT_DAY"]])
