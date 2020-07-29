import pytest
import logging
from unittest.mock import patch, call
from testfixtures import log_capture
from helm_bot.azure import login, get_token


@log_capture()
def test_login_basic(capture):
    logger = logging.getLogger()
    logger.info("Login to Azure")
    logger.info("Successfully logged into Azure")

    with patch(
        "helm_bot.azure.run_cmd", return_value={"returncode": 0}
    ) as mock_run:
        login()

        assert mock_run.call_count == 1
        assert mock_run.return_value["returncode"] == 0

        capture.check_present()


@log_capture()
def test_login_basic_exception(capture):
    logger = logging.getLogger()
    logger.info("Login to Azure")
    logger.error("Could not run command")

    with patch(
        "helm_bot.azure.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    ) as mock_run, pytest.raises(RuntimeError):
        login()

        assert mock_run.call_count == 1
        assert mock_run.return_value["returncode"] == 1
        assert mock_run.return_value["err_msg"] == "Could not run command"

        capture.check_present()


@log_capture()
def test_login_identity(capture):
    expected_call = call(["az", "login", "--identity"])
    logger = logging.getLogger()
    logger.info("Login to Azure with a Managed System Identity")
    logger.info("Successfully logged into Azure")

    with patch(
        "helm_bot.azure.run_cmd", return_value={"returncode": 0}
    ) as mock_run:
        login(identity=True)

        assert mock_run.call_count == 1
        assert mock_run.return_value["returncode"] == 0
        assert mock_run.call_args == expected_call

        capture.check_present()


@log_capture()
def test_login_identity_exception(capture):
    expected_call = call(["az", "login", "--identity"])
    logger = logging.getLogger()
    logger.info("Login to Azure with a Managed System Identity")
    logger.error("Could not run command")

    with patch(
        "helm_bot.azure.run_cmd",
        return_value={"returncode": 1, "err_msg": "Could not run command"},
    ) as mock_run, pytest.raises(RuntimeError):
        login(identity=True)

        assert mock_run.call_count == 1
        assert mock_run.return_value["returncode"] == 0
        assert mock_run.call_args == expected_call

        capture.check_present()


@log_capture()
def test_get_token(capture):
    token_name = "test_token"
    keyvault = "test_vault"
    expected_call = call(
        [
            "az",
            "keyvault",
            "secret",
            "show",
            "-n",
            token_name,
            "--vault-name",
            keyvault,
            "--query",
            "value",
            "-o",
            "tsv",
        ]
    )

    logger = logging.getLogger()
    logger.info("Retrieving scret: %s" % token_name)
    logger.info("Successfully pulled secret")

    mock_login = patch("helm_bot.azure.login")
    mock_run = patch(
        "helm_bot.azure.run_cmd",
        return_value={"returncode": 0, "output": "this_is_a_token"},
    )

    with mock_login as mock1, mock_run as mock2:
        token = get_token(token_name, keyvault)

        assert token == "this_is_a_token"
        assert mock1.call_count == 1
        assert mock2.call_count == 1
        assert mock2.call_args == expected_call

        capture.check_present()


@log_capture()
def test_get_token_exception(capture):
    token_name = "test_token"
    keyvault = "test_vault"
    expected_call = call(
        [
            "az",
            "keyvault",
            "secret",
            "show",
            "-n",
            token_name,
            "--vault-name",
            keyvault,
            "--query",
            "value",
            "-o",
            "tsv",
        ]
    )

    logger = logging.getLogger()
    logger.info("Retrieving scret: %s" % token_name)
    logger.error("Could not run command")

    mock_login = patch("helm_bot.azure.login")
    mock_run = patch(
        "helm_bot.azure.run_cmd",
        return_value={
            "returncode": 1,
            "output": "",
            "err_msg": "Could not run command",
        },
    )

    with mock_login as mock1, mock_run as mock2, pytest.raises(RuntimeError):
        token = get_token(token_name, keyvault)

        assert token == ""
        assert mock1.call_count == 1
        assert mock2.call_count == 1
        assert mock2.call_args == expected_call

        capture.check_present()
