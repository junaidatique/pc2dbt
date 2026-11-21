"""The committed dbt project in out/ is exactly what the converter writes today.

Regenerate it with:
    python -m pc2dbt convert external/flowline-pwc-demo/FLOWLINE_DEMO_JAFFLESHOP.xml --out out --mapping m_FL_JS_STAGING_FULL
"""
import pytest

from pc2dbt.project import write_project
from tests.helpers import DEMO_XML, ROOT

OUT = ROOT / "out"


@pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")
def test_committed_project_matches_the_converter(tmp_path):
    write_project(DEMO_XML, tmp_path, ["m_FL_JS_STAGING_FULL"])
    fresh = {p.relative_to(tmp_path): p.read_text() for p in tmp_path.rglob("*") if p.is_file()}
    committed = {p.relative_to(OUT): p.read_text() for p in OUT.rglob("*")
                 if p.is_file() and not set(p.relative_to(OUT).parts) & {"target", "logs"}}
    assert sorted(map(str, committed)) == sorted(map(str, fresh))
    assert [str(k) for k in fresh if fresh[k] != committed[k]] == []
