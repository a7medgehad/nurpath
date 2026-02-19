from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NurPath API"
    app_version: str = "0.1.0"
    api_prefix: str = "/v1"

    database_url: str = "postgresql+psycopg://nurpath:nurpath@localhost:5432/nurpath"
    source_catalog_path: str = "../data/samples/sources.json"

    default_language: str = "ar"
    confidence_threshold: float = 0.62
    grounding_threshold: float = 0.4
    faithfulness_threshold: float = 0.35
    weak_retrieval_threshold: float = 0.28
    retrieval_vector_weight: float = 0.55
    retrieval_lexical_weight: float = 0.45

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "nurpath_passages"
    qdrant_local_mode: bool = False

    embedding_provider: str = "sentence_transformers"
    embedding_model_name: str = "intfloat/multilingual-e5-large"
    embedding_dimension: int = 1024

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
