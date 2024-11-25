"""SamsungTV Encrypted."""

import aiohttp
from aioresponses import aioresponses
import pytest
from yarl import URL

from samsungtvws.encrypted.authenticator import (
    SamsungTVEncryptedWSAsyncAuthenticator,
)


@pytest.mark.asyncio
async def test_authenticator(aioresponse: aioresponses) -> None:
    with open("tests/fixtures/auth_pin_status.xml") as file:
        aioresponse.get("http://1.2.3.4:8080/ws/apps/CloudPINPage", body=file.read())
    with open("tests/fixtures/auth_pin_status.xml") as file:
        aioresponse.post(
            "http://1.2.3.4:8080/ws/apps/CloudPINPage",
            body="http:///ws/apps/CloudPINPage/run",
        )
    with open("tests/fixtures/auth_empty.json") as file:
        aioresponse.get(
            "http://1.2.3.4:8080/ws/pairing?step=0&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&type=1",
            body=file.read(),
        )
    with open("tests/fixtures/auth_generator_client_hello.json") as file:
        aioresponse.post(
            "http://1.2.3.4:8080/ws/pairing?step=1&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
            body=file.read(),
        )
    with open("tests/fixtures/auth_client_ack_msg.json") as file:
        aioresponse.post(
            "http://1.2.3.4:8080/ws/pairing?step=2&app_id=12345"
            "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
            body=file.read(),
        )
    aioresponse.delete("http://1.2.3.4:8080/ws/apps/CloudPINPage/run", body="")

    authenticator = SamsungTVEncryptedWSAsyncAuthenticator(
        "1.2.3.4", web_session=aiohttp.ClientSession()
    )
    await authenticator.start_pairing()
    token = await authenticator.try_pin("0997")
    assert token == "545a596ab96b289c60896255e8690288"

    session_id = await authenticator.get_session_id_and_close()
    assert session_id == "1"

    assert len(aioresponse.requests) == 6
    print(aioresponse.requests)

    request = aioresponse.requests[
        (
            "POST",
            URL(
                "http://1.2.3.4:8080/ws/pairing?app_id=12345&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&step=1"
            ),
        )
    ]
    assert (
        request[0].kwargs["data"]
        == '{"auth_Data":{"auth_type":"SPC","GeneratorServerHello":'
        '"010200000000000000008A000000063635343332317CAF9CBDC06B666D23EBC'
        "A615E0666FEB2B807091BF507404DDD18329CD64A91E513DC704298CCE49C4C5"
        "656C42141A696354A7145127BCD94CDD2B0D632D87E332437F86EBE5A50A1512"
        "F3F54C71B791A88ECBAF562FBABE2731F27D851A764CA114DBE2C2C965DF151C"
        'FC7401920FAA04636B356B97DBE1DA3A090004F81830000000000"}}'
    )
    request = aioresponse.requests[
        (
            "POST",
            URL(
                "http://1.2.3.4:8080/ws/pairing?app_id=12345&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&step=2"
            ),
        )
    ]
    assert (
        request[0].kwargs["data"]
        == '{"auth_Data":{"auth_type":"SPC","request_id":"0","ServerAckMsg":'
        '"01030000000000000000145F38EAFF0F6A6FF062CA652CD6CBAD9AF1EC62470000000000"}}'
    )
