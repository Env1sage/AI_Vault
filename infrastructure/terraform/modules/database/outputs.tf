output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "database_name" {
  value = aws_db_instance.this.db_name
}

output "instance_id" {
  value = aws_db_instance.this.identifier
}

output "security_group_id" {
  value = aws_security_group.db.id
}
