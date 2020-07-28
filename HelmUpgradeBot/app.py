import logging

from itertools import compress

from .helper_functions import (
    delete_request,
    get_request,
    post_request,
    run_cmd,
)

logger = logging.getLogger()


def check_versions(
    deployment: str, chart_info: dict, dry_run: bool = False
) -> list:
    charts = list(chart_info.keys())
    charts.remove(deployment)

    condition = [
        (
            chart_info[chart]["version"]
            != chart_info[deployment][chart]["version"]
        )
        for chart in charts
    ]
    charts_to_update = list(compress(charts, condition))

    if condition.any() and (not dry_run):
        logger.info(
            "Helm upgrade required for the following charts: %s"
            % charts_to_update
        )
    elif condition.any() and dry_run:
        logger.info(
            "Helm upgrade required for the following charts: %s. PR won't be opened due to --dry-run flag being set."
            % charts_to_update
        )
    else:
        logger.info(
            "%s is up-to-date with all current chart dependency releases!"
            % deployment
        )

    return charts_to_update
