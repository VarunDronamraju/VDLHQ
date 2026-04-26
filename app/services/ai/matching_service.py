from typing import Any, Dict, List
from uuid import UUID

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Lead, Location
from app.services.ai.embedding_client import embedding_client

logger = structlog.get_logger()


class MatchingService:
    """
    Location matching engine (A3).
    Performs vector similarity search via pgvector.
    """

    async def find_matches(self, lead_id: UUID, db: AsyncSession, limit: int = 5) -> List[Dict[str, Any]]:
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
            logger.warning("matching_lead_not_found", lead_id=str(lead_id))
            return []

        # Construct search query from intake_data
        intake = lead.intake_data or {}
        components = [intake.get("shoot_type", ""), intake.get("location_type", ""), intake.get("requirements", "")]
        search_query = " ".join([c for c in components if c]).strip()

        if not search_query:
            logger.info("matching_empty_query", lead_id=str(lead_id))
            # Safe fallback: return most popular or newest available locations?
            # For now, return empty as we can't match nothing
            return []

        logger.info("matching_search_start", lead_id=str(lead_id), query=search_query)

        # 2. Generate embedding
        try:
            query_vector = await embedding_client.embed(search_query)
            if not query_vector:
                raise ValueError("Generated embedding is empty")
        except Exception as e:
            logger.error("embedding_failed", lead_id=str(lead_id), error=str(e))
            return []

        # 3. Vector Search (Cosine Distance <=> is 1 - Cosine Similarity)
        # We search for available locations only
        try:
            stmt = (
                select(Location, Location.embedding.cosine_distance(query_vector).label("distance"))
                .filter(Location.available.is_(True), Location.embedding.isnot(None))  # Ensure we don't compare against nulls
                .order_by(text("distance ASC"))
                .limit(limit)
            )

            results = await db.execute(stmt)
            matches = []

            for loc, distance in results.all():
                dist_val = float(distance) if distance is not None else 1.0
                matches.append({"id": str(loc.id), "name": loc.name, "type": loc.type, "address": loc.address, "distance": dist_val, "similarity": round(1.0 - dist_val, 4)})

            logger.info("matching_search_complete", lead_id=str(lead_id), count=len(matches))
            return matches
        except Exception as e:
            logger.error("vector_search_failed", lead_id=str(lead_id), error=str(e))
            return []


# Singleton instance
matching_service = MatchingService()
