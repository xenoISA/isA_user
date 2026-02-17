"""
Random Data Generators

Generate random test data for various scenarios.
"""
import uuid
import random
import string
from typing import List


def random_string(length: int = 10) -> str:
    """Generate a random string"""
    return ''.join(random.choices(string.ascii_letters, k=length))


def random_email() -> str:
    """Generate a random email"""
    return f"{random_string(8).lower()}@{random_string(5).lower()}.com"


def random_phone() -> str:
    """Generate a random phone number"""
    return f"+1555{random.randint(1000000, 9999999)}"


def random_user_ids(count: int = 5) -> List[str]:
    """Generate multiple random user IDs"""
    return [f"usr_test_{uuid.uuid4().hex[:12]}" for _ in range(count)]


def random_amount(min_val: float = 0.01, max_val: float = 1000.0) -> float:
    """Generate a random monetary amount"""
    return round(random.uniform(min_val, max_val), 2)
