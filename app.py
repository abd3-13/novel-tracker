#!/usr/bin/env python3
from app import create_app  # noqa: EXE001

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
