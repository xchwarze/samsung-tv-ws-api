"""Tests for async_ip_control module."""

import ssl
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import aiohttp
from aiointercept import aiointercept
import pytest
from yarl import URL

from samsungtvws import async_ip_control
from samsungtvws.async_ip_control import SamsungTVAsyncIPControl, get_ssl_context
from samsungtvws.exceptions import (
    IPControlConnectionError,
    IPControlError,
    IPControlResponseError,
    IPControlUnauthorizedError,
)

URL_IP_CONTROL = "https://samsungtv.test:1516/"
TOKEN = "ABCDEF123456"

TV_STATES_SAMPLE = (
    '{"jsonrpc":"2.0","id":"1","result":{"speakerSelect":"internal","volume":27,'
    '"mute":"muteOff","pictureSize":"16:9","pictureMode":"Dynamic",'
    '"soundMode":"Standard","inputSource":"HDMI1"}}'
)


def _mock_session(exception: Exception | None = None) -> Mock:
    """Return a session answering with the TV states, or failing to connect."""
    response = Mock(status=200)
    response.text = AsyncMock(return_value=TV_STATES_SAMPLE)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response, side_effect=exception)
    context.__aexit__ = AsyncMock(return_value=False)
    session = Mock(aiohttp.ClientSession)
    session.post = Mock(return_value=context)
    return session


def _sent_json(aiointercept_mock: aiointercept, index: int = 0) -> dict[str, Any]:
    request = aiointercept_mock.requests[("POST", URL(URL_IP_CONTROL))]
    payload: dict[str, Any] = request[index].kwargs["json"]
    return payload


@pytest.mark.asyncio
async def test_create_access_token(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure pairing is requested without token and the token is stored."""
    aiointercept_mock.post(
        URL_IP_CONTROL,
        body='{"jsonrpc":"2.0","id":"1","result":{"AccessToken":"ABCDEF123456"}}',
    )
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session)
    assert await tv.create_access_token() == TOKEN
    assert tv.token == TOKEN
    assert _sent_json(aiointercept_mock) == {
        "jsonrpc": "2.0",
        "method": "createAccessToken",
        "id": 1,
    }


@pytest.mark.asyncio
async def test_create_access_token_missing(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure a pairing response without token raises."""
    aiointercept_mock.post(URL_IP_CONTROL, body='{"jsonrpc":"2.0","result":{}}')
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session)
    with pytest.raises(IPControlError, match="No access token"):
        await tv.create_access_token()
    assert tv.token is None


@pytest.mark.asyncio
async def test_get_tv_states(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure the states are returned and the token is sent."""
    aiointercept_mock.post(URL_IP_CONTROL, body=TV_STATES_SAMPLE)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    states = await tv.get_tv_states()
    assert states["inputSource"] == "HDMI1"
    assert states["volume"] == 27
    request = aiointercept_mock.requests[("POST", URL(URL_IP_CONTROL))]
    assert request[0].kwargs["headers"]["Accept"] == "application/json"
    assert _sent_json(aiointercept_mock) == {
        "jsonrpc": "2.0",
        "method": "getTVStates",
        "params": {"AccessToken": TOKEN},
        "id": 1,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "args", "rpc_method", "params"),
    [
        pytest.param("power_on", (), "powerControl", {"power": "powerOn"}, id="on"),
        pytest.param("power_off", (), "powerControl", {"power": "powerOff"}, id="off"),
        pytest.param(
            "input_source_control",
            ("HDMI2",),
            "inputSourceControl",
            {"inputSource": "HDMI2"},
            id="source",
        ),
    ],
)
async def test_control(
    aiointercept_mock: aiointercept,
    web_session: aiohttp.ClientSession,
    method_name: str,
    args: tuple[str, ...],
    rpc_method: str,
    params: dict[str, str],
) -> None:
    """Ensure each control sends its JSON-RPC method and parameters."""
    aiointercept_mock.post(
        URL_IP_CONTROL, body='{"jsonrpc":"2.0","id":"1","result":{"ok":"yes"}}'
    )
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    assert await getattr(tv, method_name)(*args) == {"ok": "yes"}
    assert _sent_json(aiointercept_mock) == {
        "jsonrpc": "2.0",
        "method": rpc_method,
        "params": {"AccessToken": TOKEN, **params},
        "id": 1,
    }


@pytest.mark.asyncio
async def test_request_id_increments(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure each request gets a new id."""
    aiointercept_mock.post(URL_IP_CONTROL, body=TV_STATES_SAMPLE, repeat=True)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    await tv.get_tv_states()
    await tv.get_tv_states()
    assert _sent_json(aiointercept_mock, 1)["id"] == 2


@pytest.mark.asyncio
async def test_token_required(web_session: aiohttp.ClientSession) -> None:
    """Ensure no request is sent when the token is missing."""
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session)
    with pytest.raises(IPControlUnauthorizedError, match="token is required"):
        await tv.get_tv_states()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        pytest.param('{"code": -32700, "message": "Parse error"}', id="bare_parse"),
        pytest.param(
            '{"jsonrpc":"2.0","id":"1","error":{"code":-32010,"message":"Unauthorized"}}',
            id="unauthorized",
        ),
    ],
)
async def test_token_rejected(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession, body: str
) -> None:
    """Ensure a rejected token raises IPControlUnauthorizedError."""
    aiointercept_mock.post(URL_IP_CONTROL, body=body)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    with pytest.raises(IPControlUnauthorizedError, match="token rejected"):
        await tv.get_tv_states()


@pytest.mark.asyncio
async def test_pairing_parse_error_is_not_unauthorized(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure a parse error without token is a plain response error."""
    aiointercept_mock.post(
        URL_IP_CONTROL, body='{"code": -32700, "message": "Parse error"}'
    )
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session)
    with pytest.raises(IPControlResponseError) as err:
        await tv.create_access_token()
    assert err.value.code == -32700


@pytest.mark.asyncio
async def test_response_error(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure a JSON-RPC error carries its code."""
    aiointercept_mock.post(
        URL_IP_CONTROL,
        body='{"jsonrpc":"2.0","id":"1","error":{"code":-32002,"message":"Failed"}}',
    )
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    with pytest.raises(IPControlResponseError, match="powerControl failed") as err:
        await tv.power_on()
    assert err.value.code == -32002


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        pytest.param({"status": 400, "body": ""}, "HTTP status 400", id="status"),
        pytest.param({"body": "not json"}, "Failed to parse", id="invalid_json"),
        pytest.param({"body": "[]"}, "Unexpected response", id="not_object"),
        pytest.param(
            {"body": '{"jsonrpc":"2.0","result":"x"}'}, "Unexpected result", id="result"
        ),
    ],
)
async def test_invalid_response(
    aiointercept_mock: aiointercept,
    web_session: aiohttp.ClientSession,
    kwargs: dict[str, Any],
    match: str,
) -> None:
    """Ensure malformed responses raise IPControlError."""
    aiointercept_mock.post(URL_IP_CONTROL, **kwargs)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    with pytest.raises(IPControlError, match=match):
        await tv.get_tv_states()


@pytest.mark.asyncio
async def test_unreachable(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure connection errors raise IPControlConnectionError."""
    aiointercept_mock.post(URL_IP_CONTROL, exception=True)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    with pytest.raises(IPControlConnectionError, match="TV unreachable"):
        await tv.get_tv_states()


@pytest.mark.asyncio
async def test_tls_handshake_failure() -> None:
    """Ensure a TLS failure is not reported as an unreachable TV."""
    session = _mock_session(
        aiohttp.ClientConnectorSSLError(Mock(), ssl.SSLError(1, "dh key too small"))
    )
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=session, token=TOKEN)
    with pytest.raises(IPControlConnectionError, match="TLS handshake") as err:
        await tv.get_tv_states()
    assert "dh key too small" in str(err.value)


def test_get_ssl_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the unverified context allowing legacy ciphers is cached."""
    monkeypatch.setattr(async_ip_control, "_SSL_CONTEXT", None)
    context = get_ssl_context()
    assert context.verify_mode is ssl.CERT_NONE
    assert not context.check_hostname
    assert context.security_level == 0
    assert get_ssl_context() is context


@pytest.mark.asyncio
@pytest.mark.parametrize("custom", [False, True], ids=["default", "custom"])
async def test_ssl_context_used(custom: bool) -> None:
    """Ensure the default or the given SSL context is used for requests."""
    session = _mock_session()
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if custom else None
    tv = SamsungTVAsyncIPControl(
        "samsungtv.test", session=session, token=TOKEN, ssl_context=ssl_context
    )
    assert (await tv.get_tv_states())["inputSource"] == "HDMI1"
    session.post.assert_called_once()
    assert session.post.call_args.args == (URL_IP_CONTROL,)
    assert session.post.call_args.kwargs["ssl"] is (ssl_context or get_ssl_context())


@pytest.mark.asyncio
async def test_legacy_port(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure the port of older models can be used."""
    url = "https://samsungtv.test:1515/"
    aiointercept_mock.post(url, body=TV_STATES_SAMPLE)
    tv = SamsungTVAsyncIPControl(
        "samsungtv.test",
        session=web_session,
        token=TOKEN,
        port=async_ip_control.IP_CONTROL_PORT_LEGACY,
    )
    await tv.get_tv_states()
    assert list(aiointercept_mock.requests) == [("POST", URL(url))]


@pytest.mark.asyncio
async def test_port_detected(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure the port of older models is found and then kept."""
    url_legacy = "https://samsungtv.test:1515/"
    aiointercept_mock.post(URL_IP_CONTROL, exception=True)
    aiointercept_mock.post(url_legacy, body=TV_STATES_SAMPLE, repeat=True)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    assert tv.port is None

    assert (await tv.get_tv_states())["inputSource"] == "HDMI1"
    assert tv.port == 1515
    assert list(aiointercept_mock.requests) == [
        ("POST", URL(URL_IP_CONTROL)),
        ("POST", URL(url_legacy)),
    ]

    # The other port is not tried again
    await tv.get_tv_states()
    assert len(aiointercept_mock.requests[("POST", URL(URL_IP_CONTROL))]) == 1
    assert len(aiointercept_mock.requests[("POST", URL(url_legacy))]) == 2


@pytest.mark.asyncio
async def test_port_detected_default(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure the legacy port is not tried when the default port answers."""
    aiointercept_mock.post(URL_IP_CONTROL, body=TV_STATES_SAMPLE)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    await tv.get_tv_states()
    assert tv.port == 1516
    assert list(aiointercept_mock.requests) == [("POST", URL(URL_IP_CONTROL))]


@pytest.mark.asyncio
async def test_port_not_detected(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure both ports are tried again after neither answered."""
    url_legacy = "https://samsungtv.test:1515/"
    aiointercept_mock.post(URL_IP_CONTROL, exception=True, repeat=True)
    aiointercept_mock.post(url_legacy, exception=True, repeat=True)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=web_session, token=TOKEN)
    for _ in range(2):
        with pytest.raises(IPControlConnectionError, match="TV unreachable"):
            await tv.get_tv_states()
        assert tv.port is None
    assert len(aiointercept_mock.requests[("POST", URL(URL_IP_CONTROL))]) == 2
    assert len(aiointercept_mock.requests[("POST", URL(url_legacy))]) == 2


@pytest.mark.asyncio
async def test_port_given_is_not_detected(
    aiointercept_mock: aiointercept, web_session: aiohttp.ClientSession
) -> None:
    """Ensure only the given port is used."""
    aiointercept_mock.post(URL_IP_CONTROL, exception=True)
    tv = SamsungTVAsyncIPControl(
        "samsungtv.test", session=web_session, token=TOKEN, port=1516
    )
    with pytest.raises(IPControlConnectionError):
        await tv.get_tv_states()
    assert tv.port == 1516
    assert list(aiointercept_mock.requests) == [("POST", URL(URL_IP_CONTROL))]


@pytest.mark.asyncio
async def test_port_detection_reports_tls_failure() -> None:
    """Ensure a TLS failure is reported when the other port is closed."""
    response_context = MagicMock()
    response_context.__aenter__ = AsyncMock(
        side_effect=[
            aiohttp.ClientConnectionError("refused"),
            aiohttp.ClientConnectorSSLError(
                Mock(), ssl.SSLError(1, "dh key too small")
            ),
        ]
    )
    response_context.__aexit__ = AsyncMock(return_value=False)
    session = Mock(aiohttp.ClientSession)
    session.post = Mock(return_value=response_context)
    tv = SamsungTVAsyncIPControl("samsungtv.test", session=session, token=TOKEN)
    with pytest.raises(IPControlConnectionError, match="TLS handshake"):
        await tv.get_tv_states()
    assert tv.port is None
    assert [call.args[0] for call in session.post.call_args_list] == [
        URL_IP_CONTROL,
        "https://samsungtv.test:1515/",
    ]
