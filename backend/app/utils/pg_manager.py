import time
import numpy as np
import datetime
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import register_adapter, AsIs
import logging
from typing import Optional, List, Dict, Tuple, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def adapt_numpy_array(arr):
    return AsIs(tuple(arr))

def addapt_numpy_float32(numpy_float32):
    return AsIs(numpy_float32)

register_adapter(np.ndarray, adapt_numpy_array)
register_adapter(np.float32, addapt_numpy_float32)

class PostgresManager:
    def __init__(
        self,
        host="localhost",
        port=5432,
        database="chishiki",
        user="chishiki_user",
        password="your_secure_password",
        dense_dim=1024,
    ):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        self.dense_dim = dense_dim

    def insert_passage(
        self,
        passage_id: str,
        doc_path: str,
        file_hash: str,
        filename: str,
        dense_vector: np.ndarray,
        lexical_weights: Dict[str, float],
        start_pos: int,
        end_pos: int,
        window_size: int,
    ) -> None:
        try:
            with self.conn.cursor() as cur:
                # Insert passage; PostgreSQL will generate the passage ID automatically
                vector_str = '[' + ','.join(map(str, dense_vector.tolist())) + ']'

                cur.execute("""
                    INSERT INTO passages (
                        file_hash, dense_vector, start_pos, end_pos, window_size, embedding_model
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_hash, start_pos, end_pos, window_size)
                    DO UPDATE SET dense_vector = EXCLUDED.dense_vector
                    RETURNING passage_id
                """, (
                    file_hash, vector_str,
                    start_pos, end_pos, window_size, "bge-m3"
                ))

                # Get the passage ID
                result = cur.fetchone()
                if not result:
                    # If no id was returned, query for the existing one
                    cur.execute("""
                        SELECT passage_id
                        FROM passages
                        WHERE file_hash = %s
                        AND start_pos = %s
                        AND end_pos = %s
                        AND window_size = %s
                    """, (file_hash, start_pos, end_pos, window_size))
                    result = cur.fetchone()

                if not result:
                    raise Exception("Failed to get passage_id")

                passage_id = result[0]
                logger.info(f"Passage '{passage_id}' inserted successfully")

                # Insert lexical weights
                lexical_weights_data = [
                    (passage_id, token, weight, window_size)
                    for token, weight in lexical_weights.items()
                ]
                execute_values(cur, """
                    INSERT INTO lexical_weights (passage_id, token, weight, window_size)
                    VALUES %s
                    ON CONFLICT (passage_id, token, window_size)
                    DO UPDATE SET weight = EXCLUDED.weight
                """, lexical_weights_data)

            self.conn.commit()
            logger.info(f"Passage '{passage_id}' inserted successfully")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting passage: {str(e)}")

    def insert_metadata(
        self,
        doc_path: str,
        file_hash: str,
        filename: str,
        file_extension: str,
        creation_time: str,
        modification_time: str,
        size: int,
    ) -> None:
        try:
            # Convert UNIX timestamps to datetime objects
            creation_timestamp = datetime.datetime.fromtimestamp(float(creation_time))
            modification_timestamp = datetime.datetime.fromtimestamp(float(modification_time))
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO document_metadata (
                        doc_path, file_hash, filename, tags, creation_time,
                        modification_time, ml_synced, size
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_hash) DO UPDATE SET
                        doc_path = EXCLUDED.doc_path,
                        filename = EXCLUDED.filename,
                        tags = EXCLUDED.tags,
                        modification_time = EXCLUDED.modification_time,
                        size = EXCLUDED.size
                """, (
                    doc_path, file_hash, filename, [file_extension],
                    creation_timestamp, modification_timestamp, False, size
                ))
            self.conn.commit()
            logger.info(f"Metadata for document '{doc_path}' inserted successfully")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting metadata: {str(e)}")

    def search_by_metadata(
        self,
        tags: Optional[List[str]] = None,
        path: Optional[str] = None,
        filename: Optional[str] = None,
        size_filter: Optional[str] = None,
        k: int = 1000
    ) -> List[str]:
        try:
            query = "SELECT doc_path FROM document_metadata WHERE 1=1"
            params = []

            if tags:
                query += " AND tags && %s"
                params.append(tags)
            if path:
                query += " AND doc_path LIKE %s"
                params.append(f"{path}%")
            if filename:
                query += " AND filename ILIKE %s"
                params.append(f"%{filename}%")
            if size_filter:
                size_op, size_value = size_filter.split()
                query += f" AND size {size_op} %s"
                params.append(int(size_value))

            query += f" LIMIT {k}"

            with self.conn.cursor() as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error executing metadata search: {str(e)}")
            return []

    def ml_search(
        self,
        query_dense_vector: np.ndarray,
        query_lexical_weights: Dict[str, float],
        tags: Optional[List[str]] = None,
        path: Optional[str] = None,
        filename: Optional[str] = None,
        window_size: Optional[int] = None,
        dense_weight: float = 0.7,
        sparse_weight: Optional[float] = None,
        k: int = 30,
    ) -> List[Tuple[Tuple[str, int, int], Tuple[float, float, float]]]:
        try:
            sparse_weight = sparse_weight or (1 - dense_weight)
            query_vector_str = '[' + ','.join(map(str, query_dense_vector.tolist())) + ']'

            # Build the query
            query = """
                WITH dense_scores AS (
                    SELECT
                        p.passage_id,
                        p.file_hash,
                        p.start_pos,
                        p.end_pos,
                        1 - (p.dense_vector <=> %s) as dense_score
                    FROM passages p
                    JOIN document_metadata dm ON p.file_hash = dm.file_hash
                    WHERE p.window_size = %s
            """
            params = [query_vector_str, window_size]

            if tags or path or filename:
                pre_filtered_doc_paths = self.search_by_metadata(tags, path, filename)
                if pre_filtered_doc_paths:
                    query += " AND dm.doc_path = ANY(%s)"
                    params.append(pre_filtered_doc_paths)

            query += """
                    ORDER BY dense_score DESC
                    LIMIT %s
                )
            """
            params.append(k)

            # Add lexical scores
            if query_lexical_weights:
                lexical_conditions = []
                for token, weight in query_lexical_weights.items():
                    lexical_conditions.append(
                        f"COALESCE(SUM(CASE WHEN lw.token = %s THEN lw.weight * %s END), 0)"
                    )
                    params.extend([token, weight])

                query += f"""
                    , lexical_scores AS (
                        SELECT
                            ds.passage_id,
                            ds.file_hash,
                            ds.start_pos,
                            ds.end_pos,
                            ds.dense_score,
                            ({' + '.join(lexical_conditions)}) as lexical_score
                        FROM dense_scores ds
                        LEFT JOIN lexical_weights lw ON ds.passage_id = lw.passage_id
                        GROUP BY ds.passage_id, ds.file_hash, ds.start_pos, ds.end_pos, ds.dense_score
                    )
                    SELECT
                        dm.doc_path,
                        ls.start_pos,
                        ls.end_pos,
                        ls.dense_score,
                        ls.lexical_score,
                        (%s * ls.dense_score + %s * ls.lexical_score) as combined_score
                    FROM lexical_scores ls
                    JOIN document_metadata dm ON ls.file_hash = dm.file_hash
                    ORDER BY combined_score DESC
                    LIMIT %s
                """
                params.extend([dense_weight, sparse_weight, k])

            with self.conn.cursor() as cur:
                cur.execute(query, params)
                results = cur.fetchall()

                return [
                    ((row[0], row[1], row[2]), (row[3], row[4], row[5]))
                    for row in results
                ]

        except Exception as e:
            logger.error(f"Error executing ML search: {str(e)}")
            return []

    def insert_mean_dense_vector(self, doc_path: str, mean_dense_vector: np.ndarray) -> None:
        try:
            with self.conn.cursor() as cur:
                vector_str = '[' + ','.join(map(str, mean_dense_vector.tolist())) + ']'
                cur.execute("""
                    UPDATE document_metadata
                    SET mean_dense_vector = %s
                    WHERE doc_path = %s
                """, (vector_str, doc_path))
            self.conn.commit()
            logger.info(f"Mean dense vector for document '{doc_path}' inserted successfully")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting mean dense vector: {str(e)}")

    def get_mean_dense_vector(self, doc_path: str) -> Optional[np.ndarray]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT mean_dense_vector
                    FROM document_metadata
                    WHERE doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    return np.frombuffer(result[0], dtype=np.float32)
            return None
        except Exception as e:
            logger.error(f"Error getting mean dense vector: {str(e)}")
            return None

    def search_similar_docs(self, mean_dense_vector: np.ndarray, k: int, threshold: float) -> List[Dict]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        doc_path,
                        1 - (mean_dense_vector <=> %s) as similarity_score
                    FROM document_metadata
                    WHERE mean_dense_vector IS NOT NULL
                        AND 1 - (mean_dense_vector <=> %s) > %s
                    ORDER BY similarity_score DESC
                    LIMIT %s
                """, (
                    mean_dense_vector.astype(np.float32).tobytes(),
                    mean_dense_vector.astype(np.float32).tobytes(),
                    threshold,
                    k
                ))
                results = cur.fetchall()
                return [
                    {"doc_path": row[0], "similarity_score": float(row[1])}
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            return []

    def delete_doc(self, doc_path: str) -> None:
        try:
            with self.conn.cursor() as cur:
                # Get file_hash first
                cur.execute("""
                    SELECT file_hash
                    FROM document_metadata
                    WHERE doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                if result:
                    file_hash = result[0]
                    # Due to CASCADE constraints, this will delete related passages and lexical weights
                    cur.execute("""
                        DELETE FROM document_metadata
                        WHERE file_hash = %s
                    """, (file_hash,))

                    # Delete document text
                    cur.execute("""
                        DELETE FROM document_texts
                        WHERE file_hash = %s
                    """, (file_hash,))

            self.conn.commit()
            logger.info(f"Document '{doc_path}' and its related data deleted successfully")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error deleting document '{doc_path}': {str(e)}")

    def get_doc_text(self, doc_path: str) -> Optional[str]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT dt.content
                    FROM document_texts dt
                    JOIN document_metadata dm ON dt.file_hash = dm.file_hash
                    WHERE dm.doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting document text: {str(e)}")
            return None

    def set_doc_text(self, doc_path: str, doc_text: str) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO document_texts (file_hash, content)
                    SELECT file_hash, %s
                    FROM document_metadata
                    WHERE doc_path = %s
                    ON CONFLICT (file_hash) DO UPDATE
                    SET content = EXCLUDED.content
                """, (doc_text, doc_path))
            self.conn.commit()
            logger.info(f"Document text for '{doc_path}' set successfully")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error setting document text: {str(e)}")

    def get_doc_by_path(self, doc_path: str) -> Optional[Dict]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT file_hash, filename, ml_synced, size
                    FROM document_metadata
                    WHERE doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                if result:
                    return {
                        "document": {
                            "file_hash": result[0],
                            "filename": result[1],
                            "ml_synced": result[2],
                            "size": result[3]
                        }
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting document by path: {str(e)}")
            return None

    def update_doc_hash(self, doc_path: str, file_hash: str) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE document_metadata
                    SET file_hash = %s, ml_synced = false
                    WHERE doc_path = %s
                """, (file_hash, doc_path))
            self.conn.commit()
            logger.info(f"Document hash updated for '{doc_path}'")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating document hash: {str(e)}")

    def update_doc_ml_synced(self, doc_path: str, ml_synced: bool) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE document_metadata
                    SET ml_synced = %s
                    WHERE doc_path = %s
                """, (ml_synced, doc_path))
            self.conn.commit()
            logger.info(f"ML sync status updated for '{doc_path}'")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating ML sync status: {str(e)}")

    def get_doc_ml_synced(self, doc_path: str) -> Optional[bool]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT ml_synced
                    FROM document_metadata
                    WHERE doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting ML sync status: {str(e)}")
            return None

    def get_doc_metadata(self, doc_path: str) -> Optional[Dict]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        file_hash, filename, tags, creation_time,
                        modification_time, ml_synced, size
                    FROM document_metadata
                    WHERE doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                if result:
                    return {
                        "file_hash": result[0],
                        "filename": result[1],
                        "tags": result[2],
                        "creation_time": result[3].isoformat(),
                        "modification_time": result[4].isoformat(),
                        "ml_synced": result[5],
                        "size": result[6]
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting document metadata: {str(e)}")
            return None

    def get_doc_tags(self, doc_path: str) -> List[str]:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT tags
                    FROM document_metadata
                    WHERE doc_path = %s
                """, (doc_path,))
                result = cur.fetchone()
                return result[0] if result and result[0] else []
        except Exception as e:
            logger.error(f"Error getting document tags: {str(e)}")
            return []

    def update_doc_tags(self, doc_path: str, tags: List[str]) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE document_metadata
                    SET tags = %s
                    WHERE doc_path = %s
                """, (tags, doc_path))
            self.conn.commit()
            logger.info(f"Tags updated for '{doc_path}'")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating document tags: {str(e)}")

    def close(self) -> None:
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
