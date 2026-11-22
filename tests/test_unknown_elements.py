"""Decision Q18: something the converter doesn't know never stops the run and never turns into guessed SQL.

Each case edits a temporary copy of the hand-made fixture mini_marts.xml (the committed file stays as it
is) so that one element on the path to T_STORE_TOTALS is unknown. Then:
  - every other model still converts normally;
  - that model's file is one guarded line that makes dbt stop on it with the element and its XML line
    ({% if execute %} keeps `dbt parse` working, so the rest of the project still builds);
  - flags.md lists it under "Not converted", and the command line exits with code 1.
"""
import subprocess
import sys

import duckdb
import pytest

from pc2dbt.project import write_project
from tests.helpers import DEMO_XML, MINI_MARTS_XML, line_of
from tests.reference import harness

BOX = line_of(MINI_MARTS_XML, 'TRANSFORMATION DESCRIPTION="" NAME="AGG_BY_STORE"')
TOTAL = line_of(MINI_MARTS_XML, 'NAME="TOTAL" PORTTYPE="OUTPUT"')

VARIANTS = {
    # an unknown box type
    "box": ('NAME="AGG_BY_STORE" REUSABLE="NO" TYPE="Aggregator"', 'NAME="AGG_BY_STORE" REUSABLE="NO" TYPE="Lookup Procedure"',
            "AGG_BY_STORE: Lookup Procedure", BOX),
    # an unknown function
    "function": ('EXPRESSION="SUM(AMOUNT)"', 'EXPRESSION="SUM(REG_REPLACE(AMOUNT))"', "AGG_BY_STORE.TOTAL: REG_REPLACE", TOTAL),
    # an expression that names a port the box doesn't have
    "port": ('EXPRESSION="SUM(AMOUNT)"', 'EXPRESSION="SUM(AMOUNT_EUR)"', "AGG_BY_STORE.TOTAL: unknown port AMOUNT_EUR", TOTAL),
}


def edited_copy(tmp_path, variant: str):
    old, new, what, line = VARIANTS[variant]
    text = MINI_MARTS_XML.read_text(encoding="utf-8")
    assert text.count(old) == 1
    path = tmp_path / "mini_marts_unknown.xml"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path, what, line


@pytest.fixture(params=list(VARIANTS))
def converted(request, tmp_path):
    xml, what, line = edited_copy(tmp_path, request.param)
    out = tmp_path / "out"
    return xml, out, write_project(xml, out), what, line


def test_every_other_model_still_converts(converted):
    _, out, report, _, _ = converted
    assert "from sq_t_visits" in (out / "models" / "m_mini_marts" / "t_visit_seq.sql").read_text()
    assert "from sq_raw_visits" in (out / "models" / "m_mini_stg" / "t_visits.sql").read_text()
    assert [m.name for m in report.models] == ["t_visits", "t_visit_seq", "t_store_totals"]


def test_the_unknown_model_is_a_guarded_compile_error_with_element_and_line(converted):
    _, out, _, what, line = converted
    sql = (out / "models" / "m_mini_marts" / "t_store_totals.sql").read_text()
    assert "{% if execute %}{{ exceptions.raise_compiler_error(" in sql and "{% endif %}" in sql
    assert f"{what} (L{line})" in sql
    assert "select" not in sql.lower()  # no guessed SQL


def test_the_report_lists_it_and_the_exit_code_is_1(converted):
    _, out, report, what, line = converted
    assert [(n.model, n.what, n.line) for n in report.not_converted] == [("t_store_totals", what, line)]
    assert report.exit_code == 1
    text = (out / "flags.md").read_text()
    assert "## Not converted" in text and f"L{line}: {what}" in text


def test_the_command_line_exits_1_and_names_it(converted):
    xml, out, _, what, line = converted
    done = subprocess.run([sys.executable, "-m", "pc2dbt", "convert", str(xml), "--out", str(out)],
                          capture_output=True, text=True)
    assert done.returncode == 1
    assert f"{what} (L{line})" in done.stderr


@pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")
def test_the_demo_xml_converts_completely(tmp_path):
    report = write_project(DEMO_XML, tmp_path)
    assert (len(report.models), report.not_converted, report.exit_code) == (16, [], 0)


@pytest.mark.reference
def test_dbt_stops_only_on_the_unknown_model(tmp_path):
    xml, what, line = edited_copy(tmp_path, "box")
    project, db = tmp_path / "project", tmp_path / "mini.duckdb"
    write_project(xml, project)
    con = duckdb.connect(str(db))
    con.execute("create schema raw")
    con.execute("create table raw.raw_visits (visit_id varchar, person varchar, store varchar, visited_at timestamp, amount decimal(8,2))")
    con.execute("insert into raw.raw_visits values ('v1', 'amy', 's1', '2025-01-01', 1.00)")
    con.execute("create table raw.raw_stores (store_id varchar, store_name varchar)")
    con.close()
    harness.write_profile(tmp_path / "profiles", "mini_marts", db)
    done = harness.dbt(["build"], project, tmp_path / "profiles")
    log = done.stdout + done.stderr
    assert done.returncode != 0
    assert f"pc2dbt could not convert t_store_totals" in log and f"{what} (L{line})" in log
    built = duckdb.connect(str(db), read_only=True).execute(
        "select table_name from information_schema.tables where table_schema = 'main' order by 1").fetchall()
    assert built == [("t_visit_seq",), ("t_visits",)]
