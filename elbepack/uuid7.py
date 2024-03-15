import datetime
import secrets
import struct
import uuid


def uuid7(now=None):
    if now is None:
        now = datetime.datetime.now()

    res = bytearray()

    res.extend(
        struct.pack('>Q', int(now.timestamp() * 1000))[2:]
    )

    res.extend(secrets.token_bytes(10))
    res[6] = 0b01110000 | (res[6] & 0b00001111)
    res[8] = 0b10000000 | (res[7] & 0b00111111)

    return uuid.UUID(bytes=bytes(res))


if __name__ == '__main__':
    print(uuid7())
