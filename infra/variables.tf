variable "project_id" {
  type        = string
  description = "GCP Project ID for deployment"
  default     = "personal-engineering-os-2026"
}

variable "region" {
  type        = string
  description = "Target GCP region"
  default     = "us-central1"
}

variable "container_image" {
  type        = string
  description = "Container image URI for Cloud Run deployment"
  default     = "us-central1-docker.pkg.dev/personal-engineering-os-2026/nexus/control-center:latest"
}

variable "hard_spend_limit_usd" {
  type        = number
  description = "Maximum permissible cloud spend per month in USD"
  default     = 0.0
}

variable "billing_linked" {
  type        = bool
  description = "Status of GCP billing account linkage"
  default     = false
}
