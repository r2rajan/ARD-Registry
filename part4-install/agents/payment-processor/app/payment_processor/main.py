"""Payment Processing Agent — A2A Agent on Bedrock AgentCore.

Processes travel payments and refunds. Discovered via ARD from Partner B's
catalog. Invoked over the A2A protocol.
"""

from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model
from tools import process_payment, issue_refund

SYSTEM_PROMPT = """You are a Payment Processing agent. You handle travel-related payments \
and refunds.

When a user needs to pay for something:
1. Use the process_payment tool with the amount, currency, description, and card details.
2. Report the transaction status clearly.

When a user needs a refund:
1. Use the issue_refund tool with the original transaction ID, amount, and reason.
2. Confirm the refund details.

Always confirm amounts and currency before processing. Be clear about success or failure."""

tools = [process_payment, issue_refund]

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
