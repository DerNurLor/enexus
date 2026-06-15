import hashlib

def generate_deterministic_id(name: str) -> int:
    hash_object = hashlib.sha256(name.encode('utf-8'))
    hash_hex = hash_object.hexdigest()
    hash_int = int(hash_hex, 16)
    deterministic_id = (hash_int % 900000) + 100000
    return deterministic_id
