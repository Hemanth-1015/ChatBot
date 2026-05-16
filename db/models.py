from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Text
from sqlmodel import Field, Relationship, SQLModel


# Enum classes for type safety
class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SenderType(str, Enum):
    CUSTOMER = "customer"
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ==================== TICKETS TABLE ====================
class TicketBase(SQLModel):
    customer_id: str = Field(index=True)
    current_status: str = Field(default=TicketStatus.OPEN, index=True)
    priority_level: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Ticket(TicketBase, table=True):
    __tablename__ = "tickets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Relationships
    messages: List["TicketMessage"] = Relationship(
        back_populates="ticket",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    action_proposals: List["AIActionProposal"] = Relationship(
        back_populates="ticket",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# ==================== TICKET_MESSAGES TABLE ====================
class TicketMessageBase(SQLModel):
    sender_type: str = Field(index=True)
    message_body: str = Field(sa_column=Text)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TicketMessage(TicketMessageBase, table=True):
    __tablename__ = "ticket_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign Key to tickets
    ticket_id: UUID = Field(
        foreign_key="tickets.id",
        nullable=False,
        index=True
    )

    # Relationship
    ticket: Optional[Ticket] = Relationship(back_populates="messages")


# ==================== AI_ACTION_PROPOSALS TABLE ====================
class AIActionProposalBase(SQLModel):
    proposed_action: str = Field()
    llm_reasoning: str = Field(sa_column=Text)
    approval_status: str = Field(default=ApprovalStatus.PENDING, index=True)


class AIActionProposal(AIActionProposalBase, table=True):
    __tablename__ = "ai_action_proposals"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign Key to tickets
    ticket_id: UUID = Field(
        foreign_key="tickets.id",
        nullable=False,
        index=True
    )

    # Relationships
    ticket: Optional[Ticket] = Relationship(back_populates="action_proposals")
    feedback_logs: List["HumanFeedbackLog"] = Relationship(
        back_populates="proposal",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# ==================== HUMAN_FEEDBACK_LOGS TABLE ====================
class HumanFeedbackLogBase(SQLModel):
    reviewer_id: str = Field(index=True)
    rejection_reason: Optional[str] = Field(default=None, sa_column=Text)
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class HumanFeedbackLog(HumanFeedbackLogBase, table=True):
    __tablename__ = "human_feedback_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign Key to ai_action_proposals
    proposal_id: UUID = Field(
        foreign_key="ai_action_proposals.id",
        nullable=False,
        index=True
    )

    # Relationship
    proposal: Optional[AIActionProposal] = Relationship(back_populates="feedback_logs")
