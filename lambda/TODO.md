# Lambda TODO

Backend Lambda + OCI deploy and terminate flows checks:

1. Re-check `Deploy` and `terminate` from the AWS Console after final frontend and configuration changes.
2. Verify the Lambda execution role is scoped to `CloudLaunch`, SES send, `vpn-users`, `vpn-roles`, CloudWatch Logs, and VPC ENI access only if the functions are VPC-attached.
3. Update SES to send from the new domain and verify the sender/domain identity before switching `aws.SES_SENDER`.
