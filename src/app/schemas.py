"""Schemas and validators definitions."""

import hashlib
import json
from inspect import signature
from pathlib import Path
from typing import Annotated, Any

from fastapi import Header, HTTPException, Query
from pydantic import AfterValidator
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, ValidationError, model_validator
from voxcell import RegionMap

from app.constants import MODALITIES_REGEX, NEXUS_BUCKET, NEXUS_ENDPOINT
from app.logger import L
from app.serialize import DEFAULT_SERIALIZER, SERIALIZERS_REGEX
from app.utils import attributes_to_dict, modality_to_attributes


class ValidatedParams:
    """Callable wrapper that can be used as a Dependency in FastAPI to define query parameters.

    If a ValidationError is raised in the callable, then it's converted to HTTPException.

    See also https://github.com/tiangolo/fastapi/discussions/9071
    Based on https://github.com/tiangolo/fastapi/discussions/9071#discussioncomment-5156636

    Usage:
        params: Annotated[Model, Depends(ValidatedParams(Model))]
    or
        params: Annotated[Model, Depends(ValidatedParams(Model.from_params))]
    or
        params: Annotated[Model, Depends(Model.from_params)]
        and decorate the class method `from_params` with @ValidatedParams
    """

    def __init__(self, callable_obj):
        """Init the wrapper with the given callable_obj."""
        self._callable = callable_obj
        self.__signature__ = signature(callable_obj)

    def __call__(self, *args, **kwargs):
        """Call the wrapped callable."""
        signature(self.__call__).bind(*args, **kwargs)
        try:
            return self._callable(*args, **kwargs)
        except ValidationError as e:
            # ensure that all the values are JSON serializable
            errors = json.loads(e.json())
            for error in errors:
                error["loc"] = ("query", *error["loc"])
            raise HTTPException(422, detail=errors) from None


class PathValidator:
    """Validator for paths."""

    def __init__(self, allowed_extensions: set[str] | None = None) -> None:
        """Init the wrapper with the allowed extensions.

        Args:
            allowed_extensions: allowed path extensions. If empty or None, any extension is allowed.
        """
        self._allowed_extensions = {self._format_ext(ext) for ext in allowed_extensions or {}}

    @staticmethod
    def _format_ext(ext: str) -> str:
        """Ensure that the extension starts with a dot."""
        return ext if ext.startswith(".") else f".{ext}"

    def __call__(self, input_path: Path) -> Path:
        """Validate the path."""
        if self._allowed_extensions and input_path.suffix not in self._allowed_extensions:
            msg = f"Path invalid because of the extension: {input_path}"
            L.warning(msg)
            raise ValueError(msg)
        if not input_path.exists():
            msg = f"Path invalid because non existent: {input_path}"
            L.warning(msg)
            raise ValueError(msg)
        return input_path


# Validated path to circuit config
CircuitConfigPath = Annotated[Path, AfterValidator(PathValidator({".json"})), Query()]


class BaseModel(PydanticBaseModel):
    """Custom BaseModel."""

    model_config = {
        "extra": "forbid",
    }


class FrozenBaseModel(PydanticBaseModel):
    """Frozen BaseModel."""

    model_config = BaseModel.model_config | {
        "frozen": True,
    }


class NexusConfig(BaseModel):
    """Nexus configuration."""

    endpoint: str = NEXUS_ENDPOINT
    bucket: str = NEXUS_BUCKET
    token: str | None = None

    @property
    def org(self):
        """Return Nexus organization."""
        return self.bucket.partition("/")[0]

    @property
    def project(self):
        """Return Nexus project."""
        return self.bucket.partition("/")[2]

    @classmethod
    @ValidatedParams
    def from_params(
        cls,
        nexus_token: Annotated[str | None, Header()] = None,
    ) -> "NexusConfig":
        """Return a new instance from the given parameters."""
        return cls(token=nexus_token)


class CircuitRef(FrozenBaseModel):
    """Circuit reference, having only one of id and path."""

    id: str | None = None  # Nexus ID
    path: CircuitConfigPath | None = None  # Path to the circuit config

    @model_validator(mode="after")
    def check_id_and_path_are_exclusive(self) -> "CircuitRef":
        """Check that the model is initialized with exactly one of circuit id and path."""
        if not self.id and not self.path:
            raise ValueError("circuit id or path must be specified")
        if self.id and self.path:
            raise ValueError("circuit id and path cannot be specified at the same time")
        return self

    @classmethod
    @ValidatedParams
    def from_params(
        cls,
        circuit_id: str | None = None,
        input_path: CircuitConfigPath | None = None,
    ) -> "CircuitRef":
        """Return a new instance from the given parameters."""
        return CircuitRef(id=circuit_id, path=input_path)


class QueryParams(BaseModel):
    """QueryParams."""

    circuit_id: str | None = None
    input_path: CircuitConfigPath | None = None
    attributes: list[str]
    population_name: str | None = None
    node_set: str | None = None
    sampling_ratio: Annotated[float, Field(gt=0, le=1)] = 0.01
    seed: Annotated[int, Field(ge=0)] = 0
    how: Annotated[str, Field(pattern=SERIALIZERS_REGEX)] = DEFAULT_SERIALIZER
    use_cache: bool = True
    queries: list[dict[str, Any]] | None = None

    @classmethod
    @ValidatedParams
    def from_simplified_params(
        cls,
        circuit_id: str | None = None,
        input_path: Path | None = None,
        region: Annotated[list[str] | None, Query()] = None,
        mtype: Annotated[list[str] | None, Query()] = None,
        modality: Annotated[
            list[Annotated[str, Query(pattern=MODALITIES_REGEX)]] | None, Query()
        ] = None,
        population_name: str | None = None,
        node_set: str | None = None,
        sampling_ratio: float = 0.01,
        seed: int = 0,
        how: str = DEFAULT_SERIALIZER,
        use_cache: bool = True,
    ) -> "QueryParams":
        # pylint: disable=too-many-arguments
        """Return a new instance from the given simplified parameters instead of queries."""
        attributes = modality_to_attributes(modality)
        query = attributes_to_dict(region=region, mtype=mtype)
        queries = [query] if query else None
        # the common fields are validated when the model is instantiated
        return cls(
            circuit_id=circuit_id,
            input_path=input_path,
            attributes=attributes,
            population_name=population_name,
            node_set=node_set,
            sampling_ratio=sampling_ratio,
            seed=seed,
            how=how,
            use_cache=use_cache,
            queries=queries,
        )


class SampleParams(BaseModel):
    """SampleParams."""

    circuit_id: str | None = None
    input_path: CircuitConfigPath | None = None
    population_name: str | None = None
    sampling_ratio: float = 0.01
    seed: int = 0


class CircuitCacheKey(FrozenBaseModel):
    """Parameters to be considered as cache key.

    All the attributes need to be hashable.
    """

    circuit_id: str | None  # it can be None when the Nexus id has not been specified
    circuit_config_path: CircuitConfigPath
    population_name: str
    attributes: tuple[str, ...]
    sampling_ratio: float
    seed: int

    def to_json(self) -> str:
        """Return a json representation of the object."""
        return self.model_dump_json()

    def checksum(self) -> str:
        """Calculate the checksum of the object."""
        content = self.to_json()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_file(self, path: Path | str) -> None:
        """Save the current instance to file."""
        content = self.to_json()
        Path(path).write_text(content, encoding="utf-8")


class CircuitCachePaths(FrozenBaseModel):
    """Collection of paths used for cached sampled circuits."""

    base: Path

    @property
    def circuit_config(self):
        """Return the circuit config file path."""
        return self.base / "circuit_config.json"

    @property
    def nodes(self):
        """Return the nodes file path."""
        return self.base / "nodes.h5"

    @property
    def node_sets(self):
        """Return the node_sets file path."""
        return self.base / "node_sets.json"

    @property
    def metadata(self):
        """Return the metadata file path."""
        return self.base / "metadata.json"

    @property
    def id_mapping(self):
        """Return the id_mapping file path, containing the mapping between old and new node ids."""
        return self.base / "id_mapping.json"

    @property
    def ok(self):
        """Return the OK file path."""
        return self.base / "OK"


class CircuitParams(FrozenBaseModel):
    """Parameters needed to load and work with a sampled circuit."""

    model_config = FrozenBaseModel.model_config | {
        "arbitrary_types_allowed": True,  # needed for RegionMap
    }

    key: CircuitCacheKey
    region_map: RegionMap
