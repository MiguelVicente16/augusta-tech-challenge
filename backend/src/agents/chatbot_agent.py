"""
Pydantic AI Chatbot Agent

Intelligent agent that uses tools to answer questions about
incentives, companies, and their matches.

Architecture:
- Agent decides which tool to use based on user query
- Direct DB queries for exact lookups (fast, cheap)
- Semantic search for conceptual queries (embeddings)
- Streaming responses for better UX
- Structured metadata for enhanced UI features
- Logfire instrumentation for observability
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, List
from pydantic import BaseModel, Field

import logfire
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.messages import FunctionToolCallEvent

from .chatbot_tools import ChatbotTools
from ..ai.prompts import CHATBOT_SYSTEM_PROMPT
from ..config import get_settings
from ..database.service import DatabaseService

# Configure Logfire for Pydantic AI instrumentation
logfire.configure()
logfire.instrument_pydantic_ai()

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# Response Models
# ============================================================================

class SuggestedAction(BaseModel):
    """Suggested action for the user"""
    label: str = Field(..., description="Display text for the action")
    action_type: str = Field(..., description="Type: 'view_incentive', 'view_company', 'search', 'question'")
    action_data: Optional[dict] = Field(None, description="Additional data for the action")


class ChatbotMetadata(BaseModel):
    """
    Metadata about the chatbot response.
    Sent at the end of streaming to provide UI enhancements.
    """
    tools_used: List[str] = Field(
        default_factory=list,
        description="Names of tools used to answer the question"
    )
    data_count: Optional[int] = Field(
        None,
        description="Number of data items found (e.g., 5 incentives, 3 companies)"
    )
    entity_type: Optional[str] = Field(
        None,
        description="Type of entities discussed: 'incentives', 'companies', 'matches', 'general'"
    )
    suggested_actions: List[SuggestedAction] = Field(
        default_factory=list,
        description="Suggested next actions for the user (max 3)"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Data sources used: 'incentives_table', 'companies_table', 'matches_table'"
    )


class ChatbotResponse(BaseModel):
    """Complete chatbot response with text and metadata"""
    answer: str = Field(..., description="Natural language response to the user")
    metadata: ChatbotMetadata = Field(
        default_factory=ChatbotMetadata,
        description="Metadata for UI enhancements"
    )


# ============================================================================
# Agent Dependencies
# ============================================================================

@dataclass
class ChatbotDependencies:
    """Dependencies injected into agent context"""
    db_service: DatabaseService
    tools: ChatbotTools

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.tools = ChatbotTools(db_service)


# ============================================================================
# Pydantic AI Agent
# ============================================================================

# System prompt for the agent
def create_chatbot_agent(db_service: DatabaseService) -> Agent:
    """
    Create Pydantic AI chatbot agent with tools.

    Args:
        db_service: Database service instance

    Returns:
        Configured Pydantic AI agent
    """
    # Initialize model (API key is read from environment automatically)
    model = OpenAIResponsesModel(settings.OPENAI_MODEL)

    # Create agent with structured result type
    agent = Agent(
        model=model,
        system_prompt=CHATBOT_SYSTEM_PROMPT,
        deps_type=ChatbotDependencies,
        output_type=ChatbotResponse,
        retries=1
    )

    # ========================================================================
    # Register Tools
    # ========================================================================

    @agent.tool
    async def get_company_by_name(
        ctx: RunContext[ChatbotDependencies],
        company_name: str,
        exact_match: bool = False
    ) -> dict[str, Any]:
        """
        Find a company by name.

        Use this when user asks for a specific company by name.
        Fast and cost-effective for exact lookups.

        Args:
            company_name: Name of the company to search for
            exact_match: Whether to use exact matching (default: False for fuzzy search)

        Returns:
            Company information including sector and description
        """
        return await ctx.deps.tools.get_company_by_name(company_name, exact_match)

    @agent.tool
    async def search_companies_by_sector(
        ctx: RunContext[ChatbotDependencies],
        sector: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search companies by CAE sector/industry.

        Use this when user asks about companies in a specific sector or industry.

        Args:
            sector: CAE sector label (e.g., "Tecnologia", "Agricultura", "Construção")
            limit: Maximum number of results (default: 10)

        Returns:
            List of companies in that sector
        """
        return await ctx.deps.tools.search_companies_by_sector(sector, limit)

    @agent.tool
    async def get_incentive_by_id(
        ctx: RunContext[ChatbotDependencies],
        incentive_id: int
    ) -> dict[str, Any]:
        """
        Get specific incentive by ID.

        Use this when user mentions a specific incentive ID.

        Args:
            incentive_id: Numeric ID of the incentive

        Returns:
            Complete incentive information including budget, dates, and eligibility
        """
        return await ctx.deps.tools.get_incentive_by_id(incentive_id)

    @agent.tool
    async def search_incentives_by_title(
        ctx: RunContext[ChatbotDependencies],
        title_query: str,
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search incentives by title/description keywords.

        Use this when user asks about incentives containing specific keywords.
        Uses fast keyword search.

        Args:
            title_query: Keywords to search in title/description
            limit: Maximum number of results (default: 5)

        Returns:
            List of matching incentives
        """
        return await ctx.deps.tools.search_incentives_by_title(title_query, limit)

    @agent.tool
    async def get_matches_for_company(
        ctx: RunContext[ChatbotDependencies],
        company_id: int,
        limit: int = 5
    ) -> dict[str, Any]:
        """
        Get top incentive matches for a company.

        Use this when user asks "What incentives are good for company X?"
        Returns AI-powered matching scores.

        Args:
            company_id: ID of the company
            limit: Number of top matches (default: 5)

        Returns:
            Top matched incentives with scores and reasoning
        """
        return await ctx.deps.tools.get_matches_for_company(company_id, limit)

    @agent.tool
    async def get_matches_for_incentive(
        ctx: RunContext[ChatbotDependencies],
        incentive_id: int
    ) -> dict[str, Any]:
        """
        Get top 5 company matches for an incentive BY ID.

        **SMART BEHAVIOR**:
        - If matches exist in DB → returns them instantly (like the endpoint)
        - If no matches exist → auto-computes them (~10-15s, $0.20-0.30)

        Use this when you already have the incentive ID.
        For title-based search, use get_matches_for_incentive_by_title instead.

        Args:
            incentive_id: Numeric ID of the incentive

        Returns:
            {"incentive_id": int, "matches": [{"company_id", "company_name", "score", "rank", "reasoning"}]}

        **IMPORTANT**: Response includes "score" field (0.0-1.0). ALWAYS display scores in your answer!
        """
        return await ctx.deps.tools.get_matches_for_incentive(incentive_id)

    @agent.tool
    async def get_matches_for_incentive_by_title(
        ctx: RunContext[ChatbotDependencies],
        incentive_title: str
    ) -> dict[str, Any]:
        """
        Get top 5 company matches for an incentive BY TITLE (not ID).

        **PRIMARY TOOL for match queries** - use this when user asks about matches for an incentive.

        This tool does EVERYTHING in one call:
        1. Searches for the incentive by title
        2. Gets the incentive ID
        3. Returns top 5 company matches (auto-computes if needed)

        Args:
            incentive_title: Title or partial title of the incentive

        Returns:
            {"incentive_id": int, "incentive_title": str, "matches": [{"company_id", "company_name", "score", "rank", "reasoning"}]}

        **CRITICAL**: Response includes "score" field (0.0-1.0). ALWAYS display scores in your answer!
        Format: "Company Name - **Score: X.XX** - brief reasoning"
        """
        return await ctx.deps.tools.get_matches_for_incentive_by_title(incentive_title)

    @agent.tool
    async def semantic_search(
        ctx: RunContext[ChatbotDependencies],
        query: str,
        entity_type: str = "incentives",
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Semantic search using natural language and AI embeddings.

        Use this when user asks conceptual/descriptive questions like:
        - "What incentives exist for green technology?"
        - "Find companies working on AI and machine learning"
        - "Show renewable energy funding opportunities"

        Uses pgvector embeddings for intelligent semantic matching.

        Args:
            query: Natural language search query
            entity_type: Type to search - "incentives" or "companies"
            limit: Number of results (default: 5)

        Returns:
            List of results, EACH WITH AN "id" FIELD. Extract the id from each result
            and include it in suggested_actions so users can view details.
            
            CRITICAL: Results will have IDs like {"id": 1061}, {"id": 1062}, {"id": 1149}.
            Use these EXACT IDs in suggested_actions, NOT hardcoded values like 1 or 123.
        """
        return await ctx.deps.tools.semantic_search(query, entity_type, limit)

    @agent.tool
    async def search_companies_semantic(
        ctx: RunContext[ChatbotDependencies],
        query: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search companies using semantic similarity on embeddings.

        **USE THIS INSTEAD of get_company_by_name when:**
        - User asks about companies in a sector/industry (e.g., "energia renovável", "tecnologia")
        - User searches by activity description (e.g., "solar panels", "software development")
        - You need to find multiple relevant companies at once

        **MUCH FASTER than:**
        - Calling get_company_by_name multiple times
        - Using get_matches_for_company without a specific company ID

        Examples:
        - "empresas de energia renovável" → search_companies_semantic("energia renovável")
        - "empresas que fazem software" → search_companies_semantic("desenvolvimento software")
        - "companhias de construção civil" → search_companies_semantic("construção civil")

        Args:
            query: Natural language description (sector, activity, industry)
            limit: Number of companies to return (default: 10)

        Returns:
            List of relevant companies with similarity scores
        """
        return await ctx.deps.tools.search_companies_semantic(query, limit)

    @agent.tool
    async def get_statistics(
        ctx: RunContext[ChatbotDependencies]
    ) -> dict[str, Any]:
        """
        Get overall database statistics.

        Use this when user asks about:
        - How many incentives/companies exist
        - Overall system statistics
        - Matching performance metrics

        Returns:
            Statistics about incentives, companies, and matches
        """
        return await ctx.deps.tools.get_statistics()

    @agent.tool
    async def generate_matches_for_all_incentives(
        ctx: RunContext[ChatbotDependencies],
        force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        Generate AI-powered matches for all incentives.

        Use this when user asks to:
        - "Generate matches for all incentives"
        - "Run the matching algorithm"
        - "Create matches between companies and incentives"
        - "Process all incentives for matching"

        First checks if matches already exist. If they do, returns existing count.
        If not, or if force_refresh is True, runs the AI matching algorithm.

        Args:
            force_refresh: If True, clears existing matches and regenerates all

        Returns:
            Status of match generation including counts and processing info
        """
        return await ctx.deps.tools.generate_matches_for_all_incentives(force_refresh)

    return agent


# ============================================================================
# Chatbot Service
# ============================================================================

class ChatbotService:
    """
    Service for running chatbot conversations with streaming support.
    """

    def __init__(self, db_service: DatabaseService):
        """
        Initialize chatbot service

        Args:
            db_service: Database service instance
        """
        self.db_service = db_service
        self.agent = create_chatbot_agent(db_service)
        self.deps = ChatbotDependencies(db_service)
        self.last_tool_results = {}  # Cache last tool results for ID extraction

    async def run(
        self,
        user_message: str,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Run chatbot without streaming (simple response).

        Args:
            user_message: User's message
            conversation_history: Previous messages (optional)

        Returns:
            Agent's response
        """
        try:
            result = await self.agent.run(
                user_message,
                deps=self.deps,
                message_history=conversation_history
            )

            # In Pydantic AI v1.0+, the result is directly accessible
            # result.data contains the final message content
            if hasattr(result, 'output'):
                return str(result.output)
            elif hasattr(result, 'data'):
                return str(result.data)
            else:
                # Fallback: convert result to string
                return str(result)

        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return f"Desculpe, ocorreu um erro: {str(e)}"

    async def run_stream(
        self,
        user_message: str,
        conversation_history: Optional[list] = None
    ):
        """
        Run chatbot with streaming support including tool call visibility.

        Uses agent.iter() to track tool calls in real-time and stream them to frontend.
        Yields tool call events, then response chunks, then metadata.

        Args:
            user_message: User's message
            conversation_history: Previous messages (optional)

        Yields:
            Tool call events ({"type": "tool_call", ...})
            Response text chunks ({"type": "text", ...})
            Metadata ({"type": "metadata", ...})
        """
        # Logfire span for full conversation trace
        with logfire.span('chatbot_run_stream', user_message=user_message[:100]) as span:
            try:
                tools_used = []

                # Use agent.iter() to track tool calls in real-time
                async with self.agent.iter(
                    user_message,
                    deps=self.deps,
                    message_history=conversation_history
                ) as run_context:

                    # Iterate through agent execution nodes
                    async for node in run_context:
                        # Check if this is a tool call node
                        if Agent.is_call_tools_node(node):
                            # Stream tool events from this node
                            async with node.stream(run_context.ctx) as tool_stream:
                                async for event in tool_stream:
                                    # Check if this is a function tool call event
                                    if isinstance(event, FunctionToolCallEvent):
                                        # Access tool_name from the part attribute
                                        tool_name = event.part.tool_name
                                        tools_used.append(tool_name)

                                        # Stream tool call event to frontend
                                        yield {
                                            "type": "tool_call",
                                            "content": {
                                                "tool_name": tool_name
                                            }
                                        }

                # After iteration completes, get the final result
                result = run_context.result

                # Extract usage/cost data from result if available
                if hasattr(result, 'usage'):
                    usage = result.usage()
                    span.set_attribute('tokens_total', usage.total_tokens)
                    span.set_attribute('tokens_prompt', usage.request_tokens)
                    span.set_attribute('tokens_completion', usage.response_tokens)

                    # Estimate cost (GPT-4.1-mini: $0.15/1M input, $0.60/1M output)
                    cost_input = (usage.request_tokens / 1_000_000) * 0.15
                    cost_output = (usage.response_tokens / 1_000_000) * 0.60
                    total_cost = cost_input + cost_output
                    span.set_attribute('cost_usd', round(total_cost, 6))

                # Extract the structured response
                response_data = None
                if hasattr(result, 'data'):
                    response_data = result.data
                elif hasattr(result, 'output'):
                    response_data = result.output
                else:
                    response_data = result

                # Stream the answer text
                if hasattr(response_data, 'answer'):
                    answer_text = response_data.answer

                    # Send metadata with tools used
                    if hasattr(response_data, 'metadata'):
                        metadata_dict = response_data.metadata.model_dump()

                        # Update tools_used with actual tools called
                        if tools_used:
                            metadata_dict['tools_used'] = tools_used

                        span.set_attribute('tools_used', metadata_dict.get('tools_used', []))
                        span.set_attribute('entity_type', metadata_dict.get('entity_type', 'unknown'))
                        yield {"type": "metadata", "content": metadata_dict}

                    span.set_attribute('response_length', len(answer_text))

                    # Stream by lines to preserve markdown formatting
                    lines = answer_text.split('\n')
                    for i, line in enumerate(lines):
                        chunk = line + ('\n' if i < len(lines) - 1 else '')
                        yield {"type": "text", "content": chunk}
                else:
                    # Fallback to string response
                    yield {"type": "text", "content": str(response_data)}

            except Exception as e:
                logger.error(f"Chatbot streaming error: {e}", exc_info=True)
                span.record_exception(e)
                yield {"type": "text", "content": f"Desculpe, ocorreu um erro: {str(e)}"}
