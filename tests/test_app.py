import logging
from testfixtures import log_capture
from helm_bot.app import check_versions


@log_capture()
def test_check_versions_match(capture):
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "1.2.3",
        "chart2": "4.5.6",
    }

    logger = logging.getLogger()
    logger.info(
        "%s is up-to-date with all current chart dependency releases!"
        % chart_name
    )

    charts_out = check_versions(chart_name, chart_info)

    assert charts_out == []

    capture.check_present()


@log_capture()
def test_check_versions_no_match(capture):
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "1.10.9",
    }
    expected_charts = ["chart1", "chart2"]

    logger = logging.getLogger()
    logger.info(
        "Helm upgrade required for the following charts: %s" % expected_charts
    )

    charts_out = check_versions(chart_name, chart_info)

    assert charts_out == expected_charts

    capture.check_present()


@log_capture()
def test_check_versions_no_match_dry_run(capture):
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "1.10.9",
    }
    expected_charts = ["chart1", "chart2"]

    logger = logging.getLogger()
    logger.info(
        "Helm upgrade required for the following charts: %s. PR won't be opened due to --dry-run flag being set."
        % expected_charts
    )

    charts_out = check_versions(chart_name, chart_info, dry_run=True)

    assert charts_out == expected_charts

    capture.check_present()
