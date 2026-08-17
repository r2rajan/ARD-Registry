# Agentic Resource Discovery (ARD) + A2A on Amazon Bedrock AgentCore

A four-part blog series that builds a multi-agent travel planner from scratch. An orchestrator agent discovers partner agents at runtime through an ARD registry, then calls them over the A2A protocol. The whole system runs on AWS: a serverless registry, five agents on Amazon Bedrock AgentCore, and a web front end on ECS Fargate.

The core idea: **agents should find each other the way we find a plumber in the Yellow Pages, not by having every phone number hardcoded in a config file.**

## The problem

Today, when an orchestrator agent needs a specialist (flights, payments, currency), the endpoint is hardcoded at build time. A better specialist shows up, a partner ships a new capability, or an endpoint changes, and nothing adapts until a human notices and redeploys. ARD gives agents a directory: partners publish catalogs, a registry indexes them, and an orchestrator searches at runtime. This series builds that directory and an orchestrator that uses it.

## The series

| Part | Post | What it covers | Install code |
|------|------|----------------|--------------|
| 1 | The Yellow Pages problem of AI ([LinkedIn](https://www.linkedin.com/feed/update/urn:li:ugcPost:7484620735995478016/)) | Why agents need discovery, what ARD is (catalog, registry, resolution), and when discovery does not apply | — |
| 2 | Building an ARD Registry on AWS ([LinkedIn](https://www.linkedin.com/posts/activity-7487529789415849984-ULzu)) | A `POST /search` registry that indexes partner catalogs. S3, CloudFront, Lambda, API Gateway | [part2-install](part2-install/) |
| 3 | Scoring and Ranking in an ARD Registry ([LinkedIn](https://www.linkedin.com/posts/activity-7490091867171078144-WSDo)) | Why keyword overlap breaks, four fixes tried, and why vector embeddings (Bedrock Titan) are the right starting point | [part3-install](part3-install/) |
| 4 | Building the Agents on Amazon Bedrock AgentCore | Five agents on AgentCore, A2A communication, runtime selection via ARD, and an ECS Fargate front end | [part4-install](part4-install/) |

## What gets built

A user types a request in plain language:

> Plan a 5-day trip to Tokyo from SFO, budget $3000.

The orchestrator needs four capabilities. Three come from partner agents it discovers at runtime. One is an inhouse agent it calls directly.

| Agent | Owner | How it is found | Protocol |
|-------|-------|-----------------|----------|
| Flight & Hotel Specialist | Partner A | ARD registry search at runtime | A2A |
| Payment Processor | Partner B | ARD registry search at runtime | A2A |
| Currency Exchange | Partner B | ARD registry search at runtime | A2A |
| Local Trip Activities | Inhouse | Known ARN, no discovery | A2A |

The partner agents can be replaced by a better-scoring agent from a new partner without touching the orchestrator code. Adding a partner means uploading one catalog JSON file to S3.

## Architecture

```
Browser
   │  http://<alb-url>/
   ▼
┌───────────────────────────────────────────────┐
│  ECS Fargate (FastAPI behind an ALB)           │
│   1. Queries the ARD registry per capability   │
│   2. Invokes the orchestrator on AgentCore     │
│   3. Returns the trip plan + a discovery log   │
└───────────────────────────────────────────────┘
   │                              │
   │ POST /search                 │ boto3 (SigV4)
   ▼                              ▼
┌──────────────────────┐   ┌──────────────────────────────┐
│  ARD Registry         │   │  Travel Orchestrator (AgentCore)│
│  (Lambda + S3 +       │   │   A2A clients call:            │
│   CloudFront + API GW)│   │   ├── Flight & Hotel (Partner A)│
│                       │   │   ├── Payment (Partner B)      │
│  Indexes partner      │   │   ├── Currency (Partner B)     │
│  catalogs, ranks      │   │   └── Local Activities (inhouse)│
│  results              │   └──────────────────────────────┘
└──────────────────────┘
```

Two selection patterns run in the same trip plan:

- **Runtime selection (partners):** the ECS container searches the registry for each capability and takes the top-ranked agent across all partners. A higher-scoring agent from a new partner wins the next request with no redeploy.
- **Fixed selection (inhouse):** the Local Activities agent is ours, so the orchestrator calls it directly by ARN. No catalog, no search.

## Repository layout

```
part2-install/     # Part 2 — ARD registry: CloudFormation + Lambda + search UI
part3-install/     # Part 3 — improved scoring Lambda + comparison UI
part4-install/     # Part 4 — 5 agents (AgentCore) + FastAPI backend on ECS Fargate
```

Each `partN-install/` folder has its own `README.md` with prerequisites, deploy steps, test instructions, and teardown. The blog write-ups for each part are published on LinkedIn (linked in the table above).

## Deploy order

Deploy the parts in sequence. Later parts depend on earlier ones.

1. **Part 2 registry** ([part2-install](part2-install/)) — creates the `POST /search` endpoint. Note the registry URL it prints.
2. **Part 3 scoring** ([part3-install](part3-install/)) — upgrades the Part 2 Lambda with stop words, stemming, and Titan embeddings. Reuses the Part 2 infrastructure.
3. **Part 4 agents + backend** ([part4-install](part4-install/)) — deploys the five agents to AgentCore and the FastAPI backend to ECS Fargate. Needs the registry URL from Part 2.

## Prerequisites

- AWS CLI configured with credentials
- Docker running (Part 4 backend image)
- Node.js 24+ and Python 3.13+ (Part 4 agents; the AgentCore CLI generates a CDK app)
- AgentCore CLI 0.22.0+ (`pip install bedrock-agentcore-starter-toolkit`)
- Amazon Bedrock model access in your region:
  - Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`)
  - Titan Embeddings G1 - Text v2 (`amazon.titan-embed-text-v2:0`)

Replace `<YOUR_AWS_ACCOUNT_ID>` in each agent's `aws-targets.json` before deploying Part 4. See the [part4-install](part4-install/) folder for the full list of values to edit.

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Registry compute | Lambda | Stateless lookup, no always-on cost |
| Registry storage | S3 + CloudFront | Serves partner catalogs over HTTPS |
| Registry API | API Gateway HTTP API | Public `POST /search` with CORS |
| Scoring | Keyword overlap + Titan embeddings | Semantic match beats vocabulary match |
| Agents | Bedrock AgentCore | Built-in A2A serving and agent cards |
| Agent SDK | Strands Agents | A2A client and executor |
| Front end | ECS Fargate + ALB | 300s+ request budget vs API Gateway's 30s limit |
| Model | Claude Sonnet 4.6 | Orchestrator and specialist reasoning |

## License

See individual files. Blog content and code are provided as reference implementations for the ARD + A2A pattern.
