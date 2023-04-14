import json
from contextlib import contextmanager
from pathlib import Path

TEST_DIR = Path(__file__).parent.resolve()
TEST_DATA_DIR = TEST_DIR / "data"


@contextmanager
def edit_json(json_file, encoding="utf-8"):
    """Context manager within which you can edit a json file.

    Args:
        json_file (Path): path to a json file.
        encoding (str): encoding used to read and write the file.

    Returns:
        Yields a dict instance loaded from `json_file`.
        This instance will be saved after exiting the context manager.
    """
    data = json.loads(json_file.read_text(encoding=encoding))
    try:
        yield data
    finally:
        json_file.write_text(json.dumps(data, indent=2), encoding=encoding)
