
output "postgresql_connection" {
  value     = "postgresql://psqladmin:${random_password.postgresql_admin.result}@${azurerm_postgresql_flexible_server.postgresql.fqdn}/postgres"
  sensitive = true
}

output "postgresql_host" {
  value = azurerm_postgresql_flexible_server.postgresql.fqdn
}

output "postgresql_port" {
  value = "5432"
}

output "postgresql_database" {
  value = "postgres"
}

output "postgresql_user" {
  value = "psqladmin"
}

output "postgresql_password" {
  value     = random_password.postgresql_admin.result
  sensitive = true
}