"""Configuration."""

import re

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
    )

    APP_NAME: str = "cell-service"
    APP_VERSION: str | None = None
    COMMIT_SHA: str = "UNDEFINED"
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

    # to support other Nexus endpoints and buckets, the required permissions need to be added here.
    # see https://bbpteam.epfl.ch/project/issues/browse/NSETM-2283?focusedId=234551#comment-234551
    NEXUS_READ_PERMISSIONS: dict[str, dict[str, set[str]]] = {
        "https://openbluebrain.com/api/nexus/v1": {  # aws prod openbluebrain
            "bbp/mmb-point-neuron-framework-model": {"resources/read"},
        },
        "https://www.openbraininstitute.com/api/nexus/v1": {  # aws prod openbraininstitute
            "bbp/mmb-point-neuron-framework-model": {"resources/read"},
        },
        "https://staging.openbluebrain.com/api/nexus/v1": {  # aws staging openbluebrain
            "bbp/mmb-point-neuron-framework-model": {"resources/read"},
        },
        "https://staging.openbraininstitute.org/api/nexus/v1": {  # aws staging openbraininstitute
            "bbp/mmb-point-neuron-framework-model": {"resources/read"},
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

    # alternative hierarchy view
    ALTERNATIVE_REGION_MAP_CACHE_INFO: bool = False  # hits and misses
    ALTERNATIVE_REGION_MAP_CACHE_MAX_SIZE: int = 10  # max number of region maps to keep in memory
    ALTERNATIVE_REGION_MAP_CACHE_TTL: float = 3600 * 24  # TTL in seconds

    # The tag should match NEXT_PUBLIC_BRAIN_REGION_ONTOLOGY_RESOURCE_TAG in deploy-aws-prod in
    # https://bbpgitlab.epfl.ch/project/sbo/core-web-app/-/blob/develop/.gitlab-ci.yml
    # It will be possible to remove this parameter if/when it can be obtained in other ways, e.g:
    # - from the circuit resource in Nexus, or
    # - from the frontend when the circuit endpoint is called
    BRAIN_REGION_ONTOLOGY_RESOURCE_ID: str = (
        "http://bbp.epfl.ch/neurosciencegraph/ontologies/core/brainregion?tag=v2.0.0"
    )
    BRAIN_REGION_ONTOLOGY_ID_PATTERN: re.Pattern = re.compile(r"https?://.*/Structure/(\d+)$")


settings = Settings()
