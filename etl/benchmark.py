"""
Cálculo de benchmarks: top-quartile (P75), média nacional ponderada, e meta PNE 2024-2034.

Cada indicador tem 3 dimensões de comparação no JSON de saída:
- vs_top_quartile: distância do P75 nacional
- vs_media_nacional: distância da média ponderada por pop 15-29
- vs_meta_pne_2034: distância da meta PNE (quando aplicável)

PNE 2024-2034 (Lei 15.388/2026 sancionada em 14/04/2026):
- M1: EPT integrada+concomitante ≥50% do EM até 2036
- M2: EPT subsequente +60% de matrículas
- M4: Conectividade 50% das escolas em 2 anos / 100% em 10 anos
"""

from __future__ import annotations

import statistics
from typing import Any

# Pop 15-29 por UF, em milhões. Fonte: PNAD Contínua 2024 (4 trimestres, BD)
# Query: SUM(V1028)/4/1e6 por sigla_uf, ano=2024, V2009 BETWEEN 15 AND 29
# Reproduzir: scripts/refresh_pop_15_29.py (a criar) — atualizar anualmente
POP_15_29_BY_UF: dict[str, float] = {
    "AC": 0.25,
    "AL": 0.84,
    "AP": 0.25,
    "AM": 1.15,
    "BA": 3.41,
    "CE": 2.10,
    "DF": 0.74,
    "ES": 0.89,
    "GO": 1.76,
    "MA": 1.80,
    "MT": 0.88,
    "MS": 0.64,
    "MG": 4.69,
    "PA": 2.30,
    "PB": 0.90,
    "PR": 2.60,
    "PE": 2.20,
    "PI": 0.77,
    "RJ": 3.54,
    "RN": 0.81,
    "RS": 2.29,
    "RO": 0.44,
    "RR": 0.16,
    "SC": 1.68,
    "SP": 9.90,
    "SE": 0.58,
    "TO": 0.40,
}
POP_15_29_VINTAGE = "PNAD Contínua 2024 (média anual)"

# Metas PNE 2024-2034 — referência: pne_mapping.md
PNE_TARGETS: dict[str, dict[str, Any]] = {
    "cob_distribuicao_modalidade": {
        "meta_2036": 50.0,
        "campo_calculo": "integrada_mais_concomitante",
        "descricao": "EPT integrada + concomitante ≥ 50% do EM até 2036",
        "metodologia_disagregacao": "uniforme",
    },
    "din_crescimento_matriculas_5y": {
        "meta_growth": 60.0,
        "campo_calculo": "crescimento_subsequente_pct",
        "descricao": "Expansão de 60% das matrículas em cursos subsequentes",
        "metodologia_disagregacao": "uniforme",
    },
    "inf_conectividade_ept": {
        "meta_2028": 50.0,
        "meta_2036": 100.0,
        "campo_calculo": "valor",  # tier mais alto
        "descricao": "50% banda larga em 2 anos; 100% em 10 anos",
        "metodologia_disagregacao": "uniforme",
    },
}


def top_quartile(values: list[float]) -> float | None:
    """P75 da distribuição. None se < 4 valores válidos."""
    valid = [v for v in values if v is not None]
    if len(valid) < 4:
        return None
    return float(statistics.quantiles(valid, n=4)[2])


def media_nacional(values_by_uf: dict[str, float], peso_pop: bool = True) -> float | None:
    """
    Média nacional. Se peso_pop=True, pondera por população 15-29 do estado.
    Retorna None se nenhum valor válido.
    """
    valid_pairs = [(uf, v) for uf, v in values_by_uf.items() if v is not None]
    if not valid_pairs:
        return None

    if not peso_pop:
        return statistics.fmean(v for _, v in valid_pairs)

    total_weight = sum(POP_15_29_BY_UF.get(uf, 0) for uf, _ in valid_pairs)
    if total_weight == 0:
        return statistics.fmean(v for _, v in valid_pairs)
    weighted_sum = sum(v * POP_15_29_BY_UF.get(uf, 0) for uf, v in valid_pairs)
    return weighted_sum / total_weight


def meta_pne(indicator_code: str) -> dict[str, Any] | None:
    """Retorna a meta PNE do indicador ou None se não aplicável."""
    return PNE_TARGETS.get(indicator_code)


def vs_meta_pne(value: float | None, indicator_code: str) -> float | None:
    """
    Distância do valor atual à meta PNE 2034.
    Negativo = abaixo da meta; positivo = acima.
    """
    if value is None:
        return None
    target = PNE_TARGETS.get(indicator_code)
    if not target:
        return None
    meta_value = target.get("meta_2036") or target.get("meta_growth") or target.get("meta_2028")
    if meta_value is None:
        return None
    return value - meta_value


def position_rank(
    value: float | None,
    all_values: dict[str, float],
    inverse: bool = False,
) -> int | None:
    """
    Posição do estado no ranking 1-27.
    inverse=True: menor é melhor (NEET, razão aluno/professor).
    """
    if value is None:
        return None
    valid = sorted(
        [(uf, v) for uf, v in all_values.items() if v is not None],
        key=lambda x: x[1],
        reverse=not inverse,
    )
    for i, (_uf, v) in enumerate(valid):
        if v == value:
            return i + 1
    return None


def build_benchmark_for_indicator(
    indicator_code: str,
    values_by_uf_by_recorte: dict[str, dict[str, float | None]],
) -> dict[str, Any]:
    """
    Constrói bloco de benchmark para um indicador, considerando todos os recortes.

    Estrutura:
    {
        "top_quartile": {"total_estado": ..., "rede_estadual": ...},
        "media_nacional": {"total_estado": ..., "rede_estadual": ...},
        "pne": <meta object or None>
    }
    """
    result: dict[str, Any] = {
        "top_quartile": {},
        "media_nacional": {},
    }
    for recorte, values_by_uf in values_by_uf_by_recorte.items():
        all_values = list(values_by_uf.values())
        result["top_quartile"][recorte] = top_quartile(all_values)
        result["media_nacional"][recorte] = media_nacional(values_by_uf)

    pne = meta_pne(indicator_code)
    if pne:
        result["pne"] = pne

    return result
