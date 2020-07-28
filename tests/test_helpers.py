import pytest
import logging
import responses
from testfixtures import log_capture
from helm_bot.helper_functions import delete_request


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
