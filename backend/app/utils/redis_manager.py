import time
import re
import numpy as np
from redis import Redis
from redis.commands.search.field import VectorField, TagField, NumericField, TextField
from redis.commands.search.query import Query
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(
        self,
        host="localhost",
        port=6379,
        ml_index_name="chishiki_ml_index",
        meta_index_name="chishiki_meta_index",
        dense_dim=1024,
        save_interval=300,
        write_threshold=1,
    ):
        self.redis_client = Redis(host=host, port=port)
        self.ml_index_name = ml_index_name
        self.meta_index_name = meta_index_name
        self.dense_dim = dense_dim
        self.save_interval = save_interval
        self.write_threshold = write_threshold
        self.last_save_time = time.time()
        self.write_operations = 0

    def create_index(self):
        try:
            ml_index_definition = IndexDefinition(
                prefix=[f"{self.ml_index_name}:passage:"],
                index_type=IndexType.HASH,
            )
            self.redis_client.ft(self.ml_index_name).create_index(
                [
                    VectorField(
                        "dense_vector",
                        "FLAT",
                        {
                            "TYPE": "FLOAT32",
                            "DIM": self.dense_dim,
                            "DISTANCE_METRIC": "COSINE",
                        },
                    ),
                    TextField("doc_path"),
                    NumericField("start_pos"),
                    NumericField("end_pos"),
                    NumericField("window_size"),
                ],
                definition=ml_index_definition,
            )

            meta_index_definition = IndexDefinition(
                prefix=[f"{self.meta_index_name}:doc:"],
                index_type=IndexType.HASH,
            )
            self.redis_client.ft(self.meta_index_name).create_index(
                [
                    TagField("tags"),
                    TextField("doc_path"),
                    TagField("file_hash"),
                    TextField("filename"),
                    TagField("ml_synced"),
                    NumericField("size"),
                    VectorField(
                        "mean_dense_vector",
                        "FLAT",
                        {
                            "TYPE": "FLOAT32",
                            "DIM": self.dense_dim,
                            "DISTANCE_METRIC": "COSINE",
                        },
                    ),
                ],
                definition=meta_index_definition,
            )
            logger.info(
                f"Indexes '{self.ml_index_name}' and '{self.meta_index_name}' created successfully"
            )
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")

    def insert_passage(
        self,
        passage_id,
        doc_path,
        file_hash,
        filename,
        dense_vector,
        lexical_weights,
        start_pos,
        end_pos,
        window_size,
    ):
        try:
            dense_vector_fp32 = dense_vector.astype(np.float32)
            doc_path_ml = doc_path.replace(".", "_.")

            self.redis_client.hset(
                f"{self.ml_index_name}:passage:{passage_id}",
                mapping={
                    "dense_vector": dense_vector_fp32.tobytes(),
                    "doc_path": doc_path_ml,
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                    "window_size": window_size,
                },
            )

            self._insert_lexical_weights(passage_id, lexical_weights, window_size)
            self._increment_write_operations()
            logger.info(f"Passage '{passage_id}' inserted successfully")
        except Exception as e:
            logger.error(f"Error inserting passage: {str(e)}")

    def _insert_lexical_weights(self, passage_id, lexical_weights, window_size):
        for token, weight in lexical_weights.items():
            self.redis_client.zadd(
                f"{self.ml_index_name}:lexical_index:{window_size}:{token}",
                {passage_id: float(weight)},
            )

    def _increment_write_operations(self):
        self.write_operations += 1
        self._check_save_conditions()

    def insert_metadata(
        self,
        doc_path,
        file_hash,
        filename,
        file_extension,
        creation_time,
        modification_time,
        size,
    ):
        try:
            self.redis_client.hset(
                f"{self.meta_index_name}:doc:{doc_path}",
                mapping={
                    "file_hash": file_hash,
                    "doc_path": doc_path,
                    "filename": filename,
                    "tags": file_extension,
                    "creation_time": creation_time,
                    "modification_time": modification_time,
                    "ml_synced": "false",
                    "size": size,
                },
            )
            self._increment_write_operations()
            logger.info(f"Metadata for document '{doc_path}' inserted successfully")
        except Exception as e:
            logger.error(f"Error inserting metadata: {str(e)}")

    def search_by_metadata(
        self, tags=None, path=None, filename=None, size_filter=None, k=1000
    ):
        query_parts = []
        if tags:
            query_parts.append(f"@tags:{{{'|'.join(tags)}}}")
        if path:
            query_parts.append(f"@doc_path:{path}*")
        if filename:
            query_parts.append(f"@filename:*{filename}*")
        if size_filter:
            size_op, size_value = size_filter.split()
            query_parts.append(f"@size:[{size_op} {size_value}]")

        query_str = " ".join(query_parts) if query_parts else "*"
        query = Query(query_str).paging(0, k)

        logger.info(f"Executing metadata search with query: {query_str}")

        try:
            results = self.redis_client.ft(self.meta_index_name).search(query)
            doc_paths = [doc.id.split(":")[-1] for doc in results.docs]
            unique_doc_paths = list(set(doc_paths))
            logger.info(f"Metadata search returned {len(unique_doc_paths)} results")
            return unique_doc_paths
        except Exception as e:
            logger.error(f"Error executing metadata search: {str(e)}")
            return []

    def ml_search(
        self,
        query_dense_vector,
        query_lexical_weights,
        tags=None,
        path=None,
        filename=None,
        window_size=None,
        dense_weight=0.7,
        sparse_weight=None,
        k=30,
    ):
        if tags or path or filename:
            pre_filtered_doc_paths = self.search_by_metadata(tags, path, filename)
        else:
            pre_filtered_doc_paths = None

        dense_results = self._search_dense_vector(
            query_dense_vector, window_size, k, pre_filtered_doc_paths
        )
        lexical_scores = self._get_lexical_scores(query_lexical_weights, window_size)

        sparse_weight = sparse_weight or (1 - dense_weight)
        combined_results = self._combine_scores(
            dense_results, lexical_scores, dense_weight, sparse_weight
        )
        sorted_results = sorted(
            combined_results.items(), key=lambda x: x[1][2], reverse=True
        )[:k]

        return sorted_results

    def _search_dense_vector(
        self, query_dense_vector, window_size, k, pre_filtered_doc_paths
    ):
        query_str = f"(@window_size:[{window_size} {window_size}])"

        if pre_filtered_doc_paths:
            escaped_pre_filtered_doc_paths = [
                f'"{path.replace(".", "_.")}"' for path in pre_filtered_doc_paths
            ]
            escaped_pre_filtered_doc_paths = [path.replace("-", r"\-") for path in escaped_pre_filtered_doc_paths]
            pre_filtered_doc_paths_str = "|".join(escaped_pre_filtered_doc_paths)
            query_str = f"(@window_size:[{window_size} {window_size}] @doc_path:({pre_filtered_doc_paths_str}))"

        query_str += f" =>[KNN {k} @dense_vector $vec_param AS dense_score]"
        logger.info(f"Executing dense vector search with query: {query_str}")

        dense_query = (
            Query(query_str)
            .return_fields("doc_path", "start_pos", "end_pos", "dense_score")
            .sort_by("dense_score")
            .dialect(2)
        )
        query_dense_vector_fp32 = query_dense_vector.astype(np.float32)
        dense_query_params = {"vec_param": query_dense_vector_fp32.tobytes()}

        results = self.redis_client.ft(self.ml_index_name).search(
            dense_query, query_params=dense_query_params
        )

        for result in results.docs:
            result.doc_path = result.doc_path.replace("_.", ".")

        return results

    def _get_lexical_scores(self, query_lexical_weights, window_size):
        lexical_scores = {}
        for token, weight in query_lexical_weights.items():
            passage_scores = self.redis_client.zrange(
                f"{self.ml_index_name}:lexical_index:{window_size}:{token}",
                0,
                -1,
                withscores=True,
            )
            for passage_id, score in passage_scores:
                lexical_scores[passage_id] = (
                    lexical_scores.get(passage_id, 0) + score * weight
                )
        return lexical_scores

    def _combine_scores(
        self, dense_results, lexical_scores, dense_weight, sparse_weight
    ):
        combined_results = {}
        for passage in dense_results.docs:
            passage_id = passage.id.split(":")[-1].encode()
            dense_score = 1 - float(passage.dense_score)
            lexical_score = lexical_scores.get(passage_id, 0)
            combined_score = dense_weight * dense_score + sparse_weight * lexical_score
            combined_results[(passage.doc_path, passage.start_pos, passage.end_pos)] = (
                dense_score,
                lexical_score,
                combined_score,
            )
        return combined_results

    def insert_mean_dense_vector(self, doc_path, mean_dense_vector):
        try:
            mean_dense_vector_fp32 = mean_dense_vector.astype(np.float32)
            self.redis_client.hset(
                f"{self.meta_index_name}:doc:{doc_path}",
                mapping={
                    "mean_dense_vector": mean_dense_vector_fp32.tobytes(),
                },
            )
            self._increment_write_operations()
            logger.info(
                f"Mean dense vector for document '{doc_path}' inserted successfully"
            )
        except Exception as e:
            logger.error(f"Error inserting mean dense vector: {str(e)}")

    def get_mean_dense_vector(self, doc_path):
        mean_dense_vector = self.redis_client.hget(
            f"{self.meta_index_name}:doc:{doc_path}", "mean_dense_vector"
        )
        if mean_dense_vector:
            return np.frombuffer(mean_dense_vector, dtype=np.float32)
        else:
            logger.warning(f"Mean dense vector not found for path: {doc_path}")
            return None

    def search_similar_docs(self, mean_dense_vector, k, threshold):
        mean_dense_vector_fp32 = np.array(mean_dense_vector, dtype=np.float32)
        query_str = f"*=>[KNN {k} @mean_dense_vector $vec_param AS similarity_score]"
        query = (
            Query(query_str)
            .return_fields("doc_path", "similarity_score")
            .sort_by("similarity_score")
            .dialect(2)
        )
        query_params = {"vec_param": mean_dense_vector_fp32.tobytes()}
        results = self.redis_client.ft(self.meta_index_name).search(
            query, query_params=query_params
        )
        similar_docs = [
            {"doc_path": doc.doc_path, "similarity_score": float(doc.similarity_score)}
            for doc in results.docs
        ]
        return similar_docs

    def save_datastore(self):
        self.redis_client.save()
        self.last_save_time = time.time()
        self.write_operations = 0

    def flush_datastore(self):
        self.redis_client.flushall()
        logger.info("Datastore flushed")

    def _check_save_conditions(self):
        current_time = time.time()
        time_since_last_save = current_time - self.last_save_time

        if (
            time_since_last_save >= self.save_interval
            and self.write_operations >= self.write_threshold
        ):
            self.save_datastore()

    def delete_doc(self, doc_path):
        try:
            meta_key = f"{self.meta_index_name}:doc:{doc_path}"
            self.redis_client.delete(meta_key)
            logger.info(f"Document '{doc_path}' deleted from metadata index")

            query_str = f"@doc_path:{{{doc_path.replace('.', '_.')}}}"
            query = Query(query_str).return_fields("doc_path")
            results = self.redis_client.ft(self.ml_index_name).search(query)

            for doc in results.docs:
                passage_key = doc.id
                self.redis_client.delete(passage_key)
                logger.info(f"Passage '{passage_key}' deleted from ML index")

            logger.info(f"Document '{doc_path}' and its passages deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting document '{doc_path}': {str(e)}")

    def get_doc_text(self, doc_path):
        doc_text = self.redis_client.get(f"doc_text:{doc_path}")
        if doc_text:
            return doc_text.decode("utf-8")
        else:
            logger.warning(f"Document text not found for path: {doc_path}")
            return None

    def set_doc_text(self, doc_path, doc_text):
        self.redis_client.set(f"doc_text:{doc_path}", doc_text.encode("utf-8"))

    def get_doc_by_path(self, doc_path):
        doc = self.redis_client.hgetall(f"{self.meta_index_name}:doc:{doc_path}")
        if doc:
            return {
                "document": {
                    "file_hash": doc[b"file_hash"].decode("utf-8"),
                    "filename": doc[b"filename"].decode("utf-8"),
                    "ml_synced": doc[b"ml_synced"].decode("utf-8"),
                    "size": int(doc[b"size"].decode("utf-8")),
                }
            }
        else:
            logger.warning(f"Document not found for path: {doc_path}")
            return None

    def update_doc_hash(self, doc_path, file_hash):
        self.redis_client.hset(
            f"{self.meta_index_name}:doc:{doc_path}", "file_hash", file_hash
        )
        self.redis_client.hset(
            f"{self.meta_index_name}:doc:{doc_path}", "ml_synced", "false"
        )

    def update_doc_ml_synced(self, doc_path, ml_synced):
        self.redis_client.hset(
            f"{self.meta_index_name}:doc:{doc_path}", "ml_synced", ml_synced
        )

    def get_doc_ml_synced(self, doc_path):
        ml_synced = self.redis_client.hget(
            f"{self.meta_index_name}:doc:{doc_path}", "ml_synced"
        )
        return ml_synced.decode("utf-8") if ml_synced else None

    def get_doc_metadata(self, doc_path):
        doc = self.redis_client.hgetall(f"{self.meta_index_name}:doc:{doc_path}")
        if doc:
            return {
                "file_hash": doc[b"file_hash"].decode("utf-8"),
                "filename": doc[b"filename"].decode("utf-8"),
                "tags": doc[b"tags"].decode("utf-8"),
                "creation_time": doc[b"creation_time"].decode("utf-8"),
                "modification_time": doc[b"modification_time"].decode("utf-8"),
                "ml_synced": doc[b"ml_synced"].decode("utf-8"),
                "size": int(doc[b"size"].decode("utf-8")),
            }
        else:
            logger.warning(f"Document not found for path: {doc_path}")
            return None

    def get_doc_tags(self, doc_path):
        try:
            tags = self.redis_client.hget(
                f"{self.meta_index_name}:doc:{doc_path}", "tags"
            )
            return tags.decode("utf-8").split(",") if tags else []
        except Exception as e:
            logger.error(f"Error getting tags for document '{doc_path}': {str(e)}")
            return []

    def update_doc_tags(self, doc_path, tags):
        try:
            tags_str = ",".join(tags)
            self.redis_client.hset(
                f"{self.meta_index_name}:doc:{doc_path}", "tags", tags_str
            )
            self._increment_write_operations()
            logger.info(f"Tags for document '{doc_path}' updated successfully")
        except Exception as e:
            logger.error(f"Error updating tags for document '{doc_path}': {str(e)}")

    def _convert_doc_path_to_ml(self, doc_path):
        return doc_path.replace(".", "_.")

    def _convert_doc_path_from_ml(self, doc_path_ml):
        return doc_path_ml.replace("_.", ".")
