"""
Smart pre-filtering system for efficient company-incentive matching

This module implements multiple filtering strategies to reduce 150k companies
to a manageable subset (~100-200) before expensive AI analysis.

Filtering strategies:
1. Sector-based filtering (CAE codes)
2. Keyword matching in business descriptions
3. Geographic/regional filtering
4. Business size/type filtering
5. Innovation indicators

Goal: Reduce companies by 99.9% while keeping high-quality candidates
"""

import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher

from ...models.company import CompanyModel
from ...models.incentive import IncentiveModel

logger = logging.getLogger(__name__)


class CompanyPreFilter:
    """Intelligent pre-filtering to reduce company pool before AI analysis"""
    
    def __init__(self):
        # Common CAE sector keywords for mapping
        self.sector_keywords = {
            'industria': ['manufacturing', 'production', 'industrial', 'factory', 'fabricação', 'produção', 'indústria'],
            'tecnologia': ['technology', 'software', 'digital', 'IT', 'tech', 'tecnologia', 'informática'],
            'turismo': ['tourism', 'hotel', 'restaurant', 'travel', 'turismo', 'hospitalidade'],
            'agricultura': ['agriculture', 'farming', 'agro', 'agricultura', 'pecuária'],
            'energia': ['energy', 'renewable', 'solar', 'wind', 'energia', 'renovável'],
            'comercio': ['retail', 'commerce', 'trading', 'comércio', 'vendas'],
            'servicos': ['services', 'consulting', 'serviços', 'consultoria'],
            'construcao': ['construction', 'building', 'construção', 'obra'],
            'saude': ['health', 'medical', 'healthcare', 'saúde', 'medicina'],
            'educacao': ['education', 'training', 'educação', 'formação']
        }
        
        # Innovation indicators in company descriptions
        self.innovation_keywords = [
            'inovação', 'innovation', 'I&D', 'R&D', 'research', 'desenvolvimento',
            'tecnologia', 'technology', 'digital', 'automatização', 'automation',
            'inteligência artificial', 'artificial intelligence', 'AI', 'machine learning',
            'startup', 'patente', 'patent', 'laboratório', 'laboratory'
        ]
        
        # Sustainability indicators
        self.sustainability_keywords = [
            'sustentável', 'sustainable', 'verde', 'green', 'eco', 'ambiente',
            'environment', 'renewable', 'renovável', 'eficiência energética',
            'energy efficiency', 'carbon', 'carbono', 'reciclagem', 'recycling'
        ]
        
        # Digital transformation indicators
        self.digital_keywords = [
            'digital', 'digitalization', 'digitalização', 'online', 'e-commerce',
            'plataforma', 'platform', 'software', 'app', 'website', 'sistema',
            'automatização', 'automation', 'cloud', 'nuvem'
        ]

    async def filter_companies_for_incentive(
        self, 
        companies: List[CompanyModel], 
        incentive: IncentiveModel,
        target_count: int = 150
    ) -> List[CompanyModel]:
        """
        Filter companies down to target_count most relevant candidates
        
        Args:
            companies: Full list of companies (150k)
            incentive: Incentive to match against
            target_count: Target number of companies to return (~150)
            
        Returns:
            Filtered list of most relevant companies
        """
        logger.info(f"Filtering {len(companies)} companies for incentive '{incentive.title}'")
        
        # Parse incentive criteria
        criteria = self._extract_incentive_criteria(incentive)
        logger.info(f"Extracted criteria: {criteria}")
        
        # Apply multiple filtering stages
        candidates = companies
        
        # Stage 1: Sector filtering (most selective)
        if criteria.get('target_sectors'):
            candidates = self._filter_by_sector(candidates, criteria['target_sectors'])
            logger.info(f"After sector filtering: {len(candidates)} companies")
        
        # Stage 2: Keyword matching in descriptions
        if criteria.get('relevant_keywords'):
            candidates = self._filter_by_keywords(candidates, criteria['relevant_keywords'])
            logger.info(f"After keyword filtering: {len(candidates)} companies")
        
        # Stage 3: Focus area filtering (innovation, sustainability, digital)
        focus_filters = []
        if criteria.get('innovation_focus'):
            focus_filters.extend(self.innovation_keywords)
        if criteria.get('sustainability_focus'):
            focus_filters.extend(self.sustainability_keywords)
        if criteria.get('digital_focus'):
            focus_filters.extend(self.digital_keywords)
            
        if focus_filters:
            candidates = self._filter_by_focus_areas(candidates, focus_filters)
            logger.info(f"After focus area filtering: {len(candidates)} companies")
        
        # Stage 4: If still too many, apply quality scoring and take top ones
        if len(candidates) > target_count:
            candidates = self._rank_and_limit_candidates(candidates, incentive, target_count)
            logger.info(f"After ranking and limiting: {len(candidates)} companies")
        
        # Stage 5: If too few, expand with broader criteria
        if len(candidates) < target_count // 2:  # If less than 75 companies
            logger.info("Too few candidates, expanding with broader criteria...")
            candidates = self._expand_candidate_pool(companies, incentive, target_count)
            logger.info(f"After expansion: {len(candidates)} companies")
        
        logger.info(f"Final filtered candidates: {len(candidates)}")
        return candidates

    def _extract_incentive_criteria(self, incentive: IncentiveModel) -> Dict:
        """Extract filtering criteria from incentive data"""
        criteria = {
            'target_sectors': [],
            'relevant_keywords': [],
            'innovation_focus': False,
            'sustainability_focus': False,
            'digital_focus': False,
            'regions': []
        }
        
        # Try to parse structured AI description
        structured_data = None
        if incentive.ai_description_structured:
            try:
                if isinstance(incentive.ai_description_structured, dict):
                    structured_data = incentive.ai_description_structured
                elif isinstance(incentive.ai_description_structured, str):
                    structured_data = json.loads(incentive.ai_description_structured)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback to ai_description
        if not structured_data and incentive.ai_description:
            try:
                if isinstance(incentive.ai_description, dict):
                    structured_data = incentive.ai_description
                elif isinstance(incentive.ai_description, str):
                    structured_data = json.loads(incentive.ai_description)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Extract from structured data
        if structured_data:
            criteria['target_sectors'] = structured_data.get('target_sectors', [])
            criteria['innovation_focus'] = structured_data.get('innovation_focus', False)
            criteria['sustainability_focus'] = structured_data.get('sustainability_focus', False)
            criteria['digital_focus'] = structured_data.get('digital_transformation_focus', False)
            criteria['regions'] = structured_data.get('target_regions', [])
            
            # Extract keywords from various fields
            keywords = []
            keywords.extend(structured_data.get('eligible_activities', []))
            keywords.extend(structured_data.get('key_requirements', []))
            criteria['relevant_keywords'] = keywords
        
        # Extract keywords from title and description
        text_content = f"{incentive.title} {incentive.description or ''}"
        criteria['relevant_keywords'].extend(self._extract_keywords_from_text(text_content))
        
        return criteria

    def _filter_by_sector(self, companies: List[CompanyModel], target_sectors: List[str]) -> List[CompanyModel]:
        """Filter companies by sector alignment"""
        if not target_sectors:
            return companies
            
        filtered = []
        target_sectors_lower = [s.lower() for s in target_sectors]
        
        for company in companies:
            if not company.cae_primary_label:
                continue
                
            cae_lower = company.cae_primary_label.lower()
            
            # Direct sector name matching
            for sector in target_sectors_lower:
                if sector in cae_lower:
                    filtered.append(company)
                    break
            else:
                # Keyword-based sector matching
                for sector, keywords in self.sector_keywords.items():
                    if sector in target_sectors_lower:
                        for keyword in keywords:
                            if keyword.lower() in cae_lower:
                                filtered.append(company)
                                break
                        if company in filtered:
                            break
        
        return filtered

    def _filter_by_keywords(self, companies: List[CompanyModel], keywords: List[str]) -> List[CompanyModel]:
        """Filter companies by keyword matching in descriptions"""
        if not keywords:
            return companies
            
        filtered = []
        keywords_lower = [k.lower() for k in keywords if k]
        
        for company in companies:
            description = company.trade_description_native or ""
            description_lower = description.lower()
            
            # Check if any keyword appears in description
            for keyword in keywords_lower:
                if keyword in description_lower:
                    filtered.append(company)
                    break
        
        return filtered

    def _filter_by_focus_areas(self, companies: List[CompanyModel], focus_keywords: List[str]) -> List[CompanyModel]:
        """Filter companies by focus area keywords"""
        if not focus_keywords:
            return companies
            
        filtered = []
        focus_lower = [k.lower() for k in focus_keywords]
        
        for company in companies:
            text_content = f"{company.trade_description_native or ''} {company.cae_primary_label or ''}"
            text_lower = text_content.lower()
            
            # Check if any focus keyword appears
            for keyword in focus_lower:
                if keyword in text_lower:
                    filtered.append(company)
                    break
        
        return filtered

    def _rank_and_limit_candidates(
        self, 
        companies: List[CompanyModel], 
        incentive: IncentiveModel, 
        limit: int
    ) -> List[CompanyModel]:
        """Rank companies by relevance score and take top N"""
        
        # Simple scoring based on text similarity and keyword density
        scored_companies = []
        
        incentive_text = f"{incentive.title} {incentive.description or ''}"
        incentive_words = set(incentive_text.lower().split())
        
        for company in companies:
            score = 0
            
            # Text similarity with company description
            company_text = f"{company.trade_description_native or ''} {company.cae_primary_label or ''}"
            company_words = set(company_text.lower().split())
            
            # Jaccard similarity
            intersection = len(incentive_words.intersection(company_words))
            union = len(incentive_words.union(company_words))
            if union > 0:
                score += intersection / union
            
            # Keyword density bonus
            for word in incentive_words:
                if len(word) > 3 and word in company_text.lower():
                    score += 0.1
            
            # Innovation/quality indicators bonus
            for keyword in self.innovation_keywords:
                if keyword.lower() in company_text.lower():
                    score += 0.2
                    break
            
            scored_companies.append((score, company))
        
        # Sort by score and take top candidates
        scored_companies.sort(key=lambda x: x[0], reverse=True)
        return [company for score, company in scored_companies[:limit]]

    def _expand_candidate_pool(
        self, 
        all_companies: List[CompanyModel], 
        incentive: IncentiveModel, 
        target_count: int
    ) -> List[CompanyModel]:
        """Expand candidate pool with broader criteria when too few matches"""
        
        # Use more general keywords from incentive
        general_keywords = self._extract_general_keywords(incentive)
        
        candidates = []
        for company in all_companies:
            if len(candidates) >= target_count:
                break
                
            company_text = f"{company.trade_description_native or ''} {company.cae_primary_label or ''}"
            company_text_lower = company_text.lower()
            
            # Very broad matching
            for keyword in general_keywords:
                if keyword.lower() in company_text_lower:
                    candidates.append(company)
                    break
        
        # If still not enough, take random sample
        if len(candidates) < target_count // 2:
            import random
            remaining_needed = target_count - len(candidates)
            available_companies = [c for c in all_companies if c not in candidates]
            
            if len(available_companies) > remaining_needed:
                additional = random.sample(available_companies, remaining_needed)
                candidates.extend(additional)
            else:
                candidates.extend(available_companies)
        
        return candidates

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        if not text:
            return []
            
        # Simple keyword extraction
        words = re.findall(r'\b\w{4,}\b', text.lower())  # Words with 4+ chars
        
        # Filter out common words
        stop_words = {
            'para', 'com', 'por', 'em', 'de', 'da', 'do', 'das', 'dos', 'na', 'no', 'nas', 'nos',
            'que', 'como', 'mais', 'ser', 'ter', 'estar', 'fazer', 'dizer', 'mesmo', 'outro',
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
        }
        
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Return most frequent keywords
        from collections import Counter
        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(20)]

    def _extract_general_keywords(self, incentive: IncentiveModel) -> List[str]:
        """Extract general keywords for broad matching"""
        text = f"{incentive.title} {incentive.description or ''}"
        
        # Extract key terms
        general_terms = []
        
        # Common incentive-related terms
        incentive_terms = [
            'apoio', 'incentivo', 'fundo', 'financiamento', 'subsídio',
            'modernização', 'inovação', 'desenvolvimento', 'crescimento',
            'competitividade', 'exportação', 'internacionalização',
            'support', 'funding', 'grant', 'development', 'innovation'
        ]
        
        text_lower = text.lower()
        for term in incentive_terms:
            if term in text_lower:
                general_terms.append(term)
        
        # Add sector-agnostic keywords
        general_terms.extend(['empresa', 'negócio', 'atividade', 'projeto', 'investimento'])
        
        return general_terms

    def get_filtering_stats(self, original_count: int, filtered_count: int) -> Dict:
        """Get statistics about filtering effectiveness"""
        reduction_ratio = (original_count - filtered_count) / original_count
        cost_reduction = reduction_ratio * 100
        
        return {
            'original_companies': original_count,
            'filtered_companies': filtered_count,
            'reduction_ratio': reduction_ratio,
            'cost_reduction_percent': cost_reduction,
            'estimated_cost_before': f"${original_count * 0.002:.2f}",
            'estimated_cost_after': f"${filtered_count * 0.002:.2f}"
        }