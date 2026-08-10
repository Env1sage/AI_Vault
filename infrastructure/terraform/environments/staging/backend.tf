# See environments/production/backend.tf's comment for the one-time setup
# this expects to already exist — same procedure, a separate bucket/key
# so staging and production state can never collide.
terraform {
  backend "s3" {
    bucket         = "vault-terraform-state-staging"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "vault-terraform-locks"
    encrypt        = true
  }
}
