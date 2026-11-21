"""Hunt for problems in a PowerCenter XML export. Prints findings with line numbers.

Usage: python3 -I input_checks.py <xml>
Never prints VALUEPAIR content (pcxml drops it at parse time).
"""
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pcxml import parse  # noqa: E402

X = sys.argv[1]
root = parse(X)
folder = root.kids("REPOSITORY")[0].kids("FOLDER")[0]
sources = {(s.get("DBDNAME"), s.get("NAME")): s for s in folder.kids("SOURCE")}
targets = {t.get("NAME"): t for t in folder.kids("TARGET")}


def ports_of(mapping, inst):
    """name -> (porttype, datatype, precision, scale, line, group) for an instance."""
    t = inst.get("TYPE")
    if t == "SOURCE":
        d = sources[(inst.get("DBDNAME"), inst.get("TRANSFORMATION_NAME"))]
        return {f.get("NAME"): ("OUTPUT", f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE"), f.start, None)
                for f in d.kids("SOURCEFIELD")}, d
    if t == "TARGET":
        d = targets[inst.get("TRANSFORMATION_NAME")]
        return {f.get("NAME"): ("INPUT", f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE"), f.start, None)
                for f in d.kids("TARGETFIELD")}, d
    d = next(x for x in mapping.kids("TRANSFORMATION") if x.get("NAME") == inst.get("TRANSFORMATION_NAME"))
    return {f.get("NAME"): (f.get("PORTTYPE"), f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE"), f.start,
                            f.get("GROUP")) for f in d.kids("TRANSFORMFIELD")}, d


def section(title):
    print(f"\n=== {title}")


for m in folder.kids("MAPPING"):
    M = m.get("NAME")
    insts = {i.get("NAME"): i for i in m.kids("INSTANCE")}
    P, D = {}, {}
    for n, i in insts.items():
        P[n], D[n] = ports_of(m, i)
    conns = m.kids("CONNECTOR")
    section(f"{M} (L{m.start}-{m.end}): {len(insts)} instances, {len(conns)} connectors")

    inc = defaultdict(list)   # (inst, field) -> connectors in
    out = defaultdict(list)   # (inst, field) -> connectors out
    for c in conns:
        fi, ff, ti, tf = c.get("FROMINSTANCE"), c.get("FROMFIELD"), c.get("TOINSTANCE"), c.get("TOFIELD")
        if fi not in P or ti not in P:
            print(f"  BROKEN connector L{c.start}: unknown instance {fi}->{ti}"); continue
        if ff not in P[fi] or tf not in P[ti]:
            print(f"  BROKEN connector L{c.start}: unknown port {fi}.{ff}->{ti}.{tf}"); continue
        inc[(ti, tf)].append(c); out[(fi, ff)].append(c)
        a, b = P[fi][ff], P[ti][tf]
        if a[1] != b[1]:
            print(f"  TYPE   L{c.start}: {fi}.{ff} {a[1]}({a[2]},{a[3]}) -> {ti}.{tf} {b[1]}({b[2]},{b[3]})")
        elif a[2] and b[2] and a[2].isdigit() and b[2].isdigit() and int(b[2]) < int(a[2]):
            print(f"  NARROW L{c.start}: {fi}.{ff} {a[1]}({a[2]},{a[3]}) -> {ti}.{tf} ({b[2]},{b[3]})")
        elif a[3] and b[3] and a[3].isdigit() and b[3].isdigit() and int(b[3]) < int(a[3]):
            print(f"  SCALE  L{c.start}: {fi}.{ff} ({a[2]},{a[3]}) -> {ti}.{tf} ({b[2]},{b[3]})")
    for (ti, tf), cs in inc.items():
        if len(cs) > 1:
            print(f"  MULTI-IN {ti}.{tf}: {[c.start for c in cs]}")

    # name mismatches into targets, and swap pairs anywhere
    pairs = defaultdict(dict)
    for c in conns:
        pairs[(c.get("FROMINSTANCE"), c.get("TOINSTANCE"))][c.get("FROMFIELD")] = (c.get("TOFIELD"), c.start)
    for (fi, ti), mp in pairs.items():
        tofields = {v[0] for v in mp.values()}
        for ff, (tf, ln) in mp.items():
            if ff != tf and ff in tofields and re.sub(r"\d+$", "", ff) != re.sub(r"\d+$", "", tf):
                print(f"  CROSS  L{ln}: {fi}.{ff} -> {ti}.{tf}  (a port named {ff} also exists on {ti})")
        if insts[ti].get("TYPE") == "TARGET":
            for ff, (tf, ln) in mp.items():
                if re.sub(r"\d+$", "", ff) != tf:
                    print(f"  RENAME-INTO-TARGET L{ln}: {fi}.{ff} -> {ti}.{tf}")

    # unconnected target fields, inputs, unused outputs
    for n, i in insts.items():
        t = i.get("TYPE")
        for pn, (pt, dt, pr, sc, ln, grp) in P[n].items():
            if t == "TARGET" and (n, pn) not in inc:
                print(f"  TARGET-FIELD-NOT-FED {n}.{pn} (defined L{ln})")
            if t == "TRANSFORMATION" and pt and "INPUT" in pt and (n, pn) not in inc:
                print(f"  INPUT-NOT-FED {n}.{pn} {pt} (L{ln})")
            if t in ("TRANSFORMATION", "SOURCE") and pt and "OUTPUT" in pt and (n, pn) not in out:
                if t == "SOURCE" or D[n].get("TYPE") != "Router":
                    print(f"  OUTPUT-UNUSED {n}.{pn} {pt} (L{ln})")

    # routers: groups and whether each output group is connected
    for d in m.kids("TRANSFORMATION"):
        if d.get("TYPE") == "Router":
            used = {c.get("FROMFIELD") for c in conns if c.get("FROMINSTANCE") == d.get("NAME")}
            for g in d.kids("GROUP"):
                gp = [f.get("NAME") for f in d.kids("TRANSFORMFIELD") if f.get("GROUP") == g.get("NAME")]
                con = [p for p in gp if p in used]
                print(f"  ROUTER {d.get('NAME')} group {g.get('NAME')} {g.get('TYPE')} L{g.start} "
                      f"expr={g.get('EXPRESSION')!r} ports={len(gp)} connected={len(con)}")
        if d.get("TYPE") == "Aggregator":
            ta = d.attrs_table()
            for f in d.kids("TRANSFORMFIELD"):
                e = f.get("EXPRESSION")
                if "OUTPUT" in (f.get("PORTTYPE") or "") and f.get("EXPRESSIONTYPE") != "GROUPBY" and e and \
                        not re.search(r"\b(SUM|COUNT|AVG|MAX|MIN|FIRST|LAST|MEDIAN|STDDEV|VARIANCE|PERCENTILE)\s*\(", e, re.I):
                    print(f"  AGG-NONAGG {d.get('NAME')}.{f.get('NAME')} L{f.start}: {e!r}")
            print(f"  AGG {d.get('NAME')} L{d.start} sorted_input={ta.get('Sorted Input', ('?',))[0]} "
                  f"groupby={[f.get('NAME') for f in d.kids('TRANSFORMFIELD') if f.get('EXPRESSIONTYPE') == 'GROUPBY']}")
        if d.get("TYPE") == "Joiner":
            ta = d.attrs_table()
            master = [f.get("NAME") for f in d.kids("TRANSFORMFIELD") if "MASTER" in (f.get("PORTTYPE") or "")]
            print(f"  JOIN {d.get('NAME')} L{d.start} type={ta.get('Join Type', ('?',))[0]} "
                  f"cond={ta.get('Join Condition', ('?',))[0]!r} sorted={ta.get('Sorted Input', ('?',))[0]} "
                  f"master_ports={len(master)}")

    # target instance attributes (Pre/Post SQL etc.)
    for n, i in insts.items():
        for a in i.kids("TABLEATTRIBUTE"):
            if a.get("VALUE"):
                print(f"  INST-ATTR {n} L{a.start}: {a.get('NAME')} = {a.get('VALUE')!r}")
    for tlo in m.kids("TARGETLOADORDER"):
        print(f"  LOADORDER L{tlo.start}: {tlo.a}")
    for mv in m.kids("MAPPINGVARIABLE"):
        nm = mv.get("NAME")
        uses = [f.start for f in m.iter("TRANSFORMFIELD") if nm in (f.get("EXPRESSION") or "")]
        uses += [a.start for a in m.iter("TABLEATTRIBUTE") if nm in (a.get("VALUE") or "")]
        print(f"  MAPPINGVARIABLE {nm} L{mv.start} used at {uses}")

section("Source vs target definitions of the same table")
tdefs = {t.get("NAME"): t for t in folder.kids("TARGET")}
for (db, n), s in sources.items():
    if n in tdefs:
        sf = [(f.get("NAME"), f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE")) for f in s.kids("SOURCEFIELD")]
        tf = [(f.get("NAME"), f.get("DATATYPE"), f.get("PRECISION"), f.get("SCALE")) for f in tdefs[n].kids("TARGETFIELD")]
        same_set = sorted(sf) == sorted(tf)
        print(f"  {n}: source L{s.start} ({len(sf)} cols) vs target L{tdefs[n].start} ({len(tf)} cols): "
              f"{'same columns' if same_set else 'DIFFERENT'}{'' if sf == tf else ', different order'}")
        if not same_set:
            print("    only in source:", sorted(set(sf) - set(tf)))
            print("    only in target:", sorted(set(tf) - set(sf)))

section("Definitions not used by any mapping")
used_src = {(i.get("DBDNAME"), i.get("TRANSFORMATION_NAME")) for m in folder.kids("MAPPING")
            for i in m.kids("INSTANCE") if i.get("TYPE") == "SOURCE"}
used_tgt = {i.get("TRANSFORMATION_NAME") for m in folder.kids("MAPPING")
            for i in m.kids("INSTANCE") if i.get("TYPE") == "TARGET"}
print("  unused sources:", [k for k in sources if k not in used_src])
print("  unused targets:", [k for k in targets if k not in used_tgt])

section("Expression functions")
fn = Counter()
for f in folder.iter("TRANSFORMFIELD"):
    for name in re.findall(r"\b([A-Z_][A-Z0-9_]*)\s*\(", f.get("EXPRESSION") or ""):
        fn[name] += 1
for g in folder.iter("GROUP"):
    for name in re.findall(r"\b([A-Z_][A-Z0-9_]*)\s*\(", g.get("EXPRESSION") or ""):
        fn[name] += 1
print(" ", dict(fn.most_common()))
