"""
Stripe payment stub endpoints for FairPrice Watchdog
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()


class CheckoutResponse(BaseModel):
    """Response model for checkout session creation"""
    session_id: str
    url: str


class WebhookResponse(BaseModel):
    """Response model for webhook"""
    status: str


@router.post("/stripe/checkout", response_model=CheckoutResponse)
async def create_checkout_session(request: Request) -> CheckoutResponse:
    """
    Create a fake Stripe checkout session (stub implementation)
    
    This is a stub endpoint for development/testing purposes.
    In production, this would integrate with actual Stripe API.
    
    Returns:
        CheckoutResponse: Fake session ID and checkout URL
    """
    return CheckoutResponse(
        session_id="stub_123",
        url="https://stripe.com/stub"
    )


@router.post("/stripe/webhook", response_model=WebhookResponse)
async def stripe_webhook(request: Request) -> WebhookResponse:
    """
    Handle Stripe webhook events (stub implementation)
    
    This is a stub endpoint for development/testing purposes.
    In production, this would verify webhook signatures and process events.
    
    Returns:
        WebhookResponse: Acknowledgment of webhook receipt
    """
    # In production, you would:
    # 1. Verify the webhook signature
    # 2. Parse the event data
    # 3. Process the event based on type
    # 4. Update database accordingly
    
    return WebhookResponse(status="received")


# Made with Bob