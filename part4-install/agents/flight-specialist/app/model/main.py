"""Flight & Hotel Specialist — A2A Agent on Bedrock AgentCore.

This agent searches for flights and hotels using mock data and returns
structured travel options. It is designed to be discovered via ARD and
invoked over the A2A protocol.

Runs on port 9000 at / per AgentCore A2A requirements.
"""

from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model
from tools import search_flights, search_hotels

SYSTEM_PROMPT = """You are a Flight & Hotel Specialist agent. Your job is to help users find \
flights and hotels for their trips.

When a user asks about travel, you MUST:
1. Use the search_flights tool to find flight options (outbound and return).
2. Use the search_hotels tool to find hotel options at the destination.
3. Present the results in a clear, structured format showing:
   - Top 3 flight options (outbound + return) with prices, times, and stops
   - Top 3 hotel options with nightly rate, stars, and neighborhood

Always use both tools for a complete trip query. If the user only asks about \
flights or only hotels, use just the relevant tool.

Format prices in USD. Be concise and helpful."""

tools = [search_flights, search_hotels]

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
