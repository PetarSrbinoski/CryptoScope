from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query

from ..repositories.symbols_repository import SymbolsRepository
from ..api.dependencies import get_symbols_repo

router = APIRouter()


@router.get("/api/symbols")
def list_symbols(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    q: Optional[str] = Query(None),
    repo: SymbolsRepository = Depends(get_symbols_repo),
):
    return repo.list_symbols(page=page, page_size=page_size, q=q)
