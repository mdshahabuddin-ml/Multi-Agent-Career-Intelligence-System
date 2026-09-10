from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.api import auth
from backend.models.research_source import ResearchSource, SourceType


router = APIRouter(prefix="/news", tags=["News"])


class NewsArticleResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    content: Optional[str]
    source: str
    source_url: str
    source_article_id: Optional[str]
    author: Optional[str]
    published_date: Optional[datetime]
    retrieved_date: datetime
    topics: List[str] = []
    companies_mentioned: List[str] = []
    technologies_mentioned: List[str] = []
    sentiment: Optional[str]
    language: str
    quality_score: float
    credibility_score: float
    relevance_score: float
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NewsArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    summary: Optional[str] = None
    content: Optional[str] = None
    source: str
    source_url: str
    source_article_id: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    topics: List[str] = []
    companies_mentioned: List[str] = []
    technologies_mentioned: List[str] = []
    sentiment: Optional[str] = None
    language: str = "en"
    quality_score: float = 0.0
    credibility_score: float = 0.0
    relevance_score: float = 0.0
    is_verified: bool = False


class NewsArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    summary: Optional[str] = None
    content: Optional[str] = None
    topics: Optional[List[str]] = None
    companies_mentioned: Optional[List[str]] = None
    technologies_mentioned: Optional[List[str]] = None
    sentiment: Optional[str] = None
    quality_score: Optional[float] = None
    credibility_score: Optional[float] = None
    relevance_score: Optional[float] = None
    is_verified: Optional[bool] = None


class NewsListResponse(BaseModel):
    items: List[NewsArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class NewsStatsResponse(BaseModel):
    total_articles: int
    by_sentiment: Dict[str, int]
    by_topic: Dict[str, int]
    by_source: Dict[str, int]
    by_language: Dict[str, int]
    avg_quality_score: float
    date_range: Dict[str, Optional[str]]


def to_response(source: ResearchSource) -> NewsArticleResponse:
    """Convert ResearchSource to NewsArticleResponse."""
    topics = []
    companies = []
    technologies = []
    sentiment = None
    language = "en"
    quality_score = 0.0
    
    if source.source_metadata:
        topics = source.source_metadata.get("topics", [])
        companies = source.source_metadata.get("companies_mentioned", [])
        technologies = source.source_metadata.get("technologies_mentioned", [])
        sentiment = source.source_metadata.get("sentiment")
        language = source.source_metadata.get("language", "en")
        quality_score = source.source_metadata.get("quality_score", 0.0)
    
    return NewsArticleResponse(
        id=source.id,
        title=source.title or "",
        summary=source.summary,
        content=source.content,
        source=source.domain or "",
        source_url=source.url,
        source_article_id=source.source_metadata.get("source_article_id") if source.source_metadata else None,
        author=source.author,
        published_date=source.published_date,
        retrieved_date=source.retrieved_date,
        topics=topics,
        companies_mentioned=companies,
        technologies_mentioned=technologies,
        sentiment=sentiment,
        language=language,
        quality_score=quality_score,
        credibility_score=source.credibility_score,
        relevance_score=source.relevance_score,
        is_verified=source.is_verified,
        created_at=source.created_at,
    )


@router.get("", response_model=NewsListResponse)
async def list_news(
    topic: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    technology: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    min_quality: Optional[float] = Query(None, ge=0, le=1),
    search: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("published_date", pattern="^(published_date|retrieved_date|quality_score|credibility_score|relevance_score)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """List news articles with filtering and pagination."""
    query = db.query(ResearchSource).filter(ResearchSource.source_type == SourceType.NEWS)
    
    if topic:
        query = query.filter(ResearchSource.source_metadata.contains({"topics": [topic]}))
    if company:
        query = query.filter(ResearchSource.source_metadata.contains({"companies_mentioned": [company]}))
    if technology:
        query = query.filter(ResearchSource.source_metadata.contains({"technologies_mentioned": [technology]}))
    if sentiment:
        query = query.filter(ResearchSource.source_metadata.contains({"sentiment": sentiment}))
    if source:
        query = query.filter(ResearchSource.domain.ilike(f"%{source}%"))
    if language:
        query = query.filter(ResearchSource.source_metadata.contains({"language": language}))
    if start_date:
        query = query.filter(ResearchSource.published_date >= start_date)
    if end_date:
        query = query.filter(ResearchSource.published_date <= end_date)
    if min_quality is not None:
        query = query.filter(
            func.coalesce(
                func.jsonb_extract_path_text(ResearchSource.source_metadata, 'quality_score'),
                '0'
            ).cast(float) >= min_quality
        )
    if is_verified is not None:
        query = query.filter(ResearchSource.is_verified == is_verified)
    if search:
        query = query.filter(
            or_(
                ResearchSource.title.ilike(f"%{search}%"),
                ResearchSource.content.ilike(f"%{search}%"),
                ResearchSource.summary.ilike(f"%{search}%"),
            )
        )
    
    total = query.count()
    
    sort_column = getattr(ResearchSource, sort_by)
    if sort_order == "desc":
        sort_column = desc(sort_column)
    query = query.order_by(sort_column)
    
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return NewsListResponse(
        items=[to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats", response_model=NewsStatsResponse)
async def get_news_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get news statistics."""
    query = db.query(ResearchSource).filter(ResearchSource.source_type == SourceType.NEWS)
    
    if start_date:
        query = query.filter(ResearchSource.published_date >= start_date)
    if end_date:
        query = query.filter(ResearchSource.published_date <= end_date)
    
    sources = query.all()
    
    by_sentiment = {}
    by_topic = {}
    by_source = {}
    by_language = {}
    quality_scores = []
    
    for s in sources:
        if s.source_metadata:
            sentiment = s.source_metadata.get("sentiment", "unknown")
            by_sentiment[sentiment] = by_sentiment.get(sentiment, 0) + 1
            
            for topic in s.source_metadata.get("topics", []):
                by_topic[topic] = by_topic.get(topic, 0) + 1
            
            lang = s.source_metadata.get("language", "en")
            by_language[lang] = by_language.get(lang, 0) + 1
            
            qs = s.source_metadata.get("quality_score")
            if qs is not None:
                quality_scores.append(float(qs))
        
        if s.domain:
            by_source[s.domain] = by_source.get(s.domain, 0) + 1
    
    published_dates = [s.published_date for s in sources if s.published_date]
    date_range = {}
    if published_dates:
        date_range["start"] = min(published_dates).isoformat()
        date_range["end"] = max(published_dates).isoformat()
    else:
        date_range["start"] = None
        date_range["end"] = None
    
    return NewsStatsResponse(
        total_articles=len(sources),
        by_sentiment=by_sentiment,
        by_topic=by_topic,
        by_source=by_source,
        by_language=by_language,
        avg_quality_score=sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
        date_range=date_range,
    )


@router.get("/topics", response_model=List[str])
async def get_news_topics(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all unique topics from news articles."""
    sources = db.query(ResearchSource).filter(
        ResearchSource.source_type == SourceType.NEWS
    ).all()
    
    topics = set()
    for s in sources:
        if s.source_metadata and s.source_metadata.get("topics"):
            topics.update(s.source_metadata["topics"])
    
    return sorted(list(topics))


@router.get("/companies", response_model=List[str])
async def get_news_companies(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all unique companies mentioned in news."""
    sources = db.query(ResearchSource).filter(
        ResearchSource.source_type == SourceType.NEWS
    ).all()
    
    companies = set()
    for s in sources:
        if s.source_metadata and s.source_metadata.get("companies_mentioned"):
            companies.update(s.source_metadata["companies_mentioned"])
    
    return sorted(list(companies))


@router.get("/technologies", response_model=List[str])
async def get_news_technologies(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all unique technologies mentioned in news."""
    sources = db.query(ResearchSource).filter(
        ResearchSource.source_type == SourceType.NEWS
    ).all()
    
    technologies = set()
    for s in sources:
        if s.source_metadata and s.source_metadata.get("technologies_mentioned"):
            technologies.update(s.source_metadata["technologies_mentioned"])
    
    return sorted(list(technologies))


@router.get("/sources", response_model=List[str])
async def get_news_sources(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all unique news sources/domains."""
    sources = db.query(ResearchSource.domain).filter(
        ResearchSource.source_type == SourceType.NEWS,
        ResearchSource.domain.isnot(None)
    ).distinct().all()
    
    return sorted([s[0] for s in sources if s[0]])


@router.get("/sentiments", response_model=List[str])
async def get_news_sentiments(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all unique sentiments."""
    sources = db.query(ResearchSource).filter(
        ResearchSource.source_type == SourceType.NEWS
    ).all()
    
    sentiments = set()
    for s in sources:
        if s.source_metadata and s.source_metadata.get("sentiment"):
            sentiments.add(s.source_metadata["sentiment"])
    
    return sorted(list(sentiments))


@router.get("/{article_id}", response_model=NewsArticleResponse)
async def get_news_article(
    article_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single news article by ID."""
    source = db.query(ResearchSource).filter(
        ResearchSource.id == article_id,
        ResearchSource.source_type == SourceType.NEWS
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News article not found"
        )
    
    return to_response(source)


@router.post("", response_model=NewsArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_news_article(
    article: NewsArticleCreate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new news article."""
    metadata = {
        "topics": article.topics,
        "companies_mentioned": article.companies_mentioned,
        "technologies_mentioned": article.technologies_mentioned,
        "sentiment": article.sentiment,
        "language": article.language,
        "quality_score": article.quality_score,
        "source_article_id": article.source_article_id,
    }
    
    source = ResearchSource(
        url=article.source_url,
        title=article.title,
        source_type=SourceType.NEWS,
        domain=article.source,
        author=article.author,
        published_date=article.published_date,
        retrieved_date=datetime.utcnow(),
        content=article.content,
        summary=article.summary,
        credibility_score=article.credibility_score,
        relevance_score=article.relevance_score,
        is_verified=article.is_verified,
        source_metadata=metadata,
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    return to_response(source)


@router.patch("/{article_id}", response_model=NewsArticleResponse)
async def update_news_article(
    article_id: int,
    updates: NewsArticleUpdate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a news article."""
    source = db.query(ResearchSource).filter(
        ResearchSource.id == article_id,
        ResearchSource.source_type == SourceType.NEWS
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News article not found"
        )
    
    if updates.title is not None:
        source.title = updates.title
    if updates.summary is not None:
        source.summary = updates.summary
    if updates.content is not None:
        source.content = updates.content
    if updates.is_verified is not None:
        source.is_verified = updates.is_verified
    
    if source.source_metadata is None:
        source.source_metadata = {}
    
    if updates.topics is not None:
        source.source_metadata["topics"] = updates.topics
    if updates.companies_mentioned is not None:
        source.source_metadata["companies_mentioned"] = updates.companies_mentioned
    if updates.technologies_mentioned is not None:
        source.source_metadata["technologies_mentioned"] = updates.technologies_mentioned
    if updates.sentiment is not None:
        source.source_metadata["sentiment"] = updates.sentiment
    if updates.quality_score is not None:
        source.source_metadata["quality_score"] = updates.quality_score
    if updates.credibility_score is not None:
        source.credibility_score = updates.credibility_score
    if updates.relevance_score is not None:
        source.relevance_score = updates.relevance_score
    
    db.commit()
    db.refresh(source)
    
    return to_response(source)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news_article(
    article_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a news article."""
    source = db.query(ResearchSource).filter(
        ResearchSource.id == article_id,
        ResearchSource.source_type == SourceType.NEWS
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News article not found"
        )
    
    db.delete(source)
    db.commit()