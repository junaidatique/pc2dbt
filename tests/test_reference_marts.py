"""Check 3 for the core marts mapping: build staging + core marts with dbt on DuckDB, compare with jaffle-shop.

Slow and needs external/ (demo XML and the jaffle-shop clone), so it only runs with:
    pytest -m reference
Every difference, including rows that exist on one side only, must be explained in
tests/reference/expected_differences.yml (section marts).
"""
import json

import pytest

from tests.helpers import DEMO_XML, ROOT
from tests.reference import harness

pytestmark = [pytest.mark.reference,
              pytest.mark.skipif(not (DEMO_XML.exists() and harness.JAFFLE.exists()), reason="needs external/ clones")]

RESULTS = ROOT / "tests" / "reference" / "results" / "marts.json"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    work = tmp_path_factory.mktemp("marts")
    ours = harness.build_ours(work, ["m_FL_JS_STAGING_FULL", "m_FL_JS_MARTS_CORE"])
    reference = harness.build_reference()
    return ours, reference


def test_our_project_builds_with_dbt_on_duckdb(built):
    ours, _ = built
    assert ours.returncode == 0, ours.log


def test_mart_row_counts(built):
    # orders: 61,948 orders minus the 483 with no items, dropped by the Master Outer Join at L3519.
    ours, _ = built
    counts = harness.row_counts(ours.db, "main")
    assert {t: counts[t] for t in ("customers", "orders", "order_items", "products", "supplies")} == {
        "customers": 935, "orders": 61465, "order_items": 90900, "products": 10, "supplies": 65}


def test_every_difference_from_jaffle_shop_is_explained(built):
    ours, reference = built
    results = harness.compare(ours.db, reference.db, harness.load_expected("marts"))
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(results, indent=2) + "\n")
    problems = [(t["table"], c["ours"] or c["reference"], c["status"])
                for t in results["tables"] for c in t["columns"] if c["status"] in ("unexplained", "stale")]
    problems += [(t["table"], "rows", t["rows"]["status"]) for t in results["tables"]
                 if t["rows"]["status"] not in ("matched", "explained")]
    assert problems == []
