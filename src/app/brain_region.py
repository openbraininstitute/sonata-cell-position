"""Brain Region Utilities."""

from pathlib import Path

from app.config import settings
from app.errors import ClientError
from app.utils import ensure_list, load_json


def _region_id_to_int(region_id: str) -> int:
    """Convert a region id to int.

    Example: http://api.brain-map.org/api/v2/data/Structure/8 -> 8
    """
    if match := settings.BRAIN_REGION_ONTOLOGY_ID_PATTERN.match(region_id):
        return int(match.group(1))
    err = f"Invalid region id format: {region_id}"
    raise ClientError(err)


def load_alternative_region_map(path: Path) -> dict:
    """Load a dict from a file containing the json-ld representation of a Brain Region Ontology."""
    data = load_json(path)
    result = {}
    for item in data["defines"]:
        region_id = item["@id"]
        leaves = item.get("hasLayerLeafRegionPart")
        if leaves and not settings.BRAIN_REGION_ONTOLOGY_ID_PATTERN.match(region_id):
            result[region_id] = [_region_id_to_int(leaf_id) for leaf_id in ensure_list(leaves)]
    return result
