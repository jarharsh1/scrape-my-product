#!/usr/bin/env python3
"""
Entry point for running the Product Intelligence Scraper application.
"""

import uvicorn
from app.config import config


def main():
    """Run the application server."""
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()
