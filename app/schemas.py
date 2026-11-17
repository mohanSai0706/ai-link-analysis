from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Request(StrictModel):
    url: HttpUrl


class Brand(StrictModel):
    name: Optional[str]
    category: Optional[str]
    summary: str
    products_and_services: List[str]


class Competitor(StrictModel):
    name: str
    strengths: List[str]
    weaknesses_or_gaps: List[str]
    evidence_note: str


class CompetitorAnalysis(StrictModel):
    brand_overview: str
    competitors: List[Competitor]
    brand_advantages: List[str]
    positioning_opportunities: List[str]


class SearchQuery(StrictModel):
    query: str
    platforms: List[Literal['Google', 'Facebook', 'Instagram', 'LinkedIn', 'X']]
    intent: str
    business_relevance: str
    target_audience: str


class SEO(StrictModel):
    primary_keyword: str
    secondary_keywords: List[str]
    long_tail_keywords: List[str]
    business_keywords: List[str]
    recommended_title: str
    meta_description: str
    supporting_content: List[str]


class Service(StrictModel):
    name: str
    description: str
    target_industry: str
    target_customer: str
    main_benefit: str
    basis: Literal['website', 'inferred']


class Audience(StrictModel):
    primary_audience: List[str]
    secondary_audience: List[str]
    industries: List[str]
    business_types: List[str]
    customer_profiles: List[str]
    geographic_focus: Optional[str]
    customer_needs: List[str]
    interests: List[str]
    recommended_segments: List[str]


class Analysis(StrictModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: List[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SEO
    top_services: List[Service] = Field(max_length=5)
    target_audience: Audience


class ModelResult(StrictModel):
    brand: Brand
    analysis: Analysis


class Response(StrictModel):
    success: Literal[True] = True
    website: str
    final_url: str
    brand: Brand
    analysis: Analysis
    limitations: List[str]
