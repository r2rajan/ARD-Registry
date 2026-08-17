"""Travel Orchestrator Agent — A2A Agent on Bedrock AgentCore.

Coordinates specialist agents to plan trips. Uses A2AAgent clients to invoke
partner agents over the A2A protocol. Agent connections in agentcore.json
provide the IAM permissions.
"""

import os

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from a2a.client import ClientConfig
from strands import Agent
from strands.agent import A2AAgent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a, build_runtime_url
from model.load import load_model

REGION = os.environ.get("AWS_REGION", "us-west-2")

# Agent ARNs (from environment variables set in agentcore.json)
FLIGHT_SPECIALIST_ARN = os.environ.get("FLIGHT_SPECIALIST_ARN", "")
PAYMENT_PROCESSOR_ARN = os.environ.get("PAYMENT_PROCESSOR_ARN", "")
CURRENCY_EXCHANGE_ARN = os.environ.get("CURRENCY_EXCHANGE_ARN", "")
LOCAL_ACTIVITIES_ARN = os.environ.get("LOCAL_ACTIVITIES_ARN", "")


class SigV4Auth_httpx(httpx.Auth):
    """httpx Auth class that signs requests with AWS SigV4."""

    def __init__(self, region: str = "us-west-2", service: str = "bedrock-agentcore"):
        self.region = region
        self.service = service

    def auth_flow(self, request: httpx.Request):
        # Get fresh credentials
        session = boto3.Session(region_name=self.region)
        credentials = session.get_credentials().get_frozen_credentials()

        # Build an AWSRequest for signing
        aws_request = AWSRequest(
            method=str(request.method),
            url=str(request.url),
            headers=dict(request.headers),
            data=request.content,
        )
        SigV4Auth(credentials, self.service, self.region).add_auth(aws_request)

        # Apply signed headers back to the httpx request
        for key, value in aws_request.headers.items():
            request.headers[key] = value

        yield request


def _create_a2a_agent(arn: str, name: str, description: str) -> A2AAgent:
    """Create an A2AAgent client for an AgentCore-hosted agent."""
    endpoint = build_runtime_url(arn, region=REGION)
    httpx_client = httpx.AsyncClient(
        auth=SigV4Auth_httpx(region=REGION),
        timeout=httpx.Timeout(300.0),
    )
    client_config = ClientConfig(httpx_client=httpx_client, streaming=True)
    return A2AAgent(
        endpoint=endpoint,
        name=name,
        description=description,
        client_config=client_config,
    )


# Create A2A agent clients
flight_agent = _create_a2a_agent(
    FLIGHT_SPECIALIST_ARN,
    "flight_specialist",
    "Searches flights and hotels, returns structured options with pricing and schedules.",
)

payment_agent = _create_a2a_agent(
    PAYMENT_PROCESSOR_ARN,
    "payment_processor",
    "Processes travel payments, handles multi-currency transactions and refunds.",
)

currency_agent = _create_a2a_agent(
    CURRENCY_EXCHANGE_ARN,
    "currency_exchange",
    "Converts between currencies with live rates, supports 150+ currencies.",
)

activities_agent = _create_a2a_agent(
    LOCAL_ACTIVITIES_ARN,
    "local_activities",
    "Suggests local activities, tours, restaurants, and experiences at the destination.",
)

SYSTEM_PROMPT = """You are a Travel Orchestrator. You plan complete trips by coordinating \
specialist agents.

You have access to these specialist agents:
1. flight_specialist - Search flights and hotels
2. local_activities - Suggest local activities and experiences
3. currency_exchange - Convert currencies and check rates
4. payment_processor - Process payments and refunds (only when user explicitly asks to book/pay)

When a user asks you to plan a trip:
1. Use flight_specialist to find flights and hotels
2. Use local_activities to suggest things to do at the destination
3. Use currency_exchange if the user needs costs in another currency
4. Only use payment_processor if the user explicitly asks to pay/book

Present a consolidated trip plan with:
- Flight options (top 2-3)
- Hotel options (top 2-3)
- Suggested activities
- Total estimated cost

Be concise but comprehensive."""

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=[flight_agent, payment_agent, currency_agent, activities_agent],
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
