"""HTTP boundary tests without outbound network or real credentials."""

import json
import ssl
from threading import Event, Timer

import pytest

from partsmith.ai import AICancelled, AIError, TransportError
from partsmith.ai.openai import HTTPTransport


class Response:
    def __init__(self, status=200, raw=b"{}"):
        self.status = status
        self.raw = raw

    def read(self, size):
        return self.raw[:size]


class Connection:
    def __init__(self, response=None, error=None):
        self.response = response or Response()
        self.error = error
        self.calls = []
        self.closed = Event()

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed.set()


def install(monkeypatch, connection):
    observed = []

    def factory(host, **kwargs):
        observed.append((host, kwargs))
        return connection

    monkeypatch.setattr("http.client.HTTPSConnection", factory)
    return observed


def test_fixed_https_no_redirects_or_environment_proxies(monkeypatch):
    connection = Connection(Response(raw=b'{"status":"completed"}'))
    observed = install(monkeypatch, connection)
    monkeypatch.setenv("HTTPS_PROXY", "https://attacker.example")
    result = HTTPTransport().send(
        b'{"input":"source"}', "dummy-key", 1, Event()
    )
    assert json.loads(result)["status"] == "completed"
    assert observed[0][0] == "api.openai.com"
    assert isinstance(observed[0][1]["context"], ssl.SSLContext)
    args, kwargs = connection.calls[0]
    assert args == ("POST", "/v1/responses")
    assert kwargs["headers"]["Authorization"] == "Bearer dummy-key"
    assert b"dummy-key" not in kwargs["body"]
    assert connection.closed.is_set()


@pytest.mark.parametrize(
    "status,transient",
    [
        (302, False),
        (400, False),
        (401, False),
        (403, False),
        (429, True),
        (503, True),
    ],
)
def test_safe_http_failures_discard_upstream_body(
    monkeypatch, status, transient
):
    connection = Connection(Response(status, b"api_key=do-not-log-this"))
    install(monkeypatch, connection)
    with pytest.raises(TransportError) as error:
        HTTPTransport().send(b"{}", "dummy-key", 1, Event())
    assert error.value.transient is transient
    assert "do-not-log-this" not in str(error.value)
    assert len(connection.calls) == 1 and connection.closed.is_set()


def test_tls_failure_is_not_transient(monkeypatch):
    install(
        monkeypatch,
        Connection(error=ssl.SSLCertVerificationError("secret-context")),
    )
    with pytest.raises(TransportError) as error:
        HTTPTransport().send(b"{}", "dummy-key", 1, Event())
    assert not error.value.transient and error.value.code == "tls"
    assert "secret-context" not in str(error.value)


def test_response_size_limit(monkeypatch):
    install(monkeypatch, Connection(Response(raw=b"x" * (1024 * 1024 + 1))))
    with pytest.raises(AIError, match="size limit"):
        HTTPTransport().send(b"{}", "dummy-key", 1, Event())


def test_malformed_utf8_is_a_deterministic_response_failure(monkeypatch):
    install(monkeypatch, Connection(Response(raw=b"\xff")))
    with pytest.raises(AIError, match="UTF-8"):
        HTTPTransport().send(b"{}", "dummy-key", 1, Event())


def test_cancel_closes_active_connection(monkeypatch):
    class WaitingConnection(Connection):
        def getresponse(self):
            assert self.closed.wait(2)
            return Response()

    connection = WaitingConnection()
    install(monkeypatch, connection)
    cancel = Event()
    timer = Timer(0.1, cancel.set)
    timer.start()
    try:
        with pytest.raises(AICancelled):
            HTTPTransport().send(b"{}", "dummy-key", 1, cancel)
        assert connection.closed.is_set()
    finally:
        timer.cancel()
