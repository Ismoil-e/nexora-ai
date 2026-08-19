import json
import re
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.contracts.types import ExtractedChunk, ExtractedEntity, ExtractedRelationship
from app.services.ai_service import AIService


class EntityRelationshipExtractor:
    """Extracts business entities and knowledge relationships from document content."""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def extract_from_chunks(
        self,
        chunks: list[ExtractedChunk],
        document_title: str = "",
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelationship]]:
        entities: list[ExtractedEntity] = []
        relationships: list[ExtractedRelationship] = []
        seen_entity_keys: set[str] = set()

        for chunk in chunks[:15]:  # Process up to top 15 chunks for entity extraction
            content = chunk.content

            # 1. Regex / Pattern-based Entity Extraction
            # Email / Persons / Companies
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
            for email in set(emails):
                key = f"Person:{email}"
                if key not in seen_entity_keys:
                    seen_entity_keys.add(key)
                    entities.append(
                        ExtractedEntity(
                            entity_name=email,
                            entity_type="Person",
                            confidence=0.95,
                            attributes={"email": email},
                            chunk_index=chunk.chunk_index,
                        )
                    )

            # Amounts / Financial Metrics
            amounts = re.findall(r"(?:\$|\bUSD\b|\bEUR\b|\bUZS\b|\bso'm\b)\s?\d+(?:[.,]\d+)*", content, re.IGNORECASE)
            for amt in set(amounts):
                key = f"Financial Metric:{amt}"
                if key not in seen_entity_keys:
                    seen_entity_keys.add(key)
                    entities.append(
                        ExtractedEntity(
                            entity_name=amt,
                            entity_type="Financial Metric",
                            confidence=0.9,
                            chunk_index=chunk.chunk_index,
                        )
                    )

            # Dates / Deadlines
            dates = re.findall(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b20\d{2}[./-]\d{1,2}[./-]\d{1,2}\b", content)
            for dt in set(dates):
                key = f"Date:{dt}"
                if key not in seen_entity_keys:
                    seen_entity_keys.add(key)
                    entities.append(
                        ExtractedEntity(
                            entity_name=dt,
                            entity_type="Deadline",
                            confidence=0.85,
                            chunk_index=chunk.chunk_index,
                        )
                    )

            # Organization / Company names pattern (e.g. MChJ, LLC, Inc, Corp, Company)
            orgs = re.findall(r"\b[A-Z][a-zA-Z0-9_\-\s]+(?:MChJ|OK|LLC|Inc|Corp|Company|GmbH|Ltd)\b", content)
            for org in set(orgs):
                org_clean = org.strip()
                key = f"Company:{org_clean}"
                if key not in seen_entity_keys:
                    seen_entity_keys.add(key)
                    entities.append(
                        ExtractedEntity(
                            entity_name=org_clean,
                            entity_type="Company",
                            confidence=0.9,
                            chunk_index=chunk.chunk_index,
                        )
                    )

        # 2. LLM-assisted Relationship Extraction if db & AI provider available
        if self.db and len(entities) >= 2:
            try:
                ai_service = AIService(self.db)
                entity_names = [e.entity_name for e in entities[:10]]
                prompt = (
                    f"Document: {document_title}\n"
                    f"Entities: {entity_names}\n"
                    "Identify 1-3 relationships between these entities (e.g., 'Entity A' WORKS_FOR 'Entity B').\n"
                    "Respond ONLY with valid JSON array: [{\"source\": \"A\", \"target\": \"B\", \"type\": \"WORKS_FOR\"}]"
                )

                resp = await ai_service.chat(
                    provider="openrouter",
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are a Knowledge Graph relationship extractor. Return only JSON array.",
                )

                content_str = resp.get("content", "")
                json_match = re.search(r"\[.*\]", content_str, re.DOTALL)
                if json_match:
                    rel_data = json.loads(json_match.group())
                    for r in rel_data:
                        if "source" in r and "target" in r and "type" in r:
                            relationships.append(
                                ExtractedRelationship(
                                    source_entity_name=r["source"],
                                    target_entity_name=r["target"],
                                    relationship_type=r["type"],
                                    confidence=0.85,
                                    context_snippet=document_title,
                                )
                            )
            except Exception:
                pass  # Fallback gracefully if AI LLM call unavailable

        return entities, relationships
