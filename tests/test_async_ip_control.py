"""Tests for async_ip_control module."""

from typing import Any

import aiohttp
from aiointercept import aiointercept
import pytest
from yarl import URL

from samsungtvws.async_ip_control import SamsungTVAsyncIPControl
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
