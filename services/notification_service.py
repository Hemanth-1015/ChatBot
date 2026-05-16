"""
Notification Service for Autonomous Workflow Agent.

This module handles external notifications (Discord, etc.) for AI actions
and system events.
"""

import os
import requests
from datetime import datetime, timezone
from typing import Optional


def send_discord_alert(ticket_id: str, action: str, reasoning: str) -> Optional[dict]:
    """
    Send a professional Discord embed notification when an AI action is approved.
    
    Args:
        ticket_id: The UUID of the ticket (truncated for display)
        action: The approved action name (e.g., 'route_to_senior')
        reasoning: The AI's reasoning for the action
    
    Returns:
        dict: Discord API response if successful, None otherwise
    """
    # Load Discord webhook URL from environment
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("[WARNING] DISCORD_WEBHOOK_URL not set in environment. Skipping Discord notification.")
        return None
    
    # Format the action name for display (convert snake_case to Title Case)
    formatted_action = action.replace('_', ' ').title()
    
    # Truncate ticket ID for display (first 8 chars)
    short_ticket_id = ticket_id[:8] if len(ticket_id) > 8 else ticket_id
    
    # Construct Discord embed payload
    # Discord embeds provide rich formatting with colors, fields, timestamps
    payload = {
        "embeds": [
            {
                "title": f"🚨 AI Action Approved: {formatted_action}",
                "description": f"An AI-proposed action has been approved and is being executed.",
                "color": 0x00FF00,  # Green color (success)
                "fields": [
                    {
                        "name": "🎫 Ticket ID",
                        "value": f"`{short_ticket_id}...`",
                        "inline": True
                    },
                    {
                        "name": "⚡ Action",
                        "value": f"`{action}`",
                        "inline": True
                    },
                    {
                        "name": "🤖 AI Reasoning",
                        "value": reasoning[:1024] if len(reasoning) > 1024 else reasoning,  # Discord field limit
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Autonomous Workflow Agent • Shadow Mode"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }
    
    try:
        # Send POST request to Discord webhook
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10  # 10 second timeout
        )
        
        # Check for successful delivery
        if response.status_code == 204:
            print(f"[INFO] Discord notification sent successfully for ticket {short_ticket_id}")
            return {"status": "success", "ticket_id": ticket_id}
        else:
            print(f"[WARNING] Discord notification failed with status {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[ERROR] Discord webhook request timed out after 10 seconds")
        return None
        
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Failed to connect to Discord webhook. Check network or webhook URL.")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Discord webhook request failed: {str(e)}")
        return None


def send_discord_rejection_alert(ticket_id: str, action: str, rejection_reason: str, reviewer_id: str) -> Optional[dict]:
    """
    Send a Discord notification when an AI action is rejected (for ML training feedback).
    
    Args:
        ticket_id: The UUID of the ticket
        action: The rejected action name
        rejection_reason: Why the human rejected it
        reviewer_id: Who rejected it
    
    Returns:
        dict: Discord API response if successful, None otherwise
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("[WARNING] DISCORD_WEBHOOK_URL not set. Skipping Discord notification.")
        return None
    
    formatted_action = action.replace('_', ' ').title()
    short_ticket_id = ticket_id[:8] if len(ticket_id) > 8 else ticket_id
    
    payload = {
        "embeds": [
            {
                "title": f"❌ AI Action Rejected: {formatted_action}",
                "description": f"An AI-proposed action was rejected by human review.",
                "color": 0xFF0000,  # Red color (rejection)
                "fields": [
                    {
                        "name": "🎫 Ticket ID",
                        "value": f"`{short_ticket_id}...`",
                        "inline": True
                    },
                    {
                        "name": "⚡ Rejected Action",
                        "value": f"`{action}`",
                        "inline": True
                    },
                    {
                        "name": "👤 Reviewer",
                        "value": f"`{reviewer_id}`",
                        "inline": True
                    },
                    {
                        "name": "📝 Rejection Reason",
                        "value": rejection_reason[:1024] if len(rejection_reason) > 1024 else rejection_reason,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Autonomous Workflow Agent • Feedback Logged"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 204:
            print(f"[INFO] Discord rejection alert sent for ticket {short_ticket_id}")
            return {"status": "success", "ticket_id": ticket_id}
        else:
            print(f"[WARNING] Discord alert failed: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Discord webhook failed: {str(e)}")
        return None
