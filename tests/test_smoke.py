"""Smoke tests — após primeiro refresh real, validar estrutura dos JSONs gerados."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
DIAGNOSTIC_DIR = OUTPUT_DIR / "diagnostico"

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


@pytest.mark.skipif(
    not DIAGNOSTIC_DIR.exists(),
    reason="output/diagnostico/ ainda não foi populado pelo primeiro refresh real",
)
@pytest.mark.parametrize("uf", UFS)
def test_uf_json_exists(uf):
    path = DIAGNOSTIC_DIR / f"{uf}.json"
    assert path.exists(), f"{uf}.json não existe"


@pytest.mark.skipif(
    not DIAGNOSTIC_DIR.exists(),
    reason="output/diagnostico/ ainda não foi populado pelo primeiro refresh real",
)
@pytest.mark.parametrize("uf", UFS)
def test_uf_indicators_consistent_across_ufs(uf):
    """Todos UFs devem ter o mesmo conjunto de indicadores que SP (referência).
    Pega regressões em que algum UF perde indicador no refresh, sem ser frágil
    quando o catálogo é expandido antes do próximo refresh."""
    sp_path = DIAGNOSTIC_DIR / "SP.json"
    if not sp_path.exists():
        pytest.skip("SP.json (referência) não existe ainda")
    uf_path = DIAGNOSTIC_DIR / f"{uf}.json"
    if not uf_path.exists():
        pytest.skip(f"{uf}.json não existe ainda")
    sp_data = json.loads(sp_path.read_text(encoding="utf-8"))
    uf_data = json.loads(uf_path.read_text(encoding="utf-8"))
    sp_codes = set(sp_data.get("indicators", {}).keys())
    uf_codes = set(uf_data.get("indicators", {}).keys())
    missing = sp_codes - uf_codes
    assert not missing, f"{uf} tem indicadores faltando vs SP: {sorted(missing)}"


@pytest.mark.skipif(
    not (OUTPUT_DIR / "benchmark.json").exists(),
    reason="benchmark.json ainda não foi gerado",
)
def test_benchmark_has_pne():
    data = json.loads((OUTPUT_DIR / "benchmark.json").read_text(encoding="utf-8"))
    assert "pne_2024_2034" in data
    assert "Lei 15.388" in data["pne_2024_2034"]["versao_referencia"]
