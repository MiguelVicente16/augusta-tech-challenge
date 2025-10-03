"""
Enhanced Vector database using LangChain Documents for formatting.
Combines pgvector storage with professional document formatting.
"""

from typing import List, Dict, Any, Optional
import asyncpg

from .embeddings import EmbeddingService
from .document_formatter import DocumentFormatter


class VectorDB:
    """
    PostgreSQL + pgvector with LangChain Documents.
    Uses structured document formatting for better semantic understanding.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.embeddings = EmbeddingService()
        self.formatter = DocumentFormatter()

    async def add_company_embeddings(
        self,
        companies: List[Dict[str, Any]]
    ) -> int:
        """
        Generate and store embeddings for companies using structured Documents.

        Args:
            companies: List of company dicts with keys: id, company_name,
                      cae_primary_label, trade_description_native, website

        Returns:
            Number of embeddings stored
        """
        # Format as LangChain Documents
        documents = [
            self.formatter.format_company(
                company_id=c['id'],
                company_name=c['company_name'],
                cae_primary_label=c.get('cae_primary_label'),
                trade_description_native=c.get('trade_description_native'),
                website=c.get('website')
            )
            for c in companies
        ]

        # Extract text for embedding
        texts = [doc.page_content for doc in documents]

        # Generate embeddings
        embedding_vectors = await self.embeddings.embed_texts(texts)

        # Store in database
        async with self.pool.acquire() as conn:
            count = 0
            for company, embedding in zip(companies, embedding_vectors):
                # Convert list to pgvector format: "[0.1, 0.2, ...]"
                vector_str = '[' + ','.join(map(str, embedding)) + ']'
                await conn.execute(
                    "UPDATE companies SET embedding = $1 WHERE id = $2",
                    vector_str,
                    company['id']
                )
                count += 1
            return count

    async def add_incentive_embeddings(
        self,
        incentives: List[Dict[str, Any]]
    ) -> int:
        """
        Generate and store embeddings for incentives using structured Documents.

        Args:
            incentives: List of incentive dicts with keys: id, title, description,
                       ai_description_structured, total_budget, date_start, date_end

        Returns:
            Number of embeddings stored
        """
        # Format as LangChain Documents
        documents = [
            self.formatter.format_incentive(
                incentive_id=i['id'],
                title=i['title'],
                description=i.get('description'),
                ai_description_structured=i.get('ai_description_structured'),
                total_budget=i.get('total_budget'),
                date_start=str(i.get('date_start')) if i.get('date_start') else None,
                date_end=str(i.get('date_end')) if i.get('date_end') else None
            )
            for i in incentives
        ]

        # Extract text for embedding
        texts = [doc.page_content for doc in documents]

        # Generate embeddings
        embedding_vectors = await self.embeddings.embed_texts(texts)

        # Store in database
        async with self.pool.acquire() as conn:
            count = 0
            for incentive, embedding in zip(incentives, embedding_vectors):
                # Convert list to pgvector format
                vector_str = '[' + ','.join(map(str, embedding)) + ']'
                await conn.execute(
                    "UPDATE incentives SET embedding = $1 WHERE id = $2",
                    vector_str,
                    incentive['id']
                )
                count += 1
            return count

    async def find_similar_companies(
        self,
        incentive_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find most similar companies to an incentive using cosine similarity.

        Uses pgvector's <=> operator for efficient indexed search.

        Args:
            incentive_id: ID of the incentive
            limit: Number of top matches to return

        Returns:
            List of company records with similarity scores
        """
        async with self.pool.acquire() as conn:
            # Get incentive embedding
            incentive_embedding = await conn.fetchval(
                "SELECT embedding FROM incentives WHERE id = $1",
                incentive_id
            )

            if not incentive_embedding:
                return []

            # Find similar companies using cosine similarity
            # <=> is the cosine distance operator in pgvector
            # 1 - distance = similarity score
            results = await conn.fetch(
                """
                SELECT
                    id,
                    company_name,
                    cae_primary_label,
                    trade_description_native,
                    website,
                    1 - (embedding <=> $1) as similarity_score
                FROM companies
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                incentive_embedding,
                limit
            )

            return [dict(row) for row in results]

    async def find_similar_incentives(
        self,
        company_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find most similar incentives to a company using cosine similarity.

        Args:
            company_id: ID of the company
            limit: Number of top matches to return

        Returns:
            List of incentive records with similarity scores
        """
        async with self.pool.acquire() as conn:
            # Get company embedding
            company_embedding = await conn.fetchval(
                "SELECT embedding FROM companies WHERE id = $1",
                company_id
            )

            if not company_embedding:
                return []

            # Find similar incentives
            results = await conn.fetch(
                """
                SELECT
                    id,
                    title,
                    description,
                    ai_description_structured,
                    date_start,
                    date_end,
                    total_budget,
                    1 - (embedding <=> $1) as similarity_score
                FROM incentives
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                company_embedding,
                limit
            )

            return [dict(row) for row in results]

    async def semantic_search(
        self,
        query: str,
        table: str = "incentives",
        limit: int = 10,
        timeout: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using natural language query.

        Args:
            query: Natural language search query
            table: Table to search ("incentives" or "companies")
            limit: Number of results
            timeout: Query timeout in seconds (default: 10.0)

        Returns:
            List of matching records with similarity scores
        """
        # Generate query embedding
        query_embedding_list = await self.embeddings.embed_text(query)
        query_embedding = '[' + ','.join(map(str, query_embedding_list)) + ']'

        async with self.pool.acquire() as conn:
            if table == "incentives":
                results = await conn.fetch(
                    """
                    SELECT
                        id,
                        title,
                        description,
                        ai_description_structured,
                        1 - (embedding <=> $1::vector) as similarity_score
                    FROM incentives
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    query_embedding,
                    limit,
                    timeout=timeout
                )
            else:  # companies
                results = await conn.fetch(
                    """
                    SELECT
                        id,
                        company_name,
                        cae_primary_label,
                        trade_description_native,
                        1 - (embedding <=> $1::vector) as similarity_score
                    FROM companies
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    query_embedding,
                    limit,
                    timeout=timeout
                )

            return [dict(row) for row in results]

    async def get_stats(self) -> Dict[str, int]:
        """Get embedding statistics."""
        async with self.pool.acquire() as conn:
            incentives_with_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM incentives WHERE embedding IS NOT NULL"
            )
            companies_with_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM companies WHERE embedding IS NOT NULL"
            )

            return {
                "incentives_with_embeddings": incentives_with_embeddings,
                "companies_with_embeddings": companies_with_embeddings
            }
