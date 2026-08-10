# Remote state — created ONCE, by hand, before the first `terraform init`
# here (Terraform can't create the place it stores its own state). Both
# resources need to already exist in the account:
#
#   aws s3api create-bucket --bucket vault-terraform-state-production --region us-east-1
#   aws s3api put-bucket-versioning --bucket vault-terraform-state-production \
#     --versioning-configuration Status=Enabled
#   aws dynamodb create-table --table-name vault-terraform-locks \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST
#
# State itself must stay encrypted (`encrypt = true`) — it contains every
# secret value passed as a Terraform variable, in plaintext, by design
# (this is a well-known Terraform limitation, not something this config
# can work around; restrict IAM access to this bucket accordingly).
terraform {
  backend "s3" {
    bucket         = "vault-terraform-state-production"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "vault-terraform-locks"
    encrypt        = true
  }
}
