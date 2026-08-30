from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime
import asyncio
import logging

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_embedding_task(self, text: str, model: str = "text-embedding-3-small"):
    """Generate embedding for a single text."""
    try:
        logger.info("Generating embedding")
        
        from backend.rag.embeddings import EmbeddingManager, EmbeddingConfig, EmbeddingProvider
        
        config = EmbeddingConfig(
            provider="openai",
            model_name=model,
            dimensions=1536
        )
        
        manager = EmbeddingManager(config)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manager.embed_text(text))
            return {"embedding": result.embeddings[0], "model": model}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Embedding generation failed: {exc}")
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_batch_embeddings_task(self, texts: list, model: str = "text-embedding-3-small"):
    """Generate embeddings for multiple texts."""
    try:
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        from backend.rag.embeddings import EmbeddingManager, EmbeddingConfig
        
        config = EmbeddingConfig(
            provider="openai",
            model_name=model,
            dimensions=1536,
            batch_size=100
        )
        
        manager = EmbeddingManager(config)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manager.embed_texts(texts))
            return {
                "embeddings": result.embeddings,
                "model": model,
                "count": len(result.embeddings)
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Batch embedding generation failed: {exc}")
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_document_embeddings(self, document_id: int, model: str = "text-embedding-3-small"):
    """Generate embeddings for all chunks of a document."""
    try:
        logger.info(f"Generating embeddings for document: {document_id}")
        
        from backend.database import get_db
        from backend.models import Resume
        from backend.rag.embeddings import EmbeddingManager, EmbeddingConfig
        
        db = next(get_db())
        document = db.query(Resume).filter(Resume.id == document_id).first()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        if not document.chunks:
            logger.warning(f"Document {document_id} has no chunks")
            return {"status": "completed", "chunks_processed": 0}
        
        config = EmbeddingConfig(
            provider="openai",
            model_name="text-embedding-3-small",
            dimensions=1536,
            batch_size=50
        )
        
        manager = EmbeddingManager(config)
        
        # Extract chunk texts
        chunk_texts = [chunk.content for chunk in document.chunks]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manager.embed_texts(chunk_texts))
            
            # Update chunks with embeddings
            from backend.models import DocumentChunk
            for i, chunk in enumerate(document.chunks):
                chunk.embedding = result.embeddings[i]
            
            from backend.database import get_db
            db = next(get_db())
            db.commit()
            
            logger.info(f"Generated embeddings for {len(result.embeddings)} chunks of document {document_id}")
            return {
                "status": "completed",
                "document_id": document_id,
                "chunks_processed": len(result.embeddings)
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Document embedding generation failed for {document_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_query_embedding(self, query: str, model: str = "text-embedding-3-small"):
    """Generate embedding for a search query."""
    try:
        from backend.rag.embeddings import EmbeddingManager, EmbeddingConfig
        
        config = EmbeddingConfig(
            provider="openai",
            model_name=model,
            dimensions=1536
        )
        
        manager = EmbeddingManager(config)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manager.embed_query(query))
            return {"embedding": result, "model": model}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Query embedding generation failed: {exc}")
        raise


@shared_task
def generate_pending_embeddings():
    """Generate embeddings for all documents that don't have them yet."""
    logger.info("Generating pending embeddings")
    
    from backend.database import get_db
    from backend.models import Resume, DocumentChunk
    from backend.rag.embeddings import EmbeddingManager, EmbeddingConfig
    
    db = next(get_db())
    
    # Find chunks without embeddings
    chunks_without_embeddings = db.query(DocumentChunk).filter(
        DocumentChunk.embedding == None
    ).limit(100).all()
    
    if not chunks_without_embeddings:
        return {"status": "completed", "processed": 0}
    
    config = EmbeddingConfig(
        provider="openai",
        model_name="text-embedding-3-small",
        dimensions=1536,
        batch_size=50
    )
    
    manager = EmbeddingManager(config)
    
    chunk_texts = [chunk.content for chunk in chunks_without_embeddings]
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(manager.embed_texts(chunk_texts))
        
        for i, chunk in enumerate(chunks_without_embeddings):
            chunk.embedding = result.embeddings[i]
        
        db.commit()
        
        logger.info(f"Generated embeddings for {len(result.embeddings)} chunks")
        return {"status": "completed", "processed": len(result.embeddings)}
    finally:
        loop.close()