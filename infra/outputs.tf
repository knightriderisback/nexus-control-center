output "cloud_run_service_url" {
  description = "Assigned URL of the Cloud Run control center service"
  value       = google_cloud_run_v2_service.nexus_core.uri
}

output "service_account_email" {
  description = "Dedicated non-root service account email"
  value       = google_service_account.nexus_control_plane.email
}

output "workload_identity_pool_name" {
  description = "WIF Pool Name for keyless GitHub Actions CI/CD"
  value       = google_iam_workload_identity_pool.github_pool.name
}

output "zero_cost_guardrail_active" {
  description = "FinOps zero-spend guardrail status"
  value       = var.hard_spend_limit_usd == 0.0 && !var.billing_linked
}
