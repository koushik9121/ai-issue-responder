output "resource_group_name" {
  value       = azurerm_resource_group.rg.name
  description = "The name of the Resource Group created."
}

output "function_app_name" {
  value       = azurerm_linux_function_app.function.name
  description = "The name of the Azure Function App."
}

output "function_app_default_hostname" {
  value       = azurerm_linux_function_app.function.default_hostname
  description = "The default hostname of the Azure Function App."
}

output "key_vault_name" {
  value       = azurerm_key_vault.kv.name
  description = "The name of the Key Vault."
}
