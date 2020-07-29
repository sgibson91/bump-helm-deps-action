import pytest
import logging
import responses
from testfixtures import log_capture
from helm_bot.helper_functions import (
    delete_request,
    get_request,
    post_request,
    run_cmd,
)


@responses.activate
def test_delete_request():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    responses.add(
        responses.DELETE, test_url,
    )

    delete_request(test_url, headers=test_header)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url


@responses.activate
@log_capture()
def test_delete_request_exception(capture):
    test_url = "http://josnplaceholder.typicode.com/"

    logger = logging.getLogger()
    logger.error("Could not reach provided URL")

    responses.add(
        responses.DELETE,
        test_url,
        body="Could not reach provided URL",
        status=500,
    )

    with pytest.raises(RuntimeError):
        delete_request(test_url)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    capture.check_present()


@responses.activate
def test_get_request():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    responses.add(responses.GET, test_url, json={"Response": "OK"}, status=200)

    resp = get_request(test_url, headers=test_header)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert responses.calls[0].response.text == '{"Response": "OK"}'
    assert resp.ok


@responses.activate
def test_get_request_text():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    responses.add(responses.GET, test_url, json={"Response": "OK"}, status=200)

    resp = get_request(test_url, headers=test_header, text=True)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert resp == '{"Response": "OK"}'


@responses.activate
@log_capture()
def test_get_request_exception(capture):
    test_url = "http://josnplaceholder.typicode.com/"

    logger = logging.getLogger()
    logger.error("Could not reach provided URL")

    responses.add(
        responses.GET,
        test_url,
        body="Could not reach provided URL",
        status=500,
    )

    with pytest.raises(RuntimeError):
        get_request(test_url)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    capture.check_present()


@responses.activate
def test_post_request():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}
    json = {"Payload": "Send this with the request"}

    responses.add(
        responses.POST, test_url, json={"Request": "Sent"}, status=200
    )

    post_request(test_url, headers=test_header, json=json)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert responses.calls[0].response.text == '{"Request": "Sent"}'


@responses.activate
@log_capture()
def test_post_request_exception(capture):
    test_url = "http://josnplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}
    json = {"Payload": "Send this with the request"}

    logger = logging.getLogger()
    logger.error("Could not reach provided URL")

    responses.add(
        responses.POST,
        test_url,
        body="Could not reach provided URL",
        status=500,
    )

    with pytest.raises(RuntimeError):
        post_request(test_url, headers=test_header, json=json)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    capture.check_present()


def test_run_cmd():
    test_cmd = ["echo", "hello"]
    result = run_cmd(test_cmd)

    assert result["returncode"] == 0
    assert result["output"] == "hello"
    assert result["err_msg"] == ""


def test_run_cmd_exception():
    test_cmd = ["ehco", "hello"]

    with pytest.raises(FileNotFoundError):
        run_cmd(test_cmd)
