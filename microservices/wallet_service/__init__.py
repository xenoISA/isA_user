"""
Wallet Service Package
"""

from .wallet_service import WalletService
from .models import *  # noqa: F401,F403  # re-export public model surface

__all__ = ['WalletService']
