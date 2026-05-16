"""
Autonomous Workflow Agent - FastAPI Application
Entry point for the application.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from db.database import init_db, get_session
from db.models import (
    Ticket, TicketMessage, TicketPriority, SenderType,
    AIActionProposal, HumanFeedbackLog, ApprovalStatus
)
from services.ai_service import process_ticket_with_ai
from services.notification_service import send_discord_alert


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="Autonomous Workflow Agent",
    description="Backend API for autonomous ticket management system",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ==================== PYDANTIC SCHEMAS ====================

class TicketIngestRequest(BaseModel):
    """Incoming webhook payload for new ticket ingestion."""
    customer_id: str = Field(..., description="Unique identifier for the customer")
    message_body: str = Field(..., description="Initial message content from the customer")
    priority_level: str = Field(..., description="Priority level: low, medium, high, critical")


class TicketIngestResponse(BaseModel):
    """Response after successful ticket creation."""
    ticket_id: UUID
    message: str = "Ticket created successfully"


class ProposalResponse(BaseModel):
    """Response model for AI action proposal."""
    id: UUID
    ticket_id: UUID
    proposed_action: str
    llm_reasoning: str
    approval_status: str


class RejectProposalRequest(BaseModel):
    """Request payload for rejecting a proposal."""
    rejection_reason: str = Field(..., description="Explanation for why the proposal was rejected")
    reviewer_id: str = Field(..., description="Identifier of the human reviewer")


class ApprovalResponse(BaseModel):
    """Response after approving a proposal."""
    proposal_id: UUID
    message: str
    executed_action: str


class RejectionResponse(BaseModel):
    """Response after rejecting a proposal."""
    proposal_id: UUID
    message: str
    feedback_log_id: UUID


# ==================== WEBHOOK ENDPOINT ====================

@app.post("/webhook/ticket", response_model=TicketIngestResponse)
def create_ticket_webhook(
    payload: TicketIngestRequest,
    session: Session = Depends(get_session)
) -> TicketIngestResponse:
    """
    Ingest a new helpdesk ticket via webhook.
    
    Creates a new ticket and associated customer message in the database,
    then triggers AI analysis to propose next actions (shadow mode).
    """
    # Create new ticket
    new_ticket = Ticket(
        id=uuid4(),
        customer_id=payload.customer_id,
        current_status="open",
        priority_level=payload.priority_level,
        created_at=datetime.utcnow()
    )
    session.add(new_ticket)
    session.flush()  # Flush to get the ticket_id

    # Create corresponding customer message
    new_message = TicketMessage(
        id=uuid4(),
        ticket_id=new_ticket.id,
        sender_type=SenderType.CUSTOMER,
        message_body=payload.message_body,
        created_at=datetime.utcnow()
    )
    session.add(new_message)
    session.commit()

    # Trigger AI processing in SHADOW MODE
    # AI will analyze and create a proposal, but NOT execute the action
    try:
        ai_proposal = process_ticket_with_ai(session, new_ticket.id)
        
        if ai_proposal:
            print(f"[SHADOW MODE] AI proposed action '{ai_proposal.proposed_action}' for ticket {new_ticket.id}")
            print(f"[SHADOW MODE] Reasoning: {ai_proposal.llm_reasoning}")
            print(f"[SHADOW MODE] Ticket status updated to 'awaiting_human'")
        else:
            print(f"[WARNING] AI proposal was None for ticket {new_ticket.id} - check if message was found")
    except Exception as e:
        import traceback
        print(f"[ERROR] AI processing failed for ticket {new_ticket.id}: {str(e)}")
        print(traceback.format_exc())

    return TicketIngestResponse(ticket_id=new_ticket.id)


# ==================== PROPOSAL REVIEW ENDPOINTS (HUMAN IN THE LOOP) ====================

@app.get("/proposals/pending", response_model=list[ProposalResponse])
def get_pending_proposals(
    session: Session = Depends(get_session)
) -> list[ProposalResponse]:
    """
    Fetch all pending AI action proposals awaiting human review.
    
    Returns a list of proposals with status 'pending'.
    """
    statement = select(AIActionProposal).where(
        AIActionProposal.approval_status == ApprovalStatus.PENDING
    )
    proposals = session.exec(statement).all()
    
    return [
        ProposalResponse(
            id=proposal.id,
            ticket_id=proposal.ticket_id,
            proposed_action=proposal.proposed_action,
            llm_reasoning=proposal.llm_reasoning,
            approval_status=proposal.approval_status
        )
        for proposal in proposals
    ]


@app.post("/proposals/{proposal_id}/approve", response_model=ApprovalResponse)
def approve_proposal(
    proposal_id: UUID,
    session: Session = Depends(get_session)
) -> ApprovalResponse:
    """
    Approve an AI action proposal and simulate execution.
    
    Updates the proposal status to 'approved', prints execution message,
    and updates the associated ticket status to 'resolved'.
    """
    # Fetch the proposal
    statement = select(AIActionProposal).where(AIActionProposal.id == proposal_id)
    proposal = session.exec(statement).first()
    
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found"
        )
    
    if proposal.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal is already {proposal.approval_status}"
        )
    
    # Update proposal status to approved
    proposal.approval_status = ApprovalStatus.APPROVED
    session.add(proposal)
    
    # Send Discord notification for approved action
    send_discord_alert(
        ticket_id=str(proposal.ticket_id),
        action=proposal.proposed_action,
        reasoning=proposal.llm_reasoning
    )
    
    # Update ticket status to resolved
    ticket_statement = select(Ticket).where(Ticket.id == proposal.ticket_id)
    ticket = session.exec(ticket_statement).first()
    
    if ticket:
        ticket.current_status = "resolved"
        session.add(ticket)
    
    session.commit()
    
    return ApprovalResponse(
        proposal_id=proposal.id,
        message="Proposal approved and action executed",
        executed_action=proposal.proposed_action
    )


@app.post("/proposals/{proposal_id}/reject", response_model=RejectionResponse)
def reject_proposal(
    proposal_id: UUID,
    payload: RejectProposalRequest,
    session: Session = Depends(get_session)
) -> RejectionResponse:
    """
    Reject an AI action proposal with feedback.
    
    Updates the proposal status to 'rejected' and creates a feedback log
    with the rejection reason and reviewer information.
    """
    # Fetch the proposal
    statement = select(AIActionProposal).where(AIActionProposal.id == proposal_id)
    proposal = session.exec(statement).first()
    
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found"
        )
    
    if proposal.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal is already {proposal.approval_status}"
        )
    
    # Update proposal status to rejected
    proposal.approval_status = ApprovalStatus.REJECTED
    session.add(proposal)
    
    # Create human feedback log
    feedback_log = HumanFeedbackLog(
        id=uuid4(),
        proposal_id=proposal_id,
        reviewer_id=payload.reviewer_id,
        rejection_reason=payload.rejection_reason,
        reviewed_at=datetime.utcnow()
    )
    session.add(feedback_log)
    
    session.commit()
    
    return RejectionResponse(
        proposal_id=proposal.id,
        message="Proposal rejected and feedback logged",
        feedback_log_id=feedback_log.id
    )
