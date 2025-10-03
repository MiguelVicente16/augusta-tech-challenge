"""
Matching Service using pgvector + LangChain

Architecture:
1. pgvector search: Top 20 candidates (instant, stored in DB)
2. Single LLM call: Rank top 20 → top 5 matches
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Dict, List, Tuple

from ...ai.client_factory import AIClientFactory
from ...ai.prompts import MATCHING_SYSTEM_PROMPT
from ...ai.vector_db import VectorDB
from ...config import get_settings
from ...database.service import DatabaseService
from ...models.incentive import IncentiveModel
from ...models.match import MatchModel

logger = logging.getLogger(__name__)


class MatchingResult:
    """Container for matching results with scoring details"""

    def __init__(self, company_id: int, score: Decimal, rank: int, reasoning: Dict):
        self.company_id = company_id
        self.score = score
        self.rank = rank
        self.reasoning = reasoning


class MatchingService:
    """
    Simplified matching service using pgvector.
    No in-memory storage, all queries hit the database.
    """

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        settings = get_settings()
        self.ai_client = AIClientFactory.create_client(
            provider=settings.AI_PROVIDER,
            model=settings.OPENAI_MODEL if settings.AI_PROVIDER == "openai" else settings.GEMINI_MODEL
        )
        self.vector_db = VectorDB(db_service.pool)

    async def match_companies_for_incentive(
        self,
        incentive_id: int,
        top_k_candidates: int = 20,
        max_cost_per_incentive: float = 0.30
    ) -> List[MatchingResult]:
        """
        Find top 5 companies for an incentive using pgvector + LLM.

        Args:
            incentive_id: ID of the incentive to match
            top_k_candidates: Number of candidates for LLM (default 20)
            max_cost_per_incentive: Maximum AI cost allowed

        Returns:
            List of top 5 MatchingResult objects
        """
        logger.info(f"Starting matching for incentive {incentive_id}")

        # Get incentive details
        incentive = await self.db_service.get_incentive_by_id(incentive_id)
        if not incentive:
            raise ValueError(f"Incentive {incentive_id} not found")

        # Step 1: Vector search in PostgreSQL (instant, uses index)
        logger.info("Step 1: pgvector similarity search")
        similar_companies = await self.vector_db.find_similar_companies(
            incentive_id=incentive_id,
            limit=top_k_candidates
        )

        if not similar_companies:
            logger.warning("No similar companies found")
            return []

        logger.info(f"Found {len(similar_companies)} similar companies via pgvector")

        # Step 2: Single LLM call to rank all candidates
        logger.info("Step 2: LLM ranking of candidates")
        top_5_results, llm_cost = await self._llm_rank_candidates(
            incentive,
            similar_companies,
            top_n=5
        )

        logger.info(f"Matching completed. LLM cost: ${llm_cost:.6f}")

        if llm_cost > max_cost_per_incentive:
            logger.warning(f"Cost limit exceeded: ${llm_cost:.6f} > ${max_cost_per_incentive}")

        return top_5_results

    async def _llm_rank_candidates(
        self,
        incentive: IncentiveModel,
        candidates: List[Dict],
        top_n: int = 5
    ) -> Tuple[List[MatchingResult], float]:
        """
        Use single LLM call to rank all candidates.

        Args:
            incentive: Incentive to match
            candidates: List of company dicts with similarity scores
            top_n: Number of top matches to return

        Returns:
            Tuple of (results, cost)
        """
        # Format incentive info
        incentive_info = self._format_incentive_for_llm(incentive)

        # Format candidates
        candidates_text = []
        for idx, company in enumerate(candidates, 1):
            company_text = f"""
Company {idx} (Vector Similarity: {company['similarity_score']:.3f}):
Name: {company['company_name']}
Sector: {company.get('cae_primary_label') or 'Not specified'}
Description: {company.get('trade_description_native') or 'Not available'}
Website: {company.get('website') or 'Not available'}
---"""
            candidates_text.append(company_text)

        all_candidates_text = "\n".join(candidates_text)

        # Create prompt (same as v2, but cleaner data flow)
        prompt = f"""Analyze and rank these {len(candidates)} pre-filtered companies for the following incentive.

Your task: Score each company and return the TOP {top_n} best matches.

INCENTIVE:
{incentive_info}

COMPANIES:
{all_candidates_text}

SCORING CRITERIA (Portugal 2030 methodology):
1. Adequação à Estratégia (40%): Sectoral alignment, regional strategy (RIS3)
2. Qualidade (35%): Innovation potential, diversification, project complexity
3. Capacidade de Execução (25%): Resources, experience, organizational maturity

For each company, score 1-5 on each criterion:
- 1: Very poor match
- 2: Poor match
- 3: Moderate match
- 4: Good match
- 5: Excellent match

Return ONLY the top {top_n} companies as a JSON array, ranked by best match first:
[
  {{
    "company_number": 1,
    "adequacao_estrategia": {{"score": 1-5, "reasoning": "brief explanation"}},
    "qualidade": {{"score": 1-5, "reasoning": "brief explanation"}},
    "capacidade_execucao": {{"score": 1-5, "reasoning": "brief explanation"}},
    "recommendation": "1-2 sentence recommendation"
  }},
  ...
]
"""

        # Call LLM
        loop = asyncio.get_event_loop()
        response_data = await loop.run_in_executor(
            None,
            lambda: self.ai_client.complete(
                prompt=prompt,
                system_prompt=MATCHING_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000
            )
        )

        response = response_data['content']
        llm_cost = response_data['usage'].get('total_cost', 0.0)

        # Parse response
        try:
            # Log raw response for debugging
            logger.debug(f"LLM raw response: {response[:500]}...")

            results_array = json.loads(response.strip())

            if not isinstance(results_array, list):
                raise ValueError("Expected JSON array response")

            matching_results = []

            for rank, result in enumerate(results_array[:top_n], 1):
                company_number = result.get('company_number', rank)

                if 1 <= company_number <= len(candidates):
                    company = candidates[company_number - 1]

                    # Calculate final score using Portugal 2030 weighted formula
                    # If LLM provided final_score, use it; otherwise calculate from components
                    if 'final_score' in result:
                        final_score = float(result['final_score'])
                        logger.debug(f"Using LLM-provided final_score: {final_score}")
                    else:
                        # Extract component scores
                        adequacao_score = float(result.get('adequacao_estrategia', {}).get('score', 3))
                        qualidade_score = float(result.get('qualidade', {}).get('score', 3))
                        capacidade_score = float(result.get('capacidade_execucao', {}).get('score', 3))

                        logger.debug(f"Component scores - Adequação: {adequacao_score}, Qualidade: {qualidade_score}, Capacidade: {capacidade_score}")

                        # Portugal 2030 weighted formula: 40% + 35% + 25%
                        final_score = (adequacao_score * 0.40) + (qualidade_score * 0.35) + (capacidade_score * 0.25)
                        logger.debug(f"Calculated final_score: {final_score}")
                        result['final_score'] = final_score

                    # Ensure score is within bounds
                    final_score = max(1.0, min(5.0, final_score))

                    result['vector_similarity'] = company['similarity_score']
                    result['strategic_fit'] = float(result.get('adequacao_estrategia', {}).get('score', 3))
                    result['quality'] = float(result.get('qualidade', {}).get('score', 3))
                    result['execution_capacity'] = float(result.get('capacidade_execucao', {}).get('score', 3))

                    matching_result = MatchingResult(
                        company_id=company['id'],
                        score=Decimal(str(final_score)),
                        rank=rank,
                        reasoning=result
                    )
                    matching_results.append(matching_result)

                    logger.info(f"Rank {rank}: Company {company['id']} - Final Score: {final_score:.2f}")

            logger.info(f"Successfully parsed {len(matching_results)} matches")
            return matching_results, llm_cost

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing LLM response: {e}")

            # Fallback: use vector similarity only
            fallback_results = []
            for rank, company in enumerate(candidates[:top_n], 1):
                fallback_reasoning = {
                    "adequacao_estrategia": {"score": 3, "reasoning": "LLM parsing failed"},
                    "qualidade": {"score": 3, "reasoning": "LLM parsing failed"},
                    "capacidade_execucao": {"score": 3, "reasoning": "LLM parsing failed"},
                    "final_score": 3.0,
                    "vector_similarity": company['similarity_score'],
                    "recommendation": f"Selected by vector similarity ({company['similarity_score']:.3f})",
                    "error": str(e)
                }

                result = MatchingResult(
                    company_id=company['id'],
                    score=Decimal("3.0"),
                    rank=rank,
                    reasoning=fallback_reasoning
                )
                fallback_results.append(result)

            return fallback_results, llm_cost

    def _format_incentive_for_llm(self, incentive: IncentiveModel) -> str:
        """Format incentive for LLM analysis"""
        parts = [f"Title: {incentive.title}"]

        if incentive.ai_description_structured:
            try:
                struct = (
                    incentive.ai_description_structured
                    if isinstance(incentive.ai_description_structured, dict)
                    else json.loads(incentive.ai_description_structured)
                )

                if struct.get('objective'):
                    parts.append(f"Objective: {struct['objective']}")
                if struct.get('target_sectors'):
                    parts.append(f"Target Sectors: {', '.join(struct['target_sectors'])}")
                if struct.get('target_regions'):
                    parts.append(f"Target Regions: {', '.join(struct['target_regions'])}")
                if struct.get('funding_type'):
                    parts.append(f"Funding Type: {struct['funding_type']}")
                if struct.get('key_requirements'):
                    parts.append(f"Requirements: {', '.join(struct['key_requirements'][:3])}")

            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.warning(f"Error parsing structured description: {e}")

        if incentive.description:
            parts.append(f"Description: {incentive.description[:300]}...")

        if incentive.date_start or incentive.date_end:
            parts.append(f"Period: {incentive.date_start or 'N/A'} to {incentive.date_end or 'N/A'}")
        if incentive.total_budget:
            parts.append(f"Budget: {incentive.total_budget}")

        return "\n".join(parts)

    async def save_matches_to_database(
        self,
        incentive_id: int,
        matches: List[MatchingResult]
    ) -> None:
        """Save matching results to database using upsert to handle conflicts"""
        import json
        async with self.db_service.db_manager.get_connection() as connection:
            for match in matches:
                await connection.execute(
                    """
                    INSERT INTO matches (
                        incentive_id, company_id, score, rank_position, reasoning
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (incentive_id, company_id)
                    DO UPDATE SET
                        score = EXCLUDED.score,
                        rank_position = EXCLUDED.rank_position,
                        reasoning = EXCLUDED.reasoning,
                        created_at = NOW()
                    """,
                    incentive_id,
                    match.company_id,
                    match.score,
                    match.rank,
                    json.dumps(match.reasoning) if match.reasoning else None
                )

        logger.info(f"Saved {len(matches)} matches for incentive {incentive_id}")

    async def batch_match_all_incentives(
        self,
        max_cost_total: float = None,
        save_to_db: bool = True
    ) -> Dict:
        """
        Run matching for all incentives.

        Args:
            max_cost_total: Maximum total cost
            save_to_db: Whether to save results to database

        Returns:
            Summary of matching results
        """
        logger.info("Starting batch matching for all incentives")

        incentives = await self.db_service.get_all_incentives()
        logger.info(f"Found {len(incentives)} incentives to match")

        total_cost = 0.0
        successful = 0
        failed = 0
        results_by_incentive = {}

        for incentive in incentives:
            try:
                if max_cost_total and total_cost >= max_cost_total:
                    logger.warning(f"Total cost limit reached: ${total_cost:.4f}")
                    break

                remaining_budget = max_cost_total - total_cost if max_cost_total else 0.30
                incentive_budget = min(0.30, remaining_budget)

                matches = await self.match_companies_for_incentive(
                    incentive.id,
                    max_cost_per_incentive=incentive_budget
                )

                if save_to_db and matches:
                    await self.save_matches_to_database(incentive.id, matches)

                successful += 1
                results_by_incentive[incentive.id] = {
                    'num_matches': len(matches),
                    'top_score': float(matches[0].score) if matches else 0.0
                }

                logger.info(f"Completed incentive {incentive.id}: {len(matches)} matches")

            except Exception as e:
                logger.error(f"Failed to match incentive {incentive.id}: {e}")
                failed += 1

        summary = {
            'total_incentives': len(incentives),
            'successful_matches': successful,
            'failed_matches': failed,
            'total_cost': f"${total_cost:.4f}",
            'avg_cost_per_incentive': f"${total_cost / successful:.4f}" if successful > 0 else "$0.00",
            'results_by_incentive': results_by_incentive
        }

        logger.info(f"Batch matching completed: {successful} successful, {failed} failed")
        return summary
