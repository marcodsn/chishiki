import time
import requests
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import config


def calculate_file_hash(file_path):
    with open(file_path, "rb") as file:
        file_hash = hashlib.md5(file.read()).hexdigest()
    return file_hash


class DocumentWatchdog(FileSystemEventHandler):
    def __init__(self, docs_path):
        self.docs_path = docs_path

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(tuple(config.config["extensions"])):
            print(f"WATCHDOG: Document {event.src_path} created.")
            self.process_document(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(tuple(config.config["extensions"])):
            print(f"WATCHDOG: Document {event.src_path} modified.")
            self.process_document(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith(tuple(config.config["extensions"])):
            print(f"WATCHDOG: Document {event.src_path} deleted.")
            self.delete_document(event.src_path)

    def process_document(self, doc_path):
        response = requests.post(
            f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/insert_documents",
            json={"doc_paths": [doc_path]},
        )
        if response.status_code == 200:
            print(f"Document {doc_path} processed successfully.")
        else:
            print(f"Error processing document {doc_path}: {response.json()}")

    def delete_document(self, doc_path):
        response = requests.post(
            f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/delete_documents",
            json={"doc_path": doc_path},
        )
        if response.status_code == 200:
            print(f"Document {doc_path} removed from the datastore.")
        else:
            print(f"Error removing document {doc_path} from the datastore: {response.json()}")


def run_watchdog(docs_path):
    event_handler = DocumentWatchdog(docs_path)
    observer = Observer()
    observer.schedule(event_handler, path=docs_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
