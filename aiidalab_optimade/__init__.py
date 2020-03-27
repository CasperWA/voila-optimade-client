"""
OPTIMADE

AiiDA Lab App that implements an OPTIMADE client
"""
from .query_provider import OptimadeQueryProviderWidget
from .query_filter import OptimadeQueryFilterWidget
from .summary import OptimadeSummaryWidget


__all__ = (
    "OptimadeQueryProviderWidget",
    "OptimadeQueryFilterWidget",
    "OptimadeSummaryWidget",
)
__version__ = "3.0.0"
