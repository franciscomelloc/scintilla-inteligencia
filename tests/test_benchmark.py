"""Tests de cálculo de benchmark."""

from etl.benchmark import (
    POP_15_29_BY_UF,
    media_nacional,
    meta_pne,
    position_rank,
    top_quartile,
    vs_meta_pne,
)


def test_top_quartile_basic():
    values = [1, 2, 3, 4, 5, 6, 7, 8]
    # statistics.quantiles n=4 inclusivo retorna P75 = 6.75 para [1..8]
    assert top_quartile(values) == 6.75


def test_top_quartile_with_nones():
    values = [None, 2, None, 4, 6, 8]
    valid = [v for v in values if v is not None]
    assert top_quartile(valid) == 7.5  # P75 de [2,4,6,8]


def test_top_quartile_too_few_values():
    assert top_quartile([1, 2, 3]) is None


def test_media_nacional_unweighted():
    values = {"AC": 10, "MG": 20, "SP": 30}
    result = media_nacional(values, peso_pop=False)
    assert result == 20.0


def test_media_nacional_weighted():
    """Ponderação por pop 15-29 deve dar peso muito maior a SP que AC."""
    values = {"AC": 10.0, "SP": 100.0}
    result = media_nacional(values, peso_pop=True)
    # SP tem ~52x a pop 15-29 de AC, então média deve estar perto de 100
    assert result > 95.0


def test_pop_15_29_covers_all_27_ufs():
    expected = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
    assert set(POP_15_29_BY_UF.keys()) == expected


def test_meta_pne_known_indicators():
    assert meta_pne("cob_distribuicao_modalidade") is not None
    assert meta_pne("inf_conectividade_ept") is not None
    assert meta_pne("din_crescimento_matriculas_5y") is not None


def test_meta_pne_unknown_indicator():
    assert meta_pne("indicador_inexistente") is None


def test_vs_meta_pne_conectividade():
    # meta 100% em 2036; valor atual 52% → distância = -48
    assert vs_meta_pne(52, "inf_conectividade_ept") == -48


def test_position_rank_normal():
    """Maior é melhor: SP com 100 vs AC com 10 → SP em primeiro."""
    values = {"AC": 10.0, "MG": 50.0, "SP": 100.0}
    assert position_rank(100.0, values) == 1
    assert position_rank(50.0, values) == 2
    assert position_rank(10.0, values) == 3


def test_position_rank_inverse():
    """Menor é melhor (NEET): AC com 5% melhor que SP com 25%."""
    values = {"AC": 5.0, "MG": 15.0, "SP": 25.0}
    assert position_rank(5.0, values, inverse=True) == 1
    assert position_rank(25.0, values, inverse=True) == 3
