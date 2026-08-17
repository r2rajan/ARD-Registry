"""Orchestrator tools - ARD discovery + A2A invocation for all specialist agents.

Implements:
- discover_agent: POST /search to ARD registry, return top match
- invoke_flight_specialist: Invoke Partner A's flight & hotel agent
- invoke_payment_processor: Invoke Partner B's payment agent
- invoke_currency_exchange: Invoke Partner B's currency agent
- invoke_local_activities: Invoke inhouse activities agent (no discovery)
"""

import json
import os
import time
from uuid import uuid4

import boto3
from strands import tool

# Configuration from environment variables
REGISTRY_URL = os.environ.get(
    "ARD_REGISTRY_URL",
    "https://w6jdnh5xal.execute-api.us-west-2.amazonaws.com/search",
)
FLIGHT_SPECIALIST_ARN = os.environ.get("FLIGHT_SPECIALIST_ARN", "")
PAYMENT_PROCESSOR_ARN = os.environ.get("PAYMENT_PROCESSOR_ARN", "")
CURRENCY_EXCHANGE_ARN = os.environ.get("CURRENCY_EXCHANGE_ARN", "")
LOCAL_ACTIVITIES_ARN = os.environ.get("LOCAL_ACTIVITIES_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")


def _get_agentcore_client():
    """Get a fresh bedrock-agentcore client."""
    return boto3.client("bedrock-agentcore", region_name=REGION)


def _invoke_a2a(runtime_arn: str, message_text: str, max_retries: int = 2) -> dict:
    """Invoke an AgentCore A2A runtime using the boto3 SDK."""
    session_id = str(uuid4())
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": f"req-{uuid4().hex[:8]}",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message_text}],
                "messageId": str(uuid4()),
            }
        },
    })

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            client = _get_agentcore_client()
            response = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                runtimeSessionId=session_id,
                qualifier="DEFAULT",
                contentType="application/json",
                accept="application/json",
                payload=payload.encode("utf-8"),
            )
            body = response["response"].read().decode("utf-8")
            return json.loads(body)
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    return {"error": last_error}


def _extract_response_text(result: dict) -> str:
    """Extract text from an A2A response."""
    if "error" in result:
        return f"Error: {result['error']}"
    try:
        artifacts = result.get("result", {}).get("artifacts", [])
        if artifacts:
            parts = artifacts[0].get("parts", [])
            text_parts = [p["text"] for p in parts if p.get("kind") == "text"]
            return "\n".join(text_parts)
        return str(result)
    except Exception as e:
        return f"Failed to parse response: {e}"


@tool
def discover_agent(need: str) -> str:
    """Search the ARD Registry to find a specialist agent for a given need.

    Args:
        need: Natural language description of what kind of agent is needed
              (e.g., "flight and hotel booking agent", "payment processing")

    Returns:
        JSON string with the discovery result: identifier, displayName,
        score, and source domain.
    """
    import requests

    search_body = {
        "query": {
            "text": need,
            "filter": {"type": ["application/a2a-agent-card+json"]},
        },
        "pageSize": 3,
    }

    try:
        response = requests.post(
            REGISTRY_URL,
            json=search_body,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as e:
        return json.dumps({"error": f"Registry search failed: {str(e)}"})

    if not results:
        return json.dumps({"error": "No matching agent found"})

    top = results[0]
    return json.dumps({
        "identifier": top.get("identifier"),
        "displayName": top.get("displayName"),
        "score": top.get("score"),
        "source": top.get("source"),
        "discovery_method": "ARD registry POST /search",
    }, indent=2)


@tool
def invoke_flight_specialist(message: str) -> str:
    """Invoke the Flight & Hotel Specialist agent (Partner A, discovered via ARD).

    Args:
        message: Query about flights and hotels (e.g., "Find flights from SFO to
                 Tokyo departing 2025-04-01, return 2025-04-05, and a mid-range hotel")

    Returns:
        The agent's response with flight and hotel options.
    """
    if not FLIGHT_SPECIALIST_ARN:
        return json.dumps({"error": "Flight specialist ARN not configured"})

    result = _invoke_a2a(FLIGHT_SPECIALIST_ARN, message)
    return _extract_response_text(result)


@tool
def invoke_payment_processor(message: str) -> str:
    """Invoke the Payment Processing agent (Partner B, discovered via ARD).

    Args:
        message: Payment request (e.g., "Process a payment of 1500 USD for flight
                 booking, card ending 4242")

    Returns:
        The agent's response with transaction details.
    """
    if not PAYMENT_PROCESSOR_ARN:
        return json.dumps({"error": "Payment processor ARN not configured"})

    result = _invoke_a2a(PAYMENT_PROCESSOR_ARN, message)
    return _extract_response_text(result)


@tool
def invoke_currency_exchange(message: str) -> str:
    """Invoke the Currency Exchange agent (Partner B, discovered via ARD).

    Args:
        message: Currency conversion request (e.g., "Convert 3000 USD to Japanese Yen")

    Returns:
        The agent's response with conversion details and rates.
    """
    if not CURRENCY_EXCHANGE_ARN:
        return json.dumps({"error": "Currency exchange ARN not configured"})

    result = _invoke_a2a(CURRENCY_EXCHANGE_ARN, message)
    return _extract_response_text(result)


@tool
def invoke_local_activities(message: str) -> str:
    """Invoke the Local Activities agent (inhouse, called directly by ARN, no ARD).

    Args:
        message: Request for local activities (e.g., "Suggest activities in Tokyo
                 for 5 days, mix of culture, food, and nature")

    Returns:
        The agent's response with activity recommendations.
    """
    if not LOCAL_ACTIVITIES_ARN:
        return json.dumps({"error": "Local activities ARN not configured"})

    result = _invoke_a2a(LOCAL_ACTIVITIES_ARN, message)
    return _extract_response_text(result)
