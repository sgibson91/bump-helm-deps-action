import pytest
import responses

from helm_bot.helper_functions import delete_request, get_request, post_request, run_cmd


@responses.activate
def test_delete_request():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    responses.add(responses.DELETE, test_url)

    delete_request(test_url, headers=test_header)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url


@responses.activate
def test_delete_request_exception():
    test_url = "http://josnplaceholder.typicode.com/"

    responses.add(responses.DELETE, test_url, status=500)

    with pytest.raises(RuntimeError):
        delete_request(test_url)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url


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
def test_get_request_json():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    responses.add(responses.GET, test_url, json={"Response": "OK"}, status=200)

    resp = get_request(test_url, headers=test_header, json=True)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert resp == {"Response": "OK"}


@responses.activate
def test_get_request_text():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    responses.add(responses.GET, test_url, json={"Response": "OK"}, status=200)

    resp = get_request(test_url, headers=test_header, text=True)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert resp == '{"Response": "OK"}'


def test_get_request_kwargs_exception():
    test_url = "http://jsonplaceholder.typicode.com"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}

    with pytest.raises(ValueError):
        get_request(test_url, headers=test_header, json=True, text=True)


@responses.activate
def test_get_request_url_exception():
    test_url = "http://josnplaceholder.typicode.com/"

    responses.add(responses.GET, test_url, status=500)

    with pytest.raises(RuntimeError):
        get_request(test_url)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url


@responses.activate
def test_post_request():
    test_url = "http://jsonplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}
    json = {"Payload": "Send this with the request"}

    responses.add(responses.POST, test_url, json={"Request": "Sent"}, status=200)

    post_request(test_url, headers=test_header, json=json)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == test_url
    assert responses.calls[0].response.text == '{"Request": "Sent"}'


@responses.activate
def test_post_request_exception():
    test_url = "http://josnplaceholder.typicode.com/"
    test_header = {"Authorization": "token ThIs_Is_A_ToKeN"}
    json = {"Payload": "Send this with the request"}

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
