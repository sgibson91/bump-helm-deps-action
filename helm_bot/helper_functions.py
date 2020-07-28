import logging
import requests
import subprocess

logger = logging.getLogger()


def delete_request(url: str, headers: dict = None) -> None:
    """Send a DELETE request to an HTTP API endpoint

    Args:
        url (str): The URL to send the request to
        headers (dict, optional): A dictionary of any headers to send with the
                                  request. Defaults to None.
    """
    resp = requests.delete(url, headers=headers)

    if not resp:
        logger.error(resp.text)
        raise RuntimeError(resp.text)


def get_request(url: str, headers: dict = None, text: bool = False):
    """Send a GET request to an HTTP API endpoint

    Args:
        url (str): The URL to send the request to
        headers (dict): A dictionary of headers to send with the request
        text (bool, optional): Returns the text payload. Defaults to False.
    """
    resp = requests.get(url, headers=headers)

    if not resp:
        logger.error(resp.text)
        raise RuntimeError(resp.text)

    if text:
        return resp.text
    else:
        return resp


def post_request(url: str, headers: dict = None, json: dict = None) -> None:
    """Send a POST request to an HTTP API endpoint

    Args:
        url (str): The URL to send the request to
        headers (dict, optional): A dictionary of any headers to send with the
                                  request. Defaults to None.
        json (dict, optional): A dictionary containing JSON payload to send with
                               the request. Defaults to None.
    """
    resp = requests.post(url, headers=headers, json=json)

    if not resp:
        logger.error(resp.text)
        raise RuntimeError(resp.text)


def run_cmd(cmd: list) -> dict:
    """Use Popen to run a bash command in a sub-shell

    Args:
        cmd (list): The bash command to run

    Returns:
        dict: The output of the command, including status code and error
              messages
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    msgs = proc.communicate()

    result = {
        "returncode": proc.returncode,
        "output": msgs[0].decode(encoding=("utf-8")),
        "err_msg": msgs[1].decode(encoding=("utf-8")),
    }

    return result
