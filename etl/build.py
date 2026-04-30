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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from etl.indicators import INDICATOR_CATALOG, get_indicator_codes

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

ROOT = Path(__file__).parent.parent
QUERIES_DIR = ROOT / "etl" / "queries"
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


def load_query(indicator_code: str) -> str:
    """Carrega o SQL versionado para um indicador."""
    path = QUERIES_DIR / f"{indicator_code}.sql"
    if not path.exists():
        raise FileNotFoundError(f"Query SQL não encontrada: {path}")
    return path.read_text(encoding="utf-8")


def run_indicator(code: str, uf: str) -> dict[str, Any]:
    """
    Executa o SQL do indicador para um UF e retorna estrutura de saída.

    PLACEHOLDER: até GCP_SA_KEY estar configurado, retorna estrutura vazia.
    Quando GCP estiver wired, executa basedosdados.read_sql() e processa o DataFrame.
    """
    # TODO: substituir por execução real após GCP setup
    # import basedosdados as bd
    # query = load_query(code).replace("{UF}", uf)
    # df = bd.read_sql(query, billing_project_id=os.environ["GCP_BILLING_PROJECT"])
    # return process_dataframe(code, uf, df)

    logger.warning(f"[{code}/{uf}] sem GCP_SA_KEY — retornando placeholder")
    return {
        "vintage": "pendente",
        "caveat": "GCP_SA_KEY não configurado. Execução real pendente.",
    }


def build_uf(uf: str) -> dict[str, Any]:
    """Gera o JSON completo de um estado."""
    indicators: dict[str, Any] = {}
    for code in get_indicator_codes():
        try:
            indicators[code] = run_indicator(code, uf)
        except Exception as e:
            logger.error(f"[{code}/{uf}] falhou: {e}")
            indicators[code] = {
                "error": str(e),
                "vintage": "indisponível",
                "caveat": f"Indicador falhou: {e}",
            }

    return {
        "uf": uf,
        "uf_nome": UF_NAMES[uf],
        "vintage": {
            "censo_escolar": "pendente",
            "rais": "pendente",
            "caged": "pendente",
            "pnad": "pendente",
            "ideb": "pendente",
        },
        "last_built": datetime.now(timezone.utc).isoformat(),
        "indicators": indicators,
    }


def build_metadata() -> dict[str, Any]:
    """Gera metadata.json com info do build."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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


def build_benchmark(all_uf_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Calcula top-quartile + média nacional + meta PNE para cada indicador
    cruzando dados de todos os UFs.
    """
    # TODO: implementar quando dados reais estiverem populados
    return {
        "vintage": "pendente",
        "data_atualizacao": datetime.now(timezone.utc).date().isoformat(),
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
    parser.add_argument("--no-cache", action="store_true", help="Ignora cache de queries")
    args = parser.parse_args()

    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)

    target_ufs = [args.uf] if args.uf else UFS
    logger.info(f"Construindo {len(target_ufs)} UF(s): {target_ufs}")

    all_data: dict[str, dict[str, Any]] = {}
    for uf in target_ufs:
        logger.info(f"[{uf}] iniciando")
        data = build_uf(uf)
        all_data[uf] = data
        out_path = DIAGNOSTIC_DIR / f"{uf}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[{uf}] OK → {out_path.relative_to(ROOT)}")

    # benchmark + metadata só se rodou todos
    if not args.uf:
        bench = build_benchmark(all_data)
        (OUTPUT_DIR / "benchmark.json").write_text(
            json.dumps(bench, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("benchmark.json OK")

    meta = build_metadata()
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("metadata.json OK")

    # cópia do schema para distribuição
    schema_src = SCHEMAS_DIR / "uf.schema.json"
    if schema_src.exists():
        (OUTPUT_DIR / "schema.json").write_text(
            schema_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
        logger.info("schema.json OK")

    logger.info("Build concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
