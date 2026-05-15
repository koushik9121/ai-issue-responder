data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# Storage Account required by Azure Functions
resource "azurerm_storage_account" "storage" {
  name                     = "stgithubagent${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Application Insights for monitoring
resource "azurerm_application_insights" "app_insights" {
  name                = "appi-github-agent-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  application_type    = "web"
}

# Key Vault to store credentials securely
resource "azurerm_key_vault" "kv" {
  name                        = "kv-githubagent-${random_string.suffix.result}"
  resource_group_name         = azurerm_resource_group.rg.name
  location                    = azurerm_resource_group.rg.location
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  # Access policy for Terraform deployer to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge", "Recover"
    ]
  }
}

# Secret for GitHub PAT
resource "azurerm_key_vault_secret" "github_pat" {
  name         = "github-pat"
  value        = var.github_pat
  key_vault_id = azurerm_key_vault.kv.id
}

# Secret for OpenAI API Key
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.kv.id
}

# App Service Plan (Consumption Y1 serverless plan)
resource "azurerm_service_plan" "asp" {
  name                = "asp-github-agent-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

# Azure Function App (Linux, Python)
resource "azurerm_linux_function_app" "function" {
  name                = "func-github-agent-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location

  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key
  service_plan_id            = azurerm_service_plan.asp.id

  site_config {
    application_stack {
      python_version = "3.10"
    }
    application_insights_connection_string = azurerm_application_insights.app_insights.connection_string
    application_insights_key               = azurerm_application_insights.app_insights.instrumentation_key
  }

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "GITHUB_PAT"               = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.github_pat.id})"
    "GITHUB_REPO"              = var.github_repo
    "OPENAI_API_KEY"           = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_key.id})"
  }
}

# Key Vault Access Policy for Function App Managed Identity
resource "azurerm_key_vault_access_policy" "function_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.function.identity[0].principal_id

  secret_permissions = [
    "Get"
  ]
}
