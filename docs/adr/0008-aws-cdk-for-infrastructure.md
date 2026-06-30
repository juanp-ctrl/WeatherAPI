# ADR 0008: AWS CDK for Infrastructure as Code

## Status

Accepted

## Context

The platform's production infrastructure -- VPC, subnets, security groups, Aurora PostgreSQL, ECS cluster, Fargate task definitions, ALB, ECR repositories, CloudWatch log groups -- must be defined as code to enable repeatable, auditable, and version-controlled deployments. Infrastructure as Code (IaC) is a non-functional requirement (NFR-4) of the project.

The IaC tool must support all required AWS resources, integrate well with the development workflow (git-based, reviewable diffs), and be learnable for a developer already working in TypeScript (CDK is a learning objective). The tool should also enable sharing resource references (e.g., VPC ID from the network stack used by the service stack) without manual parameter passing.

## Decision

We will use **AWS CDK (TypeScript)** to define all production infrastructure. The CDK app is structured as a single app with logically separated constructs (`NetworkStack`, `DatabaseStack`, `ServiceStack`, `MonitoringStack`). Constructs share references (VPC, security groups, database endpoints) through standard CDK cross-construct references, avoiding the need for SSM parameters or CloudFormation exports.

TypeScript was chosen as the CDK language because it provides compile-time type checking for infrastructure definitions, catching misconfigurations before deployment. CDK's higher-level constructs (L2 and L3) abstract away verbose CloudFormation boilerplate while still compiling down to CloudFormation templates.

## Alternatives Considered

### Terraform (HCL)

Terraform is the most widely adopted IaC tool, supporting multiple cloud providers through a provider plugin model. Its declarative HCL syntax is purpose-built for infrastructure definitions and has a large community with extensive module libraries. However, Terraform uses a custom language (HCL) rather than a general-purpose programming language, which means infrastructure logic (conditionals, loops, abstractions) uses HCL-specific constructs that do not transfer to application development. Terraform also requires managing state files (in S3 + DynamoDB for remote state), adding operational overhead. CDK's advantage is that it uses a general-purpose language (TypeScript), enabling standard programming patterns (classes, interfaces, loops) for infrastructure, and it manages state through CloudFormation with no additional backend configuration.

### AWS CloudFormation (raw YAML/JSON)

CloudFormation is the native AWS IaC service that CDK compiles to. Writing CloudFormation templates directly avoids the CDK abstraction layer and its associated build toolchain (`cdk synth`, `cdk deploy`). However, CloudFormation YAML is extremely verbose: a simple Fargate service with an ALB can exceed 500 lines. CloudFormation lacks programming constructs (no functions, no classes, no type checking), making complex infrastructure definitions difficult to read, refactor, and test. CDK exists precisely to address these pain points while still producing CloudFormation under the hood.

### Pulumi

Pulumi, like CDK, uses general-purpose programming languages for infrastructure definitions and supports TypeScript. It provides a similar developer experience with the added benefit of multi-cloud support (AWS, GCP, Azure) and its own state management backend. However, Pulumi is less widely adopted than CDK in the AWS ecosystem, has a smaller community for AWS-specific patterns, and its state management (Pulumi Cloud or self-hosted backend) adds a dependency. CDK's tight integration with CloudFormation and AWS-native services (e.g., CDK constructs for Aurora Serverless v2, ECS patterns) makes it the more natural choice for an AWS-only deployment.

## Consequences

- All production infrastructure is defined in TypeScript within a single CDK app.
- `cdk deploy` creates or updates all AWS resources through CloudFormation change sets.
- Infrastructure changes are reviewed as TypeScript code diffs in pull requests.
- CDK constructs encapsulate related resources (e.g., `DatabaseStack` includes the Aurora cluster, subnet group, and secrets), making the infrastructure modular and readable.
- State is managed automatically by CloudFormation; no external state backend is required.
- The CDK app compiles to CloudFormation templates, ensuring compatibility with AWS-native tooling.

## Pros

- TypeScript provides compile-time type safety, catching resource misconfiguration before deployment.
- Higher-level constructs (L2/L3) reduce boilerplate compared to raw CloudFormation.
- Cross-construct references eliminate manual parameter passing between stacks.
- Infrastructure is version-controlled alongside application code in the monorepo.
- CDK is an explicit learning objective of the project, providing educational value.
- CloudFormation-backed state management requires no additional infrastructure.

## Cons

- CDK adds a build toolchain (Node.js, `cdk synth`) that must be maintained.
- Debugging CDK-generated CloudFormation templates can be difficult when deployments fail at the CloudFormation level.
- CDK's abstraction layer can obscure what AWS resources are actually being created, requiring `cdk synth` to inspect the output.
- Vendor lock-in: CDK is AWS-specific, unlike Terraform or Pulumi which support multiple providers.
- CDK constructs evolve rapidly; breaking changes in construct libraries can require migration effort.

## References

- [Architecture Overview -- Section 9: CDK Stack Structure](../architecture/overview.md#9-deployment-architecture)
- [Architecture Overview -- Section 3: NFR-4 Infrastructure as Code](../architecture/overview.md#3-system-goals)
- [AWS CDK documentation](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
