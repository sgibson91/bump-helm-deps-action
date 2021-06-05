import pytest
import argparse
from unittest.mock import patch
from helm_bot.cli import parse_args, check_parser


@patch(
    "argparse.ArgumentParser.parse_args",
    return_value=argparse.Namespace(
        repo_owner="test_owner", repo_name="test_repo", chart_name="test_chart"
    ),
)
def test_parser_required(mock_args):
    parser = parse_args(["test_owner", "test_repo", "test_chart"])

    assert parser.repo_owner == "test_owner"
    assert parser.repo_name == "test_repo"
    assert parser.chart_name == "test_chart"
    assert mock_args.call_count == 1


@patch(
    "argparse.ArgumentParser.parse_args",
    return_value=argparse.Namespace(
        repo_owner="test_owner",
        repo_name="test_repo",
        chart_name="test_chart",
        dry_run=True,
        verbose=True,
    ),
)
def test_parser_boolean_opts(mock_args):
    parser = parse_args(
        [
            "test_owner",
            "test_repo",
            "test_chart",
            "--dry-run",
            "--verbose",
        ]
    )

    assert parser.repo_owner == "test_owner"
    assert parser.repo_name == "test_repo"
    assert parser.chart_name == "test_chart"
    assert parser.dry_run
    assert parser.verbose
    assert mock_args.call_count == 1


@patch(
    "argparse.ArgumentParser.parse_args",
    return_value=argparse.Namespace(
        repo_owner="test_owner",
        repo_name="test_repo",
        chart_name="test_chart",
        target_branch="test_target",
        base_branch="test_base",
        labels=["label1", "label2"],
    ),
)
def test_parser_opts(mock_args):
    parser = parse_args(
        [
            "test_owner",
            "test_repo",
            "test_chart",
            "-t",
            "test_target",
            "-b",
            "test_base",
            "-l",
            "label1",
            "label2",
        ]
    )

    assert parser.repo_owner == "test_owner"
    assert parser.repo_name == "test_repo"
    assert parser.chart_name == "test_chart"
    assert parser.target_branch == "test_target"
    assert parser.base_branch == "test_base"
    assert parser.labels == ["label1", "label2"]
    assert mock_args.call_count == 1


def test_check_parser():
    args1 = argparse.Namespace(
        repo_owner="test_owner",
        repo_name="test_repo",
        chart_name="test_chart",
    )
    args2 = argparse.Namespace(
        repo_owner="test_owner",
        repo_name="test_repo",
        chart_name="test_chart",
    )
    args3 = argparse.Namespace(
        repo_owner="test_owner",
        repo_name="test_repo",
        chart_name="test_chart",
    )

    with pytest.raises(ValueError):
        check_parser(args1)
        check_parser(args2)
        check_parser(args3)
