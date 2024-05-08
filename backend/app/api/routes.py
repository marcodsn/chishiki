import os
import time
import hashlib
from flask import Blueprint, request, jsonify, send_file
import torch
from app.utils.redis_manager import RedisManager
from app.models.bge import BGEModel
from app.models.nougat import Nougat
from app.utils.misc import passages_generator
from app.utils.docs2text import extractors
from config import config
from werkzeug.utils import secure_filename

api_routes = Blueprint("api", __name__)

redis_manager = RedisManager(
    host=config.config["redis"]["host"],
    port=config.config["redis"]["port"],
)

model = None
tokenizer = None
last_model_use_time = 0

nougat = None
last_nougat_use_time = 0


def load_model():
    global model, tokenizer, last_model_use_time
    if config.config["ml_services"]["use_bge"]:
        model = BGEModel()
        tokenizer = model.tokenizer
        last_model_use_time = time.time()


def load_nougat():
    global nougat, last_nougat_use_time
    if config.config["ml_services"]["use_nougat"]:
        nougat = Nougat()
        last_nougat_use_time = time.time()


def unload_model():
    global model, tokenizer
    model = None
    tokenizer = None


def generate_passage_id(dense_vector, doc_path):
    dense_str = ",".join(str(x) for x in dense_vector)
    passage_id = hashlib.md5((dense_str + doc_path).encode()).hexdigest()
    return passage_id


def calculate_file_hash(file_path):
    with open(file_path, "rb") as file:
        file_hash = hashlib.md5(file.read()).hexdigest()
    return file_hash


@api_routes.route("/create_index", methods=["POST"])
def create_index():
    redis_manager.create_index()
    return jsonify({"message": "Index created successfully"})


@api_routes.route("/flush_datastore", methods=["POST"])
def flush_datastore():
    redis_manager.flush_datastore()
    return jsonify({"message": "Datastore flushed successfully"})


@api_routes.route("/save_datastore", methods=["POST"])
def save_datastore():
    redis_manager.save_datastore()
    return jsonify({"message": "Datastore saved successfully"})


@api_routes.route("/insert_passage", methods=["POST"])
def insert_passage():
    data = request.get_json()
    doc_path = data["doc_path"]
    start_pos = data["start_pos"]
    end_pos = data["end_pos"]
    window_size = data["window_size"]
    file_hash = calculate_file_hash(doc_path)
    filename = os.path.basename(doc_path)

    if model is None:
        load_model()
    if model is None:
        return (
            jsonify(
                {"error": 'ML service not enabled, set "use_bge" to True to enable'}
            ),
            500,
        )

    text = redis_manager.get_doc_text(doc_path)[start_pos:end_pos]
    tokenized = tokenizer(text, return_tensors="pt")
    ids, mask = tokenized["input_ids"][0], tokenized["attention_mask"][0]

    encoded = model.encode(
        [(ids, mask)], return_dense=True, return_sparse=True, return_colbert_vecs=False
    )
    dense_vector = encoded["dense_vecs"][0]
    passage_id = generate_passage_id(dense_vector, doc_path)
    lexical_weights = encoded["lexical_weights"][0]

    redis_manager.insert_passage(
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
        creation_time = os.path.getctime(doc_path)
        modification_time = os.path.getmtime(doc_path)
        size = os.path.getsize(doc_path)

        redis_manager.insert_metadata(
            doc_path,
            file_hash,
            filename,
            file_extension,
            creation_time,
            modification_time,
            size,
        )

        if model is None:
            load_model()
        if model is None:
            redis_manager.update_doc_ml_synced(doc_path, "false")
            print(
                "ML service not enabled, skipping document. Set 'use_bge' to True to enable."
            )
            continue
        if nougat is None:
            load_nougat()

        if doc_path.split(".")[-1] not in extractors:
            redis_manager.update_doc_ml_synced(doc_path, "false")
            print(f"Document {doc_path} not supported")
            continue

        if nougat and doc_path.split(".")[-1] == "pdf":
            text = extractors[doc_path.split(".")[-1]](doc_path, nougat)
        else:
            text = extractors[doc_path.split(".")[-1]](doc_path)

        redis_manager.set_doc_text(doc_path, text)

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
                passage_id = generate_passage_id(dense_vector, doc_path)
                redis_manager.insert_passage(
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

        redis_manager.update_doc_ml_synced(doc_path, "true")

    return jsonify({"message": "Documents inserted successfully"})


@api_routes.route("/search", methods=["POST"])
def search():
    data = request.get_json()

    if "query" not in data:
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

    if model is None:
        load_model()
    if model is None:
        return (
            jsonify(
                {"error": 'ML service not enabled, set "use_bge" to True to enable'}
            ),
            500,
        )

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

    search_results = redis_manager.ml_search(
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
        doc_text = redis_manager.get_doc_text(doc_path)
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

    return jsonify({"passages": passages})


@api_routes.route("/get_doc_text", methods=["GET"])
def get_doc_text():
    doc_path = request.args.get("doc_path")
    doc_text = redis_manager.get_doc_text(doc_path)
    if doc_text:
        return jsonify({"doc_text": doc_text})
    else:
        return jsonify({"error": "Document text not found"}), 404


@api_routes.route("/get_ml_synced", methods=["GET"])
def get_ml_synced():
    doc_path = request.args.get("doc_path")
    ml_synced = redis_manager.get_doc_ml_synced(doc_path)
    if ml_synced:
        return jsonify({"ml_synced": ml_synced})
    else:
        return jsonify({"error": "Document ml_synced not found"}), 404


@api_routes.route("/get_doc_metadata", methods=["GET"])
def get_doc_metadata():
    doc_path = request.args.get("doc_path")
    doc_metadata = redis_manager.get_doc_metadata(doc_path)
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

    doc_paths = redis_manager.search_by_metadata(
        tags=tags, path=path, filename=filename, size_filter=size_filter
    )
    return jsonify({"doc_paths": doc_paths})


@api_routes.route("/delete_doc", methods=["POST"])
def delete_doc():
    data = request.get_json()
    doc_path = data["doc_path"]
    redis_manager.delete_doc(doc_path)
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
