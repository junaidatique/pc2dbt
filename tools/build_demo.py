"""Build the committed dbt project in out/ with dbt on DuckDB, without running the tests.

It loads the jaffle-shop seed CSVs (external/jaffle-shop/seeds/jaffle-data) into raw.* with the column
types of the XML's PC Sources (decision Q14), writes a throwaway dbt profile, runs `dbt build` on out/,
and prints the row count of every table it built. dbt's target/ and logs/ go to a temporary folder, so
out/ stays exactly as committed. The DuckDB file is kept so you can query it.

Usage, from the repo root (needs the clones in external/ and the test extras installed):
    .venv/bin/python tools/build_demo.py [--db demo.duckdb]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402

from pc2dbt.parse import parse_file  # noqa: E402
from pc2dbt.project import project_name  # noqa: E402
from tests.helpers import DEMO_XML  # noqa: E402
from tests.reference.harness import DBT, SEEDS, load_raw, write_profile  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build out/ with dbt on DuckDB from the jaffle-shop seeds.")
    parser.add_argument("--db", default=str(ROOT / "demo.duckdb"), help="DuckDB file to build into (default: demo.duckdb)")
    args = parser.parse_args()
    for needed in (DEMO_XML, SEEDS):
        if not needed.exists():
            print(f"missing {needed.relative_to(ROOT)}: clone it into external/ first (see README.md)", file=sys.stderr)
            return 2
    db = Path(args.db).resolve()
    load_raw(db)
    with tempfile.TemporaryDirectory() as tmp:
        write_profile(Path(tmp), project_name(parse_file(DEMO_XML)), db)
        done = subprocess.run([DBT, "build", "--project-dir", str(ROOT / "out"), "--profiles-dir", tmp,
                               "--target-path", f"{tmp}/target", "--log-path", f"{tmp}/logs"])
    if done.returncode != 0:
        return done.returncode
    con = duckdb.connect(str(db), read_only=True)
    tables = [r[0] for r in con.execute(
        "select table_name from information_schema.tables where table_schema = 'main' order by 1").fetchall()]
    print(f"\nBuilt {len(tables)} tables in {db}:")
    for t in tables:
        print(f"  {t:28} {con.execute(f'select count(*) from main.{t}').fetchone()[0]:>8,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
