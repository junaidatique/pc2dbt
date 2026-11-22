# pc2dbt: PowerCenter mapping XML to dbt

`pc2dbt` converts an Informatica PowerCenter mapping export (XML) into a dbt project. It was built for the
Infinite Lambda take-home on the demo export `FLOWLINE_DEMO_JAFFLESHOP.xml`, and checked against the
dbt-labs jaffle-shop project on the same seed data.

**Results at a glance**

- All 3 mappings convert: 16 dbt models in [`out/`](out/), committed so you can read them without running
  anything, plus [`out/flags.md`](out/flags.md) with 79 flags and 21 left-out items.
- dbt builds all 16 models on DuckDB.
- 139 unit tests and 12 reference tests pass.
- Compared with jaffle-shop: 0 unexplained differences.
- The enriched marts have no jaffle-shop twin, so 21 facts check them, each computed straight from the raw
  seed and all matching.
- The behaviour copied from the XML is listed below and in [`docs/results.html`](docs/results.html).

## How to run

You need git, internet access the first time, and [uv](https://docs.astral.sh/uv/). uv installs Python 3.12
for you if it isn't there.

```bash
git clone https://github.com/junaidatique/pc2dbt.git pc2dbt
cd pc2dbt
uv venv --python 3.12
uv pip install -e ".[test]"
```

Clone the two projects the checks need into `external/` (ignored by git), pinned to the commits used here:

```bash
git clone https://github.com/infinitelambda/flowline-pwc-demo.git external/flowline-pwc-demo
git -C external/flowline-pwc-demo checkout 550a222
git clone https://github.com/dbt-labs/jaffle-shop.git external/jaffle-shop
git -C external/jaffle-shop checkout 7d0d8de
```

Convert the XML. This writes the same project that is committed in `out/`, so `git status` shows no change:

```bash
.venv/bin/pc2dbt convert external/flowline-pwc-demo/FLOWLINE_DEMO_JAFFLESHOP.xml --out out
git status --short out/
```

Run the tests. The first command is fast. The second builds both projects with dbt and compares them; the
first time, it also runs `dbt deps` and builds jaffle-shop (cached in `tests/.cache/`).

```bash
.venv/bin/pytest
.venv/bin/pytest -m reference
```

Build `out/` with dbt yourself. This loads the seed CSVs with the XML's column types, runs `dbt build`, and
prints the row count of every table. The tables end up in `demo.duckdb`, which you can query:

```bash
.venv/bin/python tools/build_demo.py
```

To convert another XML: `.venv/bin/pc2dbt convert <file.xml> --out <folder> [--mapping NAME ...]`.
Anything the converter doesn't know is listed under "Not converted" in `flags.md`, and the command exits
with code 1 (see What isn't handled).

The explainer site is plain HTML: open [`docs/index.html`](docs/index.html) in a browser. It covers the
input XML, a glossary, one mapping end to end, the five steps, the decisions, the results and the process
log. Pages that show generated SQL or results read them from files that the scripts in `tools/docs/` build
from `out/` and the test results; `tests/test_docs_fresh.py` fails when one of those files is out of date.

## How it works

Five steps, in [`pc2dbt/`](pc2dbt/) (Python standard library only; dbt and DuckDB are test-only):

1. **Parse** (`parse.py`): read the XML with the line number of every element. The command task's
   credential is dropped while reading.
2. **Graph** (`convert.py`): the connectors are the only truth about where a value comes from.
   Names are never matched.
3. **Walk:** one dbt model per PowerCenter target, built from the boxes that feed it.
4. **Translate** (`convert.py`, `expr.py`): one CTE per box, with a comment giving its XML lines, and
   Informatica expressions turned into DuckDB SQL. Every column is read with the name of its step
   (`sq_raw_orders.subtotal`), so no name can mean both an input and an output.
5. **Write** (`project.py`): `dbt_project.yml`, `models/sources.yml`, one folder per mapping, and
   `flags.md`.

Behaviour that looks wrong is copied and flagged, never fixed (decision D1). Each flag is a `-- FLAG` comment
on the SQL line it concerns, and is also listed in `flags.md`.

## Decisions and assumptions

All decisions, with their options and my reasons, are on [`docs/decisions.html`](docs/decisions.html).

| | Decision |
|---|---|
| D1 | Follow the connectors, copy what the XML does and flag it; don't fix it. |
| D2 | The reference is dbt-labs/jaffle-shop, which is what the XML matches. |
| D3 | The credential in the command task is never shown, copied or committed. |
| Q1, Q2 | dbt 1.12 on jaffle-shop commit 7d0d8de; the converter is Python, tested with pytest. |
| Q3, Q4, Q8 | All 3 mappings; one model per target, with shared boxes repeated; one folder per mapping. |
| Q5, Q6, Q7 | `ref()` between mappings; one CTE per box with its XML lines; the XML's column names, lower-cased. Model names come from the target table (`ORDER_FINANCIALS1` writes `order_financials`). |
| Q9, Q17 | Every model is a table rebuilt on each run, so the `TRUNCATE` Pre SQLs and the workflow and session settings are left out and listed in `flags.md`. |
| Q10, Q11 | Flags as SQL comments plus `flags.md`. Cast every column to its target type and flag where that rounds. Rounding happens only at the targets, because high precision is off. |
| Q12, Q13 | Sorters are dropped, except where a variable port reads rows in order: the counter's Sorter is kept with its keys, case and NULL settings. Variable ports are decided by port order: one that uses this row only is pasted into the outputs with a `/* name line */` comment; one that reads a previous row must be the counter pattern, or the model stops. |
| Q14 | The raw tables are loaded with the XML's PC Source types. |
| Q15, Q16 | `$$RUN_DATE` becomes the dbt var `run_date` (default 2025-12-31). Functions with no DuckDB twin are translated call by call, with the century rule flagged. |
| Q18 | An unknown element never stops the run: everything else converts, the unknown model makes dbt stop with the element and its line, and the command exits with code 1. |
| Q19 | The comparison with jaffle-shop uses a list of expected differences. A difference that isn't listed fails, and so does a listed one that no longer appears. |

### Unknowns

Things the converter has to assume because Informatica's documentation doesn't settle them or we
couldn't confirm them. Each one has a test that pins the behaviour we chose, so a change shows up.

| Unknown | What the converter does | Pinned by |
|---|---|---|
| How an Aggregator groups rows whose group-by key is NULL. One Informatica guide (for a different product) says no group is created; a PowerCenter guide mentions "null groups". | SQL's rule: all NULL keys form one group. The jaffle-shop seed has no NULL keys, so the comparison is not affected. | `tests/test_convert_marts_mini.py::test_null_group_keys_form_one_group` |
| Whether `DATE_DIFF(date1, date2, 'DD')` returns fractions of a day. | Exact elapsed days with fractions (12 hours = 0.5). This XML truncates both dates first (L2300, L2318), so its results are whole days either way. | `tests/test_expressions.py::test_date_diff_in_days_keeps_fractions` |

More generally, PowerCenter's behaviour (port evaluation order, join sides, NULL handling, rounding) comes
from Informatica's documentation. There was no PowerCenter to run the mappings on.

## What isn't handled

- **The workflow and sessions:**
  - Run order comes from `ref()`.
  - Links, connections and load settings are left out.
  - Failure handling is out of scope: the workflow doesn't stop when a step fails (L4622-4625, L793).
  - The `TRUNCATE` Pre SQLs aren't needed, because tables are rebuilt.
  - The command task is never read; it contains the credential.

  All of these are listed in `flags.md`.
- **The parameter file** (L4554) can override `$$RUN_DATE` in PowerCenter. Here the XML's default is used
  unless you pass `--vars '{run_date: "2025-09-30"}'` to dbt.
- **Anything not in this XML** makes that one model stop at dbt, with the element and its XML line, while
  every other model still converts. `flags.md` lists it under "Not converted", and the command exits with
  code 1 (decision Q18). This covers:
  - other box types (Lookup, Update Strategy, Sequence Generator, Rank, Normalizer, mapplets …);
  - functions the translator doesn't know;
  - expressions that name a missing port;
  - variable ports that read a previous row in any pattern but the counter;
  - Source Qualifier overrides (SQL query, filter, user-defined join, distinct);
  - case-insensitive joins;
  - `DATE_DIFF` in units other than days;
  - mapping variables that aren't parameters.
- **dbt data tests** are not written. The raw PC Sources declare 5 primary keys and 4 foreign keys
  (L11-41) that could become `unique`, `not_null` and `relationships` tests.
- **Detail Outer and Full Outer joins** are translated (`right join`, `full join`), but none is in this
  XML, so they are untested.

## Where the output is most likely wrong

**Wrong on purpose.** The XML does this, and we copy it (decision D1). Each item is flagged in the SQL and
in `flags.md`; numbers are on the seed data.

| What | Where in the XML | Effect |
|---|---|---|
| Columns wired into the wrong target column | L608-613, L620-621, L2480-2482, L2542-2543 | stg_orders' cents and dollar columns are swapped; so is product price. CUSTOMER_360's spend, pre-tax and tax land in each other's columns. |
| Amounts in the wrong unit, a result of the swaps | L3534-3536, L3636-3638, L1555 | ORDERS amounts are 100 times too small; customer lifetime amounts and enriched order amounts are 100 times too big. |
| Master Outer joins keep the lookup side | L3519, L1591 (also L3664, L2243) | The 483 orders with no items are missing from ORDERS and ORDER_FINANCIALS (61,465 rows, not 61,948). Customers without orders would be dropped too; on the seed there are none. |
| The order counter never restarts per customer | L3588-3589, L1705-1706 | One running number, 1 to 61,465. It equals jaffle-shop's per-customer number only for the first customer's 190 orders. |
| The first-customer flag compares each value with itself | L2124-2127 | It is always 0, so UNIQUE_CUSTOMERS is 0 on all 538 store-days. |
| The value band compares cents with 50 | L1740 | Every order is HIGH. |
| Price in cents, cost in dollars; margin and perishable flag swapped | L1513, L2542-2543, L504 | Item margins are 99.65% to 99.89%. Every product-day has a margin of 0 and says perishable, although no supply is. |
| RFM on these values | L2341-2366 | Recency score 1 and spend score 3 for all 935 customers: 929 AT_RISK, 6 STANDARD, nobody CHAMPION or LOYAL. |
| Target columns with fewer decimals than the value | 25 `rounds` flags in `flags.md`, in 10 models | Rounded when written, for example tax in a `NUMBER(15,0)` cents column (L609). |

**Where our copy may differ from PowerCenter itself:**
- The Unknowns above.
- The two-digit-year round trip on ORDERED_AT_DAY (L110): DuckDB reads 00-68 as 20xx, and PowerCenter's
  century rule may differ.
- Case-insensitive Sorters are copied with `lower()`. Strings that differ only in the characters between
  `Z` and `a` could sort differently.
- Rows with equal sort keys may come in any order. The counter's keys include ORDER_ID, so this doesn't
  happen here.
- DuckDB rounds half away from zero when it casts to a decimal.

## Where the agent got things wrong, and how it was caught

[`agent_log.md`](agent_log.md) lists every mistake, prompt by prompt: what went wrong, who caught it, how,
and what changed. 13 were caught by me and 47 by the agent, which includes two independent
checks it ran in separate agents (prompts 7 and 13). Some that mattered:

- **Said there were 389 expressions to handle;** most are pass-throughs (about 270), and about 120 have real
  logic. Caught by me (prompt 2).
- **Missed that the first-customer flag is always 0,** and that a Master Outer join drops customers.
  Caught by me (prompt 6).
- **Said a whole-number port might round inside the mapping.** With high precision off, it doesn't.
  Caught by me, then checked against Informatica's guides (prompt 8).
- **Said the Union maps ports by position.** It lists field pairs. Caught by the agent while building
  (prompt 9).
- **The SQL relied on DuckDB's rule when a name is both read and written.** Caught by my question; now
  every column carries its step's name (prompt 10).
- **Called the counter's 190 matching rows a coincidence.** They are the first customer's orders. Caught
  by me (prompt 11).
- **Seven rounding flags were missing, and eight seed facts weren't independent of the converter.** Caught
  by the agent's independent check (prompt 13).
- **The seed facts didn't check the margins.** Caught by me (prompt 13).
- **The explainer still showed the SQL hand-written before the build** (`date_trunc` for the order day,
  0.42 in a cents column that really stores 0). Caught by me (prompt 15); those pages now read the generated
  files, and a test fails when one is stale.

## Prompts

My prompts were drafted with the help of a separate chat. I also used that chat to check the results
independently, on my own. [`agent_log.md`](agent_log.md) keeps every prompt word for word as I sent it,
from the first one. They were spoken and transcribed, so they keep the filler words, and links I shared are
replaced with `[link removed]`. The log also has a short summary of each answer and the mistakes.

The coding session ran out of context twice (21 Nov 2026, at 12:53 and 17:26 UTC) and continued from
automatic summaries. Both summaries are in the exported conversation.

## Exported conversation

The cleaned export of the whole coding conversation is added at the end of the work. The plaintext
credential (it appears once, in a command output in prompt 1) and the brief's link are removed. The result
is checked with the same scan that guards the log page.

## Process

1. **Understanding first, no code** (prompts 1-8):
   - an overview with real line numbers;
   - a multi-page explainer in `docs/`;
   - a deep read of the input XML, with the problems found;
   - an independent review of that list in a separate agent;
   - every decision written up with options, then decided by me.
2. **Building, one step at a time** (prompts 9-15):
   - staging, then the core marts, then the enriched marts, then unknown elements and this README, then
     fixes to the README and the explainer pages (prompt 15);
   - each step test-first: tests written and seen to fail before the code, with expected values worked
     out by hand from the XML;
   - after each step the agent stopped and showed the SQL, the results and the commit message, and
     committed only after my approval.
3. **Checking, in three layers:**
   - unit tests on three hand-made XML fixtures, and the real mappings on hand-made rows;
   - dbt building all models on DuckDB;
   - the comparison with jaffle-shop, plus the seed facts for the enriched marts.

## Time spent

Agent time, measured in the saved conversation from each of my prompts to the agent's last message. My
reading and checking time between prompts isn't included.

| Phase | Prompts | Agent time | Estimate |
|---|---|---|---|
| Understanding the problem, explainer, decisions | 1-8 | 1 h 46 min | |
| Step 1: staging end to end | 9 | 22 min | 1 h |
| Step 2: core marts | 10-11 | 33 min | 1 h 15 min |
| Step 3: enriched marts | 12-13 | 35 min | 1 h |
| Step 4: unknown elements, README, fresh-clone check | 14 | about 15 min | 1 h |
| Fixes after step 4: README, repo URL, explainer pages | 15 | about 17 min | |
| **Total** | 1-15 | **about 3 h 48 min** | 4 h 15 min (steps 1-4) |

My own time on the task: (I'll fill this in).
