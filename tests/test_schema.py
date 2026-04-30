"""Validação contra JSON Schema."""

import json
from pathlib import Path

import pytest

try:
    from jsonschema import validate
except ImportError:
    validate = None

ROOT = Path(__file__).parent.parent
SCHEMAS_DIR = ROOT / "etl" / "schemas"
OUTPUT_DIR = ROOT / "output"
DIAGNOSTIC_DIR = OUTPUT_DIR / "diagnostico"


@pytest.mark.skipif(
    validate is None,
    reason="jsonschema não instalado — uv sync incluiu na lista deps",
)
def test_uf_schema_loads():
    schema_path = SCHEMAS_DIR / "uf.schema.json"
    assert schema_path.exists()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["title"] == "Diagnóstico Estadual EPT — UF"


@pytest.mark.skipif(
    validate is None or not DIAGNOSTIC_DIR.exists(),
    reason="schema validation requer jsonschema + diagnósticos populados",
)
def test_mg_validates_against_schema():
    schema = json.loads((SCHEMAS_DIR / "uf.schema.json").read_text(encoding="utf-8"))
    mg_path = DIAGNOSTIC_DIR / "MG.json"
    if not mg_path.exists():
        pytest.skip("MG.json ainda não gerado")
    data = json.loads(mg_path.read_text(encoding="utf-8"))
    validate(instance=data, schema=schema)
