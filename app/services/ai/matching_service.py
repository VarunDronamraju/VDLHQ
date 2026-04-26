from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.core import Location, Lead
from app.services.ai.embedding_client import embedding_client
import structlog

logger = structlog.get_logger()

class MatchingService:
    """
    Location matching engine (A3).
    Performs vector similarity search via pgvector.
    """

    async def find_matches(
        self, 
        lead_id: UUID, 
        db: AsyncSession, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        1. Extract requirements from Lead.
        2. Embed requirements.
        3. Search locations table using cosine similarity.
        4. Return top results.
        """
        # 1. Get Lead details
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            return []

        # Construct search query from intake_data
        intake = lead.intake_data
        search_query = f"{intake.get('shoot_type', '')} {intake.get('location_type', '')} {intake.get('requirements', '')}"
        
        logger.info("matching_search_start", lead_id=str(lead_id), query=search_query)

        # 2. Generate embedding
        query_vector = await embedding_client.embed(search_query)

        # 3. Vector Search (Cosine Distance <=> is 1 - Cosine Similarity)
        # We search for available locations only
        stmt = (
            select(
                Location,
                Location.embedding.cosine_distance(query_vector).label("distance")
            )
            .filter(Location.available == True)
            .order_by(text("distance ASC"))
            .limit(limit)
        )

        results = await db.execute(stmt)
        matches = []
        
        for loc, distance in results.all():
            matches.append({
                "id": str(loc.id),
                "name": loc.name,
                "type": loc.type,
                "address": loc.address,
                "distance": float(distance),
                "similarity": round(1.0 - float(distance), 4)
            })

        logger.info("matching_search_complete", lead_id=str(lead_id), count=len(matches))
        return matches

# Singleton instance
matching_service = MatchingService()
