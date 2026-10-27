import numpy as np
import psycopg
from pgvector import HalfVector
from pgvector.psycopg import register_vector

from .settings import DATABASE_URL, EMBEDDING_DIMENSIONS


class EmbeddingStore:
    def __init__(self, database_url: str = DATABASE_URL) -> None:
        if not database_url:
            raise RuntimeError("DATABASE_URL must point to a PostgreSQL database with pgvector enabled.")
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise RuntimeError("The ML service requires DATABASE_URL to use PostgreSQL.")
        self._database_url = database_url

    def _connect(self, *, register_types: bool = True):
        connection = psycopg.connect(self._database_url)
        if register_types:
            register_vector(connection)
        return connection

    def initialize(self) -> None:
        with self._connect(register_types=False) as connection:
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS jewellery_embeddings (
                    category TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    embedding halfvec({EMBEDDING_DIMENSIONS}) NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (category, item_id, model_version)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS jewellery_embeddings_cosine_idx
                ON jewellery_embeddings USING hnsw (embedding halfvec_cosine_ops)
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS pledge_image_embeddings (
                    image_id TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    embedding halfvec({EMBEDDING_DIMENSIONS}) NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (image_id, model_version)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS pledge_image_embeddings_cosine_idx
                ON pledge_image_embeddings USING hnsw (embedding halfvec_cosine_ops)
                """
            )

    def upsert(
        self,
        category: str,
        item_id: str,
        model_version: str,
        embedding: np.ndarray,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jewellery_embeddings (category, item_id, model_version, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (category, item_id, model_version)
                DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = NOW()
                """,
                (category, item_id, model_version, HalfVector(embedding)),
            )

    def match(
        self,
        embedding: np.ndarray,
        model_version: str,
        top_k: int,
    ) -> list[dict[str, str | float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT category, item_id, 1 - (embedding <=> %s) AS similarity
                FROM jewellery_embeddings
                WHERE model_version = %s
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (HalfVector(embedding), model_version, HalfVector(embedding), top_k),
            ).fetchall()
        return [
            {
                "category": row[0],
                "item_id": row[1],
                "similarity_score": max(0.0, min(1.0, float(row[2]))),
            }
            for row in rows
        ]

    def upsert_pledge_image(self, image_id: str, model_version: str, embedding: np.ndarray) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pledge_image_embeddings (image_id, model_version, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT (image_id, model_version)
                DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = NOW()
                """,
                (image_id, model_version, HalfVector(embedding)),
            )

    def match_pledge_images(
        self,
        embedding: np.ndarray,
        model_version: str,
        top_k: int,
    ) -> list[dict[str, str | float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT image_id, 1 - (embedding <=> %s) AS similarity
                FROM pledge_image_embeddings
                WHERE model_version = %s
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (HalfVector(embedding), model_version, HalfVector(embedding), top_k),
            ).fetchall()
        return [
            {"image_id": row[0], "similarity_score": max(0.0, min(1.0, float(row[1])))}
            for row in rows
        ]
