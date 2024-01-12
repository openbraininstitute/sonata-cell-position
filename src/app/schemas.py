"""Schemas and validators definitions."""
import json
from inspect import signature
from pathlib import Path
from typing import Annotated, Any

from fastapi import HTTPException, Query
from pydantic import AfterValidator
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, ValidationError

from app.constants import MODALITIES_REGEX
from app.logger import L
from app.serialize import DEFAULT_SERIALIZER, SERIALIZERS_REGEX
from app.utils import attributes_to_dict, modality_to_attributes


class ValidatedQuery:
    """Callable wrapper that can be used as a Dependency in FastAPI to define query parameters.

    If a ValidationError is raised in the callable, then it's converted to HTTPException.

    See also https://github.com/tiangolo/fastapi/discussions/9071
    Based on https://github.com/tiangolo/fastapi/discussions/9071#discussioncomment-5156636

    Usage:
        params: Annotated[Model, Depends(ValidatedQuery(Model))]
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
            msg = f"Path invalid because not existing: {input_path}"
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


class QueryParams(BaseModel):
    """QueryParams."""

    input_path: CircuitConfigPath
    attributes: list[str]
    population_name: str | None = None
    node_set: str | None = None
    sampling_ratio: Annotated[float, Field(gt=0, le=1)] = 0.01
    seed: Annotated[int, Field(ge=0)] = 0
    how: Annotated[str, Field(pattern=SERIALIZERS_REGEX)] = DEFAULT_SERIALIZER
    use_cache: bool = True
    queries: list[dict[str, Any]] | None = None

    @classmethod
    def from_simplified_params(
        cls,
        input_path: Path,
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
    ):
        # pylint: disable=too-many-arguments
        """Return a new instance from the given simplified parameters instead of queries."""
        attributes = modality_to_attributes(modality)
        query = attributes_to_dict(region=region, mtype=mtype)
        queries = [query] if query else None
        # the common fields are validated when the model is instantiated
        return cls(
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


class DownsampleParams(BaseModel):
    """DownsampleParams."""

    input_path: CircuitConfigPath
    population_name: str | None = None
    sampling_ratio: float = 0.01
    seed: int = 0
