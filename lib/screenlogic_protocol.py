from __future__ import annotations

from dataclasses import dataclass
import struct


DISCOVERY_PORT = 1444
DISCOVERY_MESSAGE = bytes([1, 0, 0, 0, 0, 0, 0, 0])
CONNECT_BANNER = b"CONNECTSERVERHOST\r\n\r\n"
PACKET_HEADER_SIZE = 8


class HeatMode:
    OFF = 0
    SOLAR = 1
    SOLAR_PREFERRED = 2
    HEAT_PUMP = 3
    DONT_CHANGE = 4


class BodyType:
    POOL = 0
    SPA = 1


class MessageId:
    ERROR_LOGIN_REJECTED = 13
    CHALLENGE_REQUEST = 14
    CHALLENGE_RESPONSE = 15
    LOCAL_LOGIN_REQUEST = 27
    LOCAL_LOGIN_RESPONSE = 28
    VERSION_REQUEST = 8120
    VERSION_RESPONSE = 8121
    GET_CONTROLLER_CONFIG_REQUEST = 12532
    GET_CONTROLLER_CONFIG_RESPONSE = 12533
    GET_EQUIPMENT_STATE_REQUEST = 12526
    GET_EQUIPMENT_STATE_RESPONSE = 12527


@dataclass(frozen=True)
class LocalUnitConnection:
    gateway_name: str
    address: str
    port: int


@dataclass(frozen=True)
class ScreenLogicPacket:
    sender_id: int
    message_id: int
    payload: bytes

    @property
    def payload_length(self) -> int:
        return len(self.payload)


@dataclass(frozen=True)
class ChallengeInfo:
    challenge: str = ""


@dataclass(frozen=True)
class VersionInfo:
    version: str = ""


def encode_packet(sender_id: int, message_id: int, payload: bytes = b"") -> bytes:
    return (
        int(sender_id).to_bytes(2, "little", signed=False)
        + int(message_id).to_bytes(2, "little", signed=False)
        + len(payload).to_bytes(4, "little", signed=False)
        + payload
    )


def encode_message_string(value: str, utf_16: bool = False) -> bytes:
    encoding = "utf-16" if utf_16 else "utf-8"
    data = value.encode(encoding)
    length = len(data)
    padding = (4 - (length % 4)) % 4
    packed_length = length | 0x80000000 if utf_16 else length
    return struct.pack(f"<I{length + padding}s", packed_length, data)


def build_local_login_payload(
    password: str,
    *,
    client_version: str = "Android",
    schema: int = 348,
    connection_type: int = 0,
    pid: int = 2,
) -> bytes:
    normalized_password = "" if password is None else str(password).strip()
    if len(normalized_password) > 16:
        raise ValueError("ScreenLogic local login password must be 16 characters or less.")

    client_version_bytes = encode_message_string(client_version)
    password_bytes = encode_message_string(normalized_password)
    fmt = f"<II{len(client_version_bytes)}s{len(password_bytes)}sxI"
    return struct.pack(
        fmt,
        schema,
        connection_type,
        client_version_bytes,
        password_bytes,
        pid,
    )


def decode_packet_header(header: bytes) -> tuple[int, int, int]:
    if len(header) != PACKET_HEADER_SIZE:
        raise ValueError(
            f"ScreenLogic packet header must be {PACKET_HEADER_SIZE} bytes, got {len(header)}."
        )

    sender_id = int.from_bytes(header[0:2], "little", signed=False)
    message_id = int.from_bytes(header[2:4], "little", signed=False)
    payload_length = int.from_bytes(header[4:8], "little", signed=False)
    return sender_id, message_id, payload_length


def parse_challenge_payload(payload: bytes) -> ChallengeInfo:
    if len(payload) < 4:
        return ChallengeInfo()

    text_length = int.from_bytes(payload[0:4], "little", signed=False)
    challenge_bytes = payload[4 : 4 + text_length]
    challenge = challenge_bytes.decode("utf-8", errors="ignore").rstrip("\x00")
    return ChallengeInfo(challenge=challenge)


def parse_version_payload(payload: bytes) -> VersionInfo:
    if len(payload) < 4:
        return VersionInfo()

    text_length = int.from_bytes(payload[0:4], "little", signed=False)
    version_bytes = payload[4 : 4 + text_length]
    version = version_bytes.decode("utf-8", errors="ignore").rstrip("\x00")
    return VersionInfo(version=version)
