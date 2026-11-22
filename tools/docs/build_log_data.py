"""Turn agent_log.md into docs/assets/log-data.js for the Process log page.

agent_log.md is the source. This script only reads it, checks it, and writes JSON.

Checks (the script stops on any failure):
  - every prompt matches the user's message in the saved conversation, word for word,
    after shared links are replaced with [link removed]
  - no URL the user shared appears in the log or the output
  - no token unique to the XML's credential line appears in the log or the output

Usage: python3 -I build_log_data.py <repo_root> <transcript.jsonl> <xml>
"""
import json
import re
import sys

repo, transcript, xml_path = sys.argv[1:4]
md_path = f"{repo}/agent_log.md"
out_path = f"{repo}/docs/assets/log-data.js"
md = open(md_path, encoding="utf-8").read()


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def table(lines):
    rows = [l for l in lines if l.startswith("|")]
    return [cells(r) for r in rows[2:]]  # skip header + separator


# ---- parse -----------------------------------------------------------------
part1, part2 = md.split("## Part 2: Things to watch")
part1 = part1.split("## Part 1: Prompts")[1]

prompts = []
for chunk in re.split(r"^### ", part1, flags=re.M)[1:]:
    lines = chunk.splitlines()
    m = re.match(r"Prompt (\d+): (.+)", lines[0])
    n, title = int(m.group(1)), m.group(2).strip()
    meta = next(l for l in lines[1:] if l.strip())
    when, kind = [s.strip() for s in meta.split("·")]
    sec, buf = None, {"prompt": [], "answer": [], "wrong": []}
    for l in lines[1:]:
        if l.startswith("**My prompt**"): sec = "prompt"; continue
        if l.startswith("**Answer, in short**"): sec = "answer"; continue
        if l.startswith("**What the agent got wrong**"): sec = "wrong"; continue
        if sec: buf[sec].append(l)
    paras, cur = [], []
    for l in buf["prompt"]:
        if not l.startswith(">"):
            continue
        t = l[1:].strip()
        if t:
            cur.append(t)
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur: paras.append(" ".join(cur))
    answer = [l[2:].strip() for l in buf["answer"] if l.startswith("- ")]
    rows = table(buf["wrong"])
    mistakes = [{"what": r[0], "by": r[1], "how": r[2], "changed": r[3]} for r in rows]
    none_note = " ".join(l.strip() for l in buf["wrong"] if l.strip() and not l.startswith("|"))
    prompts.append({"n": n, "title": title, "when": when, "kind": kind, "prompt": paras,
                    "answer": answer, "mistakes": mistakes, "noneNote": none_note if not mistakes else ""})

status_note = ""
groups = []
for i, chunk in enumerate(re.split(r"^### ", part2, flags=re.M)):
    lines = chunk.splitlines()
    if i == 0:
        status_note = " ".join(l.strip() for l in lines if l.strip())
        continue
    items = [{"watch": r[0], "why": r[1], "status": r[2]} for r in table(lines)]
    groups.append({"group": lines[0].strip(), "items": items})

intro = [l[2:].strip() for l in md.split("## Part 1: Prompts")[0].splitlines() if l.startswith("- ")]

# ---- checks ----------------------------------------------------------------
def norm(s):
    return re.sub(r"\s+", " ", s).strip()

user_msgs = []
for line in open(transcript, encoding="utf-8"):
    d = json.loads(line)
    if d.get("type") != "user" or d.get("isMeta"):
        continue
    c = d.get("message", {}).get("content")
    if not isinstance(c, str) or c.startswith("This session is being continued"):
        continue
    if c.lstrip().startswith(("<task-notification>", "<agent-message")):
        continue  # automated notices (a background task finished, a subagent reported), not my prompts
    m = re.search(r"<bash-input>(.*?)</bash-input>", c, re.S)
    user_msgs.append(f"`{m.group(1).strip()}`" if m else c)

shared_urls = sorted({u for t in user_msgs for u in re.findall(r"https?://\S+", t)})
expected = [norm(re.sub(r"https?://\S+", "[link removed]", t)) for t in user_msgs]

errors = []
if len(expected) < len(prompts):
    errors.append(f"log has {len(prompts)} prompts but the conversation has {len(expected)}")
for p, exp in zip(prompts, expected):
    got = norm(" ".join(p["prompt"]))
    if got != exp:
        i = next((k for k in range(min(len(got), len(exp))) if got[k] != exp[k]), min(len(got), len(exp)))
        errors.append(f"prompt {p['n']} differs at char {i}: log={got[i-30:i+30]!r} conv={exp[i-30:i+30]!r}")
if len(expected) > len(prompts):
    errors.append(f"conversation has {len(expected)} prompts, log has {len(prompts)}")

xml = open(xml_path, encoding="utf-8", errors="replace").read().splitlines()
secret_lines = [l for l in xml if "VALUEPAIR" in l]
rest = "\n".join(l for l in xml if "VALUEPAIR" not in l)
secret_tokens = {t for l in secret_lines for t in re.findall(r"[^\s\"'=;&]{6,}", l) if t not in rest}

js = "/* GENERATED from agent_log.md by build_log_data.py. Edit agent_log.md, not this file. */\n"
js += "window.AGENT_LOG = " + json.dumps(
    {"intro": intro, "prompts": prompts, "statusNote": status_note, "watch": groups},
    ensure_ascii=False, indent=1) + ";\n"

for name, text in (("agent_log.md", md), ("log-data.js", js)):
    if any(t in text for t in secret_tokens):
        errors.append(f"{name}: contains a token from the credential line")
    for u in shared_urls:
        if u in text:
            errors.append(f"{name}: contains a shared link")

if errors:
    print("FAILED"); print("\n".join(errors)); sys.exit(1)

open(out_path, "w", encoding="utf-8").write(js)
n_m = sum(len(p["mistakes"]) for p in prompts)
by = {}
for p in prompts:
    for m in p["mistakes"]:
        by[m["by"]] = by.get(m["by"], 0) + 1
print(f"OK: {len(prompts)} prompts match the conversation word for word; "
      f"{n_m} mistakes {by}; {sum(len(g['items']) for g in groups)} watch items "
      f"in {len(groups)} groups; {len(shared_urls)} shared links absent; "
      f"{len(secret_tokens)} credential tokens absent")
print("wrote", out_path)
