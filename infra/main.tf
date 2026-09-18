# NEXUS Cloud Run & Zero-Trust Infrastructure Specification
# Architecture: Cloud Run (Serverless) + Workload Identity Federation (WIF) + FinOps Zero-Spend Guardrails

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------------------------------------------------------------
# 1. Least-Privilege Dedicated Service Account
# -----------------------------------------------------------------------------
resource "google_service_account" "nexus_control_plane" {
  account_id   = "sa-nexus-control-plane"
  display_name = "NEXUS Autonomous Engineering Control Plane"
  description  = "Identity for the serverless NEXUS control plane with zero static keys."
}

# -----------------------------------------------------------------------------
# 2. Workload Identity Federation (WIF) Pool & Provider (Zero Static JSON Keys)
# -----------------------------------------------------------------------------
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "nexus-github-pool"
  display_name              = "NEXUS GitHub Actions WIF Pool"
  description               = "Enables GitHub Actions CI/CD to authenticate without static service account keys."
  disabled                  = false
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "nexus-github-provider"
  display_name                       = "NEXUS GitHub Provider"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# -----------------------------------------------------------------------------
# 3. Serverless Cloud Run v2 Service
# -----------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "nexus_core" {
  name     = "nexus-control-center"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.nexus_control_plane.email

    scaling {
      min_instance_count = 0  # Scale to zero to maintain $0.00 idle cost
      max_instance_count = 2  # Hard concurrency ceiling to prevent runaway charges
    }

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1024Mi"
        }
        cpu_idle = true # CPU only allocated during request processing
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "NEXUS_COST_GUARD_STRICT"
        value = "true"
      }
      env {
        name  = "NEXUS_ZERO_SPEND_ENFORCED"
        value = "true"
      }

      startup_probe {
        http_get {
          path = "/api/health"
          port = 8080
        }
        initial_delay_seconds = 3
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/api/health"
          port = 8080
        }
        period_seconds    = 15
        failure_threshold = 3
      }
    }
  }

  labels = {
    "managed-by"         = "nexus-autonomous-os"
    "zero-spend-guard"   = "active"
    "tier"               = "production"
  }
}

# Public ingress permission (governed at API gateway / JWT token tier)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.nexus_core.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
