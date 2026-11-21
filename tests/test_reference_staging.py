"""Check 3 for the staging mapping: build our project with dbt on DuckDB and compare it with jaffle-shop.

Slow and needs external/ (demo XML and the jaffle-shop clone), so it only runs with:
    pytest -m reference
Every difference must be explained in tests/reference/expected_differences.yml.
"""
import json

import pytest

from tests.helpers import DEMO_XML, ROOT
from tests.reference import harness

pytestmark = [pytest.mark.reference,
              pytest.mark.skipif(not (DEMO_XML.exists() and harness.JAFFLE.exists()), reason="needs external/ clones")]

RESULTS = ROOT / "tests" / "reference" / "results" / "staging.json"


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
    problems += [(t["table"], "rows", t["rows"]["status"]) for t in results["tables"] if t["rows"]["status"] != "matched"]
    assert problems == []
