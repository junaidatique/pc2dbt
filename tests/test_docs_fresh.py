"""The explainer pages show what the code produces now, not what it produced when a page was written.

Each generated file in docs/assets/ is rebuilt into a temporary folder from today's inputs (the demo
XML, out/, tests/reference/results/) and must be byte-identical to the committed one. When a test
fails, rerun the builder it names. log-data.js is left out: its builder checks every prompt against
the saved conversation, which only exists on the machine that ran the session.
"""
import json
import re
import subprocess
import sys

import pytest

from tests.helpers import DEMO_XML, ROOT

ASSETS = ROOT / "docs" / "assets"
RESULTS = ROOT / "tests" / "reference" / "results"
needs_xml = pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")

BUILDERS = {
    "example-data.js": ["-I", "tools/docs/build_example_data.py", str(DEMO_XML)],
    "input-data.js": ["-I", "tools/docs/build_input_data.py", str(DEMO_XML)],
    "results-data.js": ["tools/docs/build_results_data.py", str(DEMO_XML), "{out}",
                        f"m_FL_JS_STAGING_FULL={RESULTS / 'staging.json'}",
                        f"m_FL_JS_MARTS_CORE={RESULTS / 'marts.json'}",
                        f"m_FL_JS_MARTS_ENRICHED={RESULTS / 'enriched.json'}+{RESULTS / 'enriched_facts.json'}"],
    "example-output.js": ["-I", "tools/docs/build_example_output.py", str(ROOT / "out"), str(RESULTS / "example_row.json")],
}


def rebuilt(name: str, tmp_path) -> str:
    out = tmp_path / name
    args = BUILDERS[name]
    args = [a.replace("{out}", str(out)) for a in args] if "{out}" in args else args + [str(out)]
    done = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    return out.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["example-data.js", "input-data.js", "results-data.js"])
@needs_xml
def test_the_generated_page_data_matches_its_builder(name, tmp_path):
    assert (ASSETS / name).read_text(encoding="utf-8") == rebuilt(name, tmp_path), \
        f"docs/assets/{name} is stale: rerun its builder (see tests/test_docs_fresh.py)"


def test_the_example_page_output_matches_out_and_the_last_build(tmp_path):
    assert (ASSETS / "example-output.js").read_text(encoding="utf-8") == rebuilt("example-output.js", tmp_path), \
        "docs/assets/example-output.js is stale: rerun tools/docs/build_example_output.py"


def example_output() -> dict:
    text = (ASSETS / "example-output.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.EXAMPLE_OUTPUT = (\{.*\});\s*$", text, re.S)[1])


def test_the_example_page_shows_the_generated_stg_orders_word_for_word():
    data = example_output()
    assert data["sql"] == (ROOT / "out" / "models" / "m_fl_js_staging_full" / "stg_orders.sql").read_text(encoding="utf-8")
    assert data["sql_path"] == "out/models/m_fl_js_staging_full/stg_orders.sql"
    assert "- name: raw_orders" in data["sources"] and "- name: raw_items" not in data["sources"]
    yml = (ROOT / "out" / "models" / "sources.yml").read_text(encoding="utf-8")
    assert yml.startswith(data["sources_head"]) and data["sources"] in yml


def test_the_example_row_is_the_first_order_from_both_builds():
    data = example_output()
    row = data["row"]
    assert row["raw"]["id"] == row["ours"]["order_id"] == row["reference"]["order_id"]
    assert row["rows"] == {"ours": 61948, "reference": 61948}
    assert set(data["staging_summary"]) == {"matched", "explained", "not compared"}  # nothing unexplained
    assert set(row["ours"]) == {"order_id", "customer_id", "location_id", "ordered_at_day", "subtotal_cents",
                                "tax_paid_cents", "order_total_cents", "subtotal", "tax_paid", "order_total"}
