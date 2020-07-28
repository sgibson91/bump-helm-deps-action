import logging

from .helper_functions import run_cmd

logger = logging.getLogger()


def login(identity: bool = False) -> None:
    """Login to Azure

    Args:
        identity (bool, optional): Login with Managed System Identity.
                                   Defaults to False.
    """
    login_cmd = ["az", "login"]

    if identity:
        login_cmd.append("--identity")
        logger.info("Login to Azure with a Managed System Identity")
    else:
        logger.info("Login to Azure")

    result = run_cmd(login_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        # Add clean-up functions here
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully logged into Azure")


def get_token(token_name: str, keyvault: str, identity: bool = False) -> str:
    """Get GitHub API token from Azure Key Vault

    Args:
        token_name (str): The name the token is stored as
        keyvault (str): The keyvault the token is stored within
        identity (bool, optional): Access with a Managed System Identity.
                                   Defaults to False.

    Returns:
        str: The token value
    """
    login(identity)

    logger.info("Retrieving scret: %s" % token_name)

    vault_cmd = [
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

    result = run_cmd(vault_cmd)

    if result["returncode"] != 0:
        logger.error(result["err_msg"])
        # Add clean-up functions here
        raise RuntimeError(result["err_msg"])

    logger.info("Successfully pulled secret")

    return result["output"]
