"""Test-only utilities. The converter never imports this module."""
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
MINI_XML = FIXTURES / "mini.xml"
# The demo XML is not committed (it holds a plaintext credential). Clone it into external/.
DEMO_XML = ROOT / "external" / "flowline-pwc-demo" / "FLOWLINE_DEMO_JAFFLESHOP.xml"


def render(sql: str) -> str:
    """Render the two Jinja calls our staging models use, so DuckDB can run them without dbt."""
    sql = re.sub(r"\{\{\s*config\([^}]*\)\s*\}\}", "", sql)
    return re.sub(r"\{\{\s*source\('(\w+)',\s*'(\w+)'\)\s*\}\}", r"\1.\2", sql)


def run_model(con: duckdb.DuckDBPyConnection, sql: str, order_by: str = "1") -> list[tuple]:
    return con.execute(f"select * from ({render(sql)}) order by {order_by}").fetchall()


def columns(con: duckdb.DuckDBPyConnection, sql: str) -> list[str]:
    return [d[0] for d in con.execute(f"select * from ({render(sql)}) limit 0").description]


def line_of(path: Path, needle: str) -> int:
    """1-based line number of the only line in a fixture that contains `needle`."""
    hits = [i for i, l in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if needle in l]
    assert len(hits) == 1, (needle, hits)
    return hits[0]
