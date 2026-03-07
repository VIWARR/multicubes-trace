"""Adapters for loading from various sources"""

from .base import DataSourceAdapter
from .dataframe_adapter import DataFrameAdapter

__all__ = [
    'DataFrameAdapter'
]