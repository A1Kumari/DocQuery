 uvicorn app.main:app --reload

 .\venv\Scripts\Activate.ps1

 Ready to Build ClaimCheck?
I can give you the complete implementation:

Policy Parser - Extract clauses, limits, exclusions from PDF
Neo4j Graph Builder - Model policy relationships
Claim Validator Agent - LangGraph workflow
Fraud Detection - Pattern matching
API Endpoints - Full FastAPI implementation
Evaluation Pipeline - Test with sample claims


Complete Route Reference Table
Route	Method	Status	Description
ROOT			
/	GET	✅ Working	API info
/health	GET	✅ Working	Health check
DOCUMENTS			
/api/v1/documents/	GET	✅ Working	List documents
/api/v1/documents/upload	POST	✅ Working	Upload document
/api/v1/documents/{doc_id}	GET	✅ Working	Get document
/api/v1/documents/{doc_id}	DELETE	✅ Mock	Delete document
POLICIES			
/api/v1/policies/	GET	✅ Fixed	List policies
/api/v1/policies/upload	POST	✅ Mock	Upload policy
/api/v1/policies/{id}	GET	✅ Mock	Get policy
/api/v1/policies/{id}/graph	GET	✅ Mock	Get graph
/api/v1/policies/{id}/clauses	GET	✅ Mock	Get clauses
/api/v1/policies/{id}/exclusions	GET	✅ Mock	Get exclusions
/api/v1/policies/{id}/coverage	GET	✅ Mock	Get coverage
CLAIMS			
/api/v1/claims/	GET	✅ Fixed	List claims
/api/v1/claims/	POST	✅ Mock	Submit claim
/api/v1/claims/{id}	GET	✅ Mock	Get claim
/api/v1/claims/{id}/validate	POST	✅ Mock	Validate claim
/api/v1/claims/{id}/status	GET	✅ Mock	Get status
/api/v1/claims/{id}/fraud-report	GET	✅ Mock	Get fraud report
DASHBOARD			
/api/v1/dashboard/stats	GET	✅ NEW	Dashboard stats
/api/v1/dashboard/recent-claims	GET	✅ NEW	Recent claims
/api/v1/dashboard/recent-policies	GET	✅ NEW	Recent policies
CHAT			
/api/v1/chat/query	POST	✅ Working	Single Q&A
/api/v1/chat/conversation	POST	✅ Working	Chat with history
ADMIN			
/api/v1/admin/health	GET	✅ Working	Health check
/api/v1/admin/stats	GET	✅ Working	System stats
/api/v1/admin/neo4j/status	GET	✅ Working	Neo4j status