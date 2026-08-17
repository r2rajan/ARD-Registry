# Part 4: Multi-Agent Travel Planner - Installation

Deploys five agents to Amazon Bedrock AgentCore and a FastAPI backend to ECS Fargate. The orchestrator discovers partner agents at runtime through the Part 2 ARD registry, then calls them over the A2A protocol.

## What gets deployed

**Five agents on Bedrock AgentCore (A2A runtimes):**

- Flight & Hotel Specialist (Partner A)
- Payment Processor (Partner B)
- Currency Exchange (Partner B)
- Local Activities (inhouse, called by direct ARN, not discovered)
- Travel Orchestrator (discovers the partners, delegates work)

**Backend on ECS Fargate:**

- ECR repository (`ard-travel-planner`) for the backend image
- ECS Fargate service running the FastAPI app
- Application Load Balancer (serves the UI, no 30s timeout limit)
- IAM roles (task role invokes AgentCore, execution role pulls the image)

## Prerequisites

- **Part 2 registry deployed.** The orchestrator and backend query the `POST /search` endpoint from the `ard-registry` stack. Deploy `part2-install/` first and note the registry URL.
- AWS CLI configured with credentials
- Docker running (backend image build)
- Node.js 24+ (the AgentCore CLI generates a CDK app under the hood)
- Python 3.13+
- AgentCore CLI 0.22.0+ (`pip install bedrock-agentcore-starter-toolkit`)
- Amazon Bedrock model access in your region:
  - Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`)
  - Titan Embeddings G1 - Text v2 (used by the Part 2/3 registry)

## Directory structure

```
part4-install/
├── agents/
│   ├── flight-specialist/
│   │   ├── agentcore/
│   │   │   ├── agentcore.json      # AgentCore project config
│   │   │   └── aws-targets.json    # Account + region target
│   │   └── app/flight_specialist/
│   │       ├── main.py             # A2A entrypoint
│   │       ├── tools.py            # Agent tools
│   │       ├── model/load.py       # Model loader (Claude Sonnet 4.6)
│   │       └── pyproject.toml      # Agent dependencies
│   ├── payment-processor/          # same layout
│   ├── currency-exchange/          # same layout
│   ├── local-activities/           # same layout
│   └── orchestrator/               # same layout, plus partner ARNs in agentcore.json
├── backend/
│   ├── app.py                      # FastAPI app (/plan, /search, /health)
│   ├── static/index.html           # Travel Planner UI (natural language input)
│   ├── Dockerfile
│   └── requirements.txt
└── infra/
    ├── template.yaml               # ECS + ALB CloudFormation template
    └── deploy.sh                   # Builds image, pushes to ECR, deploys stack
```

## Configuration you must edit

The agents ship with placeholder account IDs and example ARNs. Replace them before deploying.

1. **Every agent** — set your account ID in `agents/<agent>/agentcore/aws-targets.json`:

   ```json
   [
     {
       "name": "default",
       "account": "<YOUR_AWS_ACCOUNT_ID>",
       "region": "us-west-2"
     }
   ]
   ```

2. **Orchestrator** — after you deploy the four partner agents (step 1 below), paste their runtime ARNs into `agents/orchestrator/agentcore/agentcore.json`. Update both the `envVars` block and the `connections` block:

   ```
   FLIGHT_SPECIALIST_ARN
   PAYMENT_PROCESSOR_ARN
   CURRENCY_EXCHANGE_ARN
   LOCAL_ACTIVITIES_ARN
   ```

3. **Backend deploy script** — after you deploy the orchestrator (step 2 below), set `ORCHESTRATOR_ARN` and `REGISTRY_URL` in `infra/deploy.sh`.

## Deploy

Deploy in order: partner agents, then orchestrator, then backend. The orchestrator needs the partner ARNs, and the backend needs the orchestrator ARN.

### Step 1: Deploy the four partner agents

For each of `flight-specialist`, `payment-processor`, `currency-exchange`, and `local-activities`:

```bash
cd agents/flight-specialist/agentcore
agentcore deploy
```

Record the runtime ARN the CLI prints for each agent. Repeat for the other three directories.

### Step 2: Deploy the orchestrator

Paste the four ARNs from step 1 into `agents/orchestrator/agentcore/agentcore.json` (both `envVars` and `connections`), then:

```bash
cd agents/orchestrator/agentcore
agentcore deploy
```

Record the orchestrator ARN.

### Step 3: Deploy the backend

Set `ORCHESTRATOR_ARN` and `REGISTRY_URL` in `infra/deploy.sh`, then:

```bash
cd infra
chmod +x deploy.sh
./deploy.sh
```

The script creates the ECR repository, builds and pushes the backend image, and deploys the ECS + ALB stack. It prints the Travel Planner URL when done.

## Test

Open the Travel Planner URL from step 3 in your browser. Enter a natural language request:

```
Plan a 3-day trip to Tokyo. Book a flight from SFO, find a hotel,
pay in USD, and show me the total in Japanese yen.
```

The response shows the trip plan plus a discovery log that lists which agent handled each need, the ARD match score, and how it was reached (registry lookup vs direct ARN).

You can also test the registry proxy directly:

```bash
curl -s -X POST "http://<alb-dns-name>/search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"text":"flight hotel booking"},"pageSize":3}' | python3 -m json.tool
```

## Teardown

```bash
# Backend stack
aws cloudformation delete-stack --stack-name ard-travel-planner --region us-west-2

# ECR image repository
aws ecr delete-repository --repository-name ard-travel-planner --force --region us-west-2

# Each agent (run from each agentcore/ directory)
cd agents/flight-specialist/agentcore && agentcore destroy
```

Run `agentcore destroy` in each of the five `agentcore/` directories to remove the runtimes.
