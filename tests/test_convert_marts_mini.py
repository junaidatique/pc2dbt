"""The core marts box types on the hand-made fixture, run in DuckDB.

m_MINI_STG writes T_VISITS; m_MINI_MARTS reads it back (so it becomes ref('t_visits'), decision Q5).

t_visits rows (hand-made):           visit_id person store visited_at amount
                                     B1       amy    s1    2025-01-05 5.50
                                     a2       amy    s1    2025-01-05 NULL
                                     c3       bob    s2    2025-01-02 10.00
                                     d4       NULL   s1    2025-01-01 2.00
                                     e5       bob    s2    2025-01-01 4.00
                                     f6       NULL   s2    2025-01-04 1.00

T_VISIT_SEQ (counter, decision Q13). SRT_VISITS sorts by PERSON, VISITED_AT, VISIT_ID, ignoring case,
NULLs first: d4, f6, a2, B1, e5, c3 ('a2' before 'B1' only because case is ignored).
EXP_VISIT_NUM sets v_PREV_PERSON to this row's PERSON before comparing, so the comparison is true on
every row except where PERSON is NULL (NULL = NULL is not true): one running number that goes back to 1
on a NULL row.   d4=1, f6=1, a2=2, B1=3, e5=4, c3=5.

T_STORE_TOTALS. AGG_BY_STORE per store: s1 = B1, a2, d4: 3 visits, 2 paid, 7.50, 01-01..01-05;
s2 = c3, e5, f6: 3 visits, 3 paid, 15.00, 01-01..01-04. JNR_STORE_VISITS is a Master Outer Join with
RAW_STORES as master: every aggregate row is kept, s1 finds North, s2 finds no store (STORE_ID and
STORE_NAME come from the master side, so they are NULL); store s3 South has no visits and is dropped.
"""
import datetime as dt
from decimal import Decimal as D

import duckdb
import pytest

from pc2dbt.convert import UnsupportedElement, convert_mapping
from pc2dbt.parse import parse_file
from tests.helpers import MINI_MARTS_XML, line_of, run_model

VISITS = """
create table t_visits (visit_id varchar, person varchar, store varchar, visited_at timestamp, amount decimal(8,2));
insert into t_visits values ('B1', 'amy', 's1', '2025-01-05', 5.50), ('a2', 'amy', 's1', '2025-01-05', null),
    ('c3', 'bob', 's2', '2025-01-02', 10.00), ('d4', null, 's1', '2025-01-01', 2.00),
    ('e5', 'bob', 's2', '2025-01-01', 4.00), ('f6', null, 's2', '2025-01-04', 1.00);
create schema raw;
create table raw.raw_stores (store_id varchar, store_name varchar);
insert into raw.raw_stores values ('s1', 'North'), ('s3', 'South');
"""


@pytest.fixture(scope="module")
def models():
    return {m.name: m for m in convert_mapping(parse_file(MINI_MARTS_XML), "m_MINI_MARTS")}


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(VISITS)
    return c


def test_a_table_written_by_another_mapping_is_read_with_ref(models):
    sql = models["t_visit_seq"].sql
    assert "{{ ref('t_visits') }}" in sql and "source('stg'" not in sql


def test_counter_is_one_running_number_in_the_sorters_order(models, con):
    assert run_model(con, models["t_visit_seq"].sql, order_by="visit_id") == [
        ("B1", "amy", D("3")), ("a2", "amy", D("2")), ("c3", "bob", D("5")),
        ("d4", None, D("1")), ("e5", "bob", D("4")), ("f6", None, D("1"))]


def test_counter_and_its_sorter_are_flagged(models):
    flags = {f.kind: f.line for f in models["t_visit_seq"].flags}
    assert flags["counter"] == line_of(MINI_MARTS_XML, 'NAME="v_VISIT_SEQ"')
    assert flags["sort_order"] == line_of(MINI_MARTS_XML, 'TRANSFORMATION DESCRIPTION="" NAME="SRT_VISITS"')


def test_master_outer_keeps_every_detail_row_and_drops_unmatched_master_rows(models, con):
    assert run_model(con, models["t_store_totals"].sql, order_by="total") == [
        ("s1", "North", D("3"), D("2"), D("7.50"), dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 5)),
        (None, None, D("3"), D("3"), D("15.00"), dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 4))]


def test_master_outer_join_is_flagged_with_the_side_it_keeps(models):
    (flag,) = [f for f in models["t_store_totals"].flags if f.kind == "master_outer"]
    assert flag.line == line_of(MINI_MARTS_XML, 'VALUE="Master Outer Join"')
    assert "AGG_BY_STORE" in flag.message and "SQ_RAW_STORES" in flag.message


def convert_edited(tmp_path, old: str, new: str, count: int = 1):
    text = MINI_MARTS_XML.read_text(encoding="utf-8")
    assert text.count(old) == count
    path = tmp_path / "edited.xml"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return convert_mapping(parse_file(path), "m_MINI_MARTS")


def test_aggregator_port_without_an_aggregate_fails_clearly(tmp_path):
    # A non-group-by port with no aggregate returns "the last row" in PowerCenter: not translated (Q18).
    with pytest.raises(UnsupportedElement, match="AGG_BY_STORE.STORE"):
        convert_edited(tmp_path, 'EXPRESSIONTYPE="GROUPBY" NAME="STORE"', 'EXPRESSIONTYPE="GENERAL" NAME="STORE"')


def test_any_other_row_by_row_pattern_fails_clearly(tmp_path):
    # Comparing before overwriting would be a real per-person counter: a different pattern (decision Q13).
    with pytest.raises(UnsupportedElement, match="EXP_VISIT_NUM"):
        convert_edited(tmp_path, 'EXPRESSION="PERSON" EXPRESSIONTYPE="GENERAL" NAME="v_PREV_PERSON"',
                       'EXPRESSION="VISIT_ID" EXPRESSIONTYPE="GENERAL" NAME="v_PREV_PERSON"')


def test_variable_ports_need_a_sorter_right_before_them(tmp_path):
    # Without a Sorter the row order is whatever the source sends, so the numbers are not reproducible.
    with pytest.raises(UnsupportedElement, match="EXP_VISIT_NUM"):
        convert_edited(tmp_path, 'FROMINSTANCE="SRT_VISITS" FROMINSTANCETYPE="Sorter"',
                       'FROMINSTANCE="SQ_T_VISITS" FROMINSTANCETYPE="Source Qualifier"', count=2)


def test_null_group_keys_form_one_group(models):
    # Unknown in PowerCenter: the docs found don't say how an Aggregator groups NULL keys (README, Unknowns).
    # We keep SQL's rule and pin it here: g7 and h8 have no store, so AGG_BY_STORE makes ONE group of 2 visits,
    # 3.00 in total. It matches no store, so the Master Outer Join keeps it with an empty STORE_ID and STORE_NAME.
    con = duckdb.connect()
    con.execute(VISITS)
    con.execute("insert into t_visits values ('g7', 'cat', null, '2025-01-06', 1.00), ('h8', 'cat', null, '2025-01-07', 2.00)")
    assert run_model(con, models["t_store_totals"].sql, order_by="total") == [
        (None, None, D("2"), D("2"), D("3.00"), dt.datetime(2025, 1, 6), dt.datetime(2025, 1, 7)),
        ("s1", "North", D("3"), D("2"), D("7.50"), dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 5)),
        (None, None, D("3"), D("3"), D("15.00"), dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 4))]


def test_a_variable_that_reads_one_below_it_is_not_the_counter(tmp_path):
    # With v_VISIT_SEQ above v_PREV_PERSON it compares the PREVIOUS row's person: a real per-person counter,
    # a different pattern from the one in the XML, so it stops (decision Q13, prompt 12).
    prev = ('<TRANSFORMFIELD DATATYPE="string" DEFAULTVALUE="" EXPRESSION="PERSON" EXPRESSIONTYPE="GENERAL" '
            'NAME="v_PREV_PERSON" PORTTYPE="LOCAL VARIABLE" PRECISION="10" SCALE="0"/>')
    seq = ('<TRANSFORMFIELD DATATYPE="decimal" DEFAULTVALUE="" EXPRESSION="IIF(v_PREV_PERSON = PERSON, v_VISIT_SEQ + 1, 1)" '
           'EXPRESSIONTYPE="GENERAL" NAME="v_VISIT_SEQ" PORTTYPE="LOCAL VARIABLE" PRECISION="10" SCALE="0"/>')
    gap = "\n            "
    with pytest.raises(UnsupportedElement, match="EXP_VISIT_NUM.v_VISIT_SEQ"):
        convert_edited(tmp_path, prev + gap + seq, seq + gap + prev)
