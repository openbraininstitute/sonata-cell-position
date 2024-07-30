"""Main entry point."""

import uvicorn

from app.config import settings
from app.logger import configure_logging

if __name__ == "__main__":
    configure_logging()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.UVICORN_PORT,
        proxy_headers=True,
        log_config=None,
    )
