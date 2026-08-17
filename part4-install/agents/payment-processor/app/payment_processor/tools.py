"""Mock payment tools for the Payment Processing agent.

Simulates payment processing with deterministic responses.
No external payment API required.
"""

import hashlib
import json
import random
from datetime import datetime

from strands import tool


def _seed_from(*args) -> int:
    raw = "|".join(str(a) for a in args)
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


@tool
def process_payment(amount: float, currency: str, description: str, card_last_four: str) -> str:
    """Process a payment transaction.

    Args:
        amount: Payment amount
        currency: Currency code (e.g., "USD", "EUR", "JPY")
        description: Payment description (e.g., "Flight booking SFO-NRT")
        card_last_four: Last four digits of the card

    Returns:
        JSON string with transaction ID, status, and receipt details.
    """
    seed = _seed_from(amount, currency, description, card_last_four)
    rng = random.Random(seed)

    txn_id = f"TXN-{rng.randint(100000, 999999)}"
    success = rng.random() > 0.05  # 95% success rate

    result = {
        "transaction_id": txn_id,
        "status": "approved" if success else "declined",
        "amount": amount,
        "currency": currency,
        "description": description,
        "card_ending": card_last_four,
        "timestamp": datetime.now().isoformat(),
        "authorization_code": f"AUTH-{rng.randint(10000, 99999)}" if success else None,
        "message": "Payment processed successfully" if success else "Insufficient funds",
    }
    return json.dumps(result, indent=2)


@tool
def issue_refund(transaction_id: str, amount: float, reason: str) -> str:
    """Issue a refund for a previous transaction.

    Args:
        transaction_id: Original transaction ID to refund
        amount: Refund amount (can be partial)
        reason: Reason for refund (e.g., "cancelled flight", "hotel no-show")

    Returns:
        JSON string with refund ID, status, and processing details.
    """
    seed = _seed_from(transaction_id, amount, reason)
    rng = random.Random(seed)

    refund_id = f"RFD-{rng.randint(100000, 999999)}"

    result = {
        "refund_id": refund_id,
        "original_transaction": transaction_id,
        "status": "processed",
        "refund_amount": amount,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "estimated_return": "3-5 business days",
    }
    return json.dumps(result, indent=2)
