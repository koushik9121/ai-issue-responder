# Scheduled Azure AI GitHub Issue Responder Agent

An automated, serverless, and time-triggered AI agent deployed on Azure using Terraform. The agent checks for new, open GitHub issues in a target repository, classifies them using OpenAI's `gpt-4o-mini`, applies tags, and posts an automated, polite, and contextual reply.

## Architecture

- **Azure Function App (Python)**: Triggered by a timer (cron schedule) to perform regular checks on GitHub issues.
- **Azure Key Vault**: Stores sensitive credentials (GitHub PAT, OpenAI API Key) securely. The Function App references these secrets directly without exposing them in plaintext configs.
- **Azure Storage Account**: Required by the function app host for managing execution state and locks.
- **Application Insights**: Provides live execution telemetry, logs, and error tracing.
- **Terraform**: Handles resource provisioning, dependency linking, and Key Vault access policies.

## Prerequisites

- An active **Azure Subscription**.
- **Azure CLI** installed and authenticated (`az login`).
- **Terraform CLI** (>= 1.5.0).
- A **GitHub Personal Access Token (PAT)** with repository permissions to read issues, write comments, and assign labels.
- An **OpenAI API Key**.

## Deployment

1. **Initialize Terraform**:
   ```bash
   terraform init
   ```

2. **Configure Variables**:
   Create a `terraform.tfvars` file (or pass variables via the CLI):
   ```hcl
   location            = "East US"
   resource_group_name = "rg-ai-github-agent"
   github_repo         = "koushik9121/ai-issue-responder"
   github_pat          = "your-github-pat"
   openai_api_key      = "your-openai-api-key"
   ```

3. **Plan and Deploy**:
   ```bash
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

## Python Function App Details

The Python code resides in the `agent_function/` directory.

- **Host Config**: `agent_function/host.json`
- **Function App definition**: `agent_function/function_app.py`
  - Utilizes a standard timer trigger (default: every 2 hours: `0 0 */2 * * *`).
  - Checks if the issue has already been processed by looking for a hidden signature comment (`<!-- AI-AGENT-BOT -->`).
  - Sends issue body and title to OpenAI for classification.
  - Applies a label (`bug`, `enhancement`, `documentation`, or `question`) and posts the AI-generated welcome response.

## Local Testing

You can run the function app locally using the Azure Functions Core Tools:

1. Create `agent_function/local.settings.json`:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "GITHUB_PAT": "your-github-pat",
       "GITHUB_REPO": "koushik9121/ai-issue-responder",
       "OPENAI_API_KEY": "your-openai-api-key"
     }
   }
   ```
2. Navigate to the `agent_function` directory and start the runtime:
   ```bash
   cd agent_function
   func start
   ```
