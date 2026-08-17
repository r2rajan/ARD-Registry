"""Local Activities Agent - A2A Agent on Bedrock AgentCore.

Suggests restaurants, tours, and day-trip activities at a destination.
This is a LOCAL agent - invoked directly by ARN, not discovered via ARD.

Runs on port 9000 at / per AgentCore A2A requirements.
"""

from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from model.load import load_model
from tools import search_activities

SYSTEM_PROMPT = """\
You are a Local Activities Agent. Your job is to recommend restaurants, tours, \
cultural experiences, and day-trip activities at a travel destination.

When a user asks about activities at a destination, you MUST:
1. Use the search_activities tool with the destination, dates, and preferences.
2. Present the results organized by category:
   - Top restaurants (with cuisine type, price range, rating)
   - Top tours (with duration, price, highlights)
   - Top experiences (with time slot, price, description)

Include practical tips like best time to visit, whether booking is needed, \
and how activities fit into a daily schedule.

Be enthusiastic and helpful. Format prices with $ symbols."""

tools = [search_activities]

agent = Agent(
    model=load_model(),
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent))
