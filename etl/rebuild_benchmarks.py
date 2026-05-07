"""
Rebuild benchmarks-only — sem rodar BigQuery.

Lê os 27 UF.json existentes em output/diagnostico/, injeta `valor` representativo
em indicadores estruturados (sem BQ refresh), e re-popula vs_top_quartile,
vs_media_nacional, posicao via etl.benchmark.

Uso:
    GCP_BILLING_PROJECT=... python -m etl.rebuild_benchmarks
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from etl.benchmark import media_nacional, position_rank, top_quartile, vs_meta_pne
from etl.indicators import INDICATOR_CATALOG, get_indicator_codes

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
DIAGNOSTIC_DIR = OUTPUT_DIR / "diagnostico"

UFS = [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]


def _safe_dict(d: Any) -> dict[str, Any]:
    return d if isinstance(d, dict) else {}


def derive_valor(code: str, recorte: str, cut: dict[str, Any]) -> float | None:
    """Deriva 'valor' representativo do indicador para ranking cross-state."""
    if not isinstance(cut, dict):
        return None

    if code == "qua_taxas_rendimento_ept":
        v = cut.get("abandono")
        return float(v) if isinstance(v, (int, float)) else None

    existing = cut.get("valor")
    if isinstance(existing, (int, float)):
        return float(existing)

    if code == "mer_saldo_caged_tecnicos":
        v = cut.get("saldo_12m")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "mer_premio_salarial_escolaridade":
        premios = _safe_dict(cut.get("premios_pct"))
        v = premios.get("superior_vs_em")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "din_crescimento_matriculas_5y":
        # Threshold: redes com base <1000 são suprimidas do ranking (alta variância)
        base = cut.get("matriculas_base")
        if isinstance(base, (int, float)) and base < 1000:
            return None
        v = cut.get("crescimento_5y_pct")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "din_cursos_novos_ept":
        v = cut.get("saldo_liquido_2y")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "cob_perfil_alunos":
        v = cut.get("total_matriculas_ept")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "qua_saeb_proficiencia_ept":
        mat = _safe_dict(cut.get("matematica")).get("diferenca")
        port = _safe_dict(cut.get("portugues")).get("diferenca")
        diffs = [d for d in (mat, port) if isinstance(d, (int, float))]
        return round(sum(diffs) / len(diffs), 2) if diffs else None

    if code == "qua_abandono_em_ept":
        v = cut.get("com_ept_pct")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "qua_ingresso_es_pnad":
        v = cut.get("diferenca_pp")
        return float(v) if isinstance(v, (int, float)) else None

    if code == "mer_renda_jovens_pnad":
        premios = _safe_dict(cut.get("premios_pct"))
        v = premios.get("ept_vs_em_reg")
        return float(v) if isinstance(v, (int, float)) else None

    return None


def main() -> int:
    all_data: dict[str, dict[str, Any]] = {}
    for uf in UFS:
        path = DIAGNOSTIC_DIR / f"{uf}.json"
        if not path.exists():
            logger.warning(f"{uf}.json ausente — skip")
            continue
        all_data[uf] = json.loads(path.read_text(encoding="utf-8"))

    logger.info(f"Carregados {len(all_data)} estados")

    # Purga indicadores que saíram do catálogo (ex: removidos por bug)
    valid_codes = set(get_indicator_codes())
    purged = 0
    for data in all_data.values():
        inds = data.get("indicators", {})
        stale = [k for k in inds if k not in valid_codes]
        for k in stale:
            del inds[k]
            purged += 1
    if purged:
        logger.info(f"Purgados {purged} indicadores fora do catálogo")

    # Suprime crescimento_5y_pct e cagr_5y_pct para redes com base < 1000 (regra do
    # processor — JSONs antigos podem ter ficado com valores inflados antes do fix)
    base_min = 1000
    for data in all_data.values():
        ind = _safe_dict(data.get("indicators", {}).get("din_crescimento_matriculas_5y"))
        for recorte in ("total_estado", "rede_estadual"):
            cut = ind.get(recorte) if isinstance(ind, dict) else None
            if not isinstance(cut, dict):
                continue
            base = cut.get("matriculas_base")
            if isinstance(base, (int, float)) and base < base_min:
                cut["crescimento_5y_pct"] = None
                cut["cagr_5y_pct"] = None
                cut["base_insuficiente"] = True
            else:
                cut["base_insuficiente"] = False

    # Inject valor nos indicadores estruturados
    inject_count = 0
    for code in get_indicator_codes():
        meta = INDICATOR_CATALOG[code]
        for recorte in meta.get("recortes", []):
            for data in all_data.values():
                ind = _safe_dict(data.get("indicators", {}).get(code))
                cut = _safe_dict(ind.get(recorte))
                if not cut:
                    continue
                # Force override em indicadores onde 'valor' deve ser recalculado
                # toda passada (fix de polaridade ou suppression por threshold)
                force_override = code in {
                    "qua_taxas_rendimento_ept",
                    "din_crescimento_matriculas_5y",
                }
                if force_override or "valor" not in cut or cut.get("valor") is None:
                    derived = derive_valor(code, recorte, cut)
                    if force_override:
                        # Aceita None: força sobrescrita mesmo pra suprimir valor
                        cut["valor"] = derived
                        inject_count += 1
                    elif derived is not None:
                        cut["valor"] = derived
                        inject_count += 1
    logger.info(f"Injected 'valor' em {inject_count} células")

    # Re-popula benchmarks cross-state
    for code in get_indicator_codes():
        meta = INDICATOR_CATALOG[code]
        polar_inv = meta.get("polaridade_inversa", False)
        if not meta.get("ranking_aplicavel", True):
            # Limpa qualquer ranking pré-existente
            for data in all_data.values():
                ind = _safe_dict(data.get("indicators", {}).get(code))
                for recorte in meta.get("recortes", []):
                    cut = ind.get(recorte) if isinstance(ind, dict) else None
                    if isinstance(cut, dict):
                        for k in (
                            "vs_top_quartile",
                            "vs_media_nacional",
                            "vs_meta_pne_2034",
                            "posicao",
                        ):
                            cut.pop(k, None)
                        cut["meta_pne_aplicavel"] = False
                        cut["ranking_aplicavel"] = False
            continue
        for recorte in meta.get("recortes", []):
            values_by_uf: dict[str, float | None] = {}
            for uf, data in all_data.items():
                ind = _safe_dict(data.get("indicators", {}).get(code))
                cut = _safe_dict(ind.get(recorte))
                v = cut.get("valor")
                values_by_uf[uf] = float(v) if isinstance(v, (int, float)) else None

            valid = [v for v in values_by_uf.values() if v is not None]
            tq = top_quartile(valid) if valid else None
            mn = media_nacional(values_by_uf, peso_pop=True)

            for uf in values_by_uf:
                ind = _safe_dict(all_data[uf].get("indicators", {}).get(code))
                cut = ind.get(recorte) if isinstance(ind, dict) else None
                if not isinstance(cut, dict):
                    continue
                v = values_by_uf[uf]
                cut["vs_top_quartile"] = (
                    round(v - tq, 2) if (v is not None and tq is not None) else None
                )
                cut["vs_media_nacional"] = (
                    round(v - mn, 2) if (v is not None and mn is not None) else None
                )
                cut["vs_meta_pne_2034"] = vs_meta_pne(v, code)
                cut["meta_pne_aplicavel"] = cut["vs_meta_pne_2034"] is not None
                cut["posicao"] = position_rank(v, values_by_uf, inverse=polar_inv)

    # Persiste
    for uf, data in all_data.items():
        path = DIAGNOSTIC_DIR / f"{uf}.json"
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
    logger.info(f"Persistidos {len(all_data)} estados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
