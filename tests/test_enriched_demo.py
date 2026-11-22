"""The real enriched marts mapping (m_FL_JS_MARTS_ENRICHED), run in DuckDB on hand-made staging rows.

The staging rows look exactly as step 1 writes them, swaps included: stg_orders' dollar columns hold cents,
stg_products.product_price holds cents. Every expected value is worked out by hand from the XML.

  orders  o1 c1 l1 2025-08-30  items i1 (JAF), i2 (BEV)   subtotal 700, tax 42,  total 742.00 (cents)
          o2 c1 l1 2025-08-31  item  i3 (JAF)             subtotal 1600, tax 160, total 1760.00
          o3 c2 l1 2025-08-31  item  i4 (JAF)             subtotal 1100, tax 66,  total 1166.00
          o4 c2 l1 2025-08-15  no items: dropped by JNR_ORDERS_ITEMS_AGG (Master Outer, L1591)
  customers c1 Ann, c2 Bob, c3 Cat (no orders: dropped by JNR_CUSTOMERS, L2243)
  locations l1 Philly AMER tax 0.06; l2 Tokyo (no orders: its extra rows are dropped before any table)
  supplies  JAF-001: 0.07 + 0.50 = 0.57, not perishable; BEV-001: 0.30, perishable

Per item: price 1100.00 (JAF) or 450.00 (BEV); cost 0.57 / 0.30; profit 1099.43 / 449.70;
margin 0.9995 / 0.9993; tax estimate price x 0.06 = 66.00 / 27.00.
Per order: o1 2 lines, revenue 1550.00, cost 0.87, profit 1549.13, margin 0.9994, tax rate 42/700 = 0.06.
Value band: ORDER_TOTAL >= 50 (L1740) compares cents with 50, so every order is HIGH.
Counter (L1706): one running number by customer, day, order: o1 1, o2 2, o3 3.
IS_FIRST_CUSTOMER (L2127) compares each value with itself, so it is 0 and UNIQUE_CUSTOMERS (L2004) is 0.
CUSTOMER_360: recency from $$RUN_DATE 2025-12-31 to 2025-08-31 = 122 days, R 1; F 2 (c1) / 1 (c2);
lifetime spend in cents >= 200, M 3; c1 123 AT_RISK, c2 113 STANDARD. Spend, pre-tax and tax land in each
other's columns (crossed at L2480-2482).
"""
import datetime as dt
from decimal import Decimal as D

import duckdb
import pytest

from pc2dbt.convert import convert_mapping
from pc2dbt.parse import parse_file
from tests.helpers import DEMO_XML, run_model

pytestmark = pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")

STAGING = """
create table stg_customers (customer_id varchar, customer_name varchar);
insert into stg_customers values ('c1', 'Ann'), ('c2', 'Bob'), ('c3', 'Cat');
create table stg_locations (location_id varchar, location_name varchar, opened_date timestamp, tax_rate decimal(6,4), region varchar);
insert into stg_locations values ('l1', 'Philly', '2016-09-01', 0.0600, 'AMER'), ('l2', 'Tokyo', '2017-03-01', 0.1000, 'APAC');
create table stg_orders (order_id varchar, customer_id varchar, location_id varchar, ordered_at_day timestamp,
    subtotal_cents decimal(15,0), tax_paid_cents decimal(15,0), order_total_cents decimal(12,2),
    subtotal decimal(15,0), tax_paid decimal(15,0), order_total decimal(12,2));
insert into stg_orders values
    ('o1', 'c1', 'l1', '2025-08-30', 7, 0, 7.42, 700, 42, 742.00),
    ('o2', 'c1', 'l1', '2025-08-31', 16, 2, 17.60, 1600, 160, 1760.00),
    ('o3', 'c2', 'l1', '2025-08-31', 11, 1, 11.66, 1100, 66, 1166.00),
    ('o4', 'c2', 'l1', '2025-08-15', 5, 0, 5.30, 500, 30, 530.00);
create table stg_order_items (order_item_id varchar, order_id varchar, product_id varchar);
insert into stg_order_items values ('i1', 'o1', 'JAF-001'), ('i2', 'o1', 'BEV-001'), ('i3', 'o2', 'JAF-001'), ('i4', 'o3', 'JAF-001');
create table stg_products (product_id varchar, product_name varchar, product_type varchar,
    product_price_cents decimal(15,0), product_price decimal(12,2), product_description varchar,
    is_food_item decimal(1,0), is_drink_item decimal(1,0));
insert into stg_products values ('JAF-001', 'nutellaphone', 'jaffle', 11, 1100.00, 'warm', 1, 0),
    ('BEV-001', 'tea', 'beverage', 5, 450.00, 'hot', 0, 1);
create table stg_supplies (supply_id varchar, supply_name varchar, supply_cost_cents decimal(12,2),
    supply_cost decimal(12,2), is_perishable decimal(1,0), product_id varchar);
insert into stg_supplies values ('SUP-001', 'knife', 7.00, 0.07, 0, 'JAF-001'),
    ('SUP-002', 'cup', 30.00, 0.30, 1, 'BEV-001'), ('SUP-003', 'bread', 50.00, 0.50, 0, 'JAF-001');
"""
AUG30, AUG31 = dt.datetime(2025, 8, 30), dt.datetime(2025, 8, 31)


@pytest.fixture(scope="module")
def models():
    return {m.name: m for m in convert_mapping(parse_file(DEMO_XML), "m_FL_JS_MARTS_ENRICHED")}


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(STAGING)
    return c


def test_one_model_per_enriched_target_named_after_the_table(models):
    # ORDER_FINANCIALS1 is the instance; the table it writes is ORDER_FINANCIALS (L2391).
    assert sorted(models) == ["customer_360", "order_financials", "order_item_enriched",
                              "product_daily_performance", "store_daily_kpis"]


def test_order_item_enriched(models, con):
    jaffle = ("nutellaphone", "jaffle", D("1100.00"), D("1"), D("0"), D("1100.00"), D("0.57"), D("1099.43"), D("0.9995"),
              D("66.00"), D("1166.00"), D("0"))
    tea = ("tea", "beverage", D("450.00"), D("0"), D("1"), D("450.00"), D("0.30"), D("449.70"), D("0.9993"),
           D("27.00"), D("477.00"), D("1"))
    where = ("l1", "Philly", "AMER")
    assert run_model(con, models["order_item_enriched"].sql) == [
        ("i1", "o1", "JAF-001", "c1", "Ann", *where, AUG30, *jaffle),
        ("i2", "o1", "BEV-001", "c1", "Ann", *where, AUG30, *tea),
        ("i3", "o2", "JAF-001", "c1", "Ann", *where, AUG31, *jaffle),
        ("i4", "o3", "JAF-001", "c2", "Bob", *where, AUG31, *jaffle)]


def test_order_financials_every_order_is_high_value(models, con):
    assert run_model(con, models["order_financials"].sql) == [
        ("o1", "c1", "l1", AUG30, D("700.00"), D("42.00"), D("742.00"), D("2"), D("1550.00"), D("0.87"), D("1549.13"),
         D("0.9994"), D("0.0600"), D("1"), D("1"), D("0.5000"), D("0.5000"), D("1"), "HIGH"),
        ("o2", "c1", "l1", AUG31, D("1600.00"), D("160.00"), D("1760.00"), D("1"), D("1100.00"), D("0.57"), D("1099.43"),
         D("0.9995"), D("0.1000"), D("1"), D("0"), D("1.0000"), D("0.0000"), D("2"), "HIGH"),
        ("o3", "c2", "l1", AUG31, D("1100.00"), D("66.00"), D("1166.00"), D("1"), D("1100.00"), D("0.57"), D("1099.43"),
         D("0.9995"), D("0.0600"), D("1"), D("0"), D("1.0000"), D("0.0000"), D("3"), "HIGH")]


def test_product_daily_performance_copies_the_crossed_flag_and_margin(models, con):
    # L2542-2543: PERISHABLE_SALES_FLAG goes into MARGIN_PCT and the margin into the NUMBER(1,0) flag (rounds to 1).
    assert run_model(con, models["product_daily_performance"].sql, order_by="1, 4") == [
        ("BEV-001", "tea", "beverage", AUG30, D("1"), D("450.00"), D("0.30"), D("449.70"), D("1.0000"), D("1")),
        ("JAF-001", "nutellaphone", "jaffle", AUG30, D("1"), D("1100.00"), D("0.57"), D("1099.43"), D("0.0000"), D("1")),
        ("JAF-001", "nutellaphone", "jaffle", AUG31, D("2"), D("2200.00"), D("1.14"), D("2198.86"), D("0.0000"), D("1"))]


def test_store_daily_kpis_unique_customers_is_always_zero(models, con):
    # Tokyo (l2) has no orders: its extra row from JNR_ADD_LOCATION_INFO has no LOCATION_ID and FIL_LOCS drops it.
    assert run_model(con, models["store_daily_kpis"].sql, order_by="4") == [
        ("l1", "Philly", "AMER", AUG30, D("1"), D("0"), D("742.00"), D("700.00"), D("42.00"), D("0.87"), D("1549.13"),
         D("2.2130"), D("742.00"), D("1"), D("1.0000")),
        ("l1", "Philly", "AMER", AUG31, D("2"), D("0"), D("2926.00"), D("2700.00"), D("226.00"), D("1.14"), D("2198.86"),
         D("0.8144"), D("1463.00"), D("2"), D("1.0000"))]


def test_customer_360_with_the_default_run_date(models, con):
    assert run_model(con, models["customer_360"].sql) == [
        ("c1", "Ann", D("2"), AUG30, AUG31, D("2502.00"), D("2300.00"), D("202.00"), D("1.44"), D("2648.56"), D("1251.00"),
         D("2"), "returning", D("122"), D("1"), D("2"), D("3"), D("123"), "AT_RISK"),
        ("c2", "Bob", D("1"), AUG31, AUG31, D("1166.00"), D("1100.00"), D("66.00"), D("0.57"), D("1099.43"), D("1166.00"),
         D("1"), "new", D("122"), D("1"), D("1"), D("3"), D("113"), "STANDARD")]


def test_customer_360_follows_the_run_date_var(models, con):
    # With run_date 2025-09-30 the last orders are 30 days old: R 3, so c1 (F 2, M 3) is LOYAL; c2 (F 1) stays STANDARD.
    rows = run_model(con, models["customer_360"].sql, dbt_vars={"run_date": "2025-09-30"})
    assert [(r[0], r[13], r[14], r[17], r[18]) for r in rows] == [
        ("c1", D("30"), D("3"), D("323"), "LOYAL"), ("c2", D("30"), D("3"), D("313"), "STANDARD")]


def test_flags_for_the_counter_the_self_compare_and_the_run_date(models):
    def lines(model, kind):
        return sorted(f.line for f in models[model].flags if f.kind == kind)
    assert lines("order_financials", "counter") == [1706]
    assert lines("order_financials", "sort_order") == [1635]
    assert lines("store_daily_kpis", "self_compare") == [2127]
    assert lines("customer_360", "parameter") == [3104]
    assert "L4554" in next(f.message for f in models["customer_360"].flags if f.kind == "parameter")
    assert lines("customer_360", "crossed") == [2480, 2481, 2482]
    assert lines("product_daily_performance", "crossed") == [2542, 2543]


def test_rounding_is_flagged_through_variables_and_the_union(models):
    # Found by the independent check (prompt 13): ITEM_GROSS_MARGIN_PCT divides inside v_MARGIN_CALC (L1513);
    # the order ratios divide in EXP_ORDER_FINANCIALS and reach the target through UN_ORDER_BANDS.
    rounds = lambda model: {f.line for f in models[model].flags if f.kind == "rounds"}
    assert 2530 in rounds("order_item_enriched")
    assert {2494, 2495, 2509, 2510} <= rounds("order_financials")


def test_only_the_counters_sorter_is_kept(models):
    kinds = {b.box: b.note for m in models.values() for b in m.blocks if b.kind == "Sorter"}
    assert kinds["SRT_FOR_CUSTOMER_SEQ"].startswith("kept")
    assert kinds["SRT_FOR_DISTINCT_CUSTOMER"].startswith("dropped")  # its order changes no result (prompt 12)
