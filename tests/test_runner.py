"""Tests do BQRunner — validação de UF e parametrização da query."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from etl.runner import BQRunner


@pytest.mark.parametrize("bad_uf", ["", "X", "abc", "MG1", "M G", "MG;DROP", "../etc", "BRA"])
def test_run_rejects_invalid_uf(bad_uf):
    """UF que não bate em [A-Z]{2} deve falhar antes de chegar no client BQ."""
    with pytest.raises(ValueError, match="UF inválida"):
        BQRunner.run("cob_eixos_cobertos", bad_uf)


def test_run_rejects_lowercase_uf():
    """UF lowercase é rejeitada — allowlist exige uppercase."""
    with pytest.raises(ValueError, match="UF inválida"):
        BQRunner.run("cob_eixos_cobertos", "mg")


@patch.object(BQRunner, "get_client")
@patch.object(BQRunner, "load_query", return_value="SELECT 1 FROM t WHERE sigla_uf = @uf")
def test_run_uses_scalar_query_parameter_for_uf(_mock_load, mock_get_client):
    """Para UF válida (≠ BR), runner deve passar ScalarQueryParameter pro BQ."""
    fake_client = MagicMock()
    fake_df = MagicMock()
    fake_df.__len__ = MagicMock(return_value=0)
    fake_client.query.return_value.result.return_value.to_dataframe.return_value = fake_df
    mock_get_client.return_value = fake_client

    BQRunner.run("cob_eixos_cobertos", "MG")

    # Capturar o job_config passado pra client.query()
    call_args = fake_client.query.call_args
    job_config = call_args.kwargs.get("job_config") or call_args.args[1]
    params = job_config.query_parameters
    assert len(params) == 1
    assert params[0].name == "uf"
    assert params[0].value == "MG"
    # SQL passado deve ser literal (sem .replace), com @uf intacto
    sql = call_args.args[0]
    assert "@uf" in sql
    assert "MG" not in sql  # não foi feita substituição textual


@patch.object(BQRunner, "get_client")
@patch.object(BQRunner, "load_query", return_value="SELECT 1 FROM t WHERE sigla_uf = @uf")
def test_run_sets_maximum_bytes_billed_default(_mock_load, mock_get_client):
    """Job de execução real tem cap de 5 GB faturáveis por padrão."""
    fake_client = MagicMock()
    fake_df = MagicMock()
    fake_df.__len__ = MagicMock(return_value=0)
    fake_client.query.return_value.result.return_value.to_dataframe.return_value = fake_df
    mock_get_client.return_value = fake_client

    BQRunner.run("cob_eixos_cobertos", "MG")

    # Pega último call (a execução real, não o dry-run que vem antes)
    calls = fake_client.query.call_args_list
    real_call = calls[-1]
    job_config = real_call.kwargs.get("job_config") or real_call.args[1]
    assert job_config.maximum_bytes_billed == 5 * 1024**3
    assert job_config.use_query_cache is True


@patch.object(BQRunner, "get_client")
@patch.object(BQRunner, "load_query", return_value="SELECT 1 FROM t WHERE sigla_uf = @uf")
def test_run_accepts_custom_max_gb(_mock_load, mock_get_client):
    """`max_gb=10` aumenta o cap para 10 GB faturáveis na execução real."""
    fake_client = MagicMock()
    fake_df = MagicMock()
    fake_df.__len__ = MagicMock(return_value=0)
    fake_client.query.return_value.result.return_value.to_dataframe.return_value = fake_df
    mock_get_client.return_value = fake_client

    BQRunner.run("cob_eixos_cobertos", "MG", max_gb=10)

    calls = fake_client.query.call_args_list
    real_call = calls[-1]
    job_config = real_call.kwargs.get("job_config") or real_call.args[1]
    assert job_config.maximum_bytes_billed == 10 * 1024**3


@patch.object(BQRunner, "get_client")
@patch.object(
    BQRunner,
    "load_query",
    return_value="SELECT 1 FROM t WHERE sigla_uf = @uf AND e.sigla_uf = @uf",
)
def test_run_br_rewrites_filter_to_true(_mock_load, mock_get_client):
    """UF == 'BR' reescreve `sigla_uf = @uf` por TRUE (modo nacional)."""
    fake_client = MagicMock()
    fake_df = MagicMock()
    fake_df.__len__ = MagicMock(return_value=0)
    fake_client.query.return_value.result.return_value.to_dataframe.return_value = fake_df
    mock_get_client.return_value = fake_client

    BQRunner.run("cob_eixos_cobertos", "BR")

    call_args = fake_client.query.call_args
    sql = call_args.args[0]
    assert "@uf" not in sql
    assert "TRUE" in sql
    # No modo BR não há query_parameters (filter foi reescrito, não parametrizado)
    job_config = call_args.kwargs.get("job_config") or call_args.args[1]
    assert job_config.query_parameters == []
