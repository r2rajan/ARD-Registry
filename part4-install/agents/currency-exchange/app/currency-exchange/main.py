"""Currency Exchange Agent — A2A Agent on Bedrock AgentCore.

Converts between currencies with live rates. Discovered via ARD from
Partner B's catalog. Invoked over the A2A protocol.
"""

from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model
from tools import convert_currency, get_exchange_rate

SYSTEM_PROMPT = """You are a Currency Exchange agent. You help users convert between currencies \
and check exchange rates.

When a user wants to convert money:
1. Use the convert_currency tool with the amount, source currency, and target currency.
2. Present the result clearly with the rate used.

When a user wants to check a rate:
1. Use the get_exchange_rate tool.
2. Show the rate and its inverse.

Always show the full currency codes (USD, EUR, JPY, etc). Format amounts with appropriate \
decimal places for the currency."""

tools = [convert_currency, get_exchange_rate]

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
