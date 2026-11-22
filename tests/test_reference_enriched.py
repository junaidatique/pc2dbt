"""Checks 2 and 3 for the enriched marts, which have no jaffle-shop twin (prompt 12).

Check 2, seed facts: each fact is answered twice, once from our enriched models and once by a small query
written straight against the raw seed tables (never our models). They must agree.
Check 3, twins: where an enriched column repeats a jaffle-shop mart column, compare it with the same list
of expected differences as the other marts (tests/reference/expected_differences.yml, section enriched).

Slow and needs external/, so it only runs with:  pytest -m reference
"""
import json

import duckdb
import pytest

from tests.helpers import DEMO_XML, ROOT
from tests.reference import harness

pytestmark = [pytest.mark.reference,
              pytest.mark.skipif(not (DEMO_XML.exists() and harness.JAFFLE.exists()), reason="needs external/ clones")]

RESULTS = ROOT / "tests" / "reference" / "results"
MAPPINGS = ["m_FL_JS_STAGING_FULL", "m_FL_JS_MARTS_CORE", "m_FL_JS_MARTS_ENRICHED"]

# Orders that reach the enriched marts: only those with items (JNR_ORDERS_ITEMS_AGG keeps the item side, L1591).
SEED_ORDERS = """(select id, customer, store_id, date_trunc('day', ordered_at) as day, order_total from raw.raw_orders o
                  where exists (select 1 from raw.raw_items i where i.order_id = o.id))"""
SEED_CUSTOMERS = f"(select customer, count(*) as n, max(day) as last_day, sum(order_total) as spend from {SEED_ORDERS} group by 1)"
# RFM exactly as the XML writes it (L2341-2343, L2366), applied to the raw seed with $$RUN_DATE's default.
SEED_RFM = f"""(select *, case when n = 0 then 'PROSPECT' when r * 100 + f * 10 + m = 333 then 'CHAMPION'
                              when r = 3 and f >= 2 and m >= 2 then 'LOYAL' when r = 1 and f >= 2 then 'AT_RISK'
                              else 'STANDARD' end as segment
               from (select n, case when rec <= 30 then 3 when rec <= 90 then 2 else 1 end as r,
                            case when n >= 5 then 3 when n >= 2 then 2 else 1 end as f,
                            case when spend >= 200 then 3 when spend >= 50 then 2 else 1 end as m
                     from (select n, spend, date_diff('day', last_day, timestamp '2025-12-31') as rec from {SEED_CUSTOMERS})))"""
# Per product-day as the XML computes it: perishable by the L504 rule, margin = (revenue - cost) / revenue.
SEED_PRODUCT_DAYS = f"""(select i.sku, o.day, sum(p.price) as revenue, sum(c.cost) as cogs, max(c.perishable) as perishable
                        from raw.raw_items i join {SEED_ORDERS} o on o.id = i.order_id join raw.raw_products p on p.sku = i.sku
                        join (select sku, sum(cost / 100) as cost,
                                     max(case when perishable in ('Y', '1') then 1 else 0 end) as perishable
                              from raw.raw_supplies group by 1) c on c.sku = i.sku
                        group by 1, 2)"""
# Item margin as the XML computes it (L1513): price in cents (staging swap at L621) against supply cost in dollars.
SEED_MARGINS = """(select cast(round((p.price - s.cost) / p.price, 4) as decimal(10,4)) as margin from raw.raw_items i
                   join raw.raw_products p on p.sku = i.sku
                   join (select sku, sum(cost / 100) as cost from raw.raw_supplies group by 1) s on s.sku = i.sku)"""

# (fact, query on our models, query on the raw seed)
FACTS = [
    ("Last order day in the seed",
     "select max(last_ordered_at) from customer_360", "select max(date_trunc('day', ordered_at)) from raw.raw_orders"),
    ("Smallest recency in days (run_date 2025-12-31)",
     "select min(recency_days) from customer_360",
     f"select min(date_diff('day', last_day, timestamp '2025-12-31')) from {SEED_CUSTOMERS}"),
    ("Customers with recency score 1 (L2341: more than 90 days)",
     "select count(*) from customer_360 where r_score = 1", f"select count(*) from {SEED_RFM} where r = 1"),
    ("Lowest lifetime spend in cents (lands in LIFETIME_SPEND_PRETAX, L2480)",
     "select min(lifetime_spend_pretax) from customer_360", f"select min(spend) from {SEED_CUSTOMERS}"),
    ("Customers with spend score 3 (L2343: 200 or more, here in cents)",
     "select count(*) from customer_360 where m_score = 3", f"select count(*) from {SEED_RFM} where m = 3"),
    ("CHAMPION or LOYAL customers",
     "select count(*) from customer_360 where rfm_segment in ('CHAMPION', 'LOYAL')",
     f"select count(*) from {SEED_RFM} where segment in ('CHAMPION', 'LOYAL')"),
    ("AT_RISK customers (2 or more orders)",
     "select count(*) from customer_360 where rfm_segment = 'AT_RISK'", f"select count(*) from {SEED_RFM} where segment = 'AT_RISK'"),
    ("STANDARD customers (1 order)",
     "select count(*) from customer_360 where rfm_segment = 'STANDARD'", f"select count(*) from {SEED_RFM} where segment = 'STANDARD'"),
    ("Customers in CUSTOMER_360", "select count(*) from customer_360", f"select count(*) from {SEED_CUSTOMERS}"),
    ("Orders in ORDER_FINANCIALS", "select count(*) from order_financials", f"select count(*) from {SEED_ORDERS}"),
    ("Orders in the HIGH band (ORDER_TOTAL >= 50 compares cents, L1740)",
     "select count(*) from order_financials where order_value_band = 'HIGH'",
     f"select count(*) from {SEED_ORDERS} where order_total >= 50"),
    ("Store-days where UNIQUE_CUSTOMERS is not 0 (L2004, L2127)",
     "select count(*) from store_daily_kpis where unique_customers <> 0",
     # the flag is 1 only where location, day or customer is NULL, so a store-day is non-zero only if it has such an order
     f"select count(*) from (select store_id, day from {SEED_ORDERS} group by 1, 2 "
     f"having count(*) filter (where customer is null or store_id is null or day is null) > 0)"),
    ("Store-days where HIGH_VALUE_ORDERS differs from ORDERS_COUNT",
     "select count(*) from store_daily_kpis where high_value_orders <> orders_count",
     f"select count(*) from (select store_id, day from {SEED_ORDERS} group by 1, 2 "
     f"having count(*) filter (where order_total is null or order_total < 50) > 0)"),
    ("Store-days in STORE_DAILY_KPIS", "select count(*) from store_daily_kpis",
     f"select count(*) from (select distinct store_id, day from {SEED_ORDERS})"),
    ("Stores in STORE_DAILY_KPIS", "select count(distinct location_id) from store_daily_kpis",
     f"select count(distinct store_id) from {SEED_ORDERS}"),
    ("Rows in ORDER_ITEM_ENRICHED", "select count(*) from order_item_enriched", "select count(*) from raw.raw_items"),
    ("Product-days in PRODUCT_DAILY_PERFORMANCE", "select count(*) from product_daily_performance",
     f"select count(*) from (select distinct i.sku, o.day from raw.raw_items i join {SEED_ORDERS} o on o.id = i.order_id)"),
    # Found in prompt 13 (caught by you): the margins.
    ("Lowest item margin (price in cents, cost in dollars, L1513)",
     "select min(item_gross_margin_pct) from order_item_enriched", f"select min(margin) from {SEED_MARGINS}"),
    ("Highest item margin (price in cents, cost in dollars, L1513)",
     "select max(item_gross_margin_pct) from order_item_enriched", f"select max(margin) from {SEED_MARGINS}"),
    ("Supplies marked perishable (the L504 rule never matches the seed's True/False)",
     "select count(*) from stg_supplies where is_perishable <> 0",
     "select count(*) from raw.raw_supplies where perishable in ('Y', '1')"),
    ("Product-days with MARGIN_PCT 0 and PERISHABLE_SALES_FLAG 1 (crossed at L2542-2543)",
     "select count(*) from product_daily_performance where margin_pct = 0 and perishable_sales_flag = 1",
     # MARGIN_PCT gets the perishable flag and the flag gets the margin rounded to 0 places
     f"select count(*) from {SEED_PRODUCT_DAYS} where perishable = 0 and round((revenue - cogs) / revenue, 0) = 1"),
]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    ours = harness.build_ours(tmp_path_factory.mktemp("enriched"), MAPPINGS)
    return ours, harness.build_reference()


def test_our_project_builds_with_dbt_on_duckdb(built):
    ours, _ = built
    assert ours.returncode == 0, ours.log


def test_seed_facts(built):
    ours, _ = built
    con = duckdb.connect(str(ours.db), read_only=True)
    one = lambda sql: con.execute(sql).fetchone()[0]
    facts = []
    for fact, mine, seed in FACTS:
        got, want = one(mine), one(seed)
        facts.append({"fact": fact, "ours": str(got), "seed": str(want), "status": "match" if got == want else "differs"})
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "enriched_facts.json").write_text(json.dumps(facts, indent=2) + "\n")
    assert [f for f in facts if f["status"] != "match"] == []


def test_every_difference_from_jaffle_shop_twins_is_explained(built):
    ours, reference = built
    results = harness.compare(ours.db, reference.db, harness.load_expected("enriched"))
    (RESULTS / "enriched.json").write_text(json.dumps(results, indent=2) + "\n")
    problems = [(t["table"], c["ours"] or c["reference"], c["status"])
                for t in results["tables"] for c in t["columns"] if c["status"] in ("unexplained", "stale")]
    problems += [(t["table"], "rows", t["rows"]["status"]) for t in results["tables"]
                 if t["rows"]["status"] not in ("matched", "explained")]
    assert problems == []
