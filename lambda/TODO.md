# Lambda TODO

1. Manually test `Deploy` and `terminate` from the AWS Console after `CloudLaunch`, Lambda egress, OCI API access, and the updated code package are in place.
2. Verify the Lambda execution role is scoped to `CloudLaunch`, SES send, `vpn-users`, `vpn-roles`, CloudWatch Logs, and VPC ENI access only if the functions are VPC-attached.
3. Update SES to send from the new domain and verify the sender/domain identity before switching `aws.SES_SENDER`.
