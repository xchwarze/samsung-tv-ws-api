"""SamsungTV Encrypted."""
import binascii

import aiohttp
from aioresponses import aioresponses
import pytest
from yarl import URL

from samsungtvws.encrypted.authenticator import SamsungTVEncryptedWSAsyncAuthenticator
from samsungtvws.encrypted.command import SamsungTVEncryptedCommand
from samsungtvws.encrypted.session import SamsungTVEncryptedSession

TOKEN = "037739871315caef138547b03e348b72"
SESSION_ID = "1"


def test_simple_encrypt() -> None:
    session = SamsungTVEncryptedSession(TOKEN, SESSION_ID)
    message = "This is a test message"

    encrypted_bytes = session._encrypt(message)
    assert (
        encrypted_bytes
        == b"\xf9\xe8\x1c++:i\xb0\xd4\xc4\x12o$\x9e\x017\x9c\x9cS\x88\xd9\xbb"
        b"\x82/\xfb\xee\x0fD\xc2\xb9\x19\x03"
    )
    decrypted_bytes = session._decrypt(binascii.hexlify(encrypted_bytes))
    assert decrypted_bytes == message


def test_command_encryption() -> None:
    session = SamsungTVEncryptedSession(TOKEN, SESSION_ID)
    command = SamsungTVEncryptedCommand(
        "POST",
        {
            "plugin": "RemoteControl",
            "param1": "uuid:12345",
            "param2": "Click",
            "param3": "KEY_POWER",
            "param4": False,
            "api": "SendRemoteKey",
            "version": "1.000",
        },
    )

    assert (
        session.encrypt_command(command)
        == '5::/com.samsung.companion:{"name":"callCommon","args":[{"Session_Id":1,'
        '"body":"[36,178,255,123,141,203,175,38,44,80,238,135,196,244,171,173,168,'
        "203,242,52,81,131,19,209,43,150,125,3,229,60,22,185,94,51,71,133,63,60,116,"
        "56,119,181,6,91,32,218,39,71,242,208,209,160,67,81,186,70,83,138,123,99,0,"
        "64,72,86,155,165,43,171,54,77,172,34,121,51,34,203,42,110,49,65,75,172,23,"
        "19,54,30,190,174,55,214,124,242,118,85,209,204,245,255,56,29,199,94,185,6,"
        "34,82,126,32,29,81,15,137,197,87,119,61,229,138,138,26,233,26,218,47,162,"
        "132,151,47,148,22,139,193,11,253,224,235,38,228,81,172,9,73,1,119,68,22,170,"
        "159,82,31,133,14,135,250,9,176,177,154,168,133,246,223,199,55,254,201,69,76,"
        "5,234,89,212,194,79,28,96,94,86,240,99,19,152,34,38,237,222,8,185,142,127,"
        '73,181]"}]}'
    )


@pytest.mark.asyncio
async def test_authenticator(aioresponse: aioresponses) -> None:
    aioresponse.get("http://1.2.3.4:8080/ws/apps/CloudPINPage", body="")
    aioresponse.get(
        "http://1.2.3.4:8080/ws/pairing?step=0&app_id=12345"
        "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184&type=1",
        body="",
    )
    client_hello = (
        "010100000000000000009e00000006363534333231f596d0966d"
        "38bdf42546fb2a06ae96161680381fbca62498e82903c36da100eba0c148cc1545d"
        "b8f976a14423d95df7cac081b3722c2720c7ecc8d746d269319d309d36e432a1e32"
        "fea28dd7492692a71c7bf531d11a8f45ebb2a2834bb21e02e83ac7978396c03cfdd"
        "53256df124c09fdcae1711a9aeceaa83f3b8d8b2e70dcfe709b3e807dcaa9a9787f"
        "6a2f64475e9a70c1d80000000000"
    )
    aioresponse.post(
        "http://1.2.3.4:8080/ws/pairing?step=1&app_id=12345"
        "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
        body="request_id.*?1.*?GeneratorClientHello.*?:.*?" + client_hello,
    )
    client_ack = (
        "0104000000000000000014CF0EDA4882C5D560B584D5897A7EDDE7FABC16E80000000000"
    )
    aioresponse.post(
        "http://1.2.3.4:8080/ws/pairing?step=2&app_id=12345"
        "&device_id=7e509404-9d7c-46b4-8f6a-e2a9668ad184",
        body="ClientAckMsg.*?:.*?" + client_ack + ".*?session_id.*?1",
    )
    aioresponse.delete("http://1.2.3.4:8080/ws/apps/CloudPINPage/run", body="")

    authenticator = SamsungTVEncryptedWSAsyncAuthenticator(
        "1.2.3.4", web_session=aiohttp.ClientSession()
    )
    await authenticator.start_pairing()
    token = await authenticator.try_pin("0997")
    assert token == TOKEN

    session_id = await authenticator.get_session_id_and_close()
    assert session_id == SESSION_ID

    assert len(aioresponse.requests) == 5
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
