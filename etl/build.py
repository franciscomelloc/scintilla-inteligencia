"""
Orquestrador do ETL — gera 27 diagnostico/<UF>.json + benchmark.json + metadata.json.

Uso:
    uv run python etl/build.py [--uf MG] [--no-cache]

Sem --uf, gera todos os 27 estados.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from etl.benchmark import media_nacional, position_rank, top_quartile, vs_meta_pne
from etl.indicators import INDICATOR_CATALOG, get_indicator_codes
from etl.processors import PROCESSORS
from etl.runner import BQRunner

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
DIAGNOSTIC_DIR = OUTPUT_DIR / "diagnostico"
SCHEMAS_DIR = ROOT / "etl" / "schemas"

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

UF_NAMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def run_indicator(code: str, uf: str) -> dict[str, Any]:
    """Executa SQL + processador. Em caso de falha, retorna estrutura com erro."""
    try:
        df = BQRunner.run(code, uf)
        processor = PROCESSORS.get(code)
        if not processor:
            return {"vintage": "indisponível", "caveat": f"Processador não implementado: {code}"}
        return processor(df, uf)
    except Exception as e:
        logger.error(f"[{code}/{uf}] {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return {
            "vintage": "indisponível",
            "caveat": f"Falhou: {type(e).__name__}: {str(e)[:200]}",
        }


def build_uf(uf: str) -> dict[str, Any]:
    """Gera o JSON completo de um estado."""
    indicators: dict[str, Any] = {}
    for code in get_indicator_codes():
        logger.info(f"[{uf}] {code}")
        indicators[code] = run_indicator(code, uf)

    return {
        "uf": uf,
        "uf_nome": UF_NAMES[uf],
        "vintage": _summary_vintage(indicators),
        "last_built": datetime.now(UTC).isoformat(),
        "indicators": indicators,
    }


def _summary_vintage(indicators: dict[str, Any]) -> dict[str, str]:
    """Sumariza vintages das fontes principais a partir dos indicadores."""
    summary = {
        "censo_escolar": indicators.get("cob_matriculas_ept_per_jovem", {}).get("vintage", "indisponível"),
        "rais": indicators.get("mer_premio_salarial_escolaridade", {}).get("vintage", "indisponível"),
        "caged": indicators.get("mer_saldo_caged_tecnicos", {}).get("vintage", "indisponível"),
        "pnad": indicators.get("mer_neet_rate", {}).get("vintage", "indisponível"),
        "ideb": indicators.get("qua_ideb_escolas_ept", {}).get("vintage", "indisponível"),
    }
    return summary


def fill_benchmarks(all_data: dict[str, dict[str, Any]]) -> None:
    """
    Preenche vs_top_quartile, vs_media_nacional, posicao em cada indicador
    cruzando os 27 estados. Atua in-place no all_data.
    """
    for code in get_indicator_codes():
        meta = INDICATOR_CATALOG[code]
        polar_inv = meta.get("polaridade_inversa", False)
        if not meta.get("ranking_aplicavel", True):
            continue  # valor absoluto/não comparável cross-state

        # Pra cada recorte, coleta valores de cada UF
        for recorte in ["total_estado", "rede_estadual"]:
            if recorte not in meta["recortes"]:
                continue
            values_by_uf: dict[str, float | None] = {}
            for uf, data in all_data.items():
                ind = data["indicators"].get(code, {})
                cut = ind.get(recorte, {}) if isinstance(ind, dict) else {}
                v = cut.get("valor") if isinstance(cut, dict) else None
                if isinstance(v, (int, float)):
                    values_by_uf[uf] = float(v)
                else:
                    values_by_uf[uf] = None

            # Calcula stats
            valid = [v for v in values_by_uf.values() if v is not None]
            tq = top_quartile(valid) if valid else None
            mn = media_nacional(values_by_uf, peso_pop=True)

            # Aplica em cada UF
            for uf in values_by_uf:
                ind = all_data[uf]["indicators"].get(code, {})
                cut = ind.get(recorte) if isinstance(ind, dict) else None
                if not isinstance(cut, dict):
                    continue
                v = values_by_uf[uf]
                cut["vs_top_quartile"] = round(v - tq, 2) if (v is not None and tq is not None) else None
                cut["vs_media_nacional"] = round(v - mn, 2) if (v is not None and mn is not None) else None
                cut["vs_meta_pne_2034"] = vs_meta_pne(v, code)
                cut["meta_pne_aplicavel"] = cut["vs_meta_pne_2034"] is not None
                cut["posicao"] = position_rank(v, values_by_uf, inverse=polar_inv)


def build_metadata() -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "generator": "scintilla-inteligencia ETL",
        "catalog": {
            "total_indicators": len(get_indicator_codes()),
            "domains": {
                "cobertura": 5,
                "qualidade": 3,
                "infraestrutura": 1,
                "mercado": 3,
                "dinamismo": 2,
            },
        },
        "indicators": {
            code: {
                "name": meta["name"],
                "domain": meta["domain"],
                "recortes": meta["recortes"],
                "polaridade_inversa": meta.get("polaridade_inversa", False),
                "lag_months": meta["lag_months"],
                "source": meta["source"],
                "pne_meta": meta.get("pne_meta"),
            }
            for code, meta in INDICATOR_CATALOG.items()
        },
    }


def build_benchmark_summary() -> dict[str, Any]:
    return {
        "vintage": "real",
        "data_atualizacao": datetime.now(UTC).date().isoformat(),
        "pne_2024_2034": {
            "versao_referencia": "Lei 15.388/2026 (sancionada em 14/04/2026)",
            "horizonte_alvo": 2034,
            "metas": {
                "cob_distribuicao_modalidade": {
                    "meta_2036": 50,
                    "descricao": "EPT integrada + concomitante ≥ 50% do EM até 2036",
                    "metodologia_disagregacao": "uniforme",
                },
                "din_crescimento_matriculas_5y": {
                    "meta_subsequente": 60,
                    "descricao": "Expansão de 60% das matrículas em cursos subsequentes",
                    "metodologia_disagregacao": "uniforme",
                },
                "inf_conectividade_ept": {
                    "meta_2028": 50,
                    "meta_2036": 100,
                    "descricao": "50% das escolas com banda larga em 2 anos; 100% em 10 anos",
                    "metodologia_disagregacao": "uniforme",
                },
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ETL Scintilla Inteligência")
    parser.add_argument("--uf", help="UF específica (default: todos os 27)")
    parser.add_argument("--no-benchmark", action="store_true", help="Skip benchmark cross-state")
    args = parser.parse_args()

    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)

    target_ufs = [args.uf] if args.uf else UFS
    logger.info(f"Construindo {len(target_ufs)} UF(s): {target_ufs}")

    all_data: dict[str, dict[str, Any]] = {}
    for uf in target_ufs:
        logger.info(f"=== [{uf}] iniciando ===")
        data = build_uf(uf)
        all_data[uf] = data

    # Benchmark cross-state (só se gerou todos)
    if len(target_ufs) == 27 and not args.no_benchmark:
        logger.info("Calculando benchmarks cross-state")
        fill_benchmarks(all_data)

    # Persiste cada UF
    for uf, data in all_data.items():
        out_path = DIAGNOSTIC_DIR / f"{uf}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        logger.info(f"[{uf}] OK → {out_path.relative_to(ROOT)}")

    # Benchmark + metadata
    if len(target_ufs) == 27:
        bench = build_benchmark_summary()
        (OUTPUT_DIR / "benchmark.json").write_text(
            json.dumps(bench, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("benchmark.json OK")

    meta = build_metadata()
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("metadata.json OK")

    schema_src = SCHEMAS_DIR / "uf.schema.json"
    if schema_src.exists():
        (OUTPUT_DIR / "schema.json").write_text(
            schema_src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    logger.info("Build concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
