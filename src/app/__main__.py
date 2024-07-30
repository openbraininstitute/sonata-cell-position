"""Main entry point."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8010,
        proxy_headers=True,
        log_config="/code/logging.yaml",
    )
