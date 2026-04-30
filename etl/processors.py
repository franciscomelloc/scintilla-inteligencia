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


def cob_matriculas_ept_per_jovem(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, valor_total_estado, valor_rede_estadual."""
    if df.empty:
        return _empty_indicator("Sem dados Censo+PNAD para o estado.")
    latest = df.sort_values("ano").iloc[-1]
    spark_total = _valor_5y(df, "valor_total_estado")
    spark_estadual = _valor_5y(df, "valor_rede_estadual")
    return {
        "total_estado": {
            "valor": float(latest["valor_total_estado"]) if pd.notna(latest["valor_total_estado"]) else None,
            **spark_total,
        },
        "rede_estadual": {
            "valor": float(latest["valor_rede_estadual"]) if pd.notna(latest["valor_rede_estadual"]) else None,
            **spark_estadual,
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "Inclui matrículas EPT em EM regular + EJA-técnico. Pop 15-29 PNAD.",
    }


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


def qua_taxas_rendimento_ept(df: pd.DataFrame, uf: str) -> dict[str, Any]:
    """SQL retorna: ano, aprovacao/reprovacao/abandono total e estadual."""
    if df.empty:
        return _empty_indicator("Sem dados Indicadores Educacionais cruzando com escolas EPT.")
    latest = df.sort_values("ano").iloc[-1]
    return {
        "total_estado": {
            "aprovacao": float(latest.get("aprovacao_total") or 0),
            "reprovacao": float(latest.get("reprovacao_total") or 0),
            "abandono": float(latest.get("abandono_total") or 0),
        },
        "rede_estadual": {
            "aprovacao": float(latest.get("aprovacao_estadual") or 0),
            "reprovacao": float(latest.get("reprovacao_estadual") or 0),
            "abandono": float(latest.get("abandono_estadual") or 0),
        },
        "vintage": str(int(latest["ano"])),
        "caveat": "Taxas EM agregadas das escolas que ofertam EPT (proxy). Conclusão de coorte real exige cruzamento nominativo.",
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
    valor_total = float(latest.get("pct_t1_total") or 0)
    valor_estadual = float(latest.get("pct_t1_estadual") or 0)
    return {
        "total_estado": {
            "valor": valor_total,
            "tier_distribuicao": {
                "banda_larga_com_uso_aluno": valor_total,
                "banda_larga_sem_uso_aluno": float(latest.get("pct_t2_total") or 0),
                "internet_basica_sem_banda_larga": float(latest.get("pct_t3_total") or 0),
                "sem_internet": float(latest.get("pct_t4_total") or 0),
            },
            **_valor_5y(df, "pct_t1_total"),
        },
        "rede_estadual": {
            "valor": valor_estadual,
            "tier_distribuicao": {
                "banda_larga_com_uso_aluno": valor_estadual,
                "banda_larga_sem_uso_aluno": float(latest.get("pct_t2_estadual") or 0),
                "internet_basica_sem_banda_larga": float(latest.get("pct_t3_estadual") or 0),
                "sem_internet": float(latest.get("pct_t4_estadual") or 0),
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
    sem_em = float(latest.get("mediana_sem_em") or 0)
    em = float(latest.get("mediana_em_completo") or 0)
    sup = float(latest.get("mediana_superior") or 0)
    return {
        "total_estado": {
            "medianas_brl_real": {
                "sem_ensino_medio": round(sem_em, 2),
                "ensino_medio_completo": round(em, 2),
                "superior_completo": round(sup, 2),
            },
            "premios_pct": {
                "em_vs_sem_em": round((em / sem_em - 1) * 100, 1) if sem_em else None,
                "superior_vs_em": round((sup / em - 1) * 100, 1) if em else None,
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
    qtd_2019 = int(df[df["ano"] == 2019]["qtd"].sum() or 0)
    qtd_2024 = int(df[df["ano"] == 2024]["qtd"].sum() or 0)
    qtd_2019_estadual = int(df[(df["ano"] == 2019) & (df["rede"] == "estadual")]["qtd"].sum() or 0)
    qtd_2024_estadual = int(df[(df["ano"] == 2024) & (df["rede"] == "estadual")]["qtd"].sum() or 0)
    growth_total = round((qtd_2024 / qtd_2019 - 1) * 100, 2) if qtd_2019 else None
    growth_estadual = round((qtd_2024_estadual / qtd_2019_estadual - 1) * 100, 2) if qtd_2019_estadual else None
    cagr_total = round(((qtd_2024 / qtd_2019) ** (1/5) - 1) * 100, 2) if qtd_2019 else None
    cagr_estadual = round(((qtd_2024_estadual / qtd_2019_estadual) ** (1/5) - 1) * 100, 2) if qtd_2019_estadual else None
    return {
        "total_estado": {
            "crescimento_5y_pct": growth_total,
            "cagr_5y_pct": cagr_total,
            "matriculas_2020": qtd_2019,  # nota: rotulado 2020 no mock mas a base é 2019
            "matriculas_2024": qtd_2024,
        },
        "rede_estadual": {
            "crescimento_5y_pct": growth_estadual,
            "cagr_5y_pct": cagr_estadual,
            "matriculas_2020": qtd_2019_estadual,
            "matriculas_2024": qtd_2024_estadual,
        },
        "vintage": "2024",
        "caveat": "Janela 5 anos terminando no Censo Escolar mais recente. Decomposição por modalidade pendente.",
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
    return {
        "total_estado": {
            "cursos_novos_2y": novos_total,
            "cursos_descontinuados_2y": desc_total,
            "saldo_liquido_2y": novos_total - desc_total,
        },
        "rede_estadual": {
            "cursos_novos_2y": novos_estadual,
            "cursos_descontinuados_2y": desc_estadual,
            "saldo_liquido_2y": novos_estadual - desc_estadual,
        },
        "vintage": "2024",
        "caveat": "Par escola+curso novo em 2024 que não existia 2020-2023.",
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


PROCESSORS = {
    "cob_matriculas_ept_per_jovem": cob_matriculas_ept_per_jovem,
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
}
