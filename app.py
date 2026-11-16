#!/usr/bin/env python3
import os

from app import create_app  # noqa: EXE001

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=app.config["DEBUG"],
        threaded=True,
    )
