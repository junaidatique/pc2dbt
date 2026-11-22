"""tools/build_demo.py: lets a reviewer build the committed out/ project with dbt on DuckDB without the tests.

It loads the jaffle-shop seed CSVs as raw.* with the XML's PC Source column types (decision Q14), writes a
throwaway dbt profile, and runs dbt build on out/, keeping dbt's target/ and logs/ out of out/.
Slow and needs external/, so it only runs with:  pytest -m reference
"""
import subprocess
import sys

import duckdb
import pytest

from tests.helpers import DEMO_XML, ROOT
from tests.reference import harness

pytestmark = [pytest.mark.reference,
              pytest.mark.skipif(not (DEMO_XML.exists() and harness.SEEDS.exists()), reason="needs external/ clones")]


def test_build_demo_builds_all_16_models(tmp_path):
    db = tmp_path / "demo.duckdb"
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "build_demo.py"), "--db", str(db)],
                          capture_output=True, text=True, cwd=tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    con = duckdb.connect(str(db), read_only=True)
    tables = dict(con.execute("select table_name, estimated_size from duckdb_tables() where schema_name = 'main'").fetchall())
    assert len(tables) == 16
    assert con.execute("select count(*) from customer_360").fetchone()[0] == 935
    assert con.execute("select count(*) from orders").fetchone()[0] == 61465
    assert "customer_360" in done.stdout and "935" in done.stdout
    assert not (ROOT / "out" / "target").exists() and not (ROOT / "out" / "logs").exists()
