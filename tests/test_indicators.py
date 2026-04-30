"""Tests do catálogo de indicadores."""

from etl.indicators import (
    INDICATOR_CATALOG,
    get_indicator_codes,
    get_indicators_by_domain,
    get_indicators_with_pne_meta,
)


def test_catalog_has_14_indicators():
    """Total deve ser 14 — versão MVP da spec v2."""
    assert len(get_indicator_codes()) == 14


def test_domain_distribution():
    """Distribuição: 5 cobertura + 3 qualidade + 1 infra + 3 mercado + 2 dinamismo."""
    assert len(get_indicators_by_domain("cobertura")) == 5
    assert len(get_indicators_by_domain("qualidade")) == 3
    assert len(get_indicators_by_domain("infraestrutura")) == 1
    assert len(get_indicators_by_domain("mercado")) == 3
    assert len(get_indicators_by_domain("dinamismo")) == 2


def test_mercado_indicators_have_only_total_estado():
    """Mercado de trabalho não tem rede — só total_estado."""
    for code in get_indicators_by_domain("mercado"):
        assert INDICATOR_CATALOG[code]["recortes"] == ["total_estado"]


def test_polaridade_inversa_set_correctly():
    """Razão aluno/prof e NEET têm polaridade inversa."""
    assert INDICATOR_CATALOG["qua_razao_aluno_professor_ept"]["polaridade_inversa"] is True
    assert INDICATOR_CATALOG["mer_neet_rate"]["polaridade_inversa"] is True
    # restantes são polaridade normal (maior é melhor)
    for code in get_indicator_codes():
        if code not in ("qua_razao_aluno_professor_ept", "mer_neet_rate"):
            assert INDICATOR_CATALOG[code].get("polaridade_inversa") is False


def test_lead_gen_indicators_marked():
    """Indicadores com lead-gen explícito (limites do dado público)."""
    assert "lead_gen" in INDICATOR_CATALOG["qua_taxas_rendimento_ept"]
    assert "lead_gen" in INDICATOR_CATALOG["mer_premio_salarial_escolaridade"]


def test_pne_meta_indicators():
    """3 indicadores tocados pelo PNE 2024-2034."""
    pne_codes = set(get_indicators_with_pne_meta())
    expected = {
        "cob_distribuicao_modalidade",  # M1: integ+concom ≥50%
        "din_crescimento_matriculas_5y",  # M2: subsequente +60%
        "inf_conectividade_ept",  # M4: 50%/2y, 100%/10y
    }
    # também `cob_matriculas_ept_per_jovem` tem expansion_general como PNE meta
    expected.add("cob_matriculas_ept_per_jovem")
    assert expected.issubset(pne_codes)
