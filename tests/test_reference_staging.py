"""Check 3 for the staging mapping: build our project with dbt on DuckDB and compare it with jaffle-shop.

Slow and needs external/ (demo XML and the jaffle-shop clone), so it only runs with:
    pytest -m reference
Every difference must be explained in tests/reference/expected_differences.yml.
"""
import csv
import json

import duckdb
import pytest

from tests.helpers import DEMO_XML, ROOT
from tests.reference import harness

pytestmark = [pytest.mark.reference,
              pytest.mark.skipif(not (DEMO_XML.exists() and harness.JAFFLE.exists()), reason="needs external/ clones")]

RESULTS = ROOT / "tests" / "reference" / "results" / "staging.json"
EXAMPLE_ROW = ROOT / "tests" / "reference" / "results" / "example_row.json"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    work = tmp_path_factory.mktemp("staging")
    ours = harness.build_ours(work, ["m_FL_JS_STAGING_FULL"])
    reference = harness.build_reference()
    return ours, reference


def test_our_project_builds_with_dbt_on_duckdb(built):
    ours, _ = built
    assert ours.returncode == 0, ours.log


def test_row_counts_match_the_seed_data(built):
    ours, _ = built
    assert harness.row_counts(ours.db, "main") == {
        "stg_customers": 935, "stg_locations": 6, "stg_order_items": 90900,
        "stg_orders": 61948, "stg_products": 10, "stg_supplies": 65}


def test_every_difference_from_jaffle_shop_is_explained(built):
    ours, reference = built
    results = harness.compare(ours.db, reference.db, harness.load_expected("staging"))
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(results, indent=2) + "\n")
    problems = [(t["table"], c["ours"] or c["reference"], c["status"])
                for t in results["tables"] for c in t["columns"] if c["status"] in ("unexplained", "stale")]
    problems += [(t["table"], "rows", t["rows"]["status"]) for t in results["tables"]
                 if t["rows"]["status"] not in ("matched", "explained")]
    assert problems == []


def one_row(db, table: str, key: str, value: str) -> dict:
    con = duckdb.connect(str(db), read_only=True)
    cur = con.execute(f"select * from main.{table} where {key} = ?", [value])
    names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    assert len(rows) == 1
    return {n: (None if v is None else str(v)) for n, v in zip(names, rows[0])}


def test_the_example_page_row_comes_from_both_builds(built):
    """Writes the row docs/example.html shows: the first order in raw_orders.csv, from our stg_orders and
    from jaffle-shop's. tools/docs/build_example_output.py puts it on the page."""
    ours, reference = built
    with open(harness.SEEDS / "raw_orders.csv", newline="") as f:
        raw = next(csv.DictReader(f))
    row = {"raw": raw, "ours": one_row(ours.db, "stg_orders", "order_id", raw["id"]),
           "reference": one_row(reference.db, "stg_orders", "order_id", raw["id"]),
           "rows": {"ours": harness.row_counts(ours.db, "main")["stg_orders"],
                    "reference": harness.row_counts(reference.db, "main")["stg_orders"]}}
    EXAMPLE_ROW.write_text(json.dumps(row, indent=2) + "\n")
    assert row["ours"]["subtotal"] == row["raw"]["subtotal"]  # cents land in the dollar column (L611)
