"""The real core marts mapping (m_FL_JS_MARTS_CORE), run in DuckDB on hand-made staging rows.

The staging rows look exactly as step 1 writes them, swap included (L608-613, L620-621): in stg_orders the
*_cents columns hold dollars rounded to whole numbers and the dollar columns hold cents. Every expected
value is worked out by hand from the XML, mistakes included (decision D1).

  orders  o1 c1 2024-09-01  items i1 (JAF), i2 (BEV)
          o2 c1 2025-01-31  item  i3 (JAF)
          o3 c2 2025-02-01  no items
          o4 c2 2024-06-01  item  i4 (JAF)
          o5 c4 2025-04-01  item  i5 (BEV)
  customers c1 Ann, c2 Bob, c3 Cat (no orders), c4 Dan
  supplies  JAF-001: 0.07 + 0.50 = 0.57 per item; BEV-001: 0.30 per item

ORDERS: JNR_ORDERS_ITEMS_AGG (L3519) is a Master Outer Join whose detail side is the per-order item
aggregate, so o3 (no items) is dropped. EXP_ORDERS_CALC divides SUBTOTAL_CENTS by 100 (L3534), but that
column holds whole dollars, so the amounts come out 100 times too small: o1 7 -> 0.07. The counter runs
over all rows sorted by customer, day, order (L3554): o1=1, o2=2, o4=3, o5=4; it never restarts.

CUSTOMERS: AGG_ORDERS_BY_CUSTOMER sums SUBTOTAL, TAX_PAID and ORDER_TOTAL, which hold cents, so the
lifetime amounts come out 100 times too big: c1 742.00 + 1758.00 = 2500.00. JNR_CUSTOMERS_ORDERS
(L3664) is a Master Outer Join with customers as master, so c3 (no orders) is dropped.
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
insert into stg_customers values ('c1', 'Ann'), ('c2', 'Bob'), ('c3', 'Cat'), ('c4', 'Dan');
create table stg_orders (order_id varchar, customer_id varchar, location_id varchar, ordered_at_day timestamp,
    subtotal_cents decimal(15,0), tax_paid_cents decimal(15,0), order_total_cents decimal(12,2),
    subtotal decimal(15,0), tax_paid decimal(15,0), order_total decimal(12,2));
insert into stg_orders values
    ('o1', 'c1', 's1', '2024-09-01', 7, 0, 7.42, 700, 42, 742.00),
    ('o2', 'c1', 's1', '2025-01-31', 16, 2, 17.58, 1600, 158, 1758.00),
    ('o3', 'c2', 's1', '2025-02-01', 5, 0, 5.30, 500, 30, 530.00),
    ('o4', 'c2', 's1', '2024-06-01', 11, 1, 11.66, 1100, 66, 1166.00),
    ('o5', 'c4', 's1', '2025-04-01', 5, 0, 4.77, 450, 27, 477.00);
create table stg_order_items (order_item_id varchar, order_id varchar, product_id varchar);
insert into stg_order_items values ('i1', 'o1', 'JAF-001'), ('i2', 'o1', 'BEV-001'), ('i3', 'o2', 'JAF-001'),
    ('i4', 'o4', 'JAF-001'), ('i5', 'o5', 'BEV-001');
create table stg_products (product_id varchar, product_name varchar, product_type varchar,
    product_price_cents decimal(15,0), product_price decimal(12,2), product_description varchar,
    is_food_item decimal(1,0), is_drink_item decimal(1,0));
insert into stg_products values ('JAF-001', 'nutellaphone', 'jaffle', 11, 1100.00, 'warm', 1, 0),
    ('BEV-001', 'tea', 'beverage', 5, 450.00, 'hot', 0, 1);
create table stg_supplies (supply_id varchar, supply_name varchar, supply_cost_cents decimal(12,2),
    supply_cost decimal(12,2), is_perishable decimal(1,0), product_id varchar);
insert into stg_supplies values ('SUP-001', 'knife', 7.00, 0.07, 0, 'JAF-001'),
    ('SUP-002', 'cup', 30.00, 0.30, 0, 'BEV-001'), ('SUP-003', 'bread', 50.00, 0.50, 0, 'JAF-001');
"""


@pytest.fixture(scope="module")
def models():
    return {m.name: m for m in convert_mapping(parse_file(DEMO_XML), "m_FL_JS_MARTS_CORE")}


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(STAGING)
    return c


def test_one_model_per_core_target(models):
    assert sorted(models) == ["customers", "order_items", "orders", "products", "supplies"]
    assert {m.folder for m in models.values()} == {"m_fl_js_marts_core"}


def test_orders_drops_orders_without_items_and_counts_across_customers(models, con):
    assert run_model(con, models["orders"].sql) == [
        ("o1", "c1", "s1", dt.datetime(2024, 9, 1), D("0.07"), D("0.00"), D("0.07"), D("1550.00"), D("0.87"), D("1"), D("1"), D("1")),
        ("o2", "c1", "s1", dt.datetime(2025, 1, 31), D("0.16"), D("0.02"), D("0.18"), D("1100.00"), D("0.57"), D("1"), D("0"), D("2")),
        ("o4", "c2", "s1", dt.datetime(2024, 6, 1), D("0.11"), D("0.01"), D("0.12"), D("1100.00"), D("0.57"), D("1"), D("0"), D("3")),
        ("o5", "c4", "s1", dt.datetime(2025, 4, 1), D("0.05"), D("0.00"), D("0.05"), D("450.00"), D("0.30"), D("0"), D("1"), D("4")),
    ]


def test_orders_flags_the_counter_its_sorter_and_both_master_outer_joins(models):
    flags = models["orders"].flags
    assert [f.line for f in flags if f.kind == "counter"] == [3589]
    assert [f.line for f in flags if f.kind == "sort_order"] == [3554]
    assert sorted(f.line for f in flags if f.kind == "master_outer") == [3446, 3519]


def test_orders_flags_every_amount_the_target_rounds(models):
    # SUBTOTAL and TAX_PAID arrive as doubles; ORDER_TOTAL is declared decimal(12,2) but is computed as
    # ORDER_TOTAL_CENTS/100 (L3536). With high precision off it is a double at run time, so 7.42/100 = 0.0742
    # reaches the NUMBER(12,2) column and becomes 0.07 (decision Q11).
    assert sorted(f.line for f in models["orders"].flags if f.kind == "rounds") == [3783, 3784, 3785]


def test_customers_sums_cents_and_drops_customers_without_orders(models, con):
    assert run_model(con, models["customers"].sql) == [
        ("c1", "Ann", D("2"), dt.datetime(2024, 9, 1), dt.datetime(2025, 1, 31), D("2500.00"), D("2300.00"), D("200.00"), "returning"),
        ("c2", "Bob", D("2"), dt.datetime(2024, 6, 1), dt.datetime(2025, 2, 1), D("1696.00"), D("1600.00"), D("96.00"), "returning"),
        ("c4", "Dan", D("1"), dt.datetime(2025, 4, 1), dt.datetime(2025, 4, 1), D("477.00"), D("450.00"), D("27.00"), "new"),
    ]


def test_customers_flags_its_master_outer_join(models):
    assert [f.line for f in models["customers"].flags if f.kind == "master_outer"] == [3664]


def test_order_items_adds_product_and_supply_cost(models, con):
    # PRODUCT_PRICE comes from stg_products.product_price, which holds cents (swap at L621).
    jaffle = ("nutellaphone", "jaffle", D("1100.00"), D("1"), D("0"), D("0.57"), D("0"))
    tea = ("tea", "beverage", D("450.00"), D("0"), D("1"), D("0.30"), D("0"))
    assert run_model(con, models["order_items"].sql) == [
        ("i1", "o1", "JAF-001", dt.datetime(2024, 9, 1), *jaffle),
        ("i2", "o1", "BEV-001", dt.datetime(2024, 9, 1), *tea),
        ("i3", "o2", "JAF-001", dt.datetime(2025, 1, 31), *jaffle),
        ("i4", "o4", "JAF-001", dt.datetime(2024, 6, 1), *jaffle),
        ("i5", "o5", "BEV-001", dt.datetime(2025, 4, 1), *tea),
    ]
    assert [f.line for f in models["order_items"].flags if f.kind == "master_outer"] == [3319]


def test_products_and_supplies_pass_staging_through(models, con):
    assert run_model(con, models["products"].sql) == [
        ("BEV-001", "tea", "beverage", D("5"), D("450.00"), "hot", D("0"), D("1")),
        ("JAF-001", "nutellaphone", "jaffle", D("11"), D("1100.00"), "warm", D("1"), D("0"))]
    assert run_model(con, models["supplies"].sql) == [
        ("SUP-001", "knife", D("7.00"), D("0.07"), D("0"), "JAF-001"),
        ("SUP-002", "cup", D("30.00"), D("0.30"), D("0"), "BEV-001"),
        ("SUP-003", "bread", D("50.00"), D("0.50"), D("0"), "JAF-001")]
