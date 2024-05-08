import os
import sys
import threading
import requests
import time
from app.api import create_app
from app.utils.boot_sync import sync_on_boot
from app.utils.watchdog_sync import run_watchdog
from config import config


def run_app():
    app = create_app()
    app.run(
        host=config.config["backend"]["host"],
        port=config.config["backend"]["port"],
        debug=config.config["backend"]["debug"],
    )


def main():
    if len(sys.argv) < 2:
        print("Please provide a default docs_path as a command-line argument.")
        sys.exit(1)

    docs_path = sys.argv[1]  # Path to the directory containing the documents

    # Start the Flask app in a separate thread
    app_thread = threading.Thread(target=run_app)
    app_thread.daemon = True
    app_thread.start()
    print("Flask app started.")

    # Wait for the Flask app to start
    time.sleep(5)  # Adjust the delay as needed

    # Try creating index
    try:
        requests.post(
            f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/create_index"
        )
    except Exception as e:
        print(f"Error creating index: {e}")

    # Perform boot-time sync
    sync_on_boot(docs_path)
    print("Boot-time sync complete.")

    # Start the watchdog in a separate thread
    watchdog_thread = threading.Thread(target=run_watchdog, args=(docs_path,))
    watchdog_thread.daemon = True
    watchdog_thread.start()
    print("Watchdog thread started.")

    # Wait for the Flask app thread to complete
    app_thread.join()


if __name__ == "__main__":
    main()
