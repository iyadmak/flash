import base64
import binascii


def encode_cursor(id: int) -> str:
    return base64.urlsafe_b64encode(str(id).encode()).decode()


def decode_cursor(cursor: str) -> int:
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error) as e:
        raise ValueError("invalid cursor") from e
