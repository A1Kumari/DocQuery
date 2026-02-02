# app/database/neo4j_client.py
from neo4j import AsyncGraphDatabase
from typing import Optional
from app.models.policy import PolicyDocument, Clause, Exclusion, PolicyRelationship
from app.config import settings

class Neo4jClient:
    """Graph database client for policy relationships."""
    
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    async def close(self):
        await self.driver.close()
    
    async def create_policy_graph(self, policy: PolicyDocument):
        """Create full policy graph with all relationships."""
        
        async with self.driver.session() as session:
            # Create Policy node
            await session.run("""
                MERGE (p:Policy {policy_id: $policy_id})
                SET p.policy_number = $policy_number,
                    p.policy_type = $policy_type,
                    p.holder_name = $holder_name,
                    p.effective_date = $effective_date,
                    p.expiration_date = $expiration_date
            """, 
                policy_id=policy.policy_id,
                policy_number=policy.policy_number,
                policy_type=policy.policy_type.value,
                holder_name=policy.holder_name,
                effective_date=str(policy.effective_date),
                expiration_date=str(policy.expiration_date)
            )
            
            # Create Clause nodes
            for clause in policy.clauses:
                await session.run("""
                    MATCH (p:Policy {policy_id: $policy_id})
                    MERGE (c:Clause {clause_id: $clause_id})
                    SET c.clause_type = $clause_type,
                        c.title = $title,
                        c.description = $description,
                        c.section_reference = $section_reference
                    MERGE (p)-[:HAS_CLAUSE]->(c)
                """,
                    policy_id=policy.policy_id,
                    clause_id=clause.clause_id,
                    clause_type=clause.clause_type,
                    title=clause.title,
                    description=clause.description,
                    section_reference=clause.section_reference
                )
            
            # Create Exclusion nodes
            for exclusion in policy.exclusions:
                await session.run("""
                    MATCH (p:Policy {policy_id: $policy_id})
                    MERGE (e:Exclusion {exclusion_id: $exclusion_id})
                    SET e.category = $category,
                        e.description = $description
                    MERGE (p)-[:HAS_EXCLUSION]->(e)
                """,
                    policy_id=policy.policy_id,
                    exclusion_id=exclusion.exclusion_id,
                    category=exclusion.category,
                    description=exclusion.description
                )
            
            # Create Coverage nodes
            for i, limit in enumerate(policy.coverage_limits):
                coverage_id = f"{policy.policy_id}_COV_{i}"
                await session.run("""
                    MATCH (p:Policy {policy_id: $policy_id})
                    MERGE (cov:Coverage {coverage_id: $coverage_id})
                    SET cov.coverage_type = $coverage_type,
                        cov.limit_amount = $limit_amount,
                        cov.deductible = $deductible,
                        cov.currency = $currency
                    MERGE (p)-[:PROVIDES_COVERAGE]->(cov)
                """,
                    policy_id=policy.policy_id,
                    coverage_id=coverage_id,
                    coverage_type=limit.coverage_type,
                    limit_amount=limit.limit_amount,
                    deductible=limit.deductible,
                    currency=limit.currency
                )
    
    async def link_clause_to_exclusion(
        self, 
        clause_id: str, 
        exclusion_id: str,
        relationship_type: str = "LIMITS"
    ):
        """Create relationship between clause and exclusion."""
        
        async with self.driver.session() as session:
            await session.run(f"""
                MATCH (c:Clause {{clause_id: $clause_id}})
                MATCH (e:Exclusion {{exclusion_id: $exclusion_id}})
                MERGE (c)-[:{relationship_type}]->(e)
            """,
                clause_id=clause_id,
                exclusion_id=exclusion_id
            )
    
    async def find_applicable_coverage(
        self, 
        policy_id: str, 
        claim_type: str
    ) -> list[dict]:
        """Find coverage that applies to a claim type."""
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (p:Policy {policy_id: $policy_id})-[:PROVIDES_COVERAGE]->(cov:Coverage)
                WHERE toLower(cov.coverage_type) CONTAINS toLower($claim_type)
                RETURN cov.coverage_id as coverage_id,
                       cov.coverage_type as coverage_type,
                       cov.limit_amount as limit_amount,
                       cov.deductible as deductible
            """,
                policy_id=policy_id,
                claim_type=claim_type
            )
            return [record.data() async for record in result]
    
    async def find_exclusions_for_claim(
        self, 
        policy_id: str, 
        claim_description: str
    ) -> list[dict]:
        """Find exclusions that might apply to a claim."""
        
        # This uses full-text search - you'd need to create an index
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (p:Policy {policy_id: $policy_id})-[:HAS_EXCLUSION]->(e:Exclusion)
                RETURN e.exclusion_id as exclusion_id,
                       e.category as category,
                       e.description as description
            """,
                policy_id=policy_id
            )
            return [record.data() async for record in result]
    
    async def get_policy_graph(self, policy_id: str) -> dict:
        """Get complete policy graph for visualization."""
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (p:Policy {policy_id: $policy_id})
                OPTIONAL MATCH (p)-[:HAS_CLAUSE]->(c:Clause)
                OPTIONAL MATCH (p)-[:HAS_EXCLUSION]->(e:Exclusion)
                OPTIONAL MATCH (p)-[:PROVIDES_COVERAGE]->(cov:Coverage)
                RETURN p, collect(DISTINCT c) as clauses, 
                       collect(DISTINCT e) as exclusions,
                       collect(DISTINCT cov) as coverages
            """,
                policy_id=policy_id
            )
            record = await result.single()
            return record.data() if record else None