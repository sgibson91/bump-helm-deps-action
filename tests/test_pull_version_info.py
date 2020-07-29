import responses
from unittest.mock import patch
from helm_bot.pull_version_info import (
    pull_version_from_chart_file,
    pull_version_from_github_pages,
    pull_version_from_requirements_file,
)


@responses.activate
def test_pull_version_from_chart_file():
    test_dict = {}
    test_dep = "dependency"
    test_url = "http://jsonplaceholder.typicode.com/Chart.yaml"
    test_token = "tHiS_iS_a_tOkEn"

    responses.add(
        responses.GET, test_url, json={"version": "1.2.3"}, status=200
    )

    test_dict = pull_version_from_chart_file(
        test_dict, test_dep, test_url, test_token
    )

    assert len(test_dict) == 1
    assert list(test_dict.items()) == [(test_dep, "1.2.3")]

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert responses.calls[0].response.text == '{"version": "1.2.3"}'


@responses.activate
def test_pull_version_from_github_pages():
    test_dict = {}
    test_dep = "dependency"
    test_url = "http://jsonplaceholder.typicode.com/gh-pages/index.yaml"
    test_token = "tHiS_iS_a_tOkEn"

    responses.add(
        responses.GET,
        test_url,
        json={
            "entries": {
                "dependency": [
                    {
                        "created": "2020-07-26T15:33:00.0000000Z",
                        "version": "1.2.3",
                    },  # noqa: E501
                    {
                        "created": "2020-07-25T15:33:00.0000000Z",
                        "version": "1.2.2",
                    },  # noqa: E501
                ]
            }
        },
        status=200,
    )

    test_dict = pull_version_from_github_pages(
        test_dict, test_dep, test_url, test_token
    )

    assert len(test_dict) == 1
    assert list(test_dict.items()) == [(test_dep, "1.2.3")]

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert (
        responses.calls[0].response.text
        == '{"entries": {"dependency": [{"created": "2020-07-26T15:33:00.0000000Z", "version": "1.2.3"}, {"created": "2020-07-25T15:33:00.0000000Z", "version": "1.2.2"}]}}'  # noqa: E501
    )


@responses.activate
def test_pull_version_from_requirements_file():
    test_dict = {}
    test_chart = "chart_name"
    test_dict[test_chart] = {}
    test_url = "http://jsonplaceholder.typicode.com/requirements.yaml"
    test_token = "tHiS_iS_a_tOkEn"

    responses.add(
        responses.GET,
        test_url,
        json={
            "dependencies": [
                {"name": "chart-1", "version": "1.2.3"},
                {"name": "chart-2", "version": "4.5.6"},
            ]
        },
        status=200,
    )

    test_dict = pull_version_from_requirements_file(
        test_dict, test_chart, test_url, test_token
    )

    assert len(test_dict) == 1
    assert list(test_dict.items()) == [
        ("chart_name", {"chart-1": "1.2.3", "chart-2": "4.5.6"})
    ]

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert (
        responses.calls[0].response.text
        == '{"dependencies": [{"name": "chart-1", "version": "1.2.3"}, {"name": "chart-2", "version": "4.5.6"}]}'
    )
