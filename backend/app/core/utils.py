import hashlib

def generate_deterministic_id(name: str) -> int:
    """
    Генерирует уникальный числовой ID длиной 6 знаков на основе строки.
    Диапазон: 100,000 - 999,999
    """
    # Используем SHA-256 для надежности
    hash_object = hashlib.sha256(name.encode('utf-8'))
    hash_hex = hash_object.hexdigest()
    
    # Преобразуем хэш (hex) в большое целое число
    hash_int = int(hash_hex, 16)
    
    # Ограничиваем диапазон шестью цифрами (от 0 до 899,999) 
    # и прибавляем 100,000, чтобы всегда было ровно 6 знаков
    deterministic_id = (hash_int % 900000) + 100000
    
    return deterministic_id
