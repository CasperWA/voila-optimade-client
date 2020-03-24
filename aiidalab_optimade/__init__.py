"""
OPTIMADE

AiiDA Lab App that implements an OPTIMADE client
"""
from .query import OptimadeQueryWidget
from .summary import OptimadeSummaryWidget


__all__ = ("OptimadeQueryWidget", "OptimadeSummaryWidget")
__version__ = "3.0.0"
