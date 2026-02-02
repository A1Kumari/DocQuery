# app/api/v1/dashboard.py
from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# ===================
# Response Models
# ===================

class ClaimsByStatus(BaseModel):
    submitted: int = 0
    under_review: int = 0
    approved: int = 0
    denied: int = 0
    flagged_fraud: int = 0

class ClaimsByType(BaseModel):
    hospitalization: int = 0
    surgery: int = 0
    medication: int = 0
    accident: int = 0
    other: int = 0

class FinancialStats(BaseModel):
    total_claimed: float = 0.0
    total_approved: float = 0.0
    total_denied: float = 0.0
    average_claim: float = 0.0
    approval_rate: float = 0.0

class FraudMetrics(BaseModel):
    total_flagged: int = 0
    average_fraud_score: float = 0.0
    high_risk_claims: int = 0

class RecentActivity(BaseModel):
    claims_today: int = 0
    claims_this_week: int = 0
    policies_this_month: int = 0

class OverviewStats(BaseModel):
    total_policies: int = 0
    active_policies: int = 0
    total_claims: int = 0
    pending_claims: int = 0
    total_documents: int = 0

class DashboardStats(BaseModel):
    overview: OverviewStats
    claims_by_status: ClaimsByStatus
    claims_by_type: ClaimsByType
    financials: FinancialStats
    fraud_metrics: FraudMetrics
    recent_activity: RecentActivity

class RecentClaimItem(BaseModel):
    claim_id: str
    claim_number: str
    claimant_name: str
    claim_type: str
    claimed_amount: float
    status: str
    submitted_at: datetime

class RecentClaimsResponse(BaseModel):
    claims: List[RecentClaimItem]

class RecentPolicyItem(BaseModel):
    policy_id: str
    policy_number: str
    holder_name: str
    policy_type: str
    effective_date: str
    expiration_date: str
    status: str
    created_at: datetime

class RecentPoliciesResponse(BaseModel):
    policies: List[RecentPolicyItem]

# ===================
# Endpoints
# ===================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get comprehensive dashboard statistics.
    Returns overview, claims breakdown, financials, and fraud metrics.
    """
    # TODO: Implement actual database queries
    # For now, return mock data structure
    
    from app.services.store import list_files
    files = list_files()
    
    return DashboardStats(
        overview=OverviewStats(
            total_policies=0,  # TODO: Get from policy store
            active_policies=0,
            total_claims=0,    # TODO: Get from claims store
            pending_claims=0,
            total_documents=len(files)
        ),
        claims_by_status=ClaimsByStatus(
            submitted=0,
            under_review=0,
            approved=0,
            denied=0,
            flagged_fraud=0
        ),
        claims_by_type=ClaimsByType(
            hospitalization=0,
            surgery=0,
            medication=0,
            accident=0,
            other=0
        ),
        financials=FinancialStats(
            total_claimed=0.0,
            total_approved=0.0,
            total_denied=0.0,
            average_claim=0.0,
            approval_rate=0.0
        ),
        fraud_metrics=FraudMetrics(
            total_flagged=0,
            average_fraud_score=0.0,
            high_risk_claims=0
        ),
        recent_activity=RecentActivity(
            claims_today=0,
            claims_this_week=0,
            policies_this_month=0
        )
    )

@router.get("/recent-claims", response_model=RecentClaimsResponse)
async def get_recent_claims(
    limit: int = Query(5, ge=1, le=20, description="Number of claims to return")
):
    """
    Get list of recent claims for dashboard display.
    """
    # TODO: Implement actual database query
    # For now, return empty list
    return RecentClaimsResponse(claims=[])

@router.get("/recent-policies", response_model=RecentPoliciesResponse)
async def get_recent_policies(
    limit: int = Query(5, ge=1, le=20, description="Number of policies to return")
):
    """
    Get list of recent policies for dashboard display.
    """
    # TODO: Implement actual database query
    # For now, return empty list
    return RecentPoliciesResponse(policies=[])

@router.get("/claims-trend")
async def get_claims_trend(
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze")
):
    """
    Get claims trend data for charts.
    """
    # TODO: Implement actual trend calculation
    return {
        "period_days": days,
        "trend": [],
        "total_claims": 0,
        "average_per_day": 0.0
    }

@router.get("/policy-expiry-alerts")
async def get_policy_expiry_alerts(
    days_ahead: int = Query(30, ge=7, le=90, description="Days to look ahead")
):
    """
    Get policies expiring soon.
    """
    # TODO: Implement actual query
    return {
        "days_ahead": days_ahead,
        "expiring_policies": [],
        "total_expiring": 0
    }