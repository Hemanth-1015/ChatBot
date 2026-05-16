"""
AI Processing Service for Autonomous Workflow Agent.

This module implements the LangChain-based AI processing logic
that analyzes tickets and proposes actions in shadow mode.
"""

import os
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel as LangChainBaseModel, Field as LangChainField
from sqlmodel import Session, select

from db.models import Ticket, TicketMessage, AIActionProposal, ApprovalStatus


# ==================== PYDANTIC MODELS FOR LANGCHAIN ====================

class AIActionOutput(LangChainBaseModel):
    """
    Strict output structure for AI action proposal.
    The LLM must return exactly these two keys in valid JSON format.
    """
    proposed_action: str = LangChainField(
        description="The recommended triage action. Must be exactly one of: 'route_to_senior', 'send_kb_article', 'request_clarification', 'standard_queue'"
    )
    llm_reasoning: str = LangChainField(
        description="A concise 1-2 sentence explanation of WHY this action was chosen, based on customer sentiment, urgency, or request type"
    )


# ==================== LANGCHAIN PROMPT TEMPLATE ====================

# Initialize JSON parser with strict schema validation
json_parser = JsonOutputParser(pydantic_object=AIActionOutput)

ACTION_ANALYSIS_PROMPT = PromptTemplate.from_template(
    """You are an Expert Customer Support Triage Agent. Your role is to analyze incoming customer support tickets and determine the optimal routing action.

TRIAGE RULES - Analyze the ticket and select ONE action:

1. route_to_senior
   Use when: Complex technical issues, angry/frustrated customers, high-value accounts, or situations requiring expertise beyond standard agents

2. send_kb_article
   Use when: Common HOW-TO questions, feature explanations, or issues documented in knowledge base (password resets, setup guides, FAQs)

3. request_clarification
   Use when: Insufficient information to resolve, vague problem descriptions, or missing critical details (order numbers, account IDs, error messages)

4. standard_queue
   Use when: General inquiries, routine requests, or straightforward issues that any agent can handle

STRICT OUTPUT REQUIREMENTS:
You must respond with a raw JSON object containing exactly these two keys:
- "proposed_action": Must be exactly one of the four strings above (no variations, no additional actions)
- "llm_reasoning": A concise 1-2 sentence explanation of WHY you chose this action based on the customer's sentiment, urgency, or request type

Do not include markdown formatting, code blocks, or any text outside the JSON object.

CUSTOMER TICKET MESSAGE:
{ticket_message}

{format_instructions}
""",
    partial_variables={"format_instructions": json_parser.get_format_instructions()}
)


# ==================== AI PROCESSOR SERVICE ====================

class AIProcessorService:
    """
    Service for processing tickets with AI in shadow mode.
    
    Shadow Mode: AI proposes actions but NEVER executes them.
    All proposals go to ai_action_proposals table for human review.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the AI processor with Live OpenAI integration."""
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required. Set it in your .env file or pass it directly.")
        
        # Initialize ChatOpenAI with deterministic settings (temperature=0)
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # or use "gpt-3.5-turbo" for cost efficiency
            temperature=0,       # Deterministic outputs for consistent decisions
            api_key=self.api_key,
            model_kwargs={"response_format": {"type": "json_object"}}  # Force JSON output
        )
        # Note: json_parser is defined at module level with format_instructions integrated
    
    def fetch_ticket_message(self, session: Session, ticket_id: UUID) -> Optional[str]:
        """Fetch the customer's message body for a given ticket."""
        statement = select(TicketMessage).where(
            TicketMessage.ticket_id == ticket_id,
            TicketMessage.sender_type == "customer"
        )
        result = session.exec(statement).first()
        return result.message_body if result else None
    
    def analyze_with_llm(self, message_body: str) -> Dict[str, Any]:
        """
        Analyze ticket using LangChain LCEL pipeline: Prompt -> ChatOpenAI -> JsonOutputParser.
        
        Pipeline:
        1. ACTION_ANALYSIS_PROMPT formats the input with {ticket_message}
        2. ChatOpenAI (temperature=0) generates deterministic JSON response
        3. JsonOutputParser validates and parses into AIActionOutput schema
        
        Returns dict with:
        - proposed_action: One of 4 triage actions
        - llm_reasoning: Explanation for the choice
        
        On API timeout or parsing error: Falls back to 'standard_queue' for human review.
        """
        # Build LCEL chain: Prompt Template -> ChatOpenAI -> JsonOutputParser
        chain = ACTION_ANALYSIS_PROMPT | self.llm | json_parser
        
        try:
            # Invoke chain with ticket message from database
            result = chain.invoke({"ticket_message": message_body})
            
            # Extract validated fields from parsed JSON
            return {
                "proposed_action": result["proposed_action"],
                "llm_reasoning": result["llm_reasoning"]
            }
            
        except Exception as e:
            # Handle OpenAI API timeouts, rate limits, or JSON parsing errors
            error_msg = str(e).lower()
            
            if "timeout" in error_msg or "timed out" in error_msg:
                fallback_reason = "OpenAI API timeout. Falling back to standard queue for human review."
            elif "rate limit" in error_msg or "429" in error_msg:
                fallback_reason = "OpenAI rate limit exceeded. Falling back to standard queue for human review."
            elif "json" in error_msg or "parse" in error_msg:
                fallback_reason = "Failed to parse LLM response as JSON. Falling back to standard queue for human review."
            else:
                fallback_reason = f"AI analysis failed ({str(e)}). Falling back to standard queue for human review."
            
            # Safe fallback: route to standard queue for human agent review
            return {
                "proposed_action": "standard_queue",
                "llm_reasoning": fallback_reason
            }
    
    def create_action_proposal(
        self,
        session: Session,
        ticket_id: UUID,
        proposed_action: str,
        llm_reasoning: str
    ) -> AIActionProposal:
        """
        Insert a new AI action proposal into the database.
        
        SHADOW MODE: This only creates a proposal for human review.
        The action is NOT executed.
        """
        proposal = AIActionProposal(
            id=uuid4(),
            ticket_id=ticket_id,
            proposed_action=proposed_action,
            llm_reasoning=llm_reasoning,
            approval_status=ApprovalStatus.PENDING
        )
        session.add(proposal)
        session.flush()
        return proposal
    
    def update_ticket_status(
        self,
        session: Session,
        ticket_id: UUID,
        new_status: str
    ) -> Optional[Ticket]:
        """Update the ticket's current status."""
        statement = select(Ticket).where(Ticket.id == ticket_id)
        ticket = session.exec(statement).first()
        
        if ticket:
            ticket.current_status = new_status
            session.add(ticket)
        
        return ticket
    
    def process_ticket(self, session: Session, ticket_id: UUID) -> Optional[AIActionProposal]:
        """
        Main entry point: Process a ticket with AI in shadow mode.
        
        Steps:
        1. Fetch the customer message
        2. Analyze with LLM to get proposed action and reasoning
        3. Create action proposal (pending human approval)
        4. Update ticket status to 'awaiting_human'
        5. Return the created proposal
        
        SHADOW MODE: AI never executes actions directly.
        """
        # Step 1: Fetch message
        message_body = self.fetch_ticket_message(session, ticket_id)
        if not message_body:
            return None
        
        # Step 2: Analyze with LLM
        analysis = self.analyze_with_llm(message_body)
        
        # Step 3: Create action proposal (SHADOW MODE - just a proposal)
        proposal = self.create_action_proposal(
            session=session,
            ticket_id=ticket_id,
            proposed_action=analysis["proposed_action"],
            llm_reasoning=analysis["llm_reasoning"]
        )
        
        # Step 4: Update ticket status to awaiting_human
        self.update_ticket_status(session, ticket_id, "awaiting_human")
        
        # Commit all changes
        session.commit()
        
        return proposal


# ==================== CONVENIENCE FUNCTION ====================

def process_ticket_with_ai(session: Session, ticket_id: UUID) -> Optional[AIActionProposal]:
    """
    Convenience function to process a ticket with AI.
    
    Usage:
        from services.ai_service import process_ticket_with_ai
        proposal = process_ticket_with_ai(session, ticket_id)
    """
    service = AIProcessorService()
    return service.process_ticket(session, ticket_id)
