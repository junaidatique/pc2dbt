"""Step 4 (translate): Informatica expressions become DuckDB SQL with the same results.

Each case runs the translated SQL in DuckDB and checks the value PowerCenter would give,
including NULLs. Expected values are worked out by hand from Informatica's rules.
"""
import datetime as dt
from decimal import Decimal

import duckdb
import pytest

from pc2dbt.expr import Symbol, UnsupportedFunction, translate


def evaluate(expr: str, symbols: dict, row: dict, types: dict):
    """Translate, then run the SQL over one row whose columns have the given DuckDB types."""
    sql = translate(expr, symbols)
    cols = list(row)
    con = duckdb.connect()
    con.execute("create table t (" + ", ".join(f"{c} {types[c]}" for c in cols) + ")")
    con.execute(f"insert into t values ({', '.join('?' for _ in cols)})", [row[c] for c in cols])
    return con.execute(f"select {sql} from t").fetchone()[0]


TAX = {"TAX_RATE": Symbol("tax_rate", "decimal")}
REGION = "IIF(TAX_RATE >= 0.15,'EMEA',\r\nIIF(TAX_RATE >= 0.09,'APAC','AMER'))"


@pytest.mark.parametrize("tax, want", [
    (Decimal("0.2"), "EMEA"),
    (Decimal("0.1"), "APAC"),
    (Decimal("0.04"), "AMER"),
    (None, "AMER"),  # a NULL condition takes IIF's false branch
])
def test_nested_iif_region(tax, want):
    assert evaluate(REGION, TAX, {"tax_rate": tax}, {"tax_rate": "decimal(6,4)"}) == want


TYPE = {"TYPE": Symbol("type", "string")}
FOOD = "IIF( UPPER(LTRIM(RTRIM(TYPE))) = 'JAFFLE', 1, 0 )"


@pytest.mark.parametrize("value, want", [(" jaffle ", 1), ("JAFFLE", 1), ("beverage", 0), (None, 0)])
def test_trimmed_case_insensitive_flag(value, want):
    assert evaluate(FOOD, TYPE, {"type": value}, {"type": "varchar"}) == want


PERISH = {"PERISHABLE": Symbol("perishable", "string")}


@pytest.mark.parametrize("value, want", [("Y", 1), ("1", 1), ("True", 0), ("y", 0), (None, 0)])
def test_or_condition_compares_text_exactly(value, want):
    assert evaluate("IIF(PERISHABLE = 'Y' OR PERISHABLE = '1', 1, 0)", PERISH, {"perishable": value}, {"perishable": "varchar"}) == want


def test_division_keeps_decimals():
    syms = {"SUBTOTAL_IN": Symbol("subtotal_in", "double")}
    assert evaluate("SUBTOTAL_IN/100", syms, {"subtotal_in": Decimal("742")}, {"subtotal_in": "decimal(15,0)"}) == pytest.approx(7.42)


def test_two_digit_year_round_trip_keeps_the_day():
    syms = {"ORDERED_AT": Symbol("ordered_at", "date/time")}
    got = evaluate("TO_DATE(TO_CHAR(ORDERED_AT, 'DD-MM-YY'), 'DD-MM-YY')", syms,
                   {"ordered_at": dt.datetime(2024, 9, 1, 15, 1)}, {"ordered_at": "timestamp"})
    assert got == dt.datetime(2024, 9, 1, 0, 0)


def test_trunc_on_a_date_drops_the_time():
    syms = {"OPENED_AT": Symbol("opened_at", "date/time")}
    assert evaluate("TRUNC(OPENED_AT)", syms, {"opened_at": dt.datetime(2016, 9, 1, 10, 30)},
                    {"opened_at": "timestamp"}) == dt.datetime(2016, 9, 1)


def test_isnull():
    syms = {"X": Symbol("x", "string")}
    assert evaluate("ISNULL(X)", syms, {"x": None}, {"x": "varchar"}) is True
    assert evaluate("ISNULL(X)", syms, {"x": "a"}, {"x": "varchar"}) is False


def test_unknown_function_names_itself():
    with pytest.raises(UnsupportedFunction) as err:
        translate("DECODE(X, 1, 'one')", {"X": Symbol("x", "integer")})
    assert err.value.name == "DECODE"


def test_unknown_port_is_an_error():
    with pytest.raises(KeyError):
        translate("MISSING + 1", {})


# ---------------------------------------------------------------- aggregates (Aggregator boxes only)

def aggregate(expr: str, values: list) -> object:
    """Translate an Aggregator expression and run it over a one-column table of `values`."""
    sql = translate(expr, {"AMOUNT": Symbol("amount", "decimal")}, aggregates=True)
    con = duckdb.connect()
    con.execute("create table t (amount decimal(8,2))")
    con.executemany("insert into t values (?)", [[v] for v in values])
    return con.execute(f"select {sql} from t").fetchone()[0]


AMOUNTS = [Decimal("5.50"), None, Decimal("2.00")]


@pytest.mark.parametrize("expr, want", [
    ("COUNT(*)", 3),                      # every row
    ("COUNT(AMOUNT)", 2),                 # NULLs are not counted
    ("SUM(AMOUNT)", Decimal("7.50")),     # NULLs are skipped
    ("MIN(AMOUNT)", Decimal("2.00")),
    ("MAX(AMOUNT)", Decimal("5.50")),
    ("SUM(IIF(ISNULL(AMOUNT), 0, AMOUNT))", Decimal("7.50")),
])
def test_aggregate_functions(expr, want):
    assert aggregate(expr, AMOUNTS) == want


def test_sum_of_only_nulls_is_null():
    assert aggregate("SUM(AMOUNT)", [None, None]) is None


def test_aggregate_outside_an_aggregator_is_not_translated():
    with pytest.raises(UnsupportedFunction) as e:
        translate("SUM(AMOUNT)", {"AMOUNT": Symbol("amount", "decimal")})
    assert e.value.name == "SUM"


# ---------------------------------------------------------------- DATE_DIFF

DATES = {"D1": Symbol("d1", "date/time"), "D2": Symbol("d2", "date/time")}
DATE_TYPES = {"d1": "timestamp", "d2": "timestamp"}


def test_date_diff_in_days_keeps_fractions():
    # Informatica returns date1 - date2 in the unit asked for, with fractions (not calendar boundaries).
    row = {"d1": dt.datetime(2025, 6, 30), "d2": dt.datetime(2025, 6, 29, 12, 0)}
    assert evaluate("DATE_DIFF(D1, D2, 'DD')", DATES, row, DATE_TYPES) == 0.5


def test_date_diff_of_truncated_days_is_whole():
    row = {"d1": dt.datetime(2025, 12, 31, 9, 0), "d2": dt.datetime(2025, 8, 31, 18, 46)}
    assert evaluate("DATE_DIFF(TRUNC(D1), TRUNC(D2), 'DD')", DATES, row, DATE_TYPES) == 122


def test_date_diff_in_other_units_is_not_translated():
    with pytest.raises(UnsupportedFunction) as e:
        translate("DATE_DIFF(D1, D2, 'MM')", DATES)
    assert "DATE_DIFF" in e.value.name
