"""
14 processadores DataFrame → JSON dict pronto pra publicação.

Cada função recebe (df, uf) e devolve um dict que entra direto no JSON do estado.
Shapes inspirados nos mocks pra preservar contrato com os renderers do frontend.

Algumas estruturas (vs_top_quartile, vs_media_nacional, posicao) só conseguem ser
calculadas após todos os 27 estados rodarem — ficam None aqui e são preenchidas no
benchmark cross-state em build.py.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_indicator(caveat: str) -> dict[str, Any]:
    """Retorno padrão quando dados não estão disponíveis."""
    return {
        "vintage": "indisponível",
        "caveat": caveat,
    }


def _valor_5y(df: pd.DataFrame, value_col: str, year_col: str = "ano") -> dict[str, Any]:
    """Extrai sparkline de 5 anos com anos correspondentes."""
    sub = df.dropna(subset=[value_col]).sort_values(year_col).tail(5)
    return {
        "valor_5y": [float(v) for v in sub[value_col].tolist()],
        "anos_5y": [int(y) for y in sub[year_col].tolist()],
    }


def _ano_mais_recente(df: pd.DataFrame) -> int | None:
    if "ano" not in df.columns or df["ano"].dropna().empty:
        return None
    return int(df["ano"].max())


# ---------------------------------------------------------------------------
# 14 Processadores
# ---------------------------------------------------------------------------


def cob_distribuicao_dependencia(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, pct_federal, pct_estadual, pct_municipal, pct_privada, total."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    latest = df.sort_values("ano").iloc[-1]
    return {
        "total_estado": {
            "federal": float(latest.get("pct_federal", 0) or 0),
            "estadual": float(latest.get("pct_estadual", 0) or 0),
            "municipal": float(latest.get("pct_municipal", 0) or 0),
            "privada": float(latest.get("pct_privada", 0) or 0),
            "total_matriculas": int(latest.get("total_matriculas", 0) or 0),
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "Sistema S agregado em 'privada'.",
    }


def cob_municipios_com_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, pct_total_estado, pct_rede_estadual, total_municipios."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    latest = df.sort_values("ano").iloc[-1]
    spark_total = _valor_5y(df, "pct_total_estado")
    spark_estadual = _valor_5y(df, "pct_rede_estadual")
    return {
        "total_estado": {
            "valor": float(latest["pct_total_estado"]) if pd.notna(latest["pct_total_estado"]) else None,
            **spark_total,
        },
        "rede_estadual": {
            "valor": float(latest["pct_rede_estadual"]) if pd.notna(latest["pct_rede_estadual"]) else None,
            **spark_estadual,
        },
        "total_municipios": int(latest["total_municipios"]),
        "vintage": str(int(latest["ano"])),
        "caveat": "Município conta igual independente do tamanho.",
    }


def cob_eixos_cobertos(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, rede, id_curso, qtd_matriculas. Mapeamento curso→eixo é pós-query."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar para EPT.")
    # TODO: usar etl/reference/cnct_curso_eixo.csv pra mapear id_curso → eixo
    # Por enquanto retorna agregado bruto pra debug + caveat informando pendência
    latest_year = int(df["ano"].max())
    sub = df[df["ano"] == latest_year]
    total = int(sub["qtd_matriculas"].sum())
    cursos_distintos = int(sub["id_curso"].nunique())
    return {
        "total_estado": {
            "valor": None,
            "cursos_distintos": cursos_distintos,
            "total_matriculas": total,
        },
        "vintage": str(latest_year),
        "caveat": "Mapeamento curso→eixo (CNCT v4) pendente. Reportando contagem bruta de cursos distintos por enquanto.",
    }


def cob_distribuicao_modalidade(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, rede, etapa_ensino, qtd_matriculas. Classificação modalidade pós-query."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    latest_year = int(df["ano"].max())
    sub = df[df["ano"] == latest_year]
    total = int(sub["qtd_matriculas"].sum())
    return {
        "total_estado": {
            "total_matriculas_ept": total,
            "etapas_distintas": int(sub["etapa_ensino"].nunique()),
        },
        "vintage": str(latest_year),
        "caveat": "Classificação etapa_ensino → modalidade (integrada/concomitante/subsequente) pendente.",
    }


def _safe_float(v: Any) -> float | None:
    """Pandas NA-aware float coercion."""
    if v is None or pd.isna(v):
        return None
    return float(v)


def qua_taxas_rendimento_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, aprovacao/reprovacao/abandono total e estadual."""
    if df.empty:
        return _empty_indicator("Sem dados Indicadores Educacionais cruzando com escolas EPT.")
    latest = df.sort_values("ano").iloc[-1]
    # `taxa_aprovacao_em` no basedosdados.br_inep_indicadores_educacionais.escola
    # tem escala atípica (max ~20, avg ~5) — não é percentual convencional. Por isso
    # 'valor' fica None pra não enviesar o ranking. `taxa_abandono_em` está OK (0-100).
    return {
        "total_estado": {
            "valor": _safe_float(latest.get("abandono_total")),
            "aprovacao": _safe_float(latest.get("aprovacao_total")),
            "reprovacao": _safe_float(latest.get("reprovacao_total")),
            "abandono": _safe_float(latest.get("abandono_total")),
        },
        "rede_estadual": {
            "valor": _safe_float(latest.get("abandono_estadual")),
            "aprovacao": _safe_float(latest.get("aprovacao_estadual")),
            "reprovacao": _safe_float(latest.get("reprovacao_estadual")),
            "abandono": _safe_float(latest.get("abandono_estadual")),
        },
        "polaridade_inversa": True,
        "vintage": str(int(latest["ano"])),
        "caveat": "Taxa de abandono EM ponderada por matrículas EPT (proxy). taxa_aprovacao_em do BD está em escala atípica (~0-20) e foi exibida no card mas não usada para ranking.",
    }


def qua_ideb_escolas_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano (2017,2019,2021,2023), ideb_total_estado, ideb_rede_estadual."""
    if df.empty:
        return _empty_indicator("Sem dados IDEB para escolas EPT.")
    latest = df.sort_values("ano").iloc[-1]
    return {
        "total_estado": {
            "valor": float(latest["ideb_total_estado"]) if pd.notna(latest["ideb_total_estado"]) else None,
            **_valor_5y(df, "ideb_total_estado"),
        },
        "rede_estadual": {
            "valor": float(latest["ideb_rede_estadual"]) if pd.notna(latest["ideb_rede_estadual"]) else None,
            **_valor_5y(df, "ideb_rede_estadual"),
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "IDEB-EM bianual. Mede ambiente pedagógico, não componente técnico.",
    }


def qua_razao_aluno_professor_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, razao_total_estado, razao_rede_estadual."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    latest = df.sort_values("ano").iloc[-1]
    return {
        "total_estado": {
            "valor": float(latest["razao_total_estado"]) if pd.notna(latest["razao_total_estado"]) else None,
            **_valor_5y(df, "razao_total_estado"),
        },
        "rede_estadual": {
            "valor": float(latest["razao_rede_estadual"]) if pd.notna(latest["razao_rede_estadual"]) else None,
            **_valor_5y(df, "razao_rede_estadual"),
        },
        "polaridade_inversa": True,
        "vintage": str(int(latest["ano"])),
        "caveat": "Razão menor é melhor. Numerador é matrícula, denominador é docente único.",
    }


def inf_conectividade_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, pct_t1..t4 total e estadual (tier banda larga + uso aluno)."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    latest = df.sort_values("ano").iloc[-1]
    valor_total = _safe_float(latest.get("pct_t1_total"))
    valor_estadual = _safe_float(latest.get("pct_t1_estadual"))
    return {
        "total_estado": {
            "valor": valor_total,
            "tier_distribuicao": {
                "banda_larga_com_uso_aluno": valor_total,
                "banda_larga_sem_uso_aluno": _safe_float(latest.get("pct_t2_total")),
                "internet_basica_sem_banda_larga": _safe_float(latest.get("pct_t3_total")),
                "sem_internet": _safe_float(latest.get("pct_t4_total")),
            },
            **_valor_5y(df, "pct_t1_total"),
        },
        "rede_estadual": {
            "valor": valor_estadual,
            "tier_distribuicao": {
                "banda_larga_com_uso_aluno": valor_estadual,
                "banda_larga_sem_uso_aluno": _safe_float(latest.get("pct_t2_estadual")),
                "internet_basica_sem_banda_larga": _safe_float(latest.get("pct_t3_estadual")),
                "sem_internet": _safe_float(latest.get("pct_t4_estadual")),
            },
            **_valor_5y(df, "pct_t1_estadual"),
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "Auto-declaratório. Velocidade real (Mbps) não coletada pelo Censo.",
    }


def mer_saldo_caged_tecnicos(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, saldo_12m, top_3_subfamilias (struct array)."""
    if df.empty:
        return _empty_indicator("Sem dados CAGED.")
    latest = df.sort_values("ano").iloc[-1]
    saldo_12m = int(latest["saldo_12m"]) if pd.notna(latest.get("saldo_12m")) else 0
    top3 = []
    raw_top3 = latest.get("top_3_subfamilias")
    if raw_top3 is not None:
        try:
            for item in raw_top3:
                top3.append({
                    "cbo": str(item["cbo"]),
                    "saldo": int(item["saldo"]),
                })
        except (TypeError, KeyError):
            pass
    return {
        "total_estado": {
            "valor": float(saldo_12m),
            "saldo_12m": saldo_12m,
            "top_3_subfamilias_cbo": top3,
            **_valor_5y(df, "saldo_12m"),
        },
        "vintage": f"{int(latest['ano'])}-Q1",
        "caveat": "Apenas vínculos formais. CBO 3xxxx exclui ocupações afins em 5xxxx/7xxxx.",
    }


def mer_premio_salarial_escolaridade(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, mediana_sem_em, mediana_em_completo, mediana_superior, n_*."""
    if df.empty:
        return _empty_indicator("Sem dados RAIS.")
    latest = df.sort_values("ano").iloc[-1]
    sem_em = _safe_float(latest.get("mediana_sem_em")) or 0
    em = _safe_float(latest.get("mediana_em_completo")) or 0
    sup = _safe_float(latest.get("mediana_superior")) or 0
    superior_vs_em = round((sup / em - 1) * 100, 1) if em else None
    return {
        "total_estado": {
            "valor": superior_vs_em,
            "medianas_brl_real": {
                "sem_ensino_medio": round(sem_em, 2),
                "ensino_medio_completo": round(em, 2),
                "superior_completo": round(sup, 2),
            },
            "premios_pct": {
                "em_vs_sem_em": round((em / sem_em - 1) * 100, 1) if sem_em else None,
                "superior_vs_em": superior_vs_em,
                "superior_vs_sem_em": round((sup / sem_em - 1) * 100, 1) if sem_em else None,
            },
            "premio_ept_especifico_publicamente_mensuravel": False,
            "vintage_rais": str(int(latest["ano"])),
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "RAIS não distingue EM regular de EM técnico em microdados públicos. Prêmio EPT específico exige cruzamento Censo×RAIS por CPF.",
    }


def mer_neet_rate(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, neet_rate_total, neet_15_17/18_24/25_29, neet_homens/mulheres, etc."""
    if df.empty:
        return _empty_indicator("Sem dados PNAD Contínua.")
    latest = df.sort_values("ano").iloc[-1]
    return {
        "total_estado": {
            "valor": float(latest.get("neet_rate_total") or 0),
            "por_faixa_etaria": {
                "15_17": float(latest.get("neet_15_17") or 0),
                "18_24": float(latest.get("neet_18_24") or 0),
                "25_29": float(latest.get("neet_25_29") or 0),
            },
            "por_sexo": {
                "homens": float(latest.get("neet_homens") or 0),
                "mulheres": float(latest.get("neet_mulheres") or 0),
            },
            "composicao_neet": {
                "desempregados_buscando_pct": float(latest.get("pct_buscando") or 0),
                "inativos_nao_procurando_pct": float(latest.get("pct_inativos") or 0),
            },
            **_valor_5y(df, "neet_rate_total"),
            "polaridade_inversa": True,
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "PNAD amostral. Estados de pop menor têm IC mais amplo.",
    }


def din_crescimento_matriculas_5y(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna ano, rede, etapa_ensino, qtd. Classificação modalidade ainda pendente."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar 2019/2024.")
    base_year, end_year = 2019, 2024
    qtd_base = int(df[df["ano"] == base_year]["qtd"].sum() or 0)
    qtd_end = int(df[df["ano"] == end_year]["qtd"].sum() or 0)
    qtd_base_est = int(df[(df["ano"] == base_year) & (df["rede"] == "2")]["qtd"].sum() or 0)
    qtd_end_est = int(df[(df["ano"] == end_year) & (df["rede"] == "2")]["qtd"].sum() or 0)
    growth_total = round((qtd_end / qtd_base - 1) * 100, 2) if qtd_base else None
    growth_est = round((qtd_end_est / qtd_base_est - 1) * 100, 2) if qtd_base_est else None
    cagr_total = round(((qtd_end / qtd_base) ** (1/5) - 1) * 100, 2) if qtd_base else None
    cagr_est = round(((qtd_end_est / qtd_base_est) ** (1/5) - 1) * 100, 2) if qtd_base_est else None
    # Threshold: redes com base < 1000 matrículas têm crescimento % muito sensível a
    # ruído (RN rede estadual cresceu 1060% partindo de 712). Suprime tanto valor
    # exibido quanto o que entra no ranking.
    BASE_MIN = 1000
    valor_total = growth_total if qtd_base >= BASE_MIN else None
    valor_est = growth_est if qtd_base_est >= BASE_MIN else None
    return {
        "total_estado": {
            "valor": valor_total,
            "crescimento_5y_pct": valor_total,
            "cagr_5y_pct": cagr_total if qtd_base >= BASE_MIN else None,
            "matriculas_base": qtd_base,
            "matriculas_atual": qtd_end,
            "base_insuficiente": qtd_base < BASE_MIN,
        },
        "rede_estadual": {
            "valor": valor_est,
            "crescimento_5y_pct": valor_est,
            "cagr_5y_pct": cagr_est if qtd_base_est >= BASE_MIN else None,
            "matriculas_base": qtd_base_est,
            "matriculas_atual": qtd_end_est,
            "base_insuficiente": qtd_base_est < BASE_MIN,
        },
        "vintage": str(end_year),
        "caveat": f"Janela {base_year}→{end_year} (Censo Escolar via tabela turma). Redes com base <{BASE_MIN} matrículas têm crescimento suprimido (alta variância). Decomposição por modalidade pendente.",
    }


def din_cursos_novos_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna 1 linha com cursos_novos_total/estadual e cursos_descontinuados_total/estadual."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    row = df.iloc[0]
    novos_total = int(row.get("cursos_novos_total") or 0)
    desc_total = int(row.get("cursos_descontinuados_total") or 0)
    novos_estadual = int(row.get("cursos_novos_estadual") or 0)
    desc_estadual = int(row.get("cursos_descontinuados_estadual") or 0)
    saldo_total = novos_total - desc_total
    saldo_est = novos_estadual - desc_estadual
    return {
        "total_estado": {
            "valor": float(saldo_total),
            "cursos_novos_2y": novos_total,
            "cursos_descontinuados_2y": desc_total,
            "saldo_liquido_2y": saldo_total,
        },
        "rede_estadual": {
            "valor": float(saldo_est),
            "cursos_novos_2y": novos_estadual,
            "cursos_descontinuados_2y": desc_estadual,
            "saldo_liquido_2y": saldo_est,
        },
        "vintage": "2024",
        "caveat": "Par escola+curso novo em 2024 que não existia 2020-2023.",
    }


# ---------------------------------------------------------------------------
# Indicadores adicionais — Meta 12 PNE + cards reformados (2026-Q2)
# ---------------------------------------------------------------------------


def pne_m12a(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """% do EM em integrada+concomitante. Saída: total + decomposição por rede + 5y."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    df = df.sort_values("ano")
    latest = df.iloc[-1]
    valor = _safe_float(latest.get("pct_total"))
    valor_estadual = _safe_float(latest.get("pct_estadual"))
    spark = [_safe_float(v) for v in df["pct_total"].tolist()]
    spark = [v if v is not None else 0.0 for v in spark]
    anos = [int(a) for a in df["ano"].tolist()]
    var_bienio = None
    if len(df) >= 3:
        v_now = _safe_float(latest.get("pct_total"))
        v_2yago = _safe_float(df.iloc[-3].get("pct_total"))
        if v_now is not None and v_2yago is not None:
            var_bienio = round(v_now - v_2yago, 2)
    return {
        "total_estado": {
            "valor": valor,
            "valor_5y": spark,
            "anos_5y": anos,
            "por_rede": {
                "federal": _safe_float(latest.get("pct_federal")) or 0,
                "estadual": _safe_float(latest.get("pct_estadual")) or 0,
                "municipal": _safe_float(latest.get("pct_municipal")) or 0,
                "privada": _safe_float(latest.get("pct_privada")) or 0,
            },
            "var_bienio_pp": var_bienio,
            "meta_2036_pct": 50.0,
            "gap_pp": round(50.0 - valor, 2) if valor is not None else None,
        },
        "rede_estadual": {
            "valor": valor_estadual,
            "valor_5y": [_safe_float(v) or 0.0 for v in df["pct_estadual"].tolist()],
            "anos_5y": anos,
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "Numerador: matrículas em EM-técnico (integrada) + Profissional Técnica concomitante. Denominador: matrículas EM total.",
    }


def pne_m12b(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """Matrículas em curso subsequente 2020-2024 + projeção linear até 2036 + meta +60%."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    df = df.sort_values("ano")
    # Base = primeiro ano com qtd > 0 (alguns campos foram populados só a partir de 2023)
    df_pos = df[df["qtd_subsequente_total"].fillna(0) > 0]
    if df_pos.empty:
        return _empty_indicator("Sem dados de subsequente populados em nenhum ano da janela.")
    base_year = int(df_pos.iloc[0]["ano"])
    end_year = int(df.iloc[-1]["ano"])
    base_qtd = int(df_pos.iloc[0]["qtd_subsequente_total"] or 0)
    end_qtd = int(df.iloc[-1]["qtd_subsequente_total"] or 0)
    meta_2036 = round(base_qtd * 1.60) if base_qtd else None
    # Projeção linear: ritmo dos últimos anos extrapolado até 2036
    proj_2036 = None
    if len(df) >= 2 and (end_year - base_year) > 0:
        ritmo = (end_qtd - base_qtd) / (end_year - base_year)
        proj_2036 = int(end_qtd + ritmo * (2036 - end_year))
    return {
        "total_estado": {
            "valor": end_qtd,
            "matriculas_base": base_qtd,
            "matriculas_atual": end_qtd,
            "ano_base": base_year,
            "ano_atual": end_year,
            "meta_2036": meta_2036,
            "projecao_2036": proj_2036,
            "valor_5y": [int(v or 0) for v in df["qtd_subsequente_total"].tolist()],
            "anos_5y": [int(a) for a in df["ano"].tolist()],
        },
        "rede_estadual": {
            "valor": int(df.iloc[-1]["qtd_subsequente_estadual"] or 0),
            "valor_5y": [int(v or 0) for v in df["qtd_subsequente_estadual"].tolist()],
            "anos_5y": [int(a) for a in df["ano"].tolist()],
        },
        "vintage": str(end_year),
        "caveat": "Curso subsequente = curso técnico após conclusão do EM. Meta 2036: +60% sobre a base 2020.",
    }


def pne_m12c(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """% EJA articulada / EJA total — por etapa (EM e Fundamental)."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    df = df.sort_values("ano")
    latest = df.iloc[-1]
    art_em = int(latest.get("articulada_em") or 0)
    eja_em = int(latest.get("eja_em_total") or 0)
    art_ef = int(latest.get("articulada_ef") or 0)
    eja_ef = int(latest.get("eja_ef_total") or 0)
    pct_em = round(100.0 * art_em / eja_em, 2) if eja_em else 0.0
    pct_ef = round(100.0 * art_ef / eja_ef, 2) if eja_ef else 0.0
    pct_total = round(100.0 * (art_em + art_ef) / (eja_em + eja_ef), 2) if (eja_em + eja_ef) else 0.0
    meta_2031 = 25.0
    meta_2036 = 50.0
    # Gap absoluto: matrículas que faltam pra meta 2031
    gap_2031 = int((eja_em + eja_ef) * 0.25 - (art_em + art_ef)) if (eja_em + eja_ef) else 0
    return {
        "total_estado": {
            "valor": pct_total,
            "pct_em": pct_em,
            "pct_ef": pct_ef,
            "articulada_em": art_em,
            "articulada_ef": art_ef,
            "eja_em_total": eja_em,
            "eja_ef_total": eja_ef,
            "meta_2031": meta_2031,
            "meta_2036": meta_2036,
            "gap_absoluto_2031": gap_2031,
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "EJA articulada à profissional = EJA-EM técnico + EJA-Fundamental FIC. Meta progressiva: 25% em 2031 e 50% em 2036.",
    }


def pne_m12f(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """% pop 18-24 com EM técnico concluído. Decomposição por sexo e raça."""
    if df.empty:
        return _empty_indicator("Sem dados PNAD Contínua.")
    df = df.sort_values("ano")
    latest = df.iloc[-1]
    valor = _safe_float(latest.get("pct_total")) or 0.0
    pop_total = _safe_float(latest.get("pop_18_24_total")) or 0.0
    meta_2036 = 10.0
    gap_pp = round(meta_2036 - valor, 2)
    # Gap absoluto: jovens a formar até 2036
    gap_abs = int(pop_total * (meta_2036 - valor) / 100) if valor < meta_2036 else 0
    return {
        "total_estado": {
            "valor": round(valor, 2),
            "meta_2036_pct": meta_2036,
            "gap_pp": gap_pp,
            "gap_absoluto_jovens": gap_abs,
            "ritmo_anual_necessario": int(gap_abs / 12) if gap_abs > 0 else 0,
            "por_sexo": {
                "homens": round(_safe_float(latest.get("pct_homens")) or 0, 2),
                "mulheres": round(_safe_float(latest.get("pct_mulheres")) or 0, 2),
            },
            "por_raca": {
                "brancos": round(_safe_float(latest.get("pct_brancos")) or 0, 2),
                "pretos_pardos": round(_safe_float(latest.get("pct_pretos_pardos")) or 0, 2),
            },
            "valor_5y": [_safe_float(v) or 0.0 for v in df["pct_total"].tolist()],
            "anos_5y": [int(a) for a in df["ano"].tolist()],
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "PNAD V3007 amostral. Estados de pop menor têm IC mais amplo.",
    }


def cob_perfil_alunos(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """Perfil dos matriculados EPT — faixa etária, sexo, modalidade."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar EPT.")
    row = df.iloc[0]
    def _i(key: str) -> int:
        v = row.get(key)
        if v is None or pd.isna(v):
            return 0
        return int(v)
    total = _i("total")
    integrada = _i("qtd_integrada")
    concomitante = _i("qtd_concomitante")
    subsequente = _i("qtd_subsequente")
    eja_tec = _i("qtd_eja_tecnico")
    total_modalidade = integrada + concomitante + subsequente + eja_tec
    pct = lambda v, t: round(100.0 * v / t, 1) if t else 0.0
    return {
        "total_estado": {
            "valor": float(total),
            "total_matriculas_ept": total,
            "faixa_etaria": {
                "15_17_pct": pct(_i("faixa_15_17"), total),
                "18_24_pct": pct(_i("faixa_18_24"), total),
                "25_mais_pct": pct(_i("faixa_25_mais"), total),
            },
            "sexo": {
                "masculino_pct": pct(_i("masc"), total),
                "feminino_pct": pct(_i("fem"), total),
            },
            "modalidade": {
                "integrada_pct": pct(integrada, total_modalidade),
                "concomitante_pct": pct(concomitante, total_modalidade),
                "subsequente_pct": pct(subsequente, total_modalidade),
                "eja_tecnico_pct": pct(eja_tec, total_modalidade),
            },
        },
        "vintage": str(_i("ano")),
        "caveat": "Perfil sociodemográfico extraído de matricula table; modalidade extraída dos agregados de escola.",
    }


def cob_alcance_ponderado(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """% matrículas EM em município com EPT + top 5 munis sem oferta."""
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar.")
    row = df.iloc[0]
    em_em_munis_com_ept = int(row.get("qtd_em_em_munis_com_ept") or 0)
    em_total = int(row.get("qtd_em_total") or 0)
    pct_alcance = round(100.0 * em_em_munis_com_ept / em_total, 1) if em_total else 0.0
    top5 = []
    raw_top5 = row.get("top5_sem_oferta")
    if raw_top5 is not None:
        try:
            for item in raw_top5:
                if item is None:
                    continue
                top5.append({
                    "municipio": str(item.get("municipio") or "—"),
                    "pop_em_proxy": int(item.get("pop_em_proxy") or 0),
                })
        except (TypeError, KeyError, AttributeError):
            pass
    return {
        "total_estado": {
            "valor": pct_alcance,
            "matriculas_em_em_munis_com_ept": em_em_munis_com_ept,
            "matriculas_em_total": em_total,
            "top5_sem_oferta": top5,
        },
        "vintage": str(int(row["ano"])),
        "caveat": "Cobertura ponderada por matrículas EM (proxy de demanda escolar). Top 5 são municípios SEM EPT com maior matrícula EM.",
    }


def qua_saeb_proficiencia_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """Proficiência média SAEB EM em municípios COM EPT vs SEM EPT (proxy)."""
    if df.empty:
        return _empty_indicator("Sem dados SAEB.")
    def get(disc: list[str], muni_com_ept: int) -> float | None:
        sub = df[(df["disciplina"].isin(disc)) & (df["muni_com_ept"] == muni_com_ept)]
        if sub.empty:
            return None
        return _safe_float(sub.iloc[0]["proficiencia_media"])
    mat_com = get(["MT", "matematica", "Matemática", "MATEMATICA"], 1)
    mat_sem = get(["MT", "matematica", "Matemática", "MATEMATICA"], 0)
    port_com = get(["LP", "lingua_portuguesa", "portugues", "PORTUGUES"], 1)
    port_sem = get(["LP", "lingua_portuguesa", "portugues", "PORTUGUES"], 0)
    ano = int(df["ano"].max())
    diff_mat = (mat_com - mat_sem) if (mat_com is not None and mat_sem is not None) else None
    diff_port = (port_com - port_sem) if (port_com is not None and port_sem is not None) else None
    diffs = [d for d in (diff_mat, diff_port) if d is not None]
    valor_premio = round(sum(diffs) / len(diffs), 1) if diffs else None
    return {
        "total_estado": {
            "valor": valor_premio,
            "matematica": {
                "com_ept": round(mat_com, 1) if mat_com is not None else None,
                "sem_ept": round(mat_sem, 1) if mat_sem is not None else None,
                "diferenca": round(diff_mat, 1) if diff_mat is not None else None,
            },
            "portugues": {
                "com_ept": round(port_com, 1) if port_com is not None else None,
                "sem_ept": round(port_sem, 1) if port_sem is not None else None,
                "diferenca": round(diff_port, 1) if diff_port is not None else None,
            },
        },
        "vintage": str(ano),
        "caveat": "SAEB amostral. Comparação por município: alunos em municípios com pelo menos uma escola EPT vs alunos em municípios sem nenhuma escola EPT. 'valor' = média dos prêmios MT+LP.",
    }


def qua_abandono_em_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """Taxa de abandono EM ponderada por matrícula EM, escolas COM EPT vs SEM EPT, rede estadual."""
    if df.empty:
        return _empty_indicator("Sem dados Indicadores Educacionais.")
    df = df.sort_values("ano", ascending=False)
    latest_year = int(df.iloc[0]["ano"])
    df_latest = df[df["ano"] == latest_year]
    com = df_latest[df_latest["tem_ept"] == 1]
    sem = df_latest[df_latest["tem_ept"] == 0]
    com_val = _safe_float(com.iloc[0]["taxa_abandono_em_ponderada"]) if not com.empty else None
    sem_val = _safe_float(sem.iloc[0]["taxa_abandono_em_ponderada"]) if not sem.empty else None
    return {
        "total_estado": {
            "valor": round(com_val, 2) if com_val is not None else None,
            "com_ept_pct": round(com_val, 2) if com_val is not None else None,
            "sem_ept_pct": round(sem_val, 2) if sem_val is not None else None,
            "diferenca_pp": round(sem_val - com_val, 2) if (com_val is not None and sem_val is not None) else None,
        },
        "vintage": str(latest_year),
        "caveat": "Taxa publicada pelo INEP, ponderada pelas matrículas EM da escola. Comparação intra-rede estadual.",
    }


def qua_ingresso_es_pnad(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """% jovens 18-29 com EM completo cursando ES, com EPT vs sem EPT (janela 5 anos)."""
    if df.empty:
        return _empty_indicator("Sem dados PNAD Contínua.")
    tec = df[df["grupo"] == "tec"]
    reg = df[df["grupo"] == "reg"]
    tec_val = _safe_float(tec.iloc[0]["pct_em_es"]) if not tec.empty else None
    reg_val = _safe_float(reg.iloc[0]["pct_em_es"]) if not reg.empty else None
    n_tec = int(tec.iloc[0]["n_amostra"]) if not tec.empty else 0
    n_reg = int(reg.iloc[0]["n_amostra"]) if not reg.empty else 0
    diff = (tec_val - reg_val) if (tec_val is not None and reg_val is not None) else None
    return {
        "total_estado": {
            "valor": round(diff, 1) if diff is not None else None,
            "com_ept_pct": round(tec_val, 1) if tec_val is not None else None,
            "sem_ept_pct": round(reg_val, 1) if reg_val is not None else None,
            "diferenca_pp": round(diff, 1) if diff is not None else None,
            "n_amostra_com_ept": n_tec,
            "n_amostra_sem_ept": n_reg,
        },
        "vintage": "2021-2025",
        "caveat": "PNAD Contínua, janela 5 anos (2021-2025). EPT = V3007='1' (concluiu técnico EM). Avançou ao ES = VD3005 >= 13 (nível concluído inclui Superior incompleto/completo/pós). 'valor' = diferença pp (com EPT - sem EPT).",
    }


def mer_renda_jovens_pnad(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """Mediana de renda mensal por nível de formação (jovens 18-29, 4 níveis não-sobrepostos)."""
    if df.empty:
        return _empty_indicator("Sem dados PNAD Contínua.")
    def get_mediana(bucket: str) -> tuple[float | None, int]:
        sub = df[df["bucket"] == bucket]
        if sub.empty:
            return None, 0
        return _safe_float(sub.iloc[0]["mediana_renda"]), int(sub.iloc[0]["n_amostra"])
    sem_em, n_sem = get_mediana("sem_em")
    em_reg, n_reg = get_mediana("em_reg")
    tem_ept, n_ept = get_mediana("tem_ept")
    sup_sem_ept, n_sup = get_mediana("superior_sem_ept")
    pct = lambda a, b: round((a / b - 1) * 100, 1) if (a and b) else None
    premio_ept = pct(tem_ept, em_reg)
    return {
        "total_estado": {
            "valor": premio_ept,
            "medianas": {
                "sem_em": round(sem_em, 2) if sem_em is not None else None,
                "em_regular": round(em_reg, 2) if em_reg is not None else None,
                "tem_ept": round(tem_ept, 2) if tem_ept is not None else None,
                "superior_sem_ept": round(sup_sem_ept, 2) if sup_sem_ept is not None else None,
            },
            "n_amostra": {
                "sem_em": n_sem,
                "em_regular": n_reg,
                "tem_ept": n_ept,
                "superior_sem_ept": n_sup,
            },
            "premios_pct": {
                "em_reg_vs_sem_em": pct(em_reg, sem_em),
                "ept_vs_em_reg": premio_ept,
                "superior_sem_ept_vs_em_reg": pct(sup_sem_ept, em_reg),
            },
        },
        "vintage": "2021-2025",
        "caveat": "PNAD Contínua, janela 5 anos (2021-2025). Buckets não-sobrepostos: 'Com EPT' inclui toda a coorte que passou por EPT, mesmo quem avançou para o Superior. 'valor' = prêmio % EPT vs EM regular. Mediana sem ponderação amostral.",
    }


def qua_aderencia_docente_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna 1 linha com: ano, docentes_total, pct_superior_total,
    pct_pos_lato_total, pct_pos_stricto_total, docentes_estadual,
    pct_superior_estadual, pct_pos_lato_estadual, pct_pos_stricto_estadual.
    """
    if df.empty:
        return _empty_indicator("Sem dados Censo Escolar — docentes EPT.")
    row = df.iloc[0]
    docentes_total = int(row.get("docentes_total") or 0)
    docentes_estadual = int(row.get("docentes_estadual") or 0)
    return {
        "total_estado": {
            "valor": _safe_float(row.get("pct_superior_total")),
            "pct_superior": _safe_float(row.get("pct_superior_total")),
            "pct_pos_lato": _safe_float(row.get("pct_pos_lato_total")),
            "pct_pos_stricto": _safe_float(row.get("pct_pos_stricto_total")),
            "n_docentes": docentes_total,
        },
        "rede_estadual": {
            "valor": _safe_float(row.get("pct_superior_estadual")),
            "pct_superior": _safe_float(row.get("pct_superior_estadual")),
            "pct_pos_lato": _safe_float(row.get("pct_pos_lato_estadual")),
            "pct_pos_stricto": _safe_float(row.get("pct_pos_stricto_estadual")),
            "n_docentes": docentes_estadual,
        },
        "vintage": str(int(row["ano"])),
        "caveat": (
            "Universo: docentes que ensinam disciplina profissionalizante em curso EPT "
            "(disciplina_profissionalizante='1' E id_curso_educ_profissional NOT NULL). "
            "Mede formação BRUTA: % com superior, % com pós lato (especialização), % com "
            "pós stricto (mestrado ou doutorado). Não mede aderência por área — um historiador "
            "que dá aula de Mecânica conta como 'tem superior'. Aderência por área exige "
            "mapping CINE-Brasil → eixo CNCT (próximo ciclo)."
        ),
    }


# ---------------------------------------------------------------------------
# Mercado 10x — 3 cards novos (2026-Q2)
# ---------------------------------------------------------------------------


def mer_demanda_cbo_top(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano_referencia, cbo_2002, cbo_descricao, saldo_12m,
    n_admissoes, n_desligamentos, salario_p25, salario_mediano, salario_p75.

    Top 15 já vem ordenado pelo SQL. Reportamos os 10 com maior saldo absoluto
    + os 3 com maior salário mediano (mesmo se saldo modesto), pra mostrar
    onde o mercado paga melhor. Sem invenção: descrição vem do diretório CBO
    da BD; se for null, usa só o código.
    """
    if df.empty:
        return _empty_indicator("Sem dados CAGED em CBO 3xxxx para o estado.")

    ano = int(df["ano_referencia"].iloc[0])

    rows = df.to_dict("records")
    for r in rows:
        if not r.get("cbo_descricao"):
            r["cbo_descricao"] = None

    top_10_saldo = sorted(rows, key=lambda r: r["saldo_12m"] or 0, reverse=True)[:10]

    # Top salário entre os com saldo positivo + n_admissoes >= 50 (estabilidade)
    candidatos_sal = [r for r in rows if (r.get("saldo_12m") or 0) > 0 and (r.get("n_admissoes") or 0) >= 50]
    top_3_salario = sorted(candidatos_sal, key=lambda r: r["salario_mediano"] or 0, reverse=True)[:3]

    def _strip(r: dict[str, Any]) -> dict[str, Any]:
        return {
            "cbo": r["cbo_2002"],
            "descricao": r.get("cbo_descricao"),
            "saldo_12m": int(r["saldo_12m"]) if r.get("saldo_12m") is not None else None,
            "n_admissoes": int(r["n_admissoes"]) if r.get("n_admissoes") is not None else None,
            "salario_mediano": _safe_float(r.get("salario_mediano")),
            "salario_p25": _safe_float(r.get("salario_p25")),
            "salario_p75": _safe_float(r.get("salario_p75")),
        }

    return {
        "total_estado": {
            "ano_referencia": ano,
            "top_saldo": [_strip(r) for r in top_10_saldo],
            "top_salario": [_strip(r) for r in top_3_salario],
            "n_total_cbos_listados": len(rows),
        },
        "vintage": str(ano),
        "caveat": (
            f"CAGED {ano} — saldo de movimentação em CBO 3xxxx (Técnicos de Nível Médio). "
            "Salário mediano apenas em admissões com salário > 0. "
            "Descrição CBO via diretório oficial; quando ausente, mostra código."
        ),
        "ranking_aplicavel": False,  # lista, não valor único comparável
    }


def mer_demanda_mesorregiao(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano_referencia, id_mesorregiao, nome_mesorregiao, sigla_uf_meso,
    saldo_12m, n_admissoes, salario_mediano, salario_p25, salario_p75.

    Para uma UF: lista as mesorregiões do estado ordenadas por saldo CBO 3xxxx.
    Para BR: lista nacional das top mesorregiões — geometricamente desconexas.
    Frontend deve detectar via ufs_distintos > 1 e renderizar como ranking nacional.
    """
    if df.empty:
        return _empty_indicator("Sem dados CAGED por mesorregião para o estado.")

    ano = int(df["ano_referencia"].iloc[0])

    saldo_total = float(df["saldo_12m"].sum()) if not df["saldo_12m"].isna().all() else 0.0

    rows = []
    for _, r in df.iterrows():
        saldo = int(r["saldo_12m"]) if pd.notna(r["saldo_12m"]) else 0
        share = (saldo / saldo_total * 100) if saldo_total else None
        rows.append({
            "id_mesorregiao": r["id_mesorregiao"],
            "nome": r["nome_mesorregiao"],
            "sigla_uf": r.get("sigla_uf_meso"),
            "saldo_12m": saldo,
            "share_pct": round(share, 2) if share is not None else None,
            "n_admissoes": int(r["n_admissoes"]) if pd.notna(r["n_admissoes"]) else 0,
            "salario_mediano": _safe_float(r.get("salario_mediano")),
            "salario_p25": _safe_float(r.get("salario_p25")),
            "salario_p75": _safe_float(r.get("salario_p75")),
        })

    saldos_validos = [r["saldo_12m"] for r in rows if r["saldo_12m"] is not None]
    ufs_distintos = df["sigla_uf_meso"].dropna().unique().tolist() if "sigla_uf_meso" in df.columns else []

    return {
        "total_estado": {
            "ano_referencia": ano,
            "mesorregioes": rows,
            "n_mesorregioes": len(rows),
            "saldo_total": int(saldo_total) if saldo_total is not None else None,
            "saldo_max": max(saldos_validos) if saldos_validos else None,
            "saldo_min": min(saldos_validos) if saldos_validos else None,
            "modo_nacional": len(ufs_distintos) > 1,  # frontend usa pra decidir layout
        },
        "vintage": str(ano),
        "caveat": (
            f"CAGED {ano} — saldo CBO 3xxxx por mesorregião (IBGE). "
            "Mesorregiões com |saldo| < 30 suprimidas. Salário mediano só com n ≥ 50 admissões."
        ),
        "ranking_aplicavel": False,
    }


def mer_coorte_sintetica_pnad(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna linhas (ano, idade, sexo, caminho, pop_ponderada, n_amostral)
    para 2 ondas: ano_followup-1 (jovens 18-19) e ano_followup (jovens 19-20).

    Coorte sintética: PNAD trimestral é amostra rotativa; comparamos a turma
    18-19 com EM completo no Q1 ano X com a turma 19-20 em Q1 ano X+1. Não
    é tracking individual — é comparação de coortes etárias com mesmo perfil
    educacional.

    4 caminhos disjuntos: formal, informal, superior, neet (+ "outro" residual).
    """
    if df.empty:
        return _empty_indicator("Sem dados PNAD trimestral para coorte sintética.")

    if df["ano"].nunique() < 2:
        return _empty_indicator("PNAD trimestral só com 1 ano disponível — coorte sintética exige 2 ondas.")

    anos_ordenados = sorted(df["ano"].dropna().unique().tolist())
    ano_followup = int(anos_ordenados[-1])
    ano_base = int(anos_ordenados[-2])

    CAMINHOS = ["so_formal", "so_informal", "formal_estuda", "informal_estuda", "so_estuda", "neet", "outro_estuda"]

    def _agg_coorte(sub: pd.DataFrame) -> dict[str, Any] | None:
        """Agrega percentuais ponderados por caminho (6 categorias disjuntas)."""
        if sub.empty:
            return None
        total_pop = sub["pop_ponderada"].sum()
        total_n = int(sub["n_amostral"].sum())
        if total_pop <= 0 or total_n < 50:
            return {
                "amostra_insuficiente": True,
                "n_amostral": total_n,
            }
        result: dict[str, float | None] = {}
        for cam in CAMINHOS:
            mask = sub["caminho"] == cam
            pop_cam = sub.loc[mask, "pop_ponderada"].sum() if mask.any() else 0.0
            result[f"{cam}_pct"] = round(pop_cam / total_pop * 100, 2)
        # Agregados úteis pra renderer e leitura
        result["trabalha_estuda_pct"] = round(result["formal_estuda_pct"] + result["informal_estuda_pct"], 2)
        result["estuda_total_pct"] = round(result["trabalha_estuda_pct"] + result["so_estuda_pct"], 2)
        result["trabalha_total_pct"] = round(
            result["so_formal_pct"] + result["so_informal_pct"]
            + result["formal_estuda_pct"] + result["informal_estuda_pct"], 2
        )
        return {
            "amostra_insuficiente": False,
            "n_amostral": total_n,
            **result,
        }

    # Coorte base: idade 18 ou 19 no ano_base
    base_total = df[(df["ano"] == ano_base) & (df["idade"].isin([18, 19]))]
    followup_total = df[(df["ano"] == ano_followup) & (df["idade"].isin([19, 20]))]

    coorte_base = _agg_coorte(base_total)
    coorte_followup = _agg_coorte(followup_total)

    # Por sexo
    coorte_por_sexo: dict[str, dict[str, Any]] = {}
    for sexo_code, sexo_label in [("1", "homens"), ("2", "mulheres")]:
        b_sex = base_total[base_total["sexo"] == sexo_code]
        f_sex = followup_total[followup_total["sexo"] == sexo_code]
        coorte_por_sexo[sexo_label] = {
            "base": _agg_coorte(b_sex),
            "followup": _agg_coorte(f_sex),
        }

    # Deltas pp (followup - base) — só se ambos válidos
    deltas: dict[str, float | None] = {}
    if (
        coorte_base
        and coorte_followup
        and not coorte_base.get("amostra_insuficiente")
        and not coorte_followup.get("amostra_insuficiente")
    ):
        for cam in CAMINHOS + ["trabalha_estuda", "estuda_total", "trabalha_total"]:
            k = f"{cam}_pct"
            b = coorte_base.get(k)
            f = coorte_followup.get(k)
            deltas[cam] = round(f - b, 2) if (b is not None and f is not None) else None

    return {
        "total_estado": {
            "ano_base": ano_base,
            "ano_followup": ano_followup,
            "trimestre": 1,
            "coorte_base": coorte_base,
            "coorte_followup": coorte_followup,
            "deltas_pp": deltas if deltas else None,
            "por_sexo": coorte_por_sexo,
        },
        "vintage": str(ano_followup),
        "caveat": (
            f"PNAD Contínua Q1/{ano_base} → Q1/{ano_followup}. Coorte sintética: comparação "
            "de duas ondas independentes da amostra rotativa, não tracking individual. "
            "Cohort 18-20 completa (não filtrada por escolaridade). 'Cursa superior' = "
            "V3002='1' (frequenta) AND V3003A IN ('8','9','10','11') (graduação ou pós). "
            "Pesos V1028 oficiais. Categorias suprimidas com n_amostral < 50 (corte IBGE)."
        ),
        "ranking_aplicavel": False,
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


PROCESSORS = {
    "cob_distribuicao_dependencia": cob_distribuicao_dependencia,
    "cob_municipios_com_ept": cob_municipios_com_ept,
    "cob_eixos_cobertos": cob_eixos_cobertos,
    "cob_distribuicao_modalidade": cob_distribuicao_modalidade,
    "qua_taxas_rendimento_ept": qua_taxas_rendimento_ept,
    "qua_ideb_escolas_ept": qua_ideb_escolas_ept,
    "qua_razao_aluno_professor_ept": qua_razao_aluno_professor_ept,
    "inf_conectividade_ept": inf_conectividade_ept,
    "mer_saldo_caged_tecnicos": mer_saldo_caged_tecnicos,
    "mer_premio_salarial_escolaridade": mer_premio_salarial_escolaridade,
    "mer_neet_rate": mer_neet_rate,
    "din_crescimento_matriculas_5y": din_crescimento_matriculas_5y,
    "din_cursos_novos_ept": din_cursos_novos_ept,
    # 10 novos (2026-Q2) — 3 removidos por bug V3007 PNAD trimestral
    "pne_m12a": pne_m12a,
    "pne_m12b": pne_m12b,
    "pne_m12c": pne_m12c,
    # pne_m12f, qua_ingresso_es_pnad, mer_renda_jovens_pnad: REMOVIDOS
    "cob_perfil_alunos": cob_perfil_alunos,
    "cob_alcance_ponderado": cob_alcance_ponderado,
    "qua_saeb_proficiencia_ept": qua_saeb_proficiencia_ept,
    "qua_abandono_em_ept": qua_abandono_em_ept,
    "qua_aderencia_docente_ept": qua_aderencia_docente_ept,
    # Mercado 10x (2026-Q2)
    "mer_demanda_cbo_top": mer_demanda_cbo_top,
    "mer_demanda_mesorregiao": mer_demanda_mesorregiao,
    "mer_coorte_sintetica_pnad": mer_coorte_sintetica_pnad,
}
