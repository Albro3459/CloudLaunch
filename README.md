# CloudLaunch

CloudLaunch is a multi-region automated cloud deployment platform. It is built around two platform actions:

* **Region setup and cleanup**: prepares an AWS region so servers can be launched there, then removes that regional infrastructure when it is no longer needed. In this project, this flow is called "terraforming" a region, as reference to "terraforming" a planet.
* **Server deploy and terminate**: deploys a server into any region that has already been set up, then terminates that server when it is no longer needed.

The included example implementation is a WireGuard VPN product. After a region has been set up, the UI can deploy a VPN server into that region, return the client configuration, and terminate the server later. Termination and region cleanup are designed so an unused region can return to zero cloud cost.

## Built With CloudLaunch

[CloudGateway](https://github.com/Albro3459/CloudGateway) is a full production project adapted from this platform. It takes the example WireGuard VPN implementation and builds it into a hosted, multi-region WireGuard VPN service using React/TypeScript, FastAPI/Python, Firebase Auth/Firestore, and Oracle Cloud Infrastructure, all on top of CloudLaunch's multi-region deployment architecture.

## Platform Flow

1. An admin selects an AWS region to set up.
2. AWS Lambda copies the base EC2 AMI into that region.
3. The setup Lambda creates the regional network and runtime configuration: VPC, subnet, internet gateway, route table, security group, key pair, and Secrets Manager values.
4. A waiter Lambda confirms that the AMI is available and marks the region as live.
5. Users can deploy servers into any live region.
6. Cleanup can terminate servers and remove the regional resources created during setup.

## Example VPN Flow

1. A user signs in through the React frontend with Firebase Authentication.
2. The frontend calls AWS Lambda endpoints to discover live regions, deploy a VPN, retrieve VPN config values, or request termination.
3. The Deploy Lambda launches an EC2 instance from the prepared AMI in the selected region.
4. The app records instance state in Firebase and enforces VPN limits with DynamoDB.
5. SES emails the WireGuard client configuration, and the UI can also show or download the config.
6. Termination stops the VPN server and updates stored state so the instance no longer costs money.

## Services Used

### Main Platform

* **AWS Lambda**: runs the setup, cleanup, deploy, terminate, region discovery, and user helper APIs.
* **Amazon EC2**: hosts deployed servers and provides AMIs for repeatable regional deployment.
* **Amazon Machine Images (AMIs)**: store the preconfigured server image copied into target regions.
* **Amazon VPC**: creates isolated regional networking for deployed servers.
* **Subnets, internet gateways, route tables, and security groups**: provide public IPv4/IPv6 routing and firewall rules for each prepared region.
* **AWS Secrets Manager**: stores credentials and per-region server deployment values.
* **AWS IAM**: grants Lambda the permissions required by the platform and the example implementation.
* **Amazon CloudWatch Logs**: captures Lambda runtime logs and deployment diagnostics.

### Example VPN Implementation

* **React, TypeScript, and Tailwind CSS**: provide the example frontend UI.
* **Firebase Authentication**: handles user sign-in.
* **Firebase Firestore**: stores user and VPN instance state used by the UI and Lambdas.
* **Amazon DynamoDB**: tracks VPN user counts and role-based limits for the example product.
* **Amazon SES**: sends WireGuard client configuration emails.
* **WireGuard**: provides the VPN server and client protocol.

## Documentation

* [AWS Lambda functions README](./lambda/README.md)
* [React frontend README](./react-frontend/README.md)
