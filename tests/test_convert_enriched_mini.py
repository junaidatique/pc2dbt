"""The enriched marts' new parts on the hand-made fixture, run in DuckDB.

Variable ports are decided by port order (prompt 12): PowerCenter evaluates input ports, then variable
ports top to bottom, then output ports. A variable that reads only inputs or variables above it uses
this row only, so its SQL is pasted into the outputs that use it, with a /* name line */ comment.

raw_sales rows (hand-made):   sale_id shop  sold_at           price cost
                              s1      north 2025-06-01        10.00 4.00
                              s2      NULL  2025-06-29 18:30   5.00 NULL
                              s3      south 2025-05-31         0.00 1.00
                              s4      south 2025-01-01         NULL 1.00

v_COST_CL = cost or 0; v_MARGIN = (price - v_COST_CL) / price: s1 0.6, s2 1.0.
v_SAME_SHOP compares SHOP with v_PREV_SHOP, which already holds this row's SHOP: 0, or 1 when SHOP is
NULL (NULL = NULL is not true), so s1 0, s2 1.
v_AGE_DAYS = DATE_DIFF(TRUNC($$AS_OF), TRUNC(SOLD_AT), 'DD') with $$AS_OF = 06/30/2025: s1 29, s2 1.
FIL_PRICED keeps PRICE > 0: s3 (0) fails, s4 (NULL) is not true, so both are dropped.
"""
import duckdb
import pytest
from decimal import Decimal as D

from pc2dbt.convert import convert_mapping
from pc2dbt.parse import parse_file
from tests.helpers import MINI_ENRICHED_XML, line_of, run_model

SALES = """
create schema raw;
create table raw.raw_sales (sale_id varchar, shop varchar, sold_at timestamp, price decimal(8,2), cost decimal(8,2));
insert into raw.raw_sales values ('s1', 'north', '2025-06-01', 10.00, 4.00), ('s2', null, '2025-06-29 18:30', 5.00, null),
    ('s3', 'south', '2025-05-31', 0.00, 1.00), ('s4', 'south', '2025-01-01', null, 1.00);
"""


@pytest.fixture(scope="module")
def model():
    (m,) = convert_mapping(parse_file(MINI_ENRICHED_XML), "m_MINI_ENRICHED")
    return m


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(SALES)
    return c


def test_row_local_variables_filter_and_run_date(model, con):
    assert run_model(con, model.sql) == [("s1", "north", D("0.6000"), D("0"), D("29")),
                                         ("s2", None, D("1.0000"), D("1"), D("1"))]


def test_a_mapping_parameter_is_a_dbt_var_with_the_xml_default(model, con):
    assert "{{ var('as_of', '2025-06-30') }}" in model.sql
    rows = run_model(con, model.sql, dbt_vars={"as_of": "2025-07-31"})
    assert [r[4] for r in rows] == [D("60"), D("32")]


def test_each_pasted_variable_keeps_its_name_and_line(model):
    for name in ("v_COST_CL", "v_MARGIN", "v_PREV_SHOP", "v_SAME_SHOP", "v_AGE_DAYS"):
        assert f"/* {name} L{line_of(MINI_ENRICHED_XML, f'NAME=\"{name}\"')} */" in model.sql


def test_comparing_a_value_with_itself_is_flagged(model):
    (flag,) = [f for f in model.flags if f.kind == "self_compare"]
    assert flag.line == line_of(MINI_ENRICHED_XML, 'NAME="v_SAME_SHOP"')
    assert "SHOP" in flag.message


def test_the_run_date_parameter_is_flagged(model):
    (flag,) = [f for f in model.flags if f.kind == "parameter"]
    assert flag.line == line_of(MINI_ENRICHED_XML, 'NAME="$$AS_OF"')


def test_a_division_inside_a_pasted_variable_counts_for_rounding(model):
    # MARGIN = v_MARGIN, and v_MARGIN divides (price - cost) / price: a double at run time, rounded by NUMBER(10,4).
    rounds = [f.line for f in model.flags if f.kind == "rounds"]
    assert line_of(MINI_ENRICHED_XML, 'FROMFIELD="MARGIN" FROMINSTANCE="FIL_PRICED"') in rounds
