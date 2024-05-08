import os
import requests
import hashlib
from config import config


def calculate_file_hash(file_path):
    with open(file_path, "rb") as file:
        file_hash = hashlib.md5(file.read()).hexdigest()
    return file_hash


def sync_on_boot(docs_path):
    # Get the list of documents in the docs_path directory
    docs_in_filesystem = []
    for root, _, files in os.walk(docs_path):
        for file in files:
            if file.endswith(tuple(config.config["extensions"])):
                docs_in_filesystem.append(os.path.join(root, file))  # Absolute path
    print(f"Found {len(docs_in_filesystem)} documents in {docs_path}.")

    # Get the list of documents in the datastore
    payload = {"tags": [], "path": "", "filename": ""}
    response = requests.post(
        f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/search_by_metadata",
        json=payload,
    )
    if response.status_code == 200:
        docs_in_datastore = response.json()["doc_paths"]
        # docs_in_datastore = list(set(docs_in_datastore))
        print(f"Found {len(docs_in_datastore)} documents in the datastore.")
    else:
        print(
            f"Error retrieving document paths from the datastore: {response.status_code}"
        )
        return

    # Sync documents
    docs_to_insert = []
    docs_to_update = []
    for doc_path in docs_in_filesystem:
        file_hash = calculate_file_hash(doc_path)

        # Check if the document exists in the datastore and get its metadata
        response = requests.get(
            f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/get_doc_metadata",
            params={"doc_path": doc_path},
        )

        if response.status_code == 200:
            stored_doc = response.json()
            stored_hash = stored_doc.get("file_hash")
            ml_synced = stored_doc.get("ml_synced")
        else:
            stored_doc = None
            stored_hash = None
            ml_synced = None

        if stored_doc is None:
            docs_to_insert.append(doc_path)
        elif stored_hash != file_hash or ml_synced == "false":
            docs_to_update.append(doc_path)
        else:
            print(f"Document {doc_path} already exists and is fully indexed.")

    # Insert new documents
    if docs_to_insert:
        response = requests.post(
            f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/insert_documents",
            json={
                "doc_paths": docs_to_insert,
                "window_sizes": config.config["windows"],
            },
        )
        if response.status_code == 200:
            print(f"Inserted {len(docs_to_insert)} new documents.")
        else:
            print(f"Error inserting new documents: {response.status_code}")

    # Update existing documents
    if docs_to_update:
        response = requests.post(
            f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/insert_documents",
            json={
                "doc_paths": docs_to_update,
                "window_sizes": config.config["windows"],
            },
        )
        if response.status_code == 200:
            print(f"Updated {len(docs_to_update)} existing documents.")
        else:
            print(f"Error updating existing documents: {response.status_code}")

    # Remove documents from the datastore that no longer exist in the file system
    docs_to_remove = []
    for doc_path in docs_in_datastore:
        if doc_path not in docs_in_filesystem:
            docs_to_remove.append(doc_path)

    for window_size in config.config["windows"]:
        if docs_to_remove:
            response = requests.post(
                f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/delete_documents",
                json={"doc_paths": docs_to_remove, "window_size": window_size},
            )
            if response.status_code == 200:
                print(f"Removed {len(docs_to_remove)} documents from the datastore.")
            else:
                print(
                    f"Error removing documents from the datastore: {response.status_code}"
                )

    # Save the datastore
    response = requests.post(
        f"http://{config.config['backend']['host']}:{config.config['backend']['port']}/save_datastore"
    )
    if response.status_code == 200:
        print("Datastore saved successfully.")
    else:
        print(f"Error saving datastore: {response.json()}")
