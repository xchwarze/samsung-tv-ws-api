"""SamsungTV Encrypted."""

import binascii

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
