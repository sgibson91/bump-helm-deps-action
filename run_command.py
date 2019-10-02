import subprocess


def run_cmd(cmd):
    """Use Popen to run a subprocess command.

    Parameters
    ----------
    cmd: List of strings

    Returns
    -------
    result: Dictionary
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
