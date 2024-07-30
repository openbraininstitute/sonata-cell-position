"""Configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
    )

    PROJECT_PATH: str = "UNDEFINED"
    COMMIT_SHA: str = "UNDEFINED"

    APP_NAME: str = "cell-service"
    APP_DEBUG: bool = False
    UVICORN_PORT: int = 8010
    ROOT_PATH: str = ""

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    LOG_SERIALIZE: bool = True
    LOG_BACKTRACE: bool = False
    LOG_DIAGNOSE: bool = False
    LOG_ENQUEUE: bool = False
    LOG_CATCH: bool = True
    LOG_STANDARD_LOGGER: dict[str, str] = {"root": "INFO"}

    # maximum sampling ratio considered for caching
    CACHED_SAMPLING_RATIO: float = 0.01

    # Nexus endpoint and bucket can be specified by the user in the request headers.
    # We may want to make them mandatory in the future, and remove the default values below.
    NEXUS_ENDPOINT: str = "https://bbp.epfl.ch/nexus/v1"
    NEXUS_BUCKET: str = "bbp/mmb-point-neuron-framework-model"

    # to support other Nexus endpoints and buckets, the required permissions need to be added here.
    # see https://bbpteam.epfl.ch/project/issues/browse/NSETM-2283?focusedId=234551#comment-234551
    NEXUS_READ_PERMISSIONS: dict[str, dict[str, set[str]]] = {
        "https://sbo-nexus-delta.shapes-registry.org/v1": {  # aws prod
            "bbp/mmb-point-neuron-framework-model": {
                "resources/read",
            },
        },
        "https://bbp.epfl.ch/nexus/v1": {  # k8s prod
            "bbp/mmb-point-neuron-framework-model": {
                "events/read",
                "projects/read",
                "resources/read",
                "views/query",
                "gpfs-proj134/read",
            },
        },
        "https://staging.nise.bbp.epfl.ch/nexus/v1": {  # k8s staging
            "bbp/mmb-point-neuron-framework-model": {
                "events/read",
                # "projects/read",  # not available in staging
                "resources/read",
                "views/query",
                # "gpfs-proj134/read",  # not available in staging
            },
        },
    }
    NEXUS_AUTH_TIMEOUT: float = 10  # in seconds

    LOKY_EXECUTOR_ENABLED: bool = True
    LOKY_EXECUTOR_MAX_WORKERS: int = 4  # maximum number of workers
    # seconds after which idle workers automatically shutdown. any value greater than 2147483
    # (around 24.86 days) would cause OverflowError: timeout is too large
    LOKY_EXECUTOR_TIMEOUT: float = 2**31 // 1000
    LOKY_START_METHOD: str = "loky"

    ENTITY_CACHE_INFO: bool = False  # hits and misses
    ENTITY_CACHE_MAX_SIZE: int = 100  # maximum number of entities to keep in memory
    ENTITY_CACHE_TTL: float = 3600 * 24  # TTL in seconds

    REGION_MAP_CACHE_INFO: bool = False  # hits and misses
    REGION_MAP_CACHE_MAX_SIZE: int = 10  # maximum number of region maps to keep in memory
    REGION_MAP_CACHE_TTL: float = 3600 * 24  # TTL in seconds

    # circuit cache saved to disk (ideally RAM disk)
    CIRCUIT_CACHE_INFO: bool = False  # hits and misses
    CIRCUIT_CACHE_MAX_SIZE_MB: float = 400
    CIRCUIT_CACHE_CHECK_TIMEOUT: float = 600  # in seconds
    CIRCUIT_CACHE_CHECK_INTERVAL: float = 1  # in seconds


settings = Settings()
