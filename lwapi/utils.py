import base64
import hashlib

def md5hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

def encode_base64_bytes(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")
