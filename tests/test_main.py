import base64
import unittest

import pytest

from helm_bot.main import UpdateHelmDeps, assert_chart_info_input, split_str_to_list
from helm_bot.yaml_parser import YamlParser

yaml = YamlParser()


class TestUpdateHelmDeps(unittest.TestCase):
    def test_update_versions(self):
        update_versions = UpdateHelmDeps(
            "octocat/octocat",
            "ThIs_Is_A_t0k3n",
            "chart-name/Chart.yaml",
            {"some_chart": "https://come-chart.com"},
        )
        update_versions.chart_yaml = {
            "dependencies": [
                {
                    "name": "some_chart",
                    "version": "old_version",
                }
            ]
        }
        update_versions.charts_to_update = ["some_chart"]
        update_versions.chart_versions = {
            "some_chart": {
                "current": "old_version",
                "latest": "new_version",
            }
        }

        expected_output = {
            "dependencies": [{"name": "some_chart", "version": "new_version"}]
        }
        expected_output = yaml.object_to_yaml_str(expected_output).encode("utf-8")
        expected_output = base64.b64encode(expected_output)
        expected_output = expected_output.decode("utf-8")

        result = update_versions.update_versions()

        self.assertEqual(result, expected_output)


def test_split_str_to_list_simple():
    test_str1 = "label1,label2"
    test_str2 = "label1 , label2"

    expected_output = ["label1", "label2"]

    result1 = split_str_to_list(test_str1)
    result2 = split_str_to_list(test_str2)

    assert result1 == expected_output
    assert result2 == expected_output
    assert result1 == result2


def test_split_str_to_list_complex():
    test_str1 = "type: feature,impact: low"
    test_str2 = "type: feature , impact: low"

    expected_output = ["type: feature", "impact: low"]

    result1 = split_str_to_list(test_str1)
    result2 = split_str_to_list(test_str2)

    assert result1 == expected_output
    assert result2 == expected_output
    assert result1 == result2


def test_assert_chart_info_input_pass():
    chart_info = {"chart_name": {"url": "https://example.com/chart"}}
    assert_chart_info_input(chart_info)


def test_assert_chart_info_input_fail_1():
    chart_info = {"chart_name": "https://example.com/chart"}

    with pytest.raises(AssertionError):
        assert_chart_info_input(chart_info)


def test_assert_chart_info_input_fail_2():
    chart_info = ["chart_name", "https://example.com/chart"]

    with pytest.raises(AssertionError):
        assert_chart_info_input(chart_info)


def test_assert_chart_info_input_fail_3():
    chart_info = [{"chart_name": "https://example.com/chart"}]

    with pytest.raises(AssertionError):
        assert_chart_info_input(chart_info)


if __name__ == "__main__":
    unittest.main()
