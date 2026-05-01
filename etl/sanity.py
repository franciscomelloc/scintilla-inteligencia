"""
Sanity test suite — invariantes matemáticos sobre output/diagnostico/*.json.

Trava o build se algum invariante quebrar. Roda após `python -m etl.rebuild_benchmarks`
(ou após build completo) e antes de copiar pro site-v2.

Uso:
    python -m etl.sanity
    Exit code 0 = todos invariantes OK; 1 = falha.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from etl.benchmark import POP_15_29_BY_UF
from etl.indicators import INDICATOR_CATALOG, get_indicator_codes

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT = Path(__file__).parent.parent
DIAGNOSTIC_DIR = ROOT / "output" / "diagnostico"

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


class SanityFailure(Exception):
    pass


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _safe_dict(d: Any) -> dict[str, Any]:
    return d if isinstance(d, dict) else {}


# ---------------------------------------------------------------------------
# Invariantes
# ---------------------------------------------------------------------------


def check_27_files_exist(all_data: dict[str, dict]) -> list[str]:
    fails: list[str] = []
    for uf in UFS:
        if uf not in all_data:
            fails.append(f"UF.json ausente: {uf}")
    return fails


def check_indicator_count(all_data: dict[str, dict]) -> list[str]:
    """Cada UF.json deve ter exatamente os indicadores do catálogo."""
    fails: list[str] = []
    expected = set(get_indicator_codes())
    for uf, data in all_data.items():
        actual = set(data.get("indicators", {}).keys())
        missing = expected - actual
        extra = actual - expected
        if missing:
            fails.append(f"{uf}: faltam {sorted(missing)}")
        if extra:
            fails.append(f"{uf}: indicadores fora do catálogo {sorted(extra)}")
    return fails


def check_ranking_distinct(all_data: dict[str, dict]) -> list[str]:
    """Posições só podem repetir quando os valores numéricos correspondentes são iguais (empate)."""
    fails: list[str] = []
    for code, meta in INDICATOR_CATALOG.items():
        if not meta.get("ranking_aplicavel", True):
            continue
        for recorte in meta.get("recortes", []):
            pares: list[tuple[float, int, str]] = []
            for uf, data in all_data.items():
                cut = _safe_dict(_safe_dict(data.get("indicators", {}).get(code)).get(recorte))
                v = cut.get("valor")
                pos = cut.get("posicao")
                if _is_num(v) and isinstance(pos, int):
                    pares.append((float(v), pos, uf))
            if not pares:
                continue
            # Agrupa por posição; cada grupo deve ter valor único
            from collections import defaultdict
            por_pos: dict[int, list[tuple[float, str]]] = defaultdict(list)
            for v, p, uf in pares:
                por_pos[p].append((v, uf))
            for p, grupo in por_pos.items():
                vals = {round(v, 6) for v, _ in grupo}
                if len(vals) > 1:
                    fails.append(f"{code}/{recorte}: pos={p} duplicada com valores diferentes {grupo}")
            positions_set = sorted(por_pos.keys())
            if positions_set and (max(positions_set) > 27 or min(positions_set) < 1):
                fails.append(f"{code}/{recorte}: posicao fora de [1,27]: min={min(positions_set)} max={max(positions_set)}")
    return fails


def check_ranking_nullity_consistency(all_data: dict[str, dict]) -> list[str]:
    """Se posicao é None, vs_top_quartile e vs_media_nacional também devem ser."""
    fails: list[str] = []
    for code in get_indicator_codes():
        meta = INDICATOR_CATALOG[code]
        for recorte in meta.get("recortes", []):
            for uf, data in all_data.items():
                cut = _safe_dict(_safe_dict(data.get("indicators", {}).get(code)).get(recorte))
                pos = cut.get("posicao")
                tq = cut.get("vs_top_quartile")
                mn = cut.get("vs_media_nacional")
                if pos is None and (tq is not None or mn is not None):
                    fails.append(f"{code}/{recorte}/{uf}: posicao=None mas vs_top={tq} vs_mn={mn}")
    return fails


def check_ranking_aplicavel_purged(all_data: dict[str, dict]) -> list[str]:
    """Cards com ranking_aplicavel:false NÃO devem ter posicao/vs_top_quartile populados."""
    fails: list[str] = []
    for code, meta in INDICATOR_CATALOG.items():
        if meta.get("ranking_aplicavel", True):
            continue
        for recorte in meta.get("recortes", []):
            for uf, data in all_data.items():
                cut = _safe_dict(_safe_dict(data.get("indicators", {}).get(code)).get(recorte))
                if cut.get("posicao") is not None:
                    fails.append(f"{code}/{recorte}/{uf}: posicao populada apesar de ranking_aplicavel=False")
                if cut.get("vs_top_quartile") is not None:
                    fails.append(f"{code}/{recorte}/{uf}: vs_top_quartile populado apesar de ranking_aplicavel=False")
    return fails


def check_polaridade_consistency(all_data: dict[str, dict]) -> list[str]:
    """Posição 1 deve corresponder ao melhor valor segundo a polaridade."""
    fails: list[str] = []
    for code, meta in INDICATOR_CATALOG.items():
        if not meta.get("ranking_aplicavel", True):
            continue
        polar_inv = meta.get("polaridade_inversa", False)
        for recorte in meta.get("recortes", []):
            pares: list[tuple[float, int, str]] = []
            for uf, data in all_data.items():
                cut = _safe_dict(_safe_dict(data.get("indicators", {}).get(code)).get(recorte))
                v = cut.get("valor")
                pos = cut.get("posicao")
                if _is_num(v) and isinstance(pos, int):
                    pares.append((float(v), pos, uf))
            if len(pares) < 2:
                continue
            # Pos=1 deve ter o valor extremo. Inverso=False → maior; True → menor.
            ordenado = sorted(pares, key=lambda x: x[0], reverse=not polar_inv)
            esperado_pos1 = ordenado[0]
            real_pos1 = next((p for p in pares if p[1] == 1), None)
            if real_pos1 and abs(real_pos1[0] - esperado_pos1[0]) > 0.001:
                fails.append(
                    f"{code}/{recorte}: pos=1 é {real_pos1[2]} (valor {real_pos1[0]}) "
                    f"mas {'menor' if polar_inv else 'maior'} valor é {esperado_pos1[2]} ({esperado_pos1[0]})"
                )
    return fails


def check_pop_15_29_completeness() -> list[str]:
    """POP_15_29_BY_UF deve cobrir os 27 estados com valor positivo."""
    fails: list[str] = []
    for uf in UFS:
        v = POP_15_29_BY_UF.get(uf)
        if v is None or v <= 0:
            fails.append(f"POP_15_29_BY_UF[{uf}] inválido: {v}")
    return fails


def check_distribuicao_dependencia_soma(all_data: dict[str, dict]) -> list[str]:
    """% federal+estadual+municipal+privada deve somar 100±0.5."""
    fails: list[str] = []
    for uf, data in all_data.items():
        cut = _safe_dict(_safe_dict(data.get("indicators", {}).get("cob_distribuicao_dependencia")).get("total_estado"))
        pct_keys = ["federal", "estadual", "municipal", "privada"]
        vals = [cut.get(k) for k in pct_keys]
        if all(_is_num(v) for v in vals):
            soma = sum(float(v) for v in vals)
            if abs(soma - 100) > 0.5:
                fails.append(f"cob_distribuicao_dependencia/{uf}: soma={soma:.2f} (esperado ≈100)")
    return fails


def check_pne_m12a_redes_capped(all_data: dict[str, dict]) -> list[str]:
    """por_rede percentuais devem estar em [0, 100]."""
    fails: list[str] = []
    for uf, data in all_data.items():
        cut = _safe_dict(_safe_dict(data.get("indicators", {}).get("pne_m12a")).get("total_estado"))
        por_rede = _safe_dict(cut.get("por_rede"))
        for rede, v in por_rede.items():
            if _is_num(v) and (v < 0 or v > 100.5):
                fails.append(f"pne_m12a/{uf}/{rede}: valor {v} fora de [0,100]")
    return fails


def check_neet_amostra_minima(all_data: dict[str, dict], threshold: int = 50) -> list[str]:
    """NEET tem n_amostra implícito via pop ponderada. Verifica que valor está em [0, 100]."""
    fails: list[str] = []
    for uf, data in all_data.items():
        cut = _safe_dict(_safe_dict(data.get("indicators", {}).get("mer_neet_rate")).get("total_estado"))
        v = cut.get("valor")
        if _is_num(v) and (v < 0 or v > 100):
            fails.append(f"mer_neet_rate/{uf}: valor {v} fora de [0,100]")
    return fails


def check_vintage_plausivel(all_data: dict[str, dict]) -> list[str]:
    """Vintage por indicador deve ser ano entre 2015 e 2025 (ou string range)."""
    fails: list[str] = []
    for uf, data in all_data.items():
        for code in get_indicator_codes():
            ind = _safe_dict(data.get("indicators", {}).get(code))
            vintage = ind.get("vintage", "")
            if not vintage or vintage == "indisponível":
                continue
            # Aceita "2024", "2024-Q1", "2021-2025", "2024 (com a)"
            digits = "".join(c for c in str(vintage)[:4] if c.isdigit())
            if not digits:
                fails.append(f"{code}/{uf}: vintage sem ano: {vintage!r}")
                continue
            ano = int(digits)
            if ano < 2015 or ano > 2026:
                fails.append(f"{code}/{uf}: vintage com ano implausível: {vintage!r}")
    return fails


def check_crescimento_5y_range(all_data: dict[str, dict]) -> list[str]:
    """Crescimento 5y deve estar em [-100, 500]%. Acima é provável bug de cálculo."""
    fails: list[str] = []
    for uf, data in all_data.items():
        for recorte in ("total_estado", "rede_estadual"):
            cut = _safe_dict(_safe_dict(data.get("indicators", {}).get("din_crescimento_matriculas_5y")).get(recorte))
            v = cut.get("crescimento_5y_pct")
            if _is_num(v) and (v < -100 or v > 500):
                fails.append(f"din_crescimento_matriculas_5y/{recorte}/{uf}: {v}% fora de [-100, 500]")
    return fails


def check_perfil_alunos_pcts(all_data: dict[str, dict]) -> list[str]:
    """faixa_etaria 15_17+18_24+25_mais ≈ 100; sexo masc+fem ≈ 100; modalidade soma ≈ 100."""
    fails: list[str] = []
    for uf, data in all_data.items():
        cut = _safe_dict(_safe_dict(data.get("indicators", {}).get("cob_perfil_alunos")).get("total_estado"))
        fe = _safe_dict(cut.get("faixa_etaria"))
        sx = _safe_dict(cut.get("sexo"))
        md = _safe_dict(cut.get("modalidade"))
        for label, d, keys in (
            ("faixa_etaria", fe, ["15_17_pct", "18_24_pct", "25_mais_pct"]),
            ("sexo", sx, ["masculino_pct", "feminino_pct"]),
            ("modalidade", md, ["integrada_pct", "concomitante_pct", "subsequente_pct", "eja_tecnico_pct"]),
        ):
            vals = [d.get(k) for k in keys]
            if all(_is_num(v) for v in vals):
                soma = sum(float(v) for v in vals)
                if abs(soma - 100) > 1.0:
                    fails.append(f"cob_perfil_alunos.{label}/{uf}: soma {soma:.2f} (esperado ≈100)")
    return fails


CHECKS = [
    ("27_files_exist", check_27_files_exist),
    ("indicator_count_matches_catalog", check_indicator_count),
    ("ranking_positions_distinct", check_ranking_distinct),
    ("ranking_nullity_consistency", check_ranking_nullity_consistency),
    ("ranking_aplicavel_false_purged", check_ranking_aplicavel_purged),
    ("polaridade_consistente_com_pos1", check_polaridade_consistency),
    ("pop_15_29_completeness", lambda _data: check_pop_15_29_completeness()),
    ("dist_dependencia_soma_100", check_distribuicao_dependencia_soma),
    ("pne_m12a_por_rede_em_0_100", check_pne_m12a_redes_capped),
    ("neet_em_0_100", check_neet_amostra_minima),
    ("vintage_plausivel", check_vintage_plausivel),
    ("crescimento_5y_range", check_crescimento_5y_range),
    ("perfil_alunos_pcts_somam_100", check_perfil_alunos_pcts),
]


def main() -> int:
    all_data: dict[str, dict] = {}
    for uf in UFS:
        path = DIAGNOSTIC_DIR / f"{uf}.json"
        if path.exists():
            all_data[uf] = json.loads(path.read_text(encoding="utf-8"))

    total_failures: list[tuple[str, str]] = []
    for name, fn in CHECKS:
        try:
            fails = fn(all_data)
            if fails:
                logger.error(f"[FAIL] {name}: {len(fails)} violações")
                for f in fails[:10]:
                    logger.error(f"  - {f}")
                if len(fails) > 10:
                    logger.error(f"  ... +{len(fails)-10} mais")
                total_failures.extend((name, f) for f in fails)
            else:
                logger.info(f"[OK] {name}")
        except Exception as e:
            logger.error(f"[ERROR] {name}: {type(e).__name__}: {e}")
            total_failures.append((name, f"exception: {e}"))

    if total_failures:
        logger.error(f"\nTotal: {len(total_failures)} violações em {len({n for n,_ in total_failures})} checks")
        return 1
    logger.info(f"\n✓ {len(CHECKS)} checks passaram, painel está consistente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
