"""
Contratos pydantic para os 14 indicadores do diagnóstico estadual.

Cada indicador tem 1-2 recortes (total_estado + opcional rede_estadual). Indicadores
de Mercado têm apenas total_estado (mercado é geográfico, sem recorte por rede).

Estrutura idêntica à esperada pelo frontend em /inteligencia — qualquer mudança aqui
exige atualização sincronizada do schema JSON e dos renderers no frontend.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IndicatorBase(BaseModel):
    """Base de todos os indicadores — vintage + caveat sempre presentes."""
    model_config = ConfigDict(extra="allow")

    vintage: str
    caveat: str


class CutBase(BaseModel):
    """Base de cada recorte (total_estado / rede_estadual)."""
    model_config = ConfigDict(extra="allow")

    valor: float | None = None
    valor_5y: list[float | None] | None = None
    anos_5y: list[int] | None = None
    vs_top_quartile: float | None = None
    vs_media_nacional: float | None = None
    vs_meta_pne_2034: float | None = None
    meta_pne_aplicavel: bool = False
    posicao: int | None = Field(None, ge=1, le=27)


class UFDiagnostic(BaseModel):
    """Saída completa de um estado."""
    uf: str = Field(..., min_length=2, max_length=2)
    uf_nome: str
    vintage: dict[str, str]
    last_built: str
    indicators: dict[str, Any]


# ============================================================
# Catálogo de indicadores — 14 códigos + metadados
# ============================================================

INDICATOR_CATALOG: dict[str, dict[str, Any]] = {
    # Domínio Cobertura
    "cob_matriculas_ept_per_jovem": {
        "domain": "cobertura",
        "name": "Matrículas EPT por 1.000 jovens 15-29 anos",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula", "br_ibge_pnadc.microdados"],
        "pne_meta": "expansion_general",  # Meta de expansão EPT
    },
    "cob_distribuicao_dependencia": {
        "domain": "cobertura",
        "name": "Distribuição de matrículas EPT por dependência administrativa",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula"],
        "pne_meta": None,
    },
    "cob_municipios_com_ept": {
        "domain": "cobertura",
        "name": "% municípios com pelo menos 1 escola técnica",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.escola", "br_inep_censo_escolar.matricula"],
        "pne_meta": None,
    },
    "cob_eixos_cobertos": {
        "domain": "cobertura",
        "name": "Eixos tecnológicos cobertos (de 13)",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula"],
        "reference": ["etl/reference/cnct_curso_eixo.csv"],
        "pne_meta": None,
    },
    "cob_distribuicao_modalidade": {
        "domain": "cobertura",
        "name": "Distribuição de matrículas EPT por modalidade",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula"],
        "pne_meta": "integrada_concomitante_50pct_2036",  # PNE M1
    },

    # Domínio Qualidade & Resultado
    "qua_taxas_rendimento_ept": {
        "domain": "qualidade",
        "name": "Taxas de rendimento (aprovação/reprovação/abandono) na última série EPT",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": True,
        "lag_months": 12,
        "source": ["br_inep_indicadores_educacionais.escola", "br_inep_censo_escolar.matricula"],
        "pne_meta": None,
        "lead_gen": "Conclusão de coorte real exige cruzamento nominativo Censo × egressos da SEE",
    },
    "qua_ideb_escolas_ept": {
        "domain": "qualidade",
        "name": "IDEB médio das escolas com oferta EPT",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 24,
        "source": ["br_inep_ideb.escola", "br_inep_censo_escolar.escola"],
        "pne_meta": None,
    },
    "qua_razao_aluno_professor_ept": {
        "domain": "qualidade",
        "name": "Razão aluno/professor em EPT",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": True,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula", "br_inep_censo_escolar.docente"],
        "pne_meta": None,
    },

    # Domínio Infraestrutura
    "inf_conectividade_ept": {
        "domain": "infraestrutura",
        "name": "Conectividade nas escolas com EPT (pirâmide de tiers)",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.escola", "br_inep_censo_escolar.matricula"],
        "pne_meta": "conectividade_50pct_2y_100pct_10y",  # PNE M4
    },

    # Domínio Mercado de Trabalho (sem recorte por rede)
    "mer_saldo_caged_tecnicos": {
        "domain": "mercado",
        "name": "Saldo CAGED em ocupações CBO 3xxxx (12m)",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 3,
        "source": ["br_me_caged.microdados_movimentacao"],
        "pne_meta": None,
    },
    "mer_premio_salarial_escolaridade": {
        "domain": "mercado",
        "name": "Prêmio salarial por nível de escolaridade",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_me_rais.microdados_vinculos"],
        "pne_meta": None,
        "lead_gen": "Prêmio EPT específico exige cruzamento Censo × RAIS por CPF",
    },
    "mer_neet_rate": {
        "domain": "mercado",
        "name": "NEET rate — % jovens 15-29 que não estudam nem trabalham",
        "recortes": ["total_estado"],
        "polaridade_inversa": True,
        "lag_months": 6,
        "source": ["br_ibge_pnadc.microdados"],
        "pne_meta": None,  # forte candidato — confirmar texto integral PNE
    },

    # Domínio Dinamismo
    "din_crescimento_matriculas_5y": {
        "domain": "dinamismo",
        "name": "Crescimento de matrículas EPT em 5 anos",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula"],
        "pne_meta": "subsequente_60pct",  # PNE M2
    },
    "din_cursos_novos_ept": {
        "domain": "dinamismo",
        "name": "Cursos novos abertos nos últimos 2 anos",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula"],
        "pne_meta": None,
    },

    # ============================================================
    # PNE 2026-2036 · Meta 12 (4 sub-metas calculáveis publicamente)
    # ============================================================
    "pne_m12a": {
        "domain": "pne",
        "name": "Meta 12.a · % EM em integrada+concomitante",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.escola"],
        "pne_meta": "m12a_50pct_2036",
    },
    "pne_m12b": {
        "domain": "pne",
        "name": "Meta 12.b · expansão +60% em cursos subsequentes",
        "recortes": ["total_estado", "rede_estadual"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.escola"],
        "pne_meta": "m12b_60pct_2036",
    },
    "pne_m12c": {
        "domain": "pne",
        "name": "Meta 12.c · % EJA articulada à profissional",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.escola"],
        "pne_meta": "m12c_25pct_2031_50pct_2036",
    },
    "pne_m12f": {
        "domain": "pne",
        "name": "Meta 12.f · % pop 18-24 com EM técnico concluído",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 6,
        "source": ["br_ibge_pnadc.microdados"],
        "pne_meta": "m12f_10pct_2036",
    },

    # ============================================================
    # Cobertura — cards reformados (2026-Q2)
    # ============================================================
    "cob_perfil_alunos": {
        "domain": "cobertura",
        "name": "Perfil dos matriculados EPT — faixa etária, sexo, modalidade",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.matricula", "br_inep_censo_escolar.escola"],
        "pne_meta": None,
    },
    "cob_alcance_ponderado": {
        "domain": "cobertura",
        "name": "% matrículas EM em município com EPT + top 5 munis sem oferta",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 12,
        "source": ["br_inep_censo_escolar.escola", "br_bd_diretorios_brasil.municipio"],
        "pne_meta": None,
    },

    # ============================================================
    # Qualidade & Resultado — cards reformados (2026-Q2)
    # ============================================================
    "qua_saeb_proficiencia_ept": {
        "domain": "qualidade",
        "name": "Proficiência SAEB Mat/Port — escolas com EPT vs sem EPT",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 24,
        "source": ["br_inep_saeb.proficiencia", "br_inep_censo_escolar.escola"],
        "pne_meta": None,
    },
    "qua_abandono_em_ept": {
        "domain": "qualidade",
        "name": "Taxa de abandono EM — escolas com EPT vs sem EPT",
        "recortes": ["total_estado"],
        "polaridade_inversa": True,
        "lag_months": 12,
        "source": ["br_inep_indicadores_educacionais.escola", "br_inep_censo_escolar.escola"],
        "pne_meta": None,
    },
    "qua_ingresso_es_pnad": {
        "domain": "qualidade",
        "name": "% jovens 18-29 com EM completo cursando ES — com EPT vs sem EPT",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 6,
        "source": ["br_ibge_pnadc.microdados"],
        "pne_meta": None,
    },

    # ============================================================
    # Mercado — card reformado (2026-Q2)
    # ============================================================
    "mer_renda_jovens_pnad": {
        "domain": "mercado",
        "name": "Renda mensal mediana de jovens 18-29 por nível de formação",
        "recortes": ["total_estado"],
        "polaridade_inversa": False,
        "lag_months": 6,
        "source": ["br_ibge_pnadc.microdados"],
        "pne_meta": None,
    },
}


def get_indicator_codes() -> list[str]:
    """Retorna lista ordenada de códigos de indicadores."""
    return list(INDICATOR_CATALOG.keys())


def get_indicators_by_domain(domain: str) -> list[str]:
    """Retorna códigos de indicadores de um domínio específico."""
    return [
        code for code, meta in INDICATOR_CATALOG.items()
        if meta["domain"] == domain
    ]


def get_indicators_with_pne_meta() -> list[str]:
    """Retorna códigos de indicadores que têm meta PNE associada."""
    return [
        code for code, meta in INDICATOR_CATALOG.items()
        if meta.get("pne_meta") is not None
    ]
