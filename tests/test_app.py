from helm_bot.app import compare_dependency_versions


def test_compare_dependency_versions_match():
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "1.2.3",
        "chart2": "4.5.6",
    }

    charts_out = compare_dependency_versions(chart_info, chart_name)

    assert charts_out == []


def test_compare_dependency_versions_no_match():
    chart_name = "test_chart"
    chart_info = {
        chart_name: {"chart1": "1.2.3", "chart2": "4.5.6"},
        "chart1": "7.8.9",
        "chart2": "1.10.9",
    }
    expected_charts = ["chart1", "chart2"]

    charts_out = compare_dependency_versions(chart_info, chart_name)

    assert charts_out == expected_charts
