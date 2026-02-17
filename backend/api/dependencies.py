from functools import lru_cache
from backend.services.llm_service import LLMService
from backend.services.market_data_service import MarketDataService
from backend.services.db_service import DBService
from backend.pipeline.orchestrator import ValuationPipeline


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()


@lru_cache
def get_market_data_service() -> MarketDataService:
    return MarketDataService()


@lru_cache
def get_db_service() -> DBService:
    return DBService()


def get_pipeline() -> ValuationPipeline:
    return ValuationPipeline(
        llm=get_llm_service(),
        market=get_market_data_service(),
        db=get_db_service(),
    )
