"""Steps 2-4 on the hand-made fixture: every staging box type, run in DuckDB.

Raw rows (hand-made):
  p1 Ann  72.50 t1   -> HIGH, team Red (joined on UPPER(TEAM) = TEAM_ID)
  p2 Bob  49.99 t2   -> LOW,  team Blue
  p3 Cy   NULL  t1   -> SCORE is NULL, so no Router group matches: dropped (default group unconnected)
  NULL Dee 90.00 t1  -> ID is NULL and EXP_PEOPLE.ID has an ERROR() default: row dropped
  p5 Eve  60.00 t9   -> no team t9: dropped by the Normal join
"""
from decimal import Decimal

import duckdb
import pytest

from pc2dbt.convert import convert_mapping
from pc2dbt.parse import parse_file
from tests.helpers import MINI_XML, columns, line_of, run_model


@pytest.fixture(scope="module")
def model():
    (m,) = convert_mapping(parse_file(MINI_XML), "m_MINI")
    return m


@pytest.fixture(scope="module")
def rows(model):
    con = duckdb.connect()
    con.execute("create schema raw")
    # RAW_PEOPLE deliberately has no NAME column: NAME is never connected past the Source Qualifier.
    con.execute("create table raw.raw_people (id varchar, score decimal(6,2), team varchar)")
    con.execute("""insert into raw.raw_people values
        ('p1', 72.50, 't1'), ('p2', 49.99, 't2'), ('p3', null, 't1'), (null, 90.00, 't1'), ('p5', 60.00, 't9')""")
    con.execute("create table raw.raw_teams (team_id varchar, team_name varchar)")
    con.execute("insert into raw.raw_teams values ('T1', 'Red'), ('T2', 'Blue')")  # the join key is UPPER(TEAM)
    return {r[0]: r for r in run_model(con, model.sql)}


def test_model_is_named_after_the_target_table(model):
    assert (model.name, model.folder) == ("t_people", "m_mini")


def test_columns_follow_the_target_definition(model):
    con = duckdb.connect()
    con.execute("create schema raw")
    con.execute("create table raw.raw_people (id varchar, score decimal(6,2), team varchar)")
    con.execute("create table raw.raw_teams (team_id varchar, team_name varchar)")
    assert columns(con, model.sql) == ["person_id", "score_rounded", "label", "team_name"]


def test_router_and_union_keep_both_groups(rows):
    assert sorted(rows) == ["p1", "p2"]


def test_row_matching_no_router_group_is_dropped(rows):
    assert "p3" not in rows


def test_error_default_on_input_port_drops_null_rows(rows):
    assert None not in rows


def test_normal_join_drops_detail_rows_without_a_match(rows):
    assert "p5" not in rows


def test_crossed_connectors_are_copied_not_fixed(rows):
    assert rows["p1"][2:] == ("Red", "HIGH")  # LABEL column gets the team name, TEAM_NAME gets the label


def test_cast_to_target_type_rounds_at_the_target(rows):
    assert (rows["p1"][1], rows["p2"][1]) == (Decimal("73"), Decimal("50"))


def flagged_lines(model, kind):
    return sorted(f.line for f in model.flags if f.kind == kind)


def test_flags_crossed_connectors_with_their_lines(model):
    assert flagged_lines(model, "crossed") == sorted([
        line_of(MINI_XML, 'FROMFIELD="LABEL" FROMINSTANCE="UN_ALL"'),
        line_of(MINI_XML, 'FROMFIELD="TEAM_NAME" FROMINSTANCE="UN_ALL"')])


def test_flags_rounding_cast(model):
    assert flagged_lines(model, "rounds") == [line_of(MINI_XML, 'TOFIELD="SCORE_ROUNDED"')]


def test_flags_rows_dropped_by_error_default_and_router_default(model):
    assert flagged_lines(model, "error_default") == [line_of(MINI_XML, 'DEFAULTVALUE="ERROR(\'Transformation Error\')" EXPRESSION="ID"')]
    assert flagged_lines(model, "router_default") == [line_of(MINI_XML, 'NAME="DEFAULT1"')]


def test_each_sql_block_carries_its_box_and_lines(model):
    blocks = {b.box: b for b in model.blocks}
    assert set(blocks) == {"SQ_RAW_PEOPLE", "SQ_RAW_TEAMS", "EXP_PEOPLE", "SRT_PEOPLE", "JNR_TEAM", "RTR_SCORE", "UN_ALL", "T_PEOPLE"}
    assert blocks["EXP_PEOPLE"].start == line_of(MINI_XML, 'NAME="EXP_PEOPLE" REUSABLE="NO" TYPE="Expression"')
    assert blocks["SRT_PEOPLE"].sql == ""  # dropped: row order means nothing in a table (decision Q12)
