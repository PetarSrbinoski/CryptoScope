from __future__ import annotations

from ..db.connection import get_conn
from ..repositories.prices_repository import PricesRepository
from ..repositories.symbols_repository import SymbolsRepository
from ..services.technical_service import TechnicalAnalysisService


def get_prices_repo() -> PricesRepository:
    return PricesRepository(conn_factory=get_conn)


def get_symbols_repo() -> SymbolsRepository:
    return SymbolsRepository(conn_factory=get_conn)


def get_technical_service() -> TechnicalAnalysisService:
    return TechnicalAnalysisService(prices_repo=get_prices_repo())
