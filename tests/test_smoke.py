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
def test_uf_has_14_indicators(uf):
    path = DIAGNOSTIC_DIR / f"{uf}.json"
    if not path.exists():
        pytest.skip(f"{uf}.json não existe ainda")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "indicators" in data
    assert len(data["indicators"]) == 14, (
        f"{uf} tem {len(data['indicators'])} indicadores, esperado 14"
    )


@pytest.mark.skipif(
    not (OUTPUT_DIR / "benchmark.json").exists(),
    reason="benchmark.json ainda não foi gerado",
)
def test_benchmark_has_pne():
    data = json.loads((OUTPUT_DIR / "benchmark.json").read_text(encoding="utf-8"))
    assert "pne_2024_2034" in data
    assert "Lei 15.388" in data["pne_2024_2034"]["versao_referencia"]
