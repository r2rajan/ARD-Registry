"""Load the Bedrock model for the orchestrator."""

from strands.models.bedrock import BedrockModel


def load_model():
    return BedrockModel(model_id="us.anthropic.claude-sonnet-4-6")
