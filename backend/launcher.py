import threading

import uvicorn
import webview

from app.main import app


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()

    webview.create_window(
        "TaskFlow",
        "http://127.0.0.1:8000",
        width=1100,
        height=750,
        min_size=(700, 500),
    )
    webview.start()
