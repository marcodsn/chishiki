import os
import time
import numpy as np
import hashlib
import threading
from threading import Lock
from flask import Blueprint, request, jsonify, send_file
import torch
# from app.utils.redis_manager import RedisManager
from app.utils.pg_manager import PostgresManager
from app.utils.misc import calculate_file_hash
from app.models.bge import BGEModel
from app.models._docling import Docling
from app.utils.misc import passages_generator
from app.utils.docs2text import extractors
from config import config
from werkzeug.utils import secure_filename

api_routes = Blueprint("api", __name__)

# redis_manager = RedisManager(
#     host=config.config["redis"]["host"],
#     port=config.config["redis"]["port"],
# )

postgres_manager = PostgresManager(
    host=config.config["postgres"]["host"],
    port=config.config["postgres"]["port"],
    # user=config.config["postgres"]["user"],
    # password=config.config["postgres"]["password"],
    # dbname=config.config["postgres"]["database"],
)

# model = None
# tokenizer = None
# last_model_use_time = 0
# MODEL_TIMEOUT = 600  # Unload models after 10 minutes of inactivity

docling = Docling()

class ModelManager:
    def __init__(self, timeout=600):
        self.model = None
        self.tokenizer = None
        self.last_use_time = 0
        self.timeout = timeout
        self.lock = Lock()
        self._start_monitor()

    def _start_monitor(self):
        def monitor_model_usage():
            while True:
                time.sleep(60)  # Check every minute
                self.auto_unload()

        self.monitor_thread = threading.Thread(target=monitor_model_usage, daemon=True)
        self.monitor_thread.start()

    def load_model(self):
        if self.model is None and config.config["ml_services"]["use_bge"]:
            self.model = BGEModel()
            self.tokenizer = self.model.tokenizer
        self.last_use_time = time.time()
        return self.model, self.tokenizer

    def auto_unload(self):
        with self.lock:
            if self.model and time.time() - self.last_use_time > self.timeout:
                self.model = None
                self.tokenizer = None
                print("Model unloaded due to inactivity")

    def get_model(self):
        print("Getting model")
        with self.lock:
            self.load_model()
            return self.model, self.tokenizer

model_manager = ModelManager(timeout=600) # Unload models after 10 minutes of inactivity


# def load_model():
#     global model, tokenizer, last_model_use_time
#     if config.config["ml_services"]["use_bge"]:
#         model = BGEModel()
#         tokenizer = model.tokenizer
#         last_model_use_time = time.time()


# def unload_model():
#     global model, tokenizer
#     model = None
#     tokenizer = None


# def auto_unload_models():
#     global last_model_use_time
#     current_time = time.time()
#     if model and current_time - last_model_use_time > MODEL_TIMEOUT:
#         unload_model()


def generate_passage_id(dense_vector, doc_path):
    dense_str = ",".join(str(x) for x in dense_vector)
    passage_id = hashlib.md5((dense_str + doc_path).encode()).hexdigest()
    return passage_id


# @api_routes.route("/create_index", methods=["POST"])
# def create_index():
#     # redis_manager.create_index()
#     postgres_manager.create_index()
#     return jsonify({"message": "Index created successfully"})


# @api_routes.route("/flush_datastore", methods=["POST"])
# def flush_datastore():
#     redis_manager.flush_datastore()
#     return jsonify({"message": "Datastore flushed successfully"})


# @api_routes.route("/save_datastore", methods=["POST"])
# def save_datastore():
#     redis_manager.save_datastore()
#     return jsonify({"message": "Datastore saved successfully"})


@api_routes.route("/insert_passage", methods=["POST"])
def insert_passage():
    data = request.get_json()
    doc_path = data["doc_path"]
    start_pos = data["start_pos"]
    end_pos = data["end_pos"]
    window_size = data["window_size"]
    file_hash = calculate_file_hash(doc_path)
    filename = os.path.basename(doc_path)

    model, tokenizer = model_manager.get_model()
    if model is None:
        return (
            jsonify(
                {"error": 'ML service not enabled, set "use_bge" to True to enable'}
            ),
            500,
        )

    # # Update the last usage time
    # global last_model_use_time
    # last_model_use_time = time.time()

    text = postgres_manager.get_doc_text(doc_path)[start_pos:end_pos]
    tokenized = tokenizer(text, return_tensors="pt")
    ids, mask = tokenized["input_ids"][0], tokenized["attention_mask"][0]

    encoded = model.encode(
        [(ids, mask)], return_dense=True, return_sparse=True, return_colbert_vecs=False
    )
    dense_vector = encoded["dense_vecs"][0]
    passage_id = generate_passage_id(dense_vector, doc_path)
    lexical_weights = encoded["lexical_weights"][0]

    postgres_manager.insert_passage(
        passage_id,
        doc_path,
        file_hash,
        filename,
        dense_vector,
        lexical_weights,
        start_pos,
        end_pos,
        window_size,
    )
    return jsonify({"message": "Passage inserted successfully"})


@api_routes.route("/insert_documents", methods=["POST"])
def insert_documents():
    data = request.get_json()
    doc_paths = data["doc_paths"]
    window_sizes = data.get("window_sizes", [512])
    stride = data.get("stride", 0.75)

    for doc_path in doc_paths:
        file_hash = calculate_file_hash(doc_path)
        filename = os.path.basename(doc_path)
        file_extension = (
            os.path.splitext(filename)[1][1:] if "." in filename else filename
        )
        # UNIX timestamps
        creation_time = os.path.getctime(doc_path)
        modification_time = os.path.getmtime(doc_path)
        size = os.path.getsize(doc_path)

        postgres_manager.insert_metadata(
            doc_path,
            file_hash,
            filename,
            file_extension,
            creation_time,
            modification_time,
            size,
        )

        model, tokenizer = model_manager.get_model()
        if model is None:
            postgres_manager.update_doc_ml_synced(doc_path, False)
            return (
                jsonify(
                    {"error": 'ML service not enabled, set "use_bge" to True to enable'}
                ),
                500,
            )

        if doc_path.split(".")[-1] not in extractors:
            postgres_manager.update_doc_ml_synced(doc_path, False)
            print(f"Document {doc_path} not supported")
            continue

        if docling and doc_path.split(".")[-1] == "pdf":
            text = extractors[doc_path.split(".")[-1]](doc_path, docling)
        else:
            text = extractors[doc_path.split(".")[-1]](doc_path, docling)

        postgres_manager.set_doc_text(doc_path, text)

        all_dense_vectors = []

        for window_size in window_sizes:
            passage_generator = passages_generator(
                text, tokenizer, window_size=window_size, stride=stride
            )
            for i, (passage_ids, passage_mask, start_pos, end_pos) in enumerate(
                passage_generator
            ):
                print(f"Inserting passage {i + 1} with window size {window_size}")
                with torch.no_grad():
                    encoding = model.encode(
                        [(passage_ids, passage_mask)],
                        return_dense=True,
                        return_sparse=True,
                    )
                    dense_vector, lexical_weights = (
                        encoding["dense_vecs"][0],
                        encoding["lexical_weights"][0],
                    )
                all_dense_vectors.append(dense_vector)
                passage_id = generate_passage_id(dense_vector, doc_path)
                postgres_manager.insert_passage(
                    passage_id,
                    doc_path,
                    file_hash,
                    filename,
                    dense_vector,
                    lexical_weights,
                    start_pos,
                    end_pos,
                    window_size,
                )

        mean_dense_vector = np.mean(all_dense_vectors, axis=0)
        postgres_manager.insert_mean_dense_vector(doc_path, mean_dense_vector)

        postgres_manager.update_doc_ml_synced(doc_path, True)

    return jsonify({"message": "Documents inserted successfully"})


@api_routes.route("/delete_documents", methods=["POST"])
def delete_documents():
    data = request.get_json()
    doc_paths = data.get("doc_paths", [])

    if not doc_paths:
        return jsonify({"error": "Missing 'doc_paths' parameter"}), 400

    for doc_path in doc_paths:
        postgres_manager.delete_doc(doc_path)

    return jsonify({"message": f"Documents deleted successfully"})


@api_routes.route("/search", methods=["POST"])
def search():
    data = request.get_json()

    if "query" not in data or not data["query"] or data["query"].strip() == "":
        return jsonify({"error": "Missing 'query' parameter"}), 400

    query = data["query"]
    tags = data.get("tags", [])
    path = data.get("path", None)
    filename = data.get("filename", None)
    window_size = data.get("window_size", 512)
    dense_weight = data.get("dense_weight", 0.7)
    sparse_weight = data.get("sparse_weight", None)
    k = data.get("k", 30)
    size_filter = data.get("size_filter", None)

    model, tokenizer = model_manager.get_model()
    if model is None:
        return (
            jsonify(
                {"error": 'ML service not enabled, set "use_bge" to True to enable'}
            ),
            500,
        )

    # # Update the last usage time
    # global last_model_use_time
    # last_model_use_time = time.time()

    tokenized = tokenizer(query, return_tensors="pt")
    query_ids, query_mask = tokenized["input_ids"][0], tokenized["attention_mask"][0]

    with torch.no_grad():
        encoding = model.encode(
            [(query_ids, query_mask)], return_dense=True, return_sparse=True
        )
        query_dense_vector, query_lexical_weights = (
            encoding["dense_vecs"][0],
            encoding["lexical_weights"][0],
        )

    search_results = postgres_manager.ml_search(
        query_dense_vector,
        query_lexical_weights,
        tags=tags,
        path=path,
        filename=filename,
        window_size=window_size,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
        k=k,
        # size_filter=size_filter,
    )

    passages = []
    for (doc_path, start_pos, end_pos), scores in search_results:
        doc_text = postgres_manager.get_doc_text(doc_path)
        passage_text = doc_text[int(start_pos) : int(end_pos)]
        passages.append(
            {
                "text": passage_text,
                "doc_path": doc_path,
                "start_pos": start_pos,
                "end_pos": end_pos,
                "scores": scores,
            }
        )

    # filter only passages with path in the doc_path, remove after fixing metadata_search
    # if path:
    #     passages = [
    #         passage for passage in passages if passage["doc_path"].startswith(path)
    #     ]

    return jsonify({"passages": passages})


@api_routes.route("/search_similar_docs", methods=["POST"])
def search_similar_docs():
    data = request.get_json()
    doc_path = data["doc_path"]
    k = data.get("k", 10)
    threshold = data.get("threshold", 0.3)

    mean_dense_vector = postgres_manager.get_mean_dense_vector(doc_path)
    if mean_dense_vector is None:
        return (
            jsonify({"error": "Mean dense vector not found for the given document"}),
            404,
        )

    similar_docs = postgres_manager.search_similar_docs(mean_dense_vector, k, threshold)
    return jsonify({"similar_docs": similar_docs})


@api_routes.route("/get_doc_text", methods=["GET"])
def get_doc_text():
    doc_path = request.args.get("doc_path")
    doc_text = postgres_manager.get_doc_text(doc_path)
    if doc_text:
        return jsonify({"doc_text": doc_text})
    else:
        return jsonify({"error": "Document text not found"}), 404


@api_routes.route("/get_ml_synced", methods=["GET"])
def get_ml_synced():
    doc_path = request.args.get("doc_path")
    ml_synced = postgres_manager.get_doc_ml_synced(doc_path)
    if ml_synced:
        return jsonify({"ml_synced": ml_synced})
    else:
        return jsonify({"error": "Document ml_synced not found"}), 404


@api_routes.route("/update_ml_synced", methods=["POST"])
def update_ml_synced():
    data = request.get_json()
    doc_path = data.get("doc_path")
    ml_synced = data.get("ml_synced")

    if not doc_path:
        return jsonify({"error": "Missing 'doc_path' parameter"}), 400
    if ml_synced is None:
        return jsonify({"error": "Missing 'ml_synced' parameter"}), 400

    postgres_manager.update_doc_ml_synced(doc_path, ml_synced)
    return jsonify(
        {"message": "ML synced status updated successfully", "ml_synced": ml_synced}
    )


@api_routes.route("/get_doc_metadata", methods=["GET"])
def get_doc_metadata():
    doc_path = request.args.get("doc_path")
    doc_metadata = postgres_manager.get_doc_metadata(doc_path)
    if doc_metadata:
        return jsonify(doc_metadata)
    else:
        return jsonify({"error": "Document metadata not found"}), 404


@api_routes.route("/search_by_metadata", methods=["POST"])
def search_by_metadata():
    data = request.get_json()
    tags = data.get("tags", [])
    path = data.get("path", None)
    filename = data.get("filename", None)
    size_filter = data.get("size_filter", None)

    doc_paths = postgres_manager.search_by_metadata(
        tags=tags, path=path, filename=filename, size_filter=size_filter
    )
    return jsonify({"doc_paths": doc_paths})


@api_routes.route("/delete_doc", methods=["POST"])
def delete_doc():
    data = request.get_json()
    doc_path = data["doc_path"]
    postgres_manager.delete_doc(doc_path)
    return jsonify({"message": f"Document '{doc_path}' deleted successfully"})


@api_routes.route("/upload_file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(config.config["file_storage"]["upload_dir"], filename)
    file.save(file_path)

    return jsonify({"message": f"File '{filename}' uploaded successfully"})


@api_routes.route("/download_file", methods=["GET"])
def download_file():
    doc_path = request.args.get("doc_path")
    if not os.path.isfile(doc_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(doc_path, as_attachment=True, mimetype="application/octet-stream")


@api_routes.route("/get_doc_tags", methods=["GET"])
def get_doc_tags():
    doc_path = request.args.get("doc_path")
    if not doc_path:
        return jsonify({"error": "Missing 'doc_path' parameter"}), 400

    tags = postgres_manager.get_doc_tags(doc_path)
    if tags is not None:
        return jsonify({"tags": tags})
    else:
        return jsonify({"error": "Tags not found for the given document"}), 404


@api_routes.route("/update_doc_tags", methods=["POST"])
def update_doc_tags():
    data = request.get_json()
    doc_path = data.get("doc_path")
    new_tags = data.get("tags", [])

    if not doc_path:
        return jsonify({"error": "Missing 'doc_path' parameter"}), 400
    if not new_tags:
        return jsonify({"error": "Missing 'tags' parameter"}), 400

    postgres_manager.update_doc_tags(doc_path, new_tags)
    return jsonify({"message": "Tags updated successfully", "tags": new_tags})


@api_routes.route("/add_doc_tags", methods=["POST"])
def add_doc_tags():
    data = request.get_json()
    doc_path = data.get("doc_path")
    new_tags = data.get("tags", [])

    if not doc_path:
        return jsonify({"error": "Missing 'doc_path' parameter"}), 400
    if not new_tags:
        return jsonify({"error": "Missing 'tags' parameter"}), 400

    current_tags = postgres_manager.get_doc_tags(doc_path)
    if current_tags is None:
        return jsonify({"error": "Document not found"}), 404

    updated_tags = list(set(current_tags + new_tags))
    postgres_manager.update_doc_tags(doc_path, updated_tags)
    return jsonify({"message": "Tags added successfully", "tags": updated_tags})


@api_routes.route("/remove_doc_tags", methods=["POST"])
def remove_doc_tags():
    data = request.get_json()
    doc_path = data.get("doc_path")
    tags_to_remove = data.get("tags", [])

    if not doc_path:
        return jsonify({"error": "Missing 'doc_path' parameter"}), 400
    if not tags_to_remove:
        return jsonify({"error": "Missing 'tags' parameter"}), 400

    current_tags = postgres_manager.get_doc_tags(doc_path)
    if current_tags is None:
        return jsonify({"error": "Document not found"}), 404

    updated_tags = [tag for tag in current_tags if tag not in tags_to_remove]
    postgres_manager.update_doc_tags(doc_path, updated_tags)
    return jsonify({"message": "Tags removed successfully", "tags": updated_tags})
