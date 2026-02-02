# app/parsers/policy_extractor.py
import json
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_huggingface import HuggingFaceEndpoint
from app.models.policy import PolicyDocument, Clause, CoverageLimit, Exclusion

class PolicyExtractor:
    """Extract structured information from policy documents."""
    
    def __init__(self, model_name: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"):
        self.llm = HuggingFaceEndpoint(
            repo_id=model_name,
            temperature=0.1,  # Low temp for structured extraction
            max_new_tokens=4096
        )
        self.json_parser = JsonOutputParser()
    
    async def extract_clauses(self, text: str) -> list[Clause]:
        """Extract all clauses from policy text."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an insurance policy analyst. Extract all clauses from the policy text.
            
For each clause, identify:
- clause_id: Unique identifier (e.g., "CL-001")
- clause_type: One of "coverage", "exclusion", "condition", "limitation"
- title: Brief title
- description: Full clause text
- section_reference: Section number from document
- conditions: Any conditions that apply

Return as JSON array."""),
            ("human", "Policy text:\n{text}")
        ])
        
        chain = prompt | self.llm | self.json_parser
        result = await chain.ainvoke({"text": text})
        
        return [Clause(**clause) for clause in result]
    
    async def extract_coverage_limits(self, text: str) -> list[CoverageLimit]:
        """Extract coverage limits and deductibles."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract all coverage limits from this insurance policy.

For each coverage, extract:
- coverage_type: What is covered (e.g., "hospitalization", "collision")
- limit_amount: Maximum coverage amount (number only)
- deductible: Deductible amount (number only)
- currency: Currency code (default USD)
- per_incident: Is this per incident? (true/false)
- annual_aggregate: Annual maximum if mentioned (number or null)

Return as JSON array. Use 0 for unknown amounts."""),
            ("human", "Policy text:\n{text}")
        ])
        
        chain = prompt | self.llm | self.json_parser
        result = await chain.ainvoke({"text": text})
        
        return [CoverageLimit(**limit) for limit in result]
    
    async def extract_exclusions(self, text: str) -> list[Exclusion]:
        """Extract all exclusions from policy."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract all EXCLUSIONS from this insurance policy.
Exclusions are things NOT covered by the policy.

For each exclusion:
- exclusion_id: Unique ID (e.g., "EX-001")
- category: Category (e.g., "pre-existing conditions", "intentional acts", "war")
- description: Full exclusion text
- exceptions: Cases where exclusion doesn't apply (if any)

Return as JSON array."""),
            ("human", "Policy text:\n{text}")
        ])
        
        chain = prompt | self.llm | self.json_parser
        result = await chain.ainvoke({"text": text})
        
        return [Exclusion(**exc) for exc in result]
    
    async def extract_full_policy(
        self, 
        text: str, 
        policy_id: str,
        metadata: dict
    ) -> PolicyDocument:
        """Extract complete structured policy."""
        
        # Run all extractions
        clauses = await self.extract_clauses(text)
        limits = await self.extract_coverage_limits(text)
        exclusions = await self.extract_exclusions(text)
        
        return PolicyDocument(
            policy_id=policy_id,
            policy_number=metadata.get("policy_number", ""),
            policy_type=metadata.get("policy_type", "health"),
            holder_name=metadata.get("holder_name", ""),
            effective_date=metadata.get("effective_date"),
            expiration_date=metadata.get("expiration_date"),
            clauses=clauses,
            coverage_limits=limits,
            exclusions=exclusions,
            raw_text=text,
            chunk_ids=[]  # Will be filled after vectorization
        )