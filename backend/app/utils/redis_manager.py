import time
import numpy as np
from redis import Redis
from redis.commands.search.field import VectorField, TagField, NumericField
from redis.commands.search.query import Query, Filter
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
        
        # Set ft search limit to infinite
        # self.redis_client.config_set("LIMIT", "0", "0")

    def create_index(self):
        try:
            # Define the index for ML data with a specific key pattern
            ml_index_definition = IndexDefinition(
                prefix=[
                    f"{self.ml_index_name}:passage:"
                ],  # Only index keys that start with this prefix
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
                    TagField("doc_path"),
                    NumericField("start_pos"),
                    NumericField("end_pos"),
                    NumericField("window_size"),
                ],
                # definition=IndexDefinition(),
                definition=ml_index_definition
            )

            meta_index_definition = IndexDefinition(
                prefix=[
                    f"{self.meta_index_name}:doc:"
                ],  # Only index keys that start with this prefix
                index_type=IndexType.HASH,
            )
            self.redis_client.ft(self.meta_index_name).create_index(
                [
                    TagField("tags"),
                    TagField("doc_path"),
                    TagField("file_hash"),
                    TagField("filename"),
                    TagField("ml_synced"),
                    NumericField("size"),
                ],
                # definition=IndexDefinition(),
                definition=meta_index_definition
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

            self.redis_client.hset(
                f"{self.ml_index_name}:passage:{passage_id}",
                mapping={
                    "dense_vector": dense_vector_fp32.tobytes(),
                    "doc_path": doc_path,
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
        # try:
        #     metadata = {
        #         "file_hash": file_hash,
        #         "filename": filename,
        #         "tags": file_extension,
        #         "creation_time": creation_time,
        #         "modification_time": modification_time,
        #         "ml_synced": "false",
        #         "size": size,
        #     }
        #     self.redis_client.ft(self.meta_index_name).add_document(
        #         doc_path, replace=True, **metadata
        #     )
        #     self._increment_write_operations()
        #     logger.info(f"Metadata for document '{doc_path}' inserted successfully")
        # except Exception as e:
        #     logger.error(f"Error inserting metadata: {str(e)}")

    def search_by_metadata(self, tags=None, path=None, filename=None, size_filter=None, k=1000):
        query_parts = []
        if tags:
            query_parts.append(f"@tags:({' | '.join(tags)})")
        if path:
            query_parts.append(f"@doc_path:{path}")
        if filename:
            query_parts.append(f"@filename:{filename}")
        if size_filter:
            size_op, size_value = size_filter.split()
            query_parts.append(f"@size:[{size_op} {size_value}]")

        if query_parts:
            query = Query(" ".join(query_parts))
        else:
            query = Query("*")

        # print(self.redis_client.ft(self.meta_index_name).info())
        # print("search_by_metadata: query", query)

        results = self.redis_client.ft(self.meta_index_name).search(query.paging(0, k))
        
        doc_paths = [doc.id.split(":")[-1] for doc in results.docs]
        unique_doc_paths = list(set(doc_paths))

        return unique_doc_paths

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
        print("path", path)
        if tags or path or filename:
            pre_filtered_doc_paths = self.search_by_metadata(tags, path, filename)
        else:
            pre_filtered_doc_paths = None

        print("pre_filtered_doc_paths", pre_filtered_doc_paths)
        dense_results = self._search_dense_vector(
            query_dense_vector, window_size, k, pre_filtered_doc_paths
        )
        lexical_scores = self._get_lexical_scores(query_lexical_weights, window_size)

        if not sparse_weight:
            sparse_weight = 1 - dense_weight
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
        query_str = f"(@window_size:[{window_size} {window_size}]) =>[KNN {k} @dense_vector $vec_param AS dense_score]"
        if pre_filtered_doc_paths:
            pre_filtered_doc_paths_str = "|".join(pre_filtered_doc_paths)
            query_str += f" @doc_path:({pre_filtered_doc_paths_str})"

        dense_query = (
            Query(query_str)
            .return_fields("doc_path", "start_pos", "end_pos", "dense_score")
            .sort_by("dense_score")
            .dialect(2)
        )
        query_dense_vector_fp32 = query_dense_vector.astype(np.float32)
        dense_query_params = {"vec_param": query_dense_vector_fp32.tobytes()}

        return self.redis_client.ft(self.ml_index_name).search(
            dense_query, query_params=dense_query_params
        )

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
        passages = self.redis_client.ft(self.ml_index_name).search(
            Query(f"@doc_path:{doc_path}").return_fields("id")
        )
        for passage in passages.docs:
            passage_id = passage.id.split(":")[-1]
            self.redis_client.delete(f"{self.ml_index_name}:passage:{passage_id}")
        self.redis_client.delete(f"{self.meta_index_name}:doc:{doc_path}")
        self._increment_write_operations()

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
        # Set ml_synced to false when the document hash is updated
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
        if ml_synced:
            return ml_synced.decode("utf-8")
        else:
            return None

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
