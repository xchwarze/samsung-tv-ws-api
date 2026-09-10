"""SamsungTV Encrypted."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
from aiointercept import aiointercept
import pytest
from yarl import URL

from samsungtvws.encrypted.authenticator import (
    SamsungTVEncryptedError,
    SamsungTVEncryptedPairingExpiredError,
    SamsungTVEncryptedResponseError,
    SamsungTVEncryptedWSAsyncAuthenticator,
)


@pytest.mark.asyncio
async def test_authenticator(aiointercept_mock: aiointercept) -> None:
    with open("tests/fixtures/auth_pin_status.xml") as file:
        aiointercept_mock.get(
            "http://samsungtv.test:8080/ws/apps/CloudPINPage", body=file.read()
        )
    with open("tests/fixtures/auth_pin_status.xml") as file:
        aiointercept_mock.post(
            "http://samsungtv.test:8080/ws/apps/CloudPINPage",
            body="http:///ws/apps/CloudPINPage/run",
        )
    with open("tests/fixtures/auth_empty.json") as file:
        aiointercept_mock.get(
            "http://samsungtv.test:8080/ws/pairing?step=0&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&type=1",
            body=file.read(),
        )
    with open("tests/fixtures/auth_generator_client_hello.json") as file:
        aiointercept_mock.post(
            "http://samsungtv.test:8080/ws/pairing?step=1&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
            body=file.read(),
        )
    with open("tests/fixtures/auth_client_ack_msg.json") as file:
        aiointercept_mock.post(
            "http://samsungtv.test:8080/ws/pairing?step=2&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
            body=file.read(),
        )
    aiointercept_mock.delete(
        "http://samsungtv.test:8080/ws/apps/CloudPINPage/run", body=""
    )

    authenticator = SamsungTVEncryptedWSAsyncAuthenticator(
        "samsungtv.test", web_session=aiohttp.ClientSession()
    )
    await authenticator.start_pairing()
    token = await authenticator.try_pin("0997")
    assert token == "545a596ab96b289c60896255e8690288"

    session_id = await authenticator.get_session_id_and_close()
    assert session_id == "1"

    assert len(aiointercept_mock.requests) == 6
    print(aiointercept_mock.requests)

    request = aiointercept_mock.requests[
        (
            "POST",
            URL(
                "http://samsungtv.test:8080/ws/pairing?app_id=12345&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&step=1"
            ),
        )
    ]
    assert (
        request[0].kwargs["data"].decode()
        == '{"auth_Data":{"auth_type":"SPC","GeneratorServerHello":'
        '"010200000000000000008A000000063635343332317CAF9CBDC06B666D23EBC'
        "A615E0666FEB2B807091BF507404DDD18329CD64A91E513DC704298CCE49C4C5"
        "656C42141A696354A7145127BCD94CDD2B0D632D87E332437F86EBE5A50A1512"
        "F3F54C71B791A88ECBAF562FBABE2731F27D851A764CA114DBE2C2C965DF151C"
        'FC7401920FAA04636B356B97DBE1DA3A090004F81830000000000"}}'
    )
    request = aiointercept_mock.requests[
        (
            "POST",
            URL(
                "http://samsungtv.test:8080/ws/pairing?app_id=12345&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&step=2"
            ),
        )
    ]
    assert (
        request[0].kwargs["data"].decode()
        == '{"auth_Data":{"auth_type":"SPC","request_id":"0","ServerAckMsg":'
        '"01030000000000000000145F38EAFF0F6A6FF062CA652CD6CBAD9AF1EC62470000000000"}}'
    )


async def _pair_until_step2(
    aiointercept_mock: aiointercept, *, step2_body: str
) -> SamsungTVEncryptedWSAsyncAuthenticator:
    """Drive pairing up to (but not through) step 2, returning the authenticator.

    ``step2_body`` is the raw body the TV "returns" at step 2, letting each
    test exercise a different acknowledge-exchange response.
    """
    with open("tests/fixtures/auth_pin_status.xml") as file:
        aiointercept_mock.get(
            "http://samsungtv.test:8080/ws/apps/CloudPINPage", body=file.read()
        )
    aiointercept_mock.post(
        "http://samsungtv.test:8080/ws/apps/CloudPINPage",
        body="http:///ws/apps/CloudPINPage/run",
    )
    with open("tests/fixtures/auth_empty.json") as file:
        aiointercept_mock.get(
            "http://samsungtv.test:8080/ws/pairing?step=0&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&type=1",
            body=file.read(),
        )
    with open("tests/fixtures/auth_generator_client_hello.json") as file:
        aiointercept_mock.post(
            "http://samsungtv.test:8080/ws/pairing?step=1&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
            body=file.read(),
        )
    aiointercept_mock.post(
        "http://samsungtv.test:8080/ws/pairing?step=2&app_id=12345"
        "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
        body=step2_body,
    )

    authenticator = SamsungTVEncryptedWSAsyncAuthenticator(
        "samsungtv.test", web_session=aiohttp.ClientSession()
    )
    await authenticator.start_pairing()
    token = await authenticator.try_pin("0997")
    assert token == "545a596ab96b289c60896255e8690288"
    return authenticator


@pytest.mark.asyncio
async def test_acknowledge_empty_auth_data_raises_pairing_expired(
    aiointercept_mock: aiointercept,
) -> None:
    """Empty auth_data at step 2 => a distinct, retryable expired-pairing error.

    Regression test for fermulator/samsung-tv-ws-api#2.
    """
    with open("tests/fixtures/auth_empty.json") as file:
        empty_body = file.read()
    authenticator = await _pair_until_step2(aiointercept_mock, step2_body=empty_body)

    with pytest.raises(SamsungTVEncryptedPairingExpiredError) as excinfo:
        await authenticator.get_session_id_and_close()
    # The raw response is surfaced in the message (not just at DEBUG).
    assert "auth_data" in str(excinfo.value)


@pytest.mark.asyncio
async def test_acknowledge_unparseable_raises_response_error(
    aiointercept_mock: aiointercept,
) -> None:
    """Non-empty but unparseable auth_data => a response error, not expired."""
    authenticator = await _pair_until_step2(
        aiointercept_mock,
        step2_body='{"auth_data": "totally unexpected payload"}',
    )

    with pytest.raises(SamsungTVEncryptedResponseError):
        await authenticator.get_session_id_and_close()


@pytest.mark.asyncio
async def test_pairing_errors_remain_catchable_as_exception(
    aiointercept_mock: aiointercept,
) -> None:
    """Backwards-compat: new errors subclass a base that subclasses Exception."""
    assert issubclass(SamsungTVEncryptedError, Exception)
    assert issubclass(SamsungTVEncryptedPairingExpiredError, SamsungTVEncryptedError)
    assert issubclass(SamsungTVEncryptedResponseError, SamsungTVEncryptedError)

    with open("tests/fixtures/auth_empty.json") as file:
        empty_body = file.read()
    authenticator = await _pair_until_step2(aiointercept_mock, step2_body=empty_body)

    # Existing callers doing `except Exception` keep working: the raised type
    # is SamsungTVEncryptedError, which (asserted above) subclasses Exception.
    with pytest.raises(SamsungTVEncryptedError):
        await authenticator.get_session_id_and_close()


def _mock_session(get_body: str) -> MagicMock:
    """Mock aiohttp session whose get/post act as async context managers.

    aiointercept drops client-only kwargs like ``timeout=`` from its captured
    requests, so the timeout wiring is asserted directly against the session
    rather than through the mock server.
    """

    def _response(body: str) -> MagicMock:
        response = MagicMock()
        response.text = AsyncMock(return_value=body)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=response)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    session = MagicMock()
    session.get = MagicMock(return_value=_response(get_body))
    session.post = MagicMock(return_value=_response(""))
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (7.5, 7.5),  # explicit timeout is forwarded
        (None, None),  # default: forwarded as None (aiohttp: no timeout)
        (0, None),  # 0 disables the timeout, matching the rest of the SDK
    ],
)
async def test_authenticator_forwards_timeout(
    configured: float | None, expected: float | None
) -> None:
    """The configured timeout is forwarded to the underlying requests.

    Regression test for fermulator/samsung-tv-ws-api#1. ``start_pairing`` issues
    a GET (state check) and a POST (show PIN); both must carry ``timeout``.
    """
    session = _mock_session("<state>stopped</state>")
    authenticator = SamsungTVEncryptedWSAsyncAuthenticator(
        "samsungtv.test", web_session=session, timeout=configured
    )

    await authenticator.start_pairing()

    assert session.get.call_args.kwargs["timeout"] == expected
    assert session.post.call_args.kwargs["timeout"] == expected
