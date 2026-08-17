from strands.models.bedrock import BedrockModel


def load_model() -> BedrockModel:
    """Get Bedrock model client using IAM credentials.

    Uses Claude Sonnet 4.6 via the US inference profile in us-west-2.
    """
    return BedrockModel(model_id="us.anthropic.claude-sonnet-4-6")
