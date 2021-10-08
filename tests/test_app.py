from helm_bot.app import check_versions


def test_check_versions_match():
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "1.2.3",
        "chart2": "4.5.6",
    }

    charts_out = check_versions(chart_name, chart_info)

    assert charts_out == []


def test_check_versions_no_match():
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "1.10.9",
    }
    expected_charts = ["chart1", "chart2"]

    charts_out = check_versions(chart_name, chart_info)

    assert charts_out == expected_charts


def test_check_versions_no_match_dry_run():
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "1.10.9",
    }
    expected_charts = ["chart1", "chart2"]

    charts_out = check_versions(chart_name, chart_info, dry_run=True)

    assert charts_out == expected_charts
