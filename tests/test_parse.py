"""Step 1 (parse): read the XML into objects that keep their line numbers."""
import pytest

from pc2dbt.parse import parse_file
from tests.helpers import DEMO_XML, MINI_XML, line_of


def test_mini_fixture_folder_contents():
    folder = parse_file(MINI_XML)
    assert sorted(folder.sources) == [("MINI_RAW", "RAW_PEOPLE"), ("MINI_RAW", "RAW_TEAMS")]
    assert list(folder.targets) == ["T_PEOPLE"]
    assert list(folder.mappings) == ["m_MINI"]


def test_elements_keep_their_xml_line():
    folder = parse_file(MINI_XML)
    mapping = folder.mappings["m_MINI"]
    swap = next(c for c in mapping.connectors if c.from_field == "LABEL" and c.to_instance == "T_PEOPLE")
    assert swap.line == line_of(MINI_XML, 'FROMFIELD="LABEL" FROMINSTANCE="UN_ALL"')
    assert folder.targets["T_PEOPLE"].line == line_of(MINI_XML, '<TARGET DATABASETYPE="Oracle" NAME="T_PEOPLE"')


def test_ports_carry_type_and_expression():
    folder = parse_file(MINI_XML)
    exp = folder.mappings["m_MINI"].transformations["EXP_PEOPLE"]
    label = exp.ports["LABEL"]
    assert (label.port_type, label.datatype, label.expression) == ("OUTPUT", "string", "IIF(SCORE >= 50, 'HIGH', 'LOW')")
    assert exp.ports["ID"].default == "ERROR('Transformation Error')"


@pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")
def test_demo_counts_match_the_file():
    folder = parse_file(DEMO_XML)
    mappings = folder.mappings.values()
    assert (len(folder.sources), len(folder.targets), len(folder.mappings)) == (12, 16, 3)
    assert sum(len(m.transformations) for m in mappings) == 98
    assert sum(len(m.connectors) for m in mappings) == 1066
    staging = folder.mappings["m_FL_JS_STAGING_FULL"]
    first_swap = next(c for c in staging.connectors if c.from_field == "SUBTOTAL" and c.to_field == "SUBTOTAL_CENTS")
    assert first_swap.line == 608


@pytest.mark.skipif(not DEMO_XML.exists(), reason="demo XML not cloned into external/")
def test_credential_line_is_never_read():
    """The command task's VALUEPAIR holds a plaintext credential; the parser must drop it."""
    folder = parse_file(DEMO_XML)
    valuepairs = list(folder.root.iter("VALUEPAIR"))
    assert len(valuepairs) == 1
    assert valuepairs[0].attrs == {}


def test_sort_keys_and_group_by_ports_are_read():
    from tests.helpers import MINI_MARTS_XML
    m = parse_file(MINI_MARTS_XML).mappings["m_MINI_MARTS"]
    srt = m.transformations["SRT_VISITS"].ports
    assert [(p.name, p.sort_direction) for p in srt.values() if p.sort_key] == [
        ("PERSON", "ASCENDING"), ("VISITED_AT", "ASCENDING"), ("VISIT_ID", "ASCENDING")]  # in port order
    agg = m.transformations["AGG_BY_STORE"].ports
    assert [p.name for p in agg.values() if p.expression_type == "GROUPBY"] == ["STORE"]
