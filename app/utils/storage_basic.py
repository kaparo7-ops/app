import os
_BASE = os.environ.get("STORAGE_BASE","/var/data/minio")

def put_bytes(key:str, b:bytes):
    path = os.path.join(_BASE, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fp:
        fp.write(b)

def get_bytes(key:str) -> bytes:
    path = os.path.join(_BASE, key)
    with open(path, 'rb') as fp:
        return fp.read()
