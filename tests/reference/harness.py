"""Check 3 harness (test-only): build both projects on the jaffle-shop seeds and compare them.

Ours: convert the XML, load the seed CSVs with the XML's PC Source column types (decision Q14),
dbt build. Reference: jaffle-shop at commit 7d0d8de with dbt 1.12 (decision Q1), cached in
tests/.cache so it is built once. The converter itself never imports this module.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb
import yaml

from pc2dbt.parse import parse_file
from pc2dbt.project import project_name, write_project
from pc2dbt.types import duck_type
from tests.helpers import DEMO_XML, ROOT

JAFFLE = ROOT / "external" / "jaffle-shop"
JAFFLE_COMMIT = "7d0d8de"
SEEDS = JAFFLE / "seeds" / "jaffle-data"
CACHE = ROOT / "tests" / ".cache"
EXPECTED = ROOT / "tests" / "reference" / "expected_differences.yml"
DBT = str(Path(sys.executable).parent / "dbt")


@dataclass
class Build:
    db: Path
    returncode: int
    log: str


def dbt(args: list[str], project: Path, profiles: Path) -> subprocess.CompletedProcess:
    return subprocess.run([DBT, *args, "--project-dir", str(project), "--profiles-dir", str(profiles)],
                          capture_output=True, text=True)


def write_profile(path: Path, profile: str, db: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "profiles.yml").write_text(yaml.safe_dump(
        {profile: {"target": "dev", "outputs": {"dev": {"type": "duckdb", "path": str(db), "threads": 4}}}}))


def load_raw(db: Path) -> None:
    """Create raw.* from the seed CSVs, typed as the XML's PC Sources say."""
    folder = parse_file(DEMO_XML)
    con = duckdb.connect(str(db))
    con.execute("create schema if not exists raw")
    for (dbd, name), table in folder.sources.items():
        if table.owner != "RAW":
            continue
        cols = ", ".join(f"cast({f.name.lower()} as {duck_type(f.datatype, f.precision, f.scale)}) as {f.name.lower()}"
                         for f in table.fields.values())
        csv = SEEDS / f"{name.lower()}.csv"
        con.execute(f"create or replace table raw.{name.lower()} as select {cols} "
                    f"from read_csv('{csv}', header = true, all_varchar = true)")
    con.close()


def build_ours(work: Path, mappings: list[str]) -> Build:
    project, db = work / "project", work / "ours.duckdb"
    write_project(DEMO_XML, project, mappings)
    load_raw(db)
    write_profile(work / "profiles", project_name(parse_file(DEMO_XML)), db)
    done = dbt(["build"], project, work / "profiles")
    return Build(db, done.returncode, done.stdout + done.stderr)


def build_reference() -> Build:
    """jaffle-shop staging models at the pinned commit, built once and cached."""
    project, db = CACHE / f"jaffle-shop-{JAFFLE_COMMIT}", CACHE / f"reference-{JAFFLE_COMMIT}.duckdb"
    if db.exists():
        return Build(db, 0, "cached")
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(JAFFLE), "archive", JAFFLE_COMMIT], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(project)], input=archive.stdout, check=True)
    write_profile(CACHE / "profiles", "default", db)
    log = []
    for args in (["deps"], ["seed", "--vars", "{load_source_data: true}"],
                 ["run", "--select", "staging", "--vars", "{load_source_data: true}"]):
        done = dbt(args, project, CACHE / "profiles")
        log.append(done.stdout + done.stderr)
        if done.returncode != 0:
            db.unlink(missing_ok=True)
            raise RuntimeError(f"jaffle-shop dbt {args[0]} failed:\n{log[-1][-3000:]}")
    return Build(db, 0, "\n".join(log))


def row_counts(db: Path, schema: str) -> dict[str, int]:
    con = duckdb.connect(str(db), read_only=True)
    tables = [r[0] for r in con.execute(
        "select table_name from information_schema.tables where table_schema = ? order by 1", [schema]).fetchall()]
    return {t: con.execute(f"select count(*) from {schema}.{t}").fetchone()[0] for t in tables}


def load_expected(section: str) -> dict:
    return yaml.safe_load(EXPECTED.read_text())[section]


def normalised(alias: str, col: str, dtype: str, as_int: bool) -> str:
    ref = f"{alias}.{col}"
    d = dtype.upper()
    if as_int or d == "BOOLEAN":
        return f"cast({ref} as integer)"
    if d.startswith(("DECIMAL", "DOUBLE", "FLOAT", "INTEGER", "BIGINT", "HUGEINT", "SMALLINT", "REAL")):
        return f"round(cast({ref} as double), 6)"
    if d.startswith(("TIMESTAMP", "DATE")):
        return f"cast({ref} as timestamp)"
    return ref


def compare(ours_db: Path, ref_db: Path, expected: dict) -> dict:
    con = duckdb.connect()
    con.execute(f"attach '{ours_db}' as ours (read_only)")
    con.execute(f"attach '{ref_db}' as ref (read_only)")
    tables = []
    for table, spec in expected.items():
        rename = spec.get("rename", {})
        as_int = set(spec.get("boolean_as_int", []))
        explained = spec.get("explained", {})
        skip_ours = spec.get("not_compared", {}).get("ours", {}) or {}
        skip_ref = spec.get("not_compared", {}).get("reference", {}) or {}
        types_o = dict(con.execute(f"select column_name, data_type from information_schema.columns where table_catalog = 'ours' "
                                   f"and table_schema = 'main' and table_name = '{table}' order by ordinal_position").fetchall())
        types_r = dict(con.execute(f"select column_name, data_type from information_schema.columns where table_catalog = 'ref' "
                                   f"and table_schema = 'main' and table_name = '{table}' order by ordinal_position").fetchall())
        key = spec["key"]
        on = " and ".join(f"o.{k} = r.{rename.get(k, k)}" for k in key)
        n_o = con.execute(f"select count(*) from ours.main.{table}").fetchone()[0]
        n_r = con.execute(f"select count(*) from ref.main.{table}").fetchone()[0]
        only_o = con.execute(f"select count(*) from ours.main.{table} o anti join ref.main.{table} r on {on}").fetchone()[0]
        only_r = con.execute(f"select count(*) from ref.main.{table} r anti join ours.main.{table} o on {on}").fetchone()[0]
        rows = {"ours": n_o, "reference": n_r, "only_ours": only_o, "only_reference": only_r,
                "status": "matched" if (n_o == n_r and only_o == only_r == 0) else "unexplained"}
        columns = []
        mapped_ref = set()
        for col, dtype in types_o.items():
            if col in skip_ours:
                columns.append({"ours": col, "reference": None, "status": "not compared", "differing_rows": None,
                                "reason": skip_ours[col]})
                continue
            rcol = rename.get(col, col)
            if rcol not in types_r:
                columns.append({"ours": col, "reference": None, "status": "unexplained", "differing_rows": None,
                                "reason": "no column with this name in jaffle-shop"})
                continue
            mapped_ref.add(rcol)
            a = normalised("o", col, dtype, col in as_int)
            b = normalised("r", rcol, types_r[rcol], col in as_int)
            diff = con.execute(f"select count(*) from ours.main.{table} o join ref.main.{table} r on {on} "
                               f"where {a} is distinct from {b}").fetchone()[0]
            if diff == 0:
                status, reason = ("stale", f"listed as explained but matches: {explained[col]}") if col in explained else ("matched", "")
            else:
                status, reason = ("explained", explained[col]) if col in explained else ("unexplained", "")
            columns.append({"ours": col, "reference": rcol, "status": status, "differing_rows": diff, "reason": reason})
        for rcol in types_r:
            if rcol not in mapped_ref:
                columns.append({"ours": None, "reference": rcol,
                                "status": "not compared" if rcol in skip_ref else "unexplained",
                                "differing_rows": None, "reason": skip_ref.get(rcol, "no matching column in our output")})
        tables.append({"table": table, "key": key, "rows": rows, "columns": columns})
    summary = {}
    for t in tables:
        for c in t["columns"]:
            summary[c["status"]] = summary.get(c["status"], 0) + 1
    return {"reference": f"dbt-labs/jaffle-shop @ {JAFFLE_COMMIT}", "summary": summary, "tables": tables}
