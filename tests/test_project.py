"""Step 5 (write): the dbt project on disk, and the command line."""
import subprocess
import sys

import pytest
import yaml

from pc2dbt.project import write_project
from tests.helpers import DEMO_XML, MINI_XML, line_of


def test_writes_models_by_mapping_folder(tmp_path):
    write_project(MINI_XML, tmp_path)
    assert (tmp_path / "models" / "m_mini" / "t_people.sql").exists()


def test_every_model_is_a_table_rebuilt_on_each_run(tmp_path):
    write_project(MINI_XML, tmp_path)
    project = yaml.safe_load((tmp_path / "dbt_project.yml").read_text())
    assert project["models"][project["name"]]["+materialized"] == "table"


def test_sources_use_the_xml_owner_and_column_types(tmp_path):
    write_project(MINI_XML, tmp_path)
    sources = yaml.safe_load((tmp_path / "models" / "sources.yml").read_text())["sources"]
    (raw,) = sources
    assert (raw["name"], raw["schema"]) == ("raw", "raw")
    people = next(t for t in raw["tables"] if t["name"] == "raw_people")
    assert {c["name"]: c["data_type"] for c in people["columns"]} == {
        "id": "varchar", "name": "varchar", "score": "decimal(6,2)", "team": "varchar"}


def test_flags_report_lists_every_flag_with_its_line(tmp_path):
    report = write_project(MINI_XML, tmp_path)
    text = (tmp_path / "flags.md").read_text()
    assert len(report.flags) == 5
    assert f"L{line_of(MINI_XML, 'TOFIELD=\"SCORE_ROUNDED\"')}" in text


def test_left_out_items_are_reported(tmp_path):
    write_project(MINI_XML, tmp_path)
    text = (tmp_path / "flags.md").read_text()
    assert f"L{line_of(MINI_XML, 'TRUNCATE TABLE MINI.T_PEOPLE')}" in text  # Pre SQL left out (decision Q17)


def test_cli_converts_and_exits_zero(tmp_path):
    done = subprocess.run([sys.executable, "-m", "pc2dbt", "convert", str(MINI_XML), "--out", str(tmp_path)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "models" / "m_mini" / "t_people.sql").exists()


@pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")
def test_left_out_lists_the_workflow_tasks_not_session_helpers(tmp_path):
    write_project(DEMO_XML, tmp_path, ["m_FL_JS_STAGING_FULL"])
    text = (tmp_path / "flags.md").read_text()
    assert "L4058: Command task cmd_FL_JS_CREATE_RPT_VIEWS" in text
    assert "presession_variable_assignment" not in text
