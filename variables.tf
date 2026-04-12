variable "location" {
  type        = string
  description = "The Azure region to deploy resources into."
  default     = "East US"
}

variable "resource_group_name" {
  type        = string
  description = "The name of the Azure Resource Group."
  default     = "rg-ai-github-agent"
}

variable "github_pat" {
  type        = string
  description = "GitHub Personal Access Token for the AI agent to read/write issues."
  sensitive   = true
}

variable "github_repo" {
  type        = string
  description = "The GitHub repository to monitor (e.g., 'koushik9121/ai-issue-responder')."
  default     = "koushik9121/ai-issue-responder"
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API Key used by the agent to classify and reply to issues."
  sensitive   = true
}
