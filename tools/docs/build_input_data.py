"""Build docs/assets/input-data.js for the Input XML page.

Everything structural is read from the XML. Problem texts are written by hand, and every
fact they state is asserted against the XML below, so the script stops if a claim is false.
Seed-data numbers (from jaffle-shop's seeds in DuckDB) are passed in as constants and were
measured separately; they are labelled as such on the page.

Usage: python3 -I build_input_data.py <xml> <out.js>
"""
import json
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pcxml import parse, secret_tokens  # noqa: E402

XML, OUT = sys.argv[1], sys.argv[2]
root = parse(XML)
rep = root.kids("REPOSITORY")[0]
folder = rep.kids("FOLDER")[0]
maps = folder.kids("MAPPING")
M = {m.get("NAME"): m for m in maps}
wf = folder.kids("WORKFLOW")[0]
n_lines = len(open(XML, encoding="utf-8", errors="replace").read().splitlines())

src_defs = folder.kids("SOURCE")
tgt_defs = folder.kids("TARGET")
SRC = {(s.get("DBDNAME"), s.get("NAME")): s for s in src_defs}
TGT = {t.get("NAME"): t for t in tgt_defs}

STAGE = {"m_FL_JS_STAGING_FULL": "staging", "m_FL_JS_MARTS_CORE": "core marts",
         "m_FL_JS_MARTS_ENRICHED": "enriched marts"}
TERM = {"Source Qualifier": "source-qualifier", "Expression": "expression-tx", "Joiner": "joiner",
        "Sorter": "sorter", "Aggregator": "aggregator", "Router": "router",
        "Custom Transformation": "union", "Filter": "filter"}
TYPE_LABEL = {"Custom Transformation": "Union"}
PT = {"INPUT": "in", "OUTPUT": "out", "INPUT/OUTPUT": "in/out", "LOCAL VARIABLE": "variable",
      "INPUT/OUTPUT/MASTER": "in/out (master)", "INPUT/MASTER": "in (master)"}


def L(a, b=None):
    return f"L{a}" if b is None or a == b else f"L{a}–{b}"


def dtype(p):
    d, pr, sc = p.get("DATATYPE"), p.get("PRECISION"), p.get("SCALE")
    if d in ("date/time", "date", "timestamp", "integer", "double", "small integer", "bigint"):
        return d
    return f"{d}({pr},{sc})" if sc and sc != "0" else f"{d}({pr})"


def tr_def(m, inst):
    return next(x for x in m.kids("TRANSFORMATION") if x.get("NAME") == inst.get("TRANSFORMATION_NAME"))


def node(id_, tag, name, lines, what, term=None, facts=None, chips=None, kids=None, table=None, note=None):
    n = {"id": id_, "tag": tag, "name": name, "lines": list(lines), "what": what}
    if term: n["term"] = term
    if facts: n["facts"] = facts
    if chips: n["chips"] = chips
    if kids: n["kids"] = kids
    if table: n["table"] = table
    if note: n["note"] = note
    return n


def group(id_, name, what, kids, term=None, chips=None, lines=None):
    g = {"id": id_, "tag": "", "name": name, "what": what, "kids": kids, "group": True}
    if term: g["term"] = term
    if chips: g["chips"] = chips
    if lines: g["lines"] = list(lines)
    return g


# ---------------------------------------------------------------- who reads / writes what
reads, writes = defaultdict(set), defaultdict(set)
for m in maps:
    for i in m.kids("INSTANCE"):
        if i.get("TYPE") == "SOURCE":
            reads[(i.get("DBDNAME"), i.get("TRANSFORMATION_NAME"))].add(m.get("NAME"))
        if i.get("TYPE") == "TARGET":
            writes[i.get("TRANSFORMATION_NAME")].add(m.get("NAME"))
pre_sql = {}
for m in maps:
    for i in m.kids("INSTANCE"):
        for a in i.kids("TABLEATTRIBUTE"):
            if a.get("NAME") == "Pre SQL" and a.get("VALUE"):
                pre_sql[i.get("TRANSFORMATION_NAME")] = (a.get("VALUE"), a.start)


def col_table(fields):
    return {"cols": ["Column", "Type", "Key", "Line"],
            "rows": [[f.get("NAME"), dtype(f), "" if f.get("KEYTYPE") in (None, "NOT A KEY") else f.get("KEYTYPE").lower(),
                      L(f.start)] for f in fields]}


# ---------------------------------------------------------------- PC Sources
def src_node(s):
    k = (s.get("DBDNAME"), s.get("NAME"))
    fs = s.kids("SOURCEFIELD")
    by = sorted(reads[k])
    return node(f"src-{s.get('OWNERNAME')}-{s.get('NAME')}", "SOURCE", s.get("NAME"), (s.start, s.end),
                f"Read by {', '.join('`'+b+'`' for b in by)}.",
                facts=[["Database (DBD)", f"`{s.get('DBDNAME')}`"], ["Schema (owner)", f"`{s.get('OWNERNAME')}`"],
                       ["Columns", str(len(fs))]],
                chips=[f"{len(fs)} columns"], table=col_table(fs))


raw_src = [s for s in src_defs if s.get("OWNERNAME") == "RAW"]
stg_src = [s for s in src_defs if s.get("OWNERNAME") == "STG"]
assert len(raw_src) == 6 and len(stg_src) == 6
sources = group("sources", f"PC Sources ({len(src_defs)})",
                "Tables PowerCenter reads from. Each is a description (name, schema, columns), not data.",
                [group("sources-raw", f"Raw tables ({len(raw_src)})",
                       "The input data, in schema RAW. Nothing in this file writes them.",
                       [src_node(s) for s in raw_src], chips=[L(raw_src[0].start, raw_src[-1].end)],
                       lines=(raw_src[0].start, raw_src[-1].end)),
                 group("sources-stg", f"Staging tables, read again ({len(stg_src)})",
                       "The same 6 staging tables the first mapping writes. They are described a second time as sources so the mart mappings can read them.",
                       [src_node(s) for s in stg_src], chips=[L(stg_src[0].start, stg_src[-1].end)],
                       lines=(stg_src[0].start, stg_src[-1].end))],
                term="pc-source", chips=[f"{len(src_defs)} tables"])


# ---------------------------------------------------------------- PC Targets
def tgt_node(t):
    fs = t.kids("TARGETFIELD")
    by = sorted(writes[t.get("NAME")])
    facts = [["Written by", ", ".join(f"`{b}`" for b in by)], ["Columns", str(len(fs))]]
    if t.get("NAME") in pre_sql:
        v, ln = pre_sql[t.get("NAME")]
        facts.append(["Emptied first by", f"Pre SQL `{v}` ({L(ln)})"])
    return node(f"tgt-{t.get('NAME')}", "TARGET", t.get("NAME"), (t.start, t.end),
                f"Written by {', '.join('`'+b+'`' for b in by)}.", facts=facts,
                chips=[f"{len(fs)} columns"], table=col_table(fs))


tgroups = defaultdict(list)
for t in tgt_defs:
    tgroups[STAGE[sorted(writes[t.get("NAME")])[0]]].append(t)
targets = group("targets", f"PC Targets ({len(tgt_defs)})",
                "Tables the mappings write to.",
                [group(f"targets-{k.split()[0]}", f"{k.capitalize()} ({len(v)})",
                       {"staging": "Cleaned and renamed copies of the raw tables, in schema STG.",
                        "core marts": "The business tables, in schema MART. Each has a twin in jaffle-shop.",
                        "enriched marts": "Extra tables in schema MART. No twin in jaffle-shop."}[k],
                       [tgt_node(t) for t in v], lines=(v[0].start, v[-1].end))
                 for k, v in sorted(tgroups.items(), key=lambda kv: ["staging", "core marts", "enriched marts"].index(kv[0]))],
                term="pc-target", chips=[f"{len(tgt_defs)} tables"])


# ---------------------------------------------------------------- Mappings
def tx_facts(t):
    ta = {a.get("NAME"): (a.get("VALUE"), a.start) for a in t.kids("TABLEATTRIBUTE")}
    f = []
    ty = t.get("TYPE")
    if ty == "Joiner":
        f += [["Join type", f"{ta['Join Type'][0]} ({L(ta['Join Type'][1])})"],
              ["Condition", f"`{ta['Join Condition'][0]}` ({L(ta['Join Condition'][1])})"]]
    if ty == "Filter":
        f += [["Keeps rows where", f"`{ta['Filter Condition'][0]}` ({L(ta['Filter Condition'][1])})"]]
    if ty == "Sorter":
        keys = [p.get("NAME") for p in t.kids("TRANSFORMFIELD") if p.get("ISSORTKEY") == "YES"]
        f += [["Sort keys", ", ".join(f"`{k}`" for k in keys)],
              ["Removes duplicates", f"{ta['Distinct'][0]} ({L(ta['Distinct'][1])})"]]
    if ty == "Aggregator":
        gb = [p.get("NAME") for p in t.kids("TRANSFORMFIELD") if p.get("EXPRESSIONTYPE") == "GROUPBY"]
        f += [["Group by", ", ".join(f"`{k}`" for k in gb)]]
    if ty == "Router":
        for g in t.kids("GROUP"):
            if g.get("TYPE") == "OUTPUT":
                f.append([f"Group {g.get('NAME')}", f"`{(g.get('EXPRESSION') or '').strip()}` ({L(g.start)})"])
            elif g.get("TYPE") == "OUTPUT/DEFAULT":
                f.append([f"Group {g.get('NAME')}", f"rows that match no group ({L(g.start)})"])
    if ty == "Custom Transformation":
        ins = [g.get("NAME") for g in t.kids("GROUP") if g.get("TYPE") == "INPUT"]
        f += [["Input groups", ", ".join(f"`{x}`" for x in ins)]]
    return f


def mapping_node(m):
    name = m.get("NAME")
    insts = m.kids("INSTANCE")
    conns = m.kids("CONNECTOR")
    txs = m.kids("TRANSFORMATION")
    I = {i.get("NAME"): i for i in insts}
    fed_by, feeds = defaultdict(set), defaultdict(set)
    for c in conns:
        fed_by[c.get("TOINSTANCE")].add(c.get("FROMINSTANCE"))
        feeds[c.get("FROMINSTANCE")].add(c.get("TOINSTANCE"))
    by_type = defaultdict(list)
    for t in txs:
        by_type[t.get("TYPE")].append(t)
    tx_groups = []
    for ty, lst in sorted(by_type.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        kids = []
        for t in lst:
            ps = t.kids("TRANSFORMFIELD")
            facts = tx_facts(t)
            facts += [["Fed by", ", ".join(f"`{x}`" for x in sorted(fed_by[t.get("NAME")])) or "nothing"],
                      ["Feeds", ", ".join(f"`{x}`" for x in sorted(feeds[t.get("NAME")])) or "nothing"]]
            rows = [[p.get("NAME"), PT.get(p.get("PORTTYPE"), p.get("PORTTYPE")), dtype(p),
                     (p.get("EXPRESSION") or "").replace("\r\n", " ").replace("\n", " ") if p.get("EXPRESSION") != p.get("NAME") else "",
                     L(p.start)] for p in ps]
            kids.append(node(f"tx-{name}-{t.get('NAME')}", "TRANSFORMATION", t.get("NAME"), (t.start, t.end),
                             f"{TYPE_LABEL.get(ty, ty)} with {len(ps)} ports.", term=TERM.get(ty), facts=facts,
                             chips=[f"{len(ps)} ports"],
                             table={"cols": ["Port", "Kind", "Type", "Expression (blank = same name)", "Line"], "rows": rows}))
        tx_groups.append(group(f"txg-{name}-{ty}", f"{TYPE_LABEL.get(ty, ty)} ({len(lst)})", "", kids, term=TERM.get(ty)))
    it = Counter(i.get("TYPE") for i in insts)
    inst_rows = [[i.get("NAME"), {"SOURCE": "PC Source", "TARGET": "PC Target"}.get(i.get("TYPE"), i.get("TRANSFORMATION_TYPE")),
                  i.get("TRANSFORMATION_NAME") if i.get("TRANSFORMATION_NAME") != i.get("NAME") else "", L(i.start)] for i in insts]
    reads_ = sorted({i.get("TRANSFORMATION_NAME") for i in insts if i.get("TYPE") == "SOURCE"})
    writes_ = [I[t.get("TARGETINSTANCE")].get("TRANSFORMATION_NAME") for t in sorted(m.kids("TARGETLOADORDER"), key=lambda t: int(t.get("ORDER")))]
    renamed = [c for c in conns if c.get("FROMFIELD") != c.get("TOFIELD")]
    kids = [
        group(f"txs-{name}", f"Transformations ({len(txs)})",
              "The boxes, grouped by type. Open one to see its ports and formulas.", tx_groups,
              term="transformation", lines=(txs[0].start, txs[-1].end)),
        node(f"inst-{name}", "INSTANCE", f"Instances ({len(insts)})", (insts[0].start, insts[-1].end),
             "Every box placed in this mapping, including its sources and targets. Connectors join instances. A number suffix (STG_ORDERS1) means the same table is used again.",
             term="instance", chips=[f"{it['SOURCE']} sources", f"{it['TARGET']} targets", f"{it['TRANSFORMATION']} transformations"],
             table={"cols": ["Instance", "Kind", "Definition (if different)", "Line"], "rows": inst_rows}),
        node(f"conn-{name}", "CONNECTOR", f"Connectors ({len(conns)})", (conns[0].start, conns[-1].end),
             f"The wires. Each copies one column from one instance to the next. {len(renamed)} of them change the column name on the way.",
             term="connector", chips=[f"{len(conns)} wires", f"{len(renamed)} rename"]),
        node(f"tlo-{name}", "TARGETLOADORDER", f"Target load order ({len(writes_)})",
             (m.kids("TARGETLOADORDER")[0].start, m.kids("TARGETLOADORDER")[-1].end),
             "The order this mapping fills its targets in: " + " → ".join(f"`{w}`" for w in writes_) + ".",
             term="target-load-order"),
    ]
    for mv in m.kids("MAPPINGVARIABLE"):
        kids.append(node(f"mv-{name}-{mv.get('NAME')}", "MAPPINGVARIABLE", mv.get("NAME"), (mv.start, mv.end),
                         f"A run parameter, default `{mv.get('DEFAULTVALUE')}`. Used in the recency formulas.",
                         term="mapping-parameter"))
    return node(f"map-{name}", "MAPPING", name, (m.start, m.end),
                f"Builds the {STAGE[name]}: reads {len(reads_)} tables and writes {len(writes_)}.",
                term="mapping",
                facts=[["Reads", ", ".join(f"`{r}`" for r in reads_)], ["Writes", ", ".join(f"`{w}`" for w in sorted(writes_))],
                       ["Valid", m.get("ISVALID")]],
                chips=[f"{len(txs)} transformations", f"{len(conns)} connectors"], kids=kids)


mappings = group("mappings", f"Mappings ({len(maps)})",
                 "The logic. Each mapping is a drawing of boxes (transformations) joined by wires (connectors), from PC Sources to PC Targets.",
                 [mapping_node(m) for m in maps], term="mapping")

# ---------------------------------------------------------------- Config, sessions, workflow
cfg = folder.kids("CONFIG")[0]
config = node("config", "CONFIG", cfg.get("NAME"), (cfg.start, cfg.end),
              f"Default run settings that sessions use (logs, error handling, caches). {len(cfg.kids('ATTRIBUTE'))} settings. None of them changes the SQL.",
              term="session-config")

ti_over = {}
for ti in wf.kids("TASKINSTANCE"):
    for x in ti.kids("SESSIONEXTENSION"):
        for cr in x.kids("CONNECTIONREFERENCE"):
            ti_over[(ti.get("TASKNAME"), x.get("SINSTANCENAME"))] = (cr.get("CONNECTIONNAME"), cr.start)


def session_node(s, where):
    rows = []
    for x in s.kids("SESSIONEXTENSION"):
        if x.get("TYPE") not in ("WRITER", "READER"):
            continue
        crs = x.kids("CONNECTIONREFERENCE")
        if not crs:
            continue
        att = {a.get("NAME"): (a.get("VALUE"), a.start) for a in x.kids("ATTRIBUTE")}
        ov = ti_over.get((s.get("NAME"), x.get("SINSTANCENAME")))
        rows.append([x.get("SINSTANCENAME"), "writes" if x.get("TYPE") == "WRITER" else "reads",
                     f"{crs[0].get('CONNECTIONNAME')} ({L(crs[0].start)})",
                     f"{ov[0]} ({L(ov[1])})" if ov else "",
                     f"{att['Truncate target table option'][0]} ({L(att['Truncate target table option'][1])})" if "Truncate target table option" in att else ""])
    at = {a.get("NAME"): (a.get("VALUE"), a.start) for a in s.kids("ATTRIBUTE")}
    nw = sum(1 for r in rows if r[1] == "writes")
    return node(f"sess-{s.get('NAME')}", "SESSION", s.get("NAME"), (s.start, s.end),
                f"Runs `{s.get('MAPPINGNAME')}`. {where}",
                term="session",
                facts=[["Runs mapping", f"`{s.get('MAPPINGNAME')}`"], ["Reusable", s.get("REUSABLE")],
                       ["Treat source rows as", f"{at['Treat source rows as'][0]} ({L(at['Treat source rows as'][1])})"],
                       ["Commit every", f"{at['Commit Interval'][0]} rows ({L(at['Commit Interval'][1])})"]],
                chips=[f"{nw} targets"],
                table={"cols": ["Instance", "Does", "Connection in the session", "Override in the workflow", "Truncate option"], "rows": rows})


sess_folder = folder.kids("SESSION")
sess_wf = wf.kids("SESSION")
sessions = group("sessions", f"Sessions ({len(sess_folder) + len(sess_wf)})",
                 "A session runs one mapping. It names the database connection for every source and target, and how to load.",
                 [session_node(s, "Defined at folder level, so it is reusable; the workflow places it with a task instance.") for s in sess_folder] +
                 [session_node(s, "Defined inside the workflow, so only this workflow can use it.") for s in sess_wf],
                 term="session")

links = wf.kids("WORKFLOWLINK")
nxt = {l_.get("FROMTASK"): l_ for l_ in links}
chain, cur = ["Start"], "Start"
while cur in nxt:
    cur = nxt[cur].get("TOTASK"); chain.append(cur)
sched = wf.kids("SCHEDULER")[0]
tasks = wf.kids("TASK")
cmd = next(t for t in tasks if t.get("TYPE") == "Command")
wvars = wf.kids("WORKFLOWVARIABLE")
user_vars = [v for v in wvars if v.get("USERDEFINED") == "YES"]
workflow = node("workflow", "WORKFLOW", wf.get("NAME"), (wf.start, wf.end),
                "Runs the sessions in order, then a command.", term="workflow",
                facts=[["Runs on", f"Integration Service `{wf.get('SERVERNAME')}`"],
                       ["Run order", " → ".join(f"`{c}`" for c in chain)]],
                kids=[
                    node("wf-scheduler", "SCHEDULER", sched.get("NAME"), (sched.start, sched.end),
                         f"When the workflow runs: {sched.kids('SCHEDULEINFO')[0].get('SCHEDULETYPE').lower().replace('ondemand', 'on demand (started by hand)')}.",
                         term="scheduler"),
                    group("wf-tasks", f"Tasks ({len(tasks)})", "Steps that are not sessions.", [
                        node(f"task-{t.get('NAME')}", "TASK", t.get("NAME"), (t.start, t.end),
                             "Where every run begins." if t.get("TYPE") == "Start" else
                             "Runs a shell command after the last session. Its command holds a plaintext database password, so this page shows its name only.",
                             term="command-task" if t.get("TYPE") == "Command" else None,
                             chips=[t.get("TYPE")]) for t in tasks]),
                    group("wf-sessions", f"Sessions defined here ({len(sess_wf)})",
                          "Listed under Sessions above.", [], lines=(sess_wf[0].start, sess_wf[-1].end)),
                    node("wf-taskinstances", "TASKINSTANCE", f"Task instances ({len(wf.kids('TASKINSTANCE'))})",
                         (wf.kids("TASKINSTANCE")[0].start, wf.kids("TASKINSTANCE")[-1].end),
                         "Each task placed in the workflow. The one for the staging session overrides its connections.",
                         term="task-instance",
                         table={"cols": ["Instance", "Task type", "Overrides", "Line"],
                                "rows": [[t.get("NAME"), t.get("TASKTYPE"), str(len(t.kids("SESSIONEXTENSION"))) if t.kids("SESSIONEXTENSION") else "",
                                          L(t.start, t.end)] for t in wf.kids("TASKINSTANCE")]}),
                    node("wf-links", "WORKFLOWLINK", f"Links ({len(links)})", (links[0].start, links[-1].end),
                         "The arrows between tasks, so the run order. None has a condition. They are listed out of order in the file.",
                         term="workflow-link",
                         table={"cols": ["From", "To", "Line"], "rows": [[l_.get("FROMTASK"), l_.get("TOTASK"), L(l_.start)] for l_ in links]}),
                    node("wf-vars", "WORKFLOWVARIABLE", f"Variables ({len(wvars)})", (wvars[0].start, wvars[-1].end),
                         f"Built-in run variables like start time and status, {len(wvars) - len(user_vars)} of them, plus {len(user_vars)} user-defined: "
                         + ", ".join(f"`{v.get('NAME')}`" for v in user_vars) + ". The mappings don't use them."),
                ])

tree = node("powermart", "POWERMART", "the export", (root.start, root.end),
            "The wrapper around every PowerCenter export.", term="export",
            facts=[["Exported on", root.get("CREATION_DATE")], ["Repository version", root.get("REPOSITORY_VERSION")]],
            kids=[node("repository", "REPOSITORY", rep.get("NAME"), (rep.start, rep.end),
                       "The PowerCenter store this design was exported from.", term="repository",
                       facts=[["Database type", rep.get("DATABASETYPE")], ["Code page", rep.get("CODEPAGE")]],
                       kids=[node("folder", "FOLDER", folder.get("NAME"), (folder.start, folder.end),
                                  "One project folder. Everything in this file lives here.", term="folder",
                                  facts=[["Owner", folder.get("OWNER")], ["Shared", "yes" if folder.get("SHARED") == "SHARED" else "no"]],
                                  chips=[f"{len(src_defs)} sources", f"{len(tgt_defs)} targets", f"{len(maps)} mappings",
                                         f"{len(sess_folder) + len(sess_wf)} sessions", "1 workflow"],
                                  kids=[sources, targets, mappings, config, sessions, workflow])])])

# ---------------------------------------------------------------- File map
segs, cur_kind = [], None
for c in folder.children:
    if c.tag == "SOURCE":
        k = ("Raw sources", "sources-raw") if c.get("OWNERNAME") == "RAW" else ("Staging sources", "sources-stg")
    elif c.tag == "TARGET":
        k = ("Staging targets", "targets-staging") if "STG" in c.get("NAME") else ("Mart targets", "targets")
    elif c.tag == "MAPPING":
        k = (f"Mapping {c.get('NAME')}", f"map-{c.get('NAME')}")
    elif c.tag == "SESSION":
        k = (f"Session {c.get('NAME')}", f"sess-{c.get('NAME')}")
    elif c.tag == "CONFIG":
        k = ("Session config", "config")
    else:
        k = (f"Workflow {c.get('NAME')}", "workflow")
    if segs and segs[-1]["label"] == k[0]:
        segs[-1]["e"] = c.end
    else:
        segs.append({"s": c.start, "e": c.end, "label": k[0], "node": k[1], "kind": c.tag.lower()})

# ---------------------------------------------------------------- Problems (each fact asserted)
def conn_at(line):
    c = next(c for m in maps for c in m.kids("CONNECTOR") if c.start == line)
    return c.get("FROMFIELD"), c.get("TOINSTANCE"), c.get("TOFIELD")


def field(defn, name):
    return next(f for f in defn.kids("TARGETFIELD") if f.get("NAME") == name)


def port_at(line):
    return next(p for p in folder.iter("TRANSFORMFIELD") if p.start == line)


def attr_at(line):
    return next(a for a in folder.iter() if a.start == line and a.tag in ("TABLEATTRIBUTE", "ATTRIBUTE", "GROUP", "CONNECTIONREFERENCE", "MAPPINGVARIABLE", "SOURCEFIELD"))


# swaps: same-name pairs crossed between one instance and one target
swaps = {(608, 613): "STG_ORDERS", (620, 621): "STG_PRODUCTS", (2480, 2482): "CUSTOMER_360", (2542, 2543): "PRODUCT_DAILY_PERFORMANCE"}
found = []
for m in maps:
    I = {i.get("NAME"): i for i in m.kids("INSTANCE")}
    pairs = defaultdict(dict)
    for c in m.kids("CONNECTOR"):
        pairs[(c.get("FROMINSTANCE"), c.get("TOINSTANCE"))][c.get("FROMFIELD")] = (c.get("TOFIELD"), c.start)
    for (fi, ti), mp in pairs.items():
        tof = {v[0] for v in mp.values()}
        for ff, (tf, ln) in mp.items():
            if ff != tf and ff in tof and re.sub(r"\d+$", "", ff) != re.sub(r"\d+$", "", tf):
                found.append(ln)
expected = [ln for (a, b) in swaps for ln in range(a, b + 1)]
assert sorted(found) == sorted(expected), (sorted(found), expected)
assert conn_at(608) == ("SUBTOTAL", "STG_ORDERS", "SUBTOTAL_CENTS")
assert conn_at(620) == ("PRODUCT_PRICE", "STG_PRODUCTS", "PRODUCT_PRICE_CENTS")
assert [conn_at(x)[0] + ">" + conn_at(x)[2] for x in (2480, 2481, 2482)] == [
    "LIFETIME_SPEND>LIFETIME_SPEND_PRETAX", "LIFETIME_SPEND_PRETAX>LIFETIME_TAX_PAID", "LIFETIME_TAX_PAID>LIFETIME_SPEND"]
assert conn_at(2543) == ("MARGIN_PCT", "PRODUCT_DAILY_PERFORMANCE", "PERISHABLE_SALES_FLAG")
psf = field(TGT["PRODUCT_DAILY_PERFORMANCE"], "PERISHABLE_SALES_FLAG")
assert (psf.start, psf.get("PRECISION"), psf.get("SCALE")) == (1087, "1", "0")
tpc = field(TGT["STG_ORDERS"], "TAX_PAID_CENTS")
assert (tpc.start, tpc.get("SCALE")) == (73, "0")
assert port_at(3534).get("EXPRESSION") == "SUBTOTAL_CENTS/100"
assert port_at(1614).get("EXPRESSION") == "IIF(SUBTOTAL = 0, 0, TAX_PAID / SUBTOTAL)"
assert attr_at(1740).get("EXPRESSION") == "ORDER_TOTAL >= 50"
assert port_at(504).get("EXPRESSION") == "IIF(PERISHABLE = 'Y' OR PERISHABLE = '1', 1, 0)"
assert attr_at(10).get("NAME") == "PERISHABLE" and attr_at(10).get("DATATYPE") == "varchar2"
assert attr_at(3104).get("NAME") == "$$RUN_DATE" and attr_at(3104).get("DEFAULTVALUE") == "12/31/2025 00:00:00"
assert "$$RUN_DATE" in port_at(2300).get("EXPRESSION") and "$$RUN_DATE" in port_at(2318).get("EXPRESSION")
assert port_at(2341).get("EXPRESSION") == "IIF(RECENCY_DAYS<=30,3,IIF(RECENCY_DAYS<=90,2,1))"
assert "CHAMPION" in port_at(2366).get("EXPRESSION") and "LOYAL" in port_at(2366).get("EXPRESSION")
for a, b in ((3588, 3589), (1705, 1706)):
    assert port_at(a).get("NAME") == "v_PREV_CUSTOMER_ID" and port_at(a).get("EXPRESSION") == "CUSTOMER_ID"
    assert port_at(b).get("EXPRESSION") == "IIF(v_PREV_CUSTOMER_ID = CUSTOMER_ID, v_ORDER_SEQUENCE + 1, 1)"
assert conn_at(3790)[1:] == ("ORDERS", "CUSTOMER_ORDER_NUMBER") and conn_at(2496)[2] == "CUSTOMER_ORDER_NUMBER"
assert attr_at(919).get("NAME") == "Truncate target table option" and attr_at(919).get("VALUE") == "NO"
assert attr_at(541).get("VALUE") == "TRUNCATE TABLE STG.STG_ORDERS"
writers = [a for s in sess_folder + sess_wf for x in s.kids("SESSIONEXTENSION") if x.get("TYPE") == "WRITER"
           for a in x.kids("ATTRIBUTE") if a.get("NAME") == "Truncate target table option"]
assert len(writers) == 16 and all(a.get("VALUE") == "NO" for a in writers)
assert len(pre_sql) == 16 and all(v.startswith("TRUNCATE TABLE ") for v, _ in pre_sql.values())
assert attr_at(912).get("CONNECTIONNAME") == "MART_Jaffleshop"
assert ti_over[("s_FL_JS_STAGING_FULL", "STG_ORDERS")] == ("STG_Jaffleshop", 4587)
assert {v[0] for v in ti_over.values()} == {"STG_Jaffleshop", "RAW_Jaffleshop"}
assert attr_at(277).get("TYPE") == "OUTPUT/DEFAULT" and attr_at(1741).get("TYPE") == "OUTPUT/DEFAULT"
for t in (x for m in maps for x in m.kids("TRANSFORMATION") if x.get("TYPE") == "Router"):
    used = {c.get("FROMFIELD") for m in maps for c in m.kids("CONNECTOR") if c.get("FROMINSTANCE") == t.get("NAME")}
    dg = next(g for g in t.kids("GROUP") if g.get("TYPE") == "OUTPUT/DEFAULT")
    assert not any(p.get("GROUP") == dg.get("NAME") and p.get("NAME") in used for p in t.kids("TRANSFORMFIELD"))
assert port_at(236).get("NAME") == "REGION" and "0.15" in port_at(236).get("EXPRESSION")
assert attr_at(276).get("EXPRESSION").endswith("\r\n")
assert port_at(110).get("NAME") == "ORDERED_AT_DAY" and "DD-MM-YY" in port_at(110).get("EXPRESSION")
sorters = [x for m in maps for x in m.kids("TRANSFORMATION") if x.get("TYPE") == "Sorter"]
assert len(sorters) == 15 and all(x.attrs_table()["Distinct"][0] == "NO" for x in sorters)
assert attr_at(1434).get("NAME") == "Distinct"

# columns read but never used, and an unused join key
unused_sq, unused_other = [], []
for m in maps:
    out = {(c.get("FROMINSTANCE"), c.get("FROMFIELD")) for c in m.kids("CONNECTOR")}
    for i in m.kids("INSTANCE"):
        if i.get("TYPE") != "TRANSFORMATION":
            continue
        d = tr_def(m, i)
        if d.get("TYPE") == "Router":
            continue
        for p in d.kids("TRANSFORMFIELD"):
            if "OUTPUT" in p.get("PORTTYPE", "") and (i.get("NAME"), p.get("NAME")) not in out:
                (unused_sq if d.get("TYPE") == "Source Qualifier" else unused_other).append((i.get("NAME"), p.get("NAME"), p.start))
assert len(unused_sq) == 42 and [x[:2] for x in unused_other] == [("JNR_SUPPLIES_PRODUCTS", "SKU1")] and unused_other[0][2] == 485
assert [x[2] for x in unused_sq if x[0] == "SQ_STG_ORDERS" and 1232 <= x[2] <= 1237] == list(range(1232, 1238))

# names reused across mappings
names = defaultdict(list)
for m in maps:
    for t in m.kids("TRANSFORMATION"):
        names[t.get("NAME")].append(t.start)
dup_names = {k: v for k, v in names.items() if len(v) > 1}
assert len(dup_names) == 13 and dup_names["AGG_SUPPLIES_BY_PRODUCT"] == [1441, 3287]

# staging tables defined twice, same columns
for s in stg_src:
    t = TGT[s.get("NAME")]
    assert sorted((f.get("NAME"), f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE")) for f in s.kids("SOURCEFIELD")) == \
        sorted((f.get("NAME"), f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE")) for f in t.kids("TARGETFIELD"))

# forward lineage: which mart columns are computed from swapped staging columns
def fwd(m, inst, fieldname, seen, hits):
    I = {i.get("NAME"): i for i in m.kids("INSTANCE")}
    for c in m.kids("CONNECTOR"):
        if c.get("FROMINSTANCE") != inst or c.get("FROMFIELD") != fieldname:
            continue
        ti, tf = c.get("TOINSTANCE"), c.get("TOFIELD")
        if (ti, tf) in seen:
            continue
        seen.add((ti, tf))
        if I[ti].get("TYPE") == "TARGET":
            hits.add((I[ti].get("TRANSFORMATION_NAME"), tf)); continue
        d = tr_def(m, I[ti]); ps = d.kids("TRANSFORMFIELD")
        todo, done = [tf], set()
        while todo:
            p = todo.pop()
            if p in done:
                continue
            done.add(p)
            pp = next((x for x in ps if x.get("NAME") == p), None)
            if pp is not None and "OUTPUT" in pp.get("PORTTYPE", ""):
                fwd(m, ti, p, seen, hits)
            todo += [x.get("NAME") for x in ps if x.get("NAME") != p and re.search(r"\b" + re.escape(p) + r"\b", x.get("EXPRESSION") or "")]
            if d.get("TYPE") == "Router":
                todo += [x.get("NAME") for x in ps if re.fullmatch(re.escape(p) + r"\d+", x.get("NAME"))]
            if d.get("TYPE") == "Custom Transformation":
                base = re.sub(r"\d+$", "", p)
                todo += [x.get("NAME") for x in ps if x.get("NAME") == base and "OUTPUT" in x.get("PORTTYPE", "")]


swapped_cols = {"STG_ORDERS": ["SUBTOTAL_CENTS", "TAX_PAID_CENTS", "ORDER_TOTAL_CENTS", "SUBTOTAL", "TAX_PAID", "ORDER_TOTAL"],
                "STG_PRODUCTS": ["PRODUCT_PRICE", "PRODUCT_PRICE_CENTS"]}
affected = set()
for m in maps:
    for i in m.kids("INSTANCE"):
        if i.get("TYPE") == "SOURCE" and i.get("TRANSFORMATION_NAME") in swapped_cols:
            for col in swapped_cols[i.get("TRANSFORMATION_NAME")]:
                fwd(m, i.get("NAME"), col, set(), affected)
aff_tables = sorted({t for t, _ in affected})
assert len(affected) == 40 and len(aff_tables) == 9, (len(affected), aff_tables)

# copy-then-compare: a variable copies a port, and a later port compares the copy with that port
stale = []
for m in maps:
    for t in m.kids("TRANSFORMATION"):
        ps = t.kids("TRANSFORMFIELD"); order = [x.get("NAME") for x in ps]
        for i, v in enumerate(ps):
            if v.get("PORTTYPE") != "LOCAL VARIABLE":
                continue
            src = (v.get("EXPRESSION") or "").strip()
            if src not in order or src == v.get("NAME"):
                continue
            for w in ps:
                e = w.get("EXPRESSION") or ""
                if w is not v and re.search(r"\b" + re.escape(v.get("NAME")) + r"\b", e) and re.search(r"\b" + re.escape(src) + r"\b", e):
                    if (w.get("PORTTYPE") == "LOCAL VARIABLE" and order.index(w.get("NAME")) > i) or w.get("PORTTYPE") == "OUTPUT":
                        stale.append((t.get("NAME"), m.get("NAME"), w.start))
assert sorted({(n, w) for n, _, w in stale}) == [("EXP_CUSTOMER_ORDER_NUM", 1706), ("EXP_CUSTOMER_ORDER_NUM", 3589), ("EXP_MARK_FIRST_CUSTOMER", 2127)]
assert [port_at(x).get("NAME") for x in (2124, 2125, 2126)] == ["v_PREV_LOCATION", "v_PREV_DAY", "v_PREV_CUSTOMER"]
assert port_at(2004).get("EXPRESSION") == "SUM(IS_FIRST_CUSTOMER)"
assert conn_at(2549)[1:] == ("STORE_DAILY_KPIS", "UNIQUE_CUSTOMERS")
# sorters that feed those transformations
stateful = {(n, mn) for n, mn, _ in stale}
order_sorters = sorted({(c.get("FROMINSTANCE"), m.get("NAME")) for m in maps for c in m.kids("CONNECTOR")
                        if (c.get("TOINSTANCE"), m.get("NAME")) in stateful and c.get("FROMINSTANCETYPE") == "Sorter"})
srt_line = {(n, mn): next(t.start for t in M[mn].kids("TRANSFORMATION") if t.get("NAME") == n) for n, mn in order_sorters}
assert srt_line == {("SRT_BY_CUSTOMER", "m_FL_JS_MARTS_CORE"): 3554, ("SRT_FOR_CUSTOMER_SEQ", "m_FL_JS_MARTS_ENRICHED"): 1635,
                    ("SRT_FOR_DISTINCT_CUSTOMER", "m_FL_JS_MARTS_ENRICHED"): 2091}, srt_line
# Master Outer joins: which side is master
def side_sources(m, t, master):
    ps = [x.get("NAME") for x in t.kids("TRANSFORMFIELD") if ("MASTER" in x.get("PORTTYPE", "")) == master]
    return {c.get("FROMINSTANCE") for c in m.kids("CONNECTOR") if c.get("TOINSTANCE") == t.get("NAME") and c.get("TOFIELD") in ps}
mo = [(m, t) for m in maps for t in m.kids("TRANSFORMATION") if t.get("TYPE") == "Joiner" and t.attrs_table()["Join Type"][0] == "Master Outer Join"]
assert len(mo) == 10
core, enr = M["m_FL_JS_MARTS_CORE"], M["m_FL_JS_MARTS_ENRICHED"]
def joiner(m, name):
    return next(t for t in m.kids("TRANSFORMATION") if t.get("NAME") == name)
jco = joiner(core, "JNR_CUSTOMERS_ORDERS")
assert jco.start == 3651 and jco.attrs_table()["Join Type"] == ("Master Outer Join", 3664)
assert side_sources(core, jco, True) == {"SQ_STG_CUSTOMERS"} and side_sources(core, jco, False) == {"AGG_ORDERS_BY_CUSTOMER"}
jc = joiner(enr, "JNR_CUSTOMERS")
assert jc.start == 2227 and side_sources(enr, jc, True) == {"SQ_STG_CUSTOMERS1"}
assert port_at(3677).get("EXPRESSION") == "IIF(ISNULL(LIFETIME_ORDERS), 0, LIFETIME_ORDERS)"
assert "'PROSPECT'" in port_at(2366).get("EXPRESSION")
for mm, ln in ((core, 3499), (enr, 1573)):
    j = next(t for t in mm.kids("TRANSFORMATION") if t.start == ln)
    assert j.get("NAME") == "JNR_ORDERS_ITEMS_AGG" and side_sources(mm, j, False) == {"AGG_ITEMS_BY_ORDER"}
jl = joiner(enr, "JNR_ADD_LOCATION_INFO")
assert jl.start == 2061 and side_sources(enr, jl, False) == {"SQ_STG_LOCATIONS1"}
assert attr_at(2385).get("VALUE") == "NOT ISNULL(LOCATION_ID)"
# target instance named differently from its table
renamed_t = [(i.get("NAME"), i.get("TRANSFORMATION_NAME"), i.start) for m in maps for i in m.kids("INSTANCE")
             if i.get("TYPE") == "TARGET" and i.get("NAME") != i.get("TRANSFORMATION_NAME")]
assert renamed_t == [("ORDER_FINANCIALS1", "ORDER_FINANCIALS", 2391)] and TGT["ORDER_FINANCIALS"].start == 1112
assert next(x for x in folder.iter("SESSIONEXTENSION") if x.start == 4466).get("SINSTANCENAME") == "ORDER_FINANCIALS1"

# corrections from the independent check (prompt 7)
for ln, name in ((72, "SUBTOTAL_CENTS"), (56, "PRODUCT_PRICE_CENTS")):
    f_ = next(x for x in folder.iter("TARGETFIELD") if x.start == ln)
    assert f_.get("NAME") == name and f_.get("SCALE") == "0"
assert attr_at(488).get("NAME") == "Join Condition" and attr_at(488).get("VALUE") == "SKU1 = SKU"
assert attr_at(4554).get("NAME") == "Parameter Filename" and attr_at(4554).get("VALUE")
assert [a.get("VALUE") for s_ in sess_folder + sess_wf for a in s_.kids("ATTRIBUTE") if a.get("NAME") == "Parameter Filename" and a.get("VALUE")] == [attr_at(4554).get("VALUE")]
assert port_at(2256).get("EXPRESSION") == "COUNT_LIFETIME_ORDERS_IN" and port_at(2256).get("NAME") == "COUNT_LIFETIME_ORDERS"
assert port_at(2267).get("EXPRESSION") == "IIF(ISNULL(COUNT_LIFETIME_ORDERS_IN),0,COUNT_LIFETIME_ORDERS_IN)"
for t_, c_ in (("ORDER_FINANCIALS", "ORDER_VALUE_BAND"), ("STORE_DAILY_KPIS", "HIGH_VALUE_ORDERS"),
               ("STORE_DAILY_KPIS", "HIGH_VALUE_ORDERS_PCT"), ("CUSTOMER_360", "HIGH_VALUE_ORDERS")):
    assert any(x.get("NAME") == c_ for x in TGT[t_].kids("TARGETFIELD"))

# findings from the blind review (prompt 7), each re-checked
assert port_at(1501).get("EXPRESSION") == "PRODUCT_PRICE" and port_at(1501).get("NAME") == "ITEM_REVENUE"
assert port_at(1513).get("EXPRESSION") == "IIF(PRODUCT_PRICE = 0, 0, (PRODUCT_PRICE - v_SUPPLY_COST_CL) / PRODUCT_PRICE)"
assert port_at(503).get("EXPRESSION") == "COST/100" and conn_at(627) == ("SUPPLY_COST", "STG_SUPPLIES", "SUPPLY_COST")
assert port_at(2190).get("EXPRESSION") == "SUM(ORDER_TOTAL)" and port_at(2343).get("EXPRESSION") == "IIF(LIFETIME_SPEND>=200,3,IIF(LIFETIME_SPEND>=50,2,1))"
wv = next(v for v in wf.kids("WORKFLOWVARIABLE") if v.start == 4677)
assert wv.get("NAME") == "$$wf_run_date" and wv.get("USERDEFINED") == "YES"
assert open(XML, encoding="utf-8", errors="replace").read().count("wf_run_date") == 1
assert [(x.get("FAIL_PARENT_IF_INSTANCE_FAILS"), x.start) for x in wf.kids("TASKINSTANCE") if x.get("TASKTYPE") != "Start"] == [("NO", 4577), ("NO", 4579), ("NO", 4620), ("NO", 4621)]
assert all(l_.get("CONDITION") == "" for l_ in links)
assert [attr_at(x).get("VALUE") for x in (1000, 4285, 4563)] == ["Fail task and continue workflow"] * 3
assert attr_at(793).get("NAME") == "Stop on errors" and attr_at(793).get("VALUE") == "0"
err_in = [(x.start, x.parent.get("NAME"), x.get("NAME")) for x in folder.iter("TRANSFORMFIELD") if "ERROR(" in (x.get("DEFAULTVALUE") or "") and "INPUT" in x.get("PORTTYPE", "")]
assert err_in == [(235, "EXP_LOCATIONS", "TAX_RATE"), (455, "EXP_ORDER_ITEMS", "ORDER_ID")]
assert port_at(503).get("DEFAULTVALUE") == "0" and port_at(504).get("DEFAULTVALUE") == "0"
assert (port_at(3382).get("PRECISION"), port_at(3382).get("SCALE")) == ("10", "0") and (port_at(3291).get("PRECISION"), port_at(3291).get("SCALE")) == ("12", "2")
assert [attr_at(x).get("VALUE") for x in (1007, 4292, 4570)] == ["NO"] * 3 and attr_at(1007).get("NAME") == "Enable high precision"
for t_ in (x for x in folder.iter("TRANSFORMATION") if x.get("NAME") in ("RTR_REGION", "UN_REGIONS")):
    g_ = {x.get("NAME"): x.get("GROUP") for x in t_.kids("TRANSFORMFIELD")}
    assert (g_["REGION2"] == "DEFAULT1") if t_.get("NAME") == "RTR_REGION" else (g_["REGION2"] == "APAC")
assert [attr_at(x).get("VALUE") for x in (1654, 3567)] == ["NO", "NO"] and attr_at(1654).get("NAME") == "Case Sensitive"
assert (attr_at(3571).get("NAME"), attr_at(3571).get("VALUE"), attr_at(1658).get("VALUE")) == ("Null Treated Low", "YES", "NO")
assert port_at(2300).get("EXPRESSION") == port_at(2318).get("EXPRESSION")
assert port_at(1444).get("EXPRESSION") == "MAX(IS_PERISHABLE)"
assert sorted({x.get("TYPE") for x in folder.iter("TRANSFORMATION")}) == ["Aggregator", "Custom Transformation", "Expression", "Filter", "Joiner", "Router", "Sorter", "Source Qualifier"]
assert not list(folder.iter("MAPPLET"))

# extra rows from lookup-side Master Outer joins (prompt 8): check the downstream paths
def reach(m, start):
    down = defaultdict(set)
    for c in m.kids("CONNECTOR"):
        down[c.get("FROMINSTANCE")].add(c.get("TOINSTANCE"))
    seen, todo = set(), [start]
    while todo:
        n = todo.pop()
        for d in down[n]:
            if d not in seen:
                seen.add(d); todo.append(d)
    return seen
lookup_side = [t.get("NAME") for m, t in mo if t.get("NAME") in ("JNR_ADD_CUSTOMERS", "JNR_ADD_LOCATIONS", "JNR_ADD_SUPPLIES",
                                                                   "JNR_ADD_LOCATION_INFO", "JNR_ADD_SUPPLY_COST", "JNR_ITEMS_SUPPLIES")]
assert len(lookup_side) == 6
jal = joiner(enr, "JNR_ADD_LOCATIONS"); jas = joiner(enr, "JNR_ADD_SUPPLIES")
assert jal.start == 1378 and side_sources(enr, jas, True) == {"JNR_ADD_LOCATIONS"} and jas.attrs_table()["Join Condition"][0] == "PRODUCT_ID = PRODUCT_ID1"
def kinds(m, names):
    I_ = {i.get("NAME"): i for i in m.kids("INSTANCE")}
    out = defaultdict(set)
    for n in names:
        i = I_[n]
        out["TARGET" if i.get("TYPE") == "TARGET" else tr_def(m, i).get("TYPE")].add(i.get("TRANSFORMATION_NAME") if i.get("TYPE") == "TARGET" else n)
    return out
k_li = kinds(enr, reach(enr, "JNR_ADD_LOCATION_INFO"))
assert k_li["TARGET"] == {"STORE_DAILY_KPIS"} and k_li["Filter"] == {"FIL_LOCS"} and not k_li["Joiner"]
k_sc = kinds(core, reach(core, "JNR_ADD_SUPPLY_COST"))
assert k_sc["TARGET"] == {"ORDER_ITEMS"} and not k_sc["Joiner"] and not k_sc["Filter"] and not k_sc["Aggregator"]
assert "ORDERS" in kinds(core, reach(core, "JNR_ITEMS_SUPPLIES"))["TARGET"]
assert {"ORDER_ITEM_ENRICHED", "PRODUCT_DAILY_PERFORMANCE"} <= kinds(enr, reach(enr, "JNR_ADD_SUPPLIES"))["TARGET"]

# seed-data measurements (jaffle-shop seeds loaded in DuckDB, measured 2026-11-21)
SEED = {"orders": 61948, "orders_lt_50c": 483, "orders_ge_5000c": 1216, "tax_not_whole": 61296,
        "supplies": 65, "perishable_true": 30, "customers": 935, "orders_no_items": 483, "orders_with_items": 61465,
        "orders_with_items_ge_5000c": 1216, "customers_no_orders": 0, "stores_no_orders": 4,
        "tax_to_zero": 45175, "tax_to_1_6": 16121, "customers_with_itemless_order": 85, "store_days_with_itemless_order": 319,
        "margin_min": "0.9965", "margin_max": "0.9989", "margin_mixed_avg": "0.9979", "margin_intended_avg": "0.7933",
        "m3_dollars": 797, "m2_dollars": 112, "m1_dollars": 26, "at_risk": 929, "standard": 6,
        "order_cost_exact": "131,788.38", "order_cost_rounded": "151,444", "supply_rows": 65, "supply_ids": 29,
        "counter_match": 190, "first_last_changed": 5, "last_order": "31 Aug 2025", "min_recency": 122, "stores": 6, "max_tax_rate": "8%"}
high = SEED["orders"] - SEED["orders_lt_50c"]
assert SEED["orders_lt_50c"] == SEED["orders_no_items"] and SEED["orders_with_items"] == SEED["orders"] - SEED["orders_no_items"]

problems = [
    {"id": "swap", "sev": "wrong", "title": "Columns wired into the wrong target column, in 4 places",
     "body": ["Each time, the port order matches the target's column order but not its names, which suggests the ports were linked by position. So the value lands in a column with another name. Decision D1: we copy this and flag it.",
              "STG_ORDERS L608–613: the 3 dollar values go into the `*_CENTS` columns, and the cents go into the dollar columns.",
              "STG_PRODUCTS L620–621: `PRODUCT_PRICE` and `PRODUCT_PRICE_CENTS` trade places.",
              "CUSTOMER_360 L2480–2482: three columns rotate: spend goes into pretax spend, pretax spend into tax paid, and tax paid into spend.",
              "PRODUCT_DAILY_PERFORMANCE L2542–2543: `MARGIN_PCT` and `PERISHABLE_SALES_FLAG` trade places."],
     "nodes": ["conn-m_FL_JS_STAGING_FULL", "conn-m_FL_JS_MARTS_ENRICHED", "tgt-STG_ORDERS", "tgt-STG_PRODUCTS", "tgt-CUSTOMER_360", "tgt-PRODUCT_DAILY_PERFORMANCE"],
     "earlier": "Before this page we knew only the first one."},
    {"id": "round", "sev": "wrong", "title": "Two of the swaps also lose data in the original database",
     "body": ["The receiving column holds whole numbers only, so the value is rounded. Oracle does this on insert; we have not tested whether PowerCenter converts the value first.",
              f"`MARGIN_PCT` lands in `PERISHABLE_SALES_FLAG`, a NUMBER(1,0) column (L1087), so it becomes 0 or 1. On the seed data every margin is between {SEED['margin_min']} and {SEED['margin_max']}, so the flag is 1 on every row. In return, `MARGIN_PCT` gets the perishable flag, which is 0 on every row if PERISHABLE is read as text (see the perishable rule).",
              f"Tax in dollars lands in `TAX_PAID_CENTS`, a NUMBER(15,0) column (L73). {SEED['tax_not_whole']:,} of {SEED['orders']:,} seed orders have tax that is not a whole dollar: {SEED['tax_to_zero']:,} of them become 0 and {SEED['tax_to_1_6']:,} become 1 to 6.",
              "Two more swapped dollar values land in NUMBER(15,0) columns: `SUBTOTAL_CENTS` (L72) and `PRODUCT_PRICE_CENTS` (L56). They lose nothing today only because every seed subtotal and price is a whole dollar."],
     "earlier": "This first said the tax 'becomes 0'. That is true for most orders, not all.",
     "open": "Open question: should our output also copy the target column types, so the rounding happens in dbt too?",
     "nodes": ["tgt-PRODUCT_DAILY_PERFORMANCE", "tgt-STG_ORDERS"]},
    {"id": "spread", "sev": "wrong", "title": "The staging swaps spread into the marts",
     "body": [f"{len(affected)} columns in {len(aff_tables)} mart tables are computed from swapped staging columns (traced by script).",
              "Example: `ORDERS.SUBTOTAL` is `SUBTOTAL_CENTS/100` (L3534), but STG_ORDERS.SUBTOTAL_CENTS holds dollars, so the result is 100 times too small.",
              "Ratios such as `EFFECTIVE_TAX_RATE = TAX_PAID / SUBTOTAL` (L1614) still come out right, because both sides are off by the same factor.",
              "Four more columns change through the Router's condition rather than the data flow: ORDER_FINANCIALS.ORDER_VALUE_BAND, STORE_DAILY_KPIS.HIGH_VALUE_ORDERS and HIGH_VALUE_ORDERS_PCT, and CUSTOMER_360.HIGH_VALUE_ORDERS (see the dollar rule below).",
              "Check 3 will show many of these columns as different from jaffle-shop."],
     "list": [f"{t}: " + ", ".join(sorted(c for tt, c in affected if tt == t)) for t in aff_tables],
     "nodes": [f"tgt-{t}" for t in aff_tables]},
    {"id": "mixedunits", "sev": "wrong", "by": "review", "title": "Profit and margin subtract dollars from cents",
     "body": ["`ITEM_REVENUE` is `PRODUCT_PRICE` (L1501), which holds cents because of the STG_PRODUCTS swap. The supply cost is in dollars, because STG_SUPPLIES is wired correctly (`COST/100` at L503, connector L627). Profit is then price minus cost (L1513), so every gross profit and margin in the enriched marts mixes the two units.",
              f"On the seed data the item margin averages {SEED['margin_mixed_avg']}; with both in the same unit it would be {SEED['margin_intended_avg']}."],
     "nodes": ["tx-m_FL_JS_MARTS_ENRICHED-EXP_ITEM_CALCULATIONS", "tgt-ORDER_ITEM_ENRICHED", "tgt-PRODUCT_DAILY_PERFORMANCE"]},
    {"id": "counter", "sev": "wrong", "title": "The per-customer order counter never restarts",
     "body": ["PowerCenter works out variable ports top to bottom on each row. `v_PREV_CUSTOMER_ID` is set to the current customer (L3588) before `v_ORDER_SEQUENCE` compares it with the current customer (L3589). So the comparison is always true and the count just keeps going: 1, 2, 3… across all customers.",
              "The intent was clearly a number per customer, like jaffle-shop's `customer_order_number`. The same pair is in the enriched mapping (L1705–1706).",
              "It ends up in `ORDERS.CUSTOMER_ORDER_NUMBER` (L3790) and `ORDER_FINANCIALS.CUSTOMER_ORDER_NUMBER` (L2496). The same mistake breaks the first-customer flag (next).",
              f"On the seed data only {SEED['counter_match']} of {SEED['orders_with_items']:,} numbers match jaffle-shop's per-customer number. Copying the order exactly needs two details: both Sorters ignore case (L1654, L3567), and they place empty customers differently (first in core, L3571; last in enriched, L1658)."],
     "nodes": ["tx-m_FL_JS_MARTS_CORE-EXP_CUSTOMER_ORDER_NUM", "tx-m_FL_JS_MARTS_ENRICHED-EXP_CUSTOMER_ORDER_NUM"],
     "earlier": "My first answer called this 'a running order number per customer'. That is the intent, not what it does."},
    {"id": "firstcustomer", "sev": "wrong", "by": "you", "title": "The first-customer flag is always 0",
     "body": ["The same mistake as the counter. `v_PREV_LOCATION`, `v_PREV_DAY` and `v_PREV_CUSTOMER` are set to the current row (L2124–2126) before `v_IS_FIRST_CUSTOMER` compares them with the current row (L2127). All three always match, so the flag is 0.",
              "So `UNIQUE_CUSTOMERS = SUM(IS_FIRST_CUSTOMER)` (L2004) is 0 for every store and day in STORE_DAILY_KPIS (L2549). Only a row with an empty location, day or customer would get 1, and the seed data has none."],
     "nodes": ["tx-m_FL_JS_MARTS_ENRICHED-EXP_MARK_FIRST_CUSTOMER", "tgt-STORE_DAILY_KPIS"]},
    {"id": "masterouter", "sev": "wrong", "by": "you", "byNote": "You found JNR_CUSTOMERS_ORDERS and asked about extra rows. The agent then checked the other 9 joins and traced where the extra rows go.",
     "title": "All 10 Master Outer joins keep the other side",
     "body": ["A Master Outer join keeps every detail row and drops the master rows that find no match. In all 10 Master Outer joins here, the main table is on the master side, so each one keeps the lookup side instead. The author seems to have read it the other way round.",
              "JNR_CUSTOMERS_ORDERS (L3651, Master Outer at L3664): customers are the master, so a customer with no orders is dropped. Yet `LIFETIME_ORDERS_CL` (L3677) turns a missing order count into 0, which only matters if those customers survive. The author most likely meant Detail Outer. JNR_CUSTOMERS (L2227) does the same for CUSTOMER_360, whose PROSPECT segment (L2366) is meant for customers with no orders. The seed data has no customers without orders, so these counts match today.",
              f"One pair changes counts today. JNR_ORDERS_ITEMS_AGG (L3499 and L1573) keeps only orders that have items. {SEED['orders_no_items']} seed orders have no items, so ORDERS and ORDER_FINANCIALS get {SEED['orders_with_items']:,} rows instead of {SEED['orders']:,}. The same join feeds CUSTOMER_360 and STORE_DAILY_KPIS: {SEED['customers_with_itemless_order']} customers have an order with no items, so their lifetime order count comes out lower, and {SEED['store_days_with_itemless_order']} store-days count fewer orders.",
              "Even a Detail Outer join would not produce PROSPECT customers: COUNT_LIFETIME_ORDERS reaches the test at L2366 as the raw value (L2256), so a customer with no orders has NULL, not 0. The NULL-to-0 version (L2267) is computed but not used for that test.",
              "It can add rows too. Master Outer keeps every detail row, and in 6 of these joins the detail side is a lookup table (customers, locations or supply totals). A lookup row with nothing to match comes through with empty columns.",
              f"On the seed data, the {SEED['stores_no_orders']} stores with no orders create {SEED['stores_no_orders']} extra rows at JNR_ADD_LOCATIONS (L1378) and {SEED['stores_no_orders']} at JNR_ADD_LOCATION_INFO (L2061), but none reaches a table: the next join drops the first set (its product is empty), and the Filter (L2385) drops the second. Every customer and every supplied product has a match, so the other lookup joins add nothing today.",
              "With other data, a product that has supplies but was never sold would add rows with empty IDs to ORDER_ITEMS and ORDERS (core), and to ORDER_ITEM_ENRICHED and PRODUCT_DAILY_PERFORMANCE (enriched). These paths are traced by script; the effect is reasoned, not run."],
     "nodes": [f"tx-{m.get('NAME')}-{t.get('NAME')}" for m, t in mo]},
    {"id": "disagree", "sev": "wrong", "by": "review", "title": "The core and enriched marts disagree with each other",
     "body": ["Both mart mappings compute order amounts and customer totals, and the results don't match.",
              "Order amounts: ORDERS holds the raw cents divided by 10,000 (L3534–3536, on top of the swap), while ORDER_FINANCIALS holds cents. The same order differs by a factor of 10,000.",
              f"Customers: CUSTOMERS.LIFETIME_SPEND is the sum of cents, while CUSTOMER_360.LIFETIME_SPEND holds tax (the rotation), so all {SEED['customers']} differ. Order counts differ for {SEED['customers_with_itemless_order']} customers (only CUSTOMER_360 loses the orders with no items), and first and last order dates for {SEED['first_last_changed']} customers each."],
     "nodes": ["tgt-ORDERS", "tgt-ORDER_FINANCIALS", "tgt-CUSTOMERS", "tgt-CUSTOMER_360"]},
    {"id": "threshold", "sev": "wrong", "title": "Dollar rules applied to cents, in 2 places",
     "body": ["The Router sends an order to HIGH_VALUE when `ORDER_TOTAL >= 50` (L1740). That ORDER_TOTAL comes from STG_ORDERS.ORDER_TOTAL, which holds cents because of the swap.",
              f"So every order that reaches the Router is HIGH: {SEED['orders_with_items']:,} of {SEED['orders_with_items']:,}, and STANDARD stays empty. The {SEED['orders_lt_50c']} orders under 50 cents are exactly the orders with no items, which the join before the Router has already dropped. Read as dollars, {SEED['orders_with_items_ge_5000c']:,} ({SEED['orders_with_items_ge_5000c'] / SEED['orders_with_items']:.1%}) would be HIGH.",
              f"The same happens to the customer score M_SCORE: 3 when LIFETIME_SPEND >= 200, 2 when >= 50 (L2343), but the spend is a sum of cents (L2190). Every one of the {SEED['customers']} customers gets 3; in dollars it would be {SEED['m3_dollars']} / {SEED['m2_dollars']} / {SEED['m1_dollars']}. The independent review found this second place."],
     "nodes": ["tx-m_FL_JS_MARTS_ENRICHED-RTR_ORDER_VALUE_BAND"],
     "earlier": f"This page first said {high:,} of {SEED['orders']:,} orders (99.2%). That counted orders the join drops before the Router."},
    {"id": "perishable", "sev": "wrong", "title": "The perishable rule doesn't match the data",
     "body": ["`IS_PERISHABLE` is 1 when `PERISHABLE = 'Y'` or `'1'` (L504). The XML says the column is text (L10), but the seed data holds True and False.",
              f"Read as text, no supply is perishable (0 of {SEED['supplies']}). DuckDB loads the column as true/false and reads 'Y' and '1' as true, which gives {SEED['perishable_true']} of {SEED['supplies']}. The same rule gives different answers depending on the column type.",
              "Read as text, `HAS_PERISHABLE_SUPPLY` (L1444) is then 0 for every product and every order item."],
     "nodes": ["tx-m_FL_JS_STAGING_FULL-EXP_SUPPLIES", "src-RAW-RAW_SUPPLIES"]},
    {"id": "rundate", "sev": "confusing", "title": "Customer recency depends on a run-date setting",
     "body": ["`$$RUN_DATE` defaults to 12/31/2025 (L3104). Recency is the number of days from it to the customer's last order (L2300, L2318).",
              f"The seed orders end on {SEED['last_order']}, so every customer is at least {SEED['min_recency']} days old and gets R_SCORE 1 (L2341). Nobody can be CHAMPION or LOYAL (L2366), because both need R_SCORE 3.",
              f"The result: {SEED['at_risk']} customers are AT_RISK and {SEED['standard']} are STANDARD.",
              "The enriched session also names a parameter file (L4554) that is not in the demo repo. When PowerCenter runs, that file may set a different date. A workflow variable `$$wf_run_date` (L4677) has the same default but is never used."],
     "earlier": "This first missed the parameter file.",
     "nodes": ["mv-m_FL_JS_MARTS_ENRICHED-$$RUN_DATE"]},
    {"id": "truncate", "sev": "confusing", "title": "'Truncate target = NO', yet every table is emptied first",
     "body": ["All 16 session writers say Truncate target table = NO (for example L919). But every target in the mappings has a Pre SQL that empties it first, like `TRUNCATE TABLE STG.STG_ORDERS` (L541).",
              "So each run fully reloads every table, which is what a dbt table does too. The Pre SQL also hard-codes the schema names STG and MART."],
     "nodes": ["sess-s_FL_JS_STAGING_FULL", "tgt-STG_ORDERS"],
     "earlier": "Open question O3 said PowerCenter adds rows on every run. That missed the Pre SQL."},
    {"id": "connection", "sev": "confusing", "title": "The staging session has two sets of connections",
     "body": ["The reusable session `s_FL_JS_STAGING_FULL` points every source and target at `MART_Jaffleshop` (for example L912).",
              "The workflow's task instance overrides them: `RAW_Jaffleshop` for reading and `STG_Jaffleshop` for writing (L4580–4618). The override is what actually runs."],
     "nodes": ["sess-s_FL_JS_STAGING_FULL", "wf-taskinstances"],
     "earlier": "The example page showed only MART_Jaffleshop."},
    {"id": "instancename", "sev": "confusing", "by": "you", "title": "A target instance named differently from its table",
     "body": ["In the enriched mapping the target instance is called `ORDER_FINANCIALS1` (L2391), but it writes the table `ORDER_FINANCIALS` (L1112). The session refers to it by the instance name too (L4466). So the dbt model's name has to come from the table, not the instance. It is the only target like this."],
     "nodes": ["inst-m_FL_JS_MARTS_ENRICHED", "tgt-ORDER_FINANCIALS"]},
    {"id": "default-group", "sev": "confusing", "title": "Rows that match no Router group are dropped",
     "body": ["Both Routers leave their default group unconnected (L277, L1741), so a row that matches no condition just disappears.",
              "Today nothing is lost: REGION always gets a value (L236), and no seed order has a missing ORDER_TOTAL. A NULL would drop the row without any error."],
     "nodes": ["tx-m_FL_JS_STAGING_FULL-RTR_REGION", "tx-m_FL_JS_MARTS_ENRICHED-RTR_ORDER_VALUE_BAND"]},
    {"id": "region", "sev": "confusing", "title": "Region is guessed from the tax rate",
     "body": ["REGION is EMEA when TAX_RATE >= 0.15, APAC when it is >= 0.09, and AMER otherwise (L236).",
              f"All {SEED['stores']} seed stores have a tax rate of {SEED['max_tax_rate']} or less, so all are AMER, and the APAC and EMEA branches stay empty. The APAC condition also ends with a stray line break (L276).",
              "Port numbers don't line up either: in the Router `REGION2` is the default group, but in the Union `REGION2` is APAC. Only the connectors say which is which."],
     "nodes": ["tx-m_FL_JS_STAGING_FULL-EXP_LOCATIONS", "tx-m_FL_JS_STAGING_FULL-RTR_REGION"]},
    {"id": "failures", "sev": "confusing", "by": "review", "title": "If a step fails, the next one still runs",
     "body": ["None of the 4 workflow links has a condition (L4622–4625), no task instance fails the workflow (for example L4579), all 3 sessions use 'Fail task and continue workflow' (L1000, L4285, L4563), and the session config sets Stop on errors to 0 (L793).",
              "So if staging fails after its Pre SQL has emptied the tables, the marts are still rebuilt from empty or half-filled staging tables. dbt behaves differently: it skips everything downstream of a failed model. The XML settings are certain; what happens on a real failure is reasoning, not tested."],
     "nodes": ["wf-links", "wf-taskinstances", "config"]},
    {"id": "errordefaults", "sev": "confusing", "by": "review", "title": "Two ports silently drop rows with an empty input",
     "body": ["`TAX_RATE` in EXP_LOCATIONS (L235) and `ORDER_ID` in EXP_ORDER_ITEMS (L455) pass a value through but have the default ERROR('Transformation Error'). By Informatica's documentation, an empty (NULL) input then skips the whole row as a row error, and Stop on errors = 0 (L793) lets the session carry on.",
              "Separately, the '0' defaults on `SUPPLY_COST` and `IS_PERISHABLE` (L503–504) only apply when the formula fails, not when the input is empty. No seed row is affected today."],
     "nodes": ["tx-m_FL_JS_STAGING_FULL-EXP_LOCATIONS", "tx-m_FL_JS_STAGING_FULL-EXP_ORDER_ITEMS"]},
    {"id": "precision", "sev": "confusing", "by": "review", "title": "Supply cost passes through a whole-number port, but is not rounded there",
     "body": ["In the core mapping, `SUPPLY_COST_PER_PRODUCT` is decimal(10,0) in AGG_SUPPLIES_BY_PRODUCT2 (L3382), while the same sum is decimal(12,2) in AGG_SUPPLIES_BY_PRODUCT (L3291). It then flows through more scale-0 ports (L3459–3460, L3465) into ORDERS.",
              "All sessions have 'Enable high precision' = NO (L1007, L4292, L4570). Informatica's Advanced Workflow Guide says a session without high precision converts decimal values to doubles. So the port's scale is not applied and nothing is rounded inside the mapping; rounding happens only when a value is written to a target column (decision Q11).",
              f"One caveat: a Designer Guide table says Decimal ports with precision up to 15 stay Decimal even without high precision. That page mixes in another product's rules, so we follow the Advanced Workflow Guide. If the scale were applied, the seed's total ORDER_COST would be {SEED['order_cost_rounded']} instead of {SEED['order_cost_exact']}."],
     "earlier": "This first said we can't tell whether the port rounds. You pointed to the high-precision setting, and the documentation supports you.",
     "nodes": ["tx-m_FL_JS_MARTS_CORE-AGG_SUPPLIES_BY_PRODUCT2", "tgt-ORDERS"]},
    {"id": "year", "sev": "confusing", "title": "Order dates pass through a 2-digit year",
     "body": ["`ORDERED_AT_DAY` turns the timestamp into text with a 2-digit year and back (L110). That drops the time of day, but the century has to be guessed on the way back. Fine for 2024–2025, not in general."],
     "nodes": ["tx-m_FL_JS_STAGING_FULL-EXP_ORDERS"]},
    {"id": "sorters", "sev": "confusing", "title": "15 Sorters: most change nothing, 3 matter",
     "body": ["None removes duplicates (Distinct = NO, for example L1434). Row order means nothing in a SQL table, so most Sorters have no effect on the result.",
              "But 3 Sorters feed the row-by-row ports above: SRT_BY_CUSTOMER (L3554) before the core counter, SRT_FOR_CUSTOMER_SEQ (L1635) before the enriched counter, and SRT_FOR_DISTINCT_CUSTOMER (L2091) before the first-customer flag. Which row gets which counter number depends on that order, and the flag would too if it worked. What to do with Sorters is an open decision."],
     "earlier": "This was listed as harmless noise, and Things to watch marked it decided. You never decided it.",
     "nodes": [f"txg-{m.get('NAME')}-Sorter" for m in maps]},
    {"id": "unused", "sev": "noise", "title": f"{len(unused_sq)} Source Qualifier columns are never passed on",
     "body": ["No connector takes these columns any further. For example, in the enriched mapping SQ_STG_ORDERS has all 6 money columns (L1232–1237) and passes none of them on. Informatica's documentation says unconnected Source Qualifier ports are left out of the generated SELECT, so they are probably never read at all (not tested).",
              "Separately, the Joiner port SKU1 (L485) is used only in its join condition (L488); its output is not connected."],
     "earlier": "This first called SKU1 an unused join key. It is used in the join condition at L488.",
     "nodes": [f"txg-{m.get('NAME')}-Source Qualifier" for m in maps]},
    {"id": "names", "sev": "noise", "title": f"{len(dup_names)} transformation names appear in both mart mappings, and some logic is duplicated",
     "body": ["For example `AGG_SUPPLIES_BY_PRODUCT` is at L1441 and again at L3287. Names are unique only inside one mapping, so the converter has to keep them apart.",
              "Some logic is also computed twice: the core mapping has two supply aggregators with different precision (L3291 and L3382, see above), and the enriched mapping computes recency twice with the same formula (L2300, L2318)."],
     "nodes": ["map-m_FL_JS_MARTS_CORE", "map-m_FL_JS_MARTS_ENRICHED"]},
    {"id": "supplyid", "sev": "noise", "by": "review", "title": "Supply IDs are not unique",
     "body": [f"The seed has {SEED['supply_rows']} supply rows but only {SEED['supply_ids']} distinct supply IDs (jaffle-shop adds a supply_uuid for this reason). Staging joins supplies to products with a Normal join (L488–489), so a supply with an unknown product would vanish; none does today.",
              "So no data test should assume SUPPLY_ID is unique."],
     "nodes": ["tx-m_FL_JS_STAGING_FULL-JNR_SUPPLIES_PRODUCTS", "tgt-STG_SUPPLIES"]},
    {"id": "twice", "sev": "noise", "title": "Each staging table is described twice",
     "body": ["Once as a PC Target (L44–89) and again as a PC Source (L1014–1059), so the mart mappings can read it. The columns match (checked). The converter has to treat each pair as one table."],
     "nodes": ["targets-staging", "sources-stg"]},
    {"id": "credential", "sev": "security", "title": "A plaintext database password in the command task",
     "body": ["`cmd_FL_JS_CREATE_RPT_VIEWS` (L4058–4062) runs a shell command after the last session, and the command contains a database password. We never show it.",
              "The report views it creates are not defined in any mapping, so our dbt project won't have them."],
     "nodes": ["task-cmd_FL_JS_CREATE_RPT_VIEWS"]},
]

# checks that found nothing
all_conns = [c for m in maps for c in m.kids("CONNECTOR")]
sq_over = [a for m in maps for t in m.kids("TRANSFORMATION") if t.get("TYPE") == "Source Qualifier"
           for a in t.kids("TABLEATTRIBUTE") if a.get("NAME") in ("Sql Query", "Source Filter", "User Defined Join") and a.get("VALUE")]
assert not sq_over
assert all(m.get("ISVALID") == "YES" for m in maps)
clean = [f"All {len(all_conns):,} connectors point at a real instance and port.",
         "Every target column is fed by exactly one connector, and every transformation input is fed.",
         "Every Aggregator output is either grouped by or aggregated, so no 'any row wins' values.",
         "No text column gets shorter on its way into a target.",
         "No Source Qualifier has a SQL override, a filter or a custom join.",
         "Every PC Source and PC Target is used by a mapping, and all 3 mappings are marked valid.",
         "There are no Lookups, Mapplets, Update Strategies or Sequence Generators: only the 8 box types in the tree."]

data = {"file": {"name": "FLOWLINE_DEMO_JAFFLESHOP.xml", "lines": n_lines},
        "segments": segs, "tree": tree, "problems": problems, "clean": clean, "seed": SEED}
js = "/* GENERATED from the demo XML by build_input_data.py. Do not edit by hand. */\nwindow.INPUT = " + \
     json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
toks = secret_tokens(XML)
assert not any(t in js for t in toks), "credential token in output"
assert "VALUEPAIR" not in js
open(OUT, "w", encoding="utf-8").write(js)

cnt = Counter(p["sev"] for p in problems)
print(f"OK: {len(problems)} problems {dict(cnt)}; {len(segs)} file segments; {len(js) // 1024} KB; "
      f"{len(toks)} credential tokens absent")
