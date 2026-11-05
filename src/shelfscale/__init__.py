"""ShelfScale Open: provenance-first food nutrition data engine."""

from .npm import NPMResult, calculate_npm
from .service import assess_bulk, assess_product

__all__ = ["NPMResult", "calculate_npm", "assess_product", "assess_bulk"]
__version__ = "0.1.0"
