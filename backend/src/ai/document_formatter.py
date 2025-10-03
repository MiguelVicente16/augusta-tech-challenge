"""
Document formatting for structured embeddings using LangChain Documents.
Creates properly formatted text with metadata for better retrieval.
"""

from typing import Dict, Any, Optional
from langchain.schema import Document
import json


class DocumentFormatter:
    """Format database records as LangChain Documents for embedding."""

    @staticmethod
    def format_company(
        company_id: int,
        company_name: str,
        cae_primary_label: Optional[str],
        trade_description_native: Optional[str],
        website: Optional[str] = None
    ) -> Document:
        """
        Format a company record as a structured LangChain Document.

        Args:
            company_id: Company ID
            company_name: Company name
            cae_primary_label: Sector classification
            trade_description_native: Company description
            website: Company website (optional)

        Returns:
            LangChain Document with structured page_content and metadata
        """
        # Build structured content
        content_parts = [
            f"Company: {company_name}",
        ]

        if cae_primary_label:
            content_parts.append(f"Sector: {cae_primary_label}")

        if trade_description_native:
            content_parts.append(f"Activity: {trade_description_native}")

        if website:
            content_parts.append(f"Website: {website}")

        page_content = "\n".join(content_parts)

        # Metadata for filtering and identification
        metadata = {
            "id": company_id,
            "type": "company",
            "name": company_name,
            "sector": cae_primary_label or "unknown",
        }

        return Document(page_content=page_content, metadata=metadata)

    @staticmethod
    def format_incentive(
        incentive_id: int,
        title: str,
        description: Optional[str],
        ai_description_structured: Optional[Dict[str, Any]],
        total_budget: Optional[float] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None
    ) -> Document:
        """
        Format an incentive record as a structured LangChain Document.

        Args:
            incentive_id: Incentive ID
            title: Incentive title
            description: Full description
            ai_description_structured: Structured JSON with sectors, regions, etc.
            total_budget: Total budget (optional)
            date_start: Start date (optional)
            date_end: End date (optional)

        Returns:
            LangChain Document with structured page_content and metadata
        """
        # Build structured content
        content_parts = [
            f"Incentive: {title}",
        ]

        if description:
            content_parts.append(f"Description: {description}")

        # Extract structured fields
        structured_info = []
        if ai_description_structured:
            # Parse if string
            if isinstance(ai_description_structured, str):
                try:
                    ai_description_structured = json.loads(ai_description_structured)
                except json.JSONDecodeError:
                    ai_description_structured = {}

            # Add target sectors
            if ai_description_structured.get('target_sectors'):
                sectors = ai_description_structured['target_sectors']
                if isinstance(sectors, list) and sectors:
                    structured_info.append(f"Target Sectors: {', '.join(sectors)}")

            # Add target regions
            if ai_description_structured.get('target_regions'):
                regions = ai_description_structured['target_regions']
                if isinstance(regions, list) and regions:
                    structured_info.append(f"Target Regions: {', '.join(regions)}")

            # Add focus areas
            focus_areas = []
            if ai_description_structured.get('innovation_focus'):
                focus_areas.append("Innovation")
            if ai_description_structured.get('sustainability_focus'):
                focus_areas.append("Sustainability")
            if ai_description_structured.get('digital_transformation_focus'):
                focus_areas.append("Digital Transformation")
            if focus_areas:
                structured_info.append(f"Focus Areas: {', '.join(focus_areas)}")

            # Add funding type
            if ai_description_structured.get('funding_type'):
                structured_info.append(f"Funding Type: {ai_description_structured['funding_type']}")

        if structured_info:
            content_parts.extend(structured_info)

        # Add budget and dates
        if total_budget:
            content_parts.append(f"Budget: €{total_budget:,.2f}")

        if date_start or date_end:
            period = f"Period: {date_start or 'N/A'} to {date_end or 'N/A'}"
            content_parts.append(period)

        page_content = "\n".join(content_parts)

        # Metadata for filtering and identification
        metadata = {
            "id": incentive_id,
            "type": "incentive",
            "title": title,
            "budget": total_budget,
        }

        # Add structured fields to metadata for easy filtering
        if ai_description_structured:
            if ai_description_structured.get('target_sectors'):
                metadata['sectors'] = ai_description_structured['target_sectors']
            if ai_description_structured.get('target_regions'):
                metadata['regions'] = ai_description_structured['target_regions']

        return Document(page_content=page_content, metadata=metadata)

    @staticmethod
    def extract_text_for_embedding(doc: Document) -> str:
        """
        Extract clean text from Document for embedding.

        Args:
            doc: LangChain Document

        Returns:
            Clean text string suitable for embedding
        """
        return doc.page_content
