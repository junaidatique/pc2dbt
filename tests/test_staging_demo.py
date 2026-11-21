"""The real staging mapping, run in DuckDB on a few hand-made raw rows.

Raw tables use the XML's PC Source column types (decision Q14). Every expected value is
worked out by hand from the XML, including its mistakes (decision D1).
"""
import datetime as dt
from decimal import Decimal as D

import duckdb
import pytest

from pc2dbt.convert import convert_mapping
from pc2dbt.parse import parse_file
from tests.helpers import DEMO_XML, run_model

pytestmark = pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")

RAW = """
create schema raw;
create table raw.raw_customers (id varchar, name varchar);
insert into raw.raw_customers values ('c1', 'Ann');
create table raw.raw_orders (id varchar, customer varchar, ordered_at timestamp, store_id varchar,
                             subtotal decimal(15,0), tax_paid decimal(15,0), order_total decimal(12,2));
insert into raw.raw_orders values ('o1', 'c1', '2024-09-01 15:01:00', 's1', 700, 42, 742),
                                  ('o2', 'c1', '2025-01-31 08:00:00', 's1', 1600, 158, 1758);
create table raw.raw_items (id varchar, order_id varchar, sku varchar);
insert into raw.raw_items values ('i1', 'o1', 'JAF-001'), ('i2', null, 'BEV-001');
create table raw.raw_products (sku varchar, name varchar, type varchar, price decimal(15,0), description varchar);
insert into raw.raw_products values ('JAF-001', 'nutellaphone', 'jaffle', 1100, 'warm'),
                                    ('BEV-001', 'tea', 'beverage', 450, 'hot');
create table raw.raw_supplies (id varchar, name varchar, cost decimal(15,0), perishable varchar, sku varchar);
insert into raw.raw_supplies values ('SUP-001', 'knife', 7, 'False', 'JAF-001'),
                                    ('SUP-002', 'cup', 30, 'True', 'BEV-001'),
                                    ('SUP-009', 'ghost', 5, 'Y', 'NOPE-001');
create table raw.raw_stores (id varchar, name varchar, opened_at timestamp, tax_rate decimal(6,4));
insert into raw.raw_stores values ('s1', 'Philadelphia', '2016-09-01 10:00:00', 0.06),
                                  ('s2', 'Tokyo', '2017-03-01 09:00:00', 0.10),
                                  ('s3', 'Berlin', '2018-05-01 08:00:00', 0.20),
                                  ('s4', 'Nowhere', '2019-01-01 00:00:00', null);
"""


@pytest.fixture(scope="module")
def models():
    return {m.name: m for m in convert_mapping(parse_file(DEMO_XML), "m_FL_JS_STAGING_FULL")}


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(RAW)
    return c


def test_one_model_per_staging_target(models):
    assert sorted(models) == ["stg_customers", "stg_locations", "stg_order_items", "stg_orders", "stg_products", "stg_supplies"]
    assert {m.folder for m in models.values()} == {"m_fl_js_staging_full"}


def test_stg_orders_copies_the_swap_and_rounds_at_the_target(models, con):
    # *_CENTS get dollars (L608-610), rounded by their NUMBER(15,0)/(12,2) columns; the dollar columns get cents.
    assert run_model(con, models["stg_orders"].sql) == [
        ("o1", "c1", "s1", dt.datetime(2024, 9, 1), D("7"), D("0"), D("7.42"), D("700"), D("42"), D("742.00")),
        ("o2", "c1", "s1", dt.datetime(2025, 1, 31), D("16"), D("2"), D("17.58"), D("1600"), D("158"), D("1758.00")),
    ]


def test_stg_orders_flags_the_six_crossed_connectors(models):
    assert sorted(f.line for f in models["stg_orders"].flags if f.kind == "crossed") == [608, 609, 610, 611, 612, 613]


def test_stg_orders_flags_the_two_digit_year_round_trip(models):
    assert [f.line for f in models["stg_orders"].flags if f.kind == "century"] == [110]  # decision Q16


def test_stg_products_copies_the_price_swap(models, con):
    assert run_model(con, models["stg_products"].sql) == [
        ("BEV-001", "tea", "beverage", D("5"), D("450.00"), "hot", D("0"), D("1")),
        ("JAF-001", "nutellaphone", "jaffle", D("11"), D("1100.00"), "warm", D("1"), D("0")),
    ]
    assert sorted(f.line for f in models["stg_products"].flags if f.kind == "crossed") == [620, 621]


def test_stg_supplies_inner_joins_products_and_reads_perishable_as_text(models, con):
    assert run_model(con, models["stg_supplies"].sql) == [
        ("SUP-001", "knife", D("7.00"), D("0.07"), D("0"), "JAF-001"),
        ("SUP-002", "cup", D("30.00"), D("0.30"), D("0"), "BEV-001"),  # 'True' is neither 'Y' nor '1'
    ]


def test_stg_locations_routes_every_region_and_drops_null_tax_rate(models, con):
    assert run_model(con, models["stg_locations"].sql) == [
        ("s1", "Philadelphia", dt.datetime(2016, 9, 1), D("0.0600"), "AMER"),
        ("s2", "Tokyo", dt.datetime(2017, 3, 1), D("0.1000"), "APAC"),
        ("s3", "Berlin", dt.datetime(2018, 5, 1), D("0.2000"), "EMEA"),
    ]


def test_stg_order_items_drops_null_order_id(models, con):
    assert run_model(con, models["stg_order_items"].sql) == [("i1", "o1", "JAF-001")]


def test_stg_customers_renames(models, con):
    assert run_model(con, models["stg_customers"].sql) == [("c1", "Ann")]
