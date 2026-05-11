"""Tests do catálogo de indicadores."""

from etl.indicators import (
    INDICATOR_CATALOG,
    get_indicator_codes,
    get_indicators_by_domain,
    get_indicators_with_pne_meta,
)


def test_catalog_has_25_indicators():
    """Total atual: 25 indicadores (6 cob + 5 qua + 1 inf + 8 mer + 2 din + 3 pne)."""
    assert len(get_indicator_codes()) == 25


def test_domain_distribution():
    """Distribuição: 6 cob + 5 qua + 1 inf + 8 mer + 2 din + 3 pne."""
    assert len(get_indicators_by_domain("cobertura")) == 6
    assert len(get_indicators_by_domain("qualidade")) == 5
    assert len(get_indicators_by_domain("infraestrutura")) == 1
    assert len(get_indicators_by_domain("mercado")) == 8
    assert len(get_indicators_by_domain("dinamismo")) == 2
    assert len(get_indicators_by_domain("pne")) == 3


def test_mercado_indicators_have_only_total_estado():
    """Mercado de trabalho não tem rede — só total_estado."""
    for code in get_indicators_by_domain("mercado"):
        assert INDICATOR_CATALOG[code]["recortes"] == ["total_estado"]


def test_polaridade_inversa_set_correctly():
    """Indicadores onde menor valor é melhor: rendimento (abandono), razão aluno/prof,
    NEET, abandono EM."""
    polar_inv_esperados = {
        "qua_taxas_rendimento_ept",
        "qua_razao_aluno_professor_ept",
        "mer_neet_rate",
        "qua_abandono_em_ept",
    }
    for code in get_indicator_codes():
        if code in polar_inv_esperados:
            assert INDICATOR_CATALOG[code]["polaridade_inversa"] is True, code
        else:
            assert INDICATOR_CATALOG[code].get("polaridade_inversa") is not True, code


def test_lead_gen_indicators_marked():
    """Indicadores com lead-gen explícito (limites do dado público)."""
    assert "lead_gen" in INDICATOR_CATALOG["qua_taxas_rendimento_ept"]
    assert "lead_gen" in INDICATOR_CATALOG["mer_premio_salarial_escolaridade"]


def test_pne_meta_indicators():
    """Indicadores tocados pelo PNE 2024-2034."""
    pne_codes = set(get_indicators_with_pne_meta())
    expected = {
        "cob_distribuicao_modalidade",  # M1: integ+concom ≥50%
        "din_crescimento_matriculas_5y",  # M2: subsequente +60%
        "inf_conectividade_ept",  # M4: 50%/2y, 100%/10y
        "pne_m12a",  # Meta 12 PNE
        "pne_m12b",
        "pne_m12c",
    }
    assert expected.issubset(pne_codes)
