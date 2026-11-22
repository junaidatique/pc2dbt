"""Every column in the generated SQL is read with the name of the step it comes from.

A bare name can mean two things when a step also writes an output with that name. EXP_ORDERS
reads SUBTOTAL_IN (called subtotal upstream) and writes SUBTOTAL; the stg_orders select writes
subtotal_cents and then reads subtotal_cents three lines later. DuckDB picks the input in both
places, but that is DuckDB's rule. A qualified name (sq_raw_orders.subtotal) can only mean the
input, in any database, so the generated SQL never depends on the rule.
"""
import json

import duckdb
import pytest

from pc2dbt.convert import convert_mapping
from pc2dbt.parse import parse_file
from tests.helpers import DEMO_XML, MINI_MARTS_XML, MINI_XML, render

CASES = [(MINI_XML, "m_MINI"), (MINI_MARTS_XML, "m_MINI_STG"), (MINI_MARTS_XML, "m_MINI_MARTS"),
         (DEMO_XML, "m_FL_JS_STAGING_FULL"), (DEMO_XML, "m_FL_JS_MARTS_CORE")]


def column_refs(sql: str) -> list[list[str]]:
    tree = json.loads(duckdb.connect().execute("select json_serialize_sql(?::varchar)", [sql]).fetchall()[0][0])
    assert not tree["error"], tree.get("error_message")
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("class") == "COLUMN_REF":
                found.append(node["column_names"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(tree)
    return found


def models():
    for xml, mapping in CASES:
        if xml.exists():
            yield from ((mapping, m) for m in convert_mapping(parse_file(xml), mapping))


@pytest.mark.parametrize("mapping,model", list(models()), ids=lambda x: getattr(x, "name", x))
def test_every_column_is_read_with_the_name_of_its_step(mapping, model):
    bare = [".".join(r) for r in column_refs(render(model.sql)) if len(r) != 2]
    assert bare == []
