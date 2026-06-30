# ADR 0007: AWS ECS Fargate for Container Orchestration

## Status

Accepted

## Context

The platform's two microservices are packaged as Docker images and need a production container orchestration environment. The orchestrator must run containers without requiring the developer to manage underlying servers, support health checks and automatic task replacement, integrate with AWS networking (VPC, subnets, security groups, ALB), and provide logging to CloudWatch. The project is developed and operated by a single developer, so minimizing operational overhead is critical.

The services are stateless by design (all state lives in PostgreSQL), which means the orchestrator does not need to manage persistent volumes or sticky sessions. The expected load is low (periodic polling every 5-15 minutes, occasional API queries), so auto-scaling is not an immediate requirement, though the architecture should not preclude it.

## Decision

We will use **AWS ECS Fargate** to run both microservices in production. Each service runs as a Fargate task (one container per task) within an ECS cluster. Fargate eliminates the need to provision, patch, or scale EC2 instances -- AWS manages the underlying compute. Task definitions specify CPU/memory limits, environment variables, container image URIs (from ECR), and CloudWatch log configuration.

Fargate tasks are deployed in public subnets with `assignPublicIp: true` to avoid the cost of NAT Gateways (~$64/month for two AZs), with security groups restricting inbound traffic to the ALB only.

## Alternatives Considered

### Amazon ECS on EC2

ECS on EC2 provides the same ECS control plane but runs tasks on self-managed EC2 instances. This gives more control over instance types, allows GPU workloads, and can be cheaper at scale through Reserved Instances or Spot pricing. However, ECS on EC2 requires managing an Auto Scaling Group, patching AMIs, monitoring instance health, and right-sizing instance capacity. For a portfolio project with minimal compute requirements, this operational overhead is unjustified. Fargate's per-task pricing is higher per vCPU-hour, but the total cost is lower because there is no idle EC2 capacity to pay for.

### Amazon EKS (Kubernetes)

EKS provides managed Kubernetes, the industry-standard container orchestrator. Kubernetes offers a richer ecosystem (Helm charts, Operators, service mesh, custom controllers) and greater portability across cloud providers. However, EKS has a base cost of ~$72/month for the control plane alone, requires learning Kubernetes concepts (Pods, Deployments, Services, Ingress, RBAC), and adds significant operational complexity. The platform consists of two simple stateless services -- the full power of Kubernetes is unnecessary. ECS provides sufficient orchestration with far less configuration surface.

### AWS Lambda

Lambda would provide a fully serverless compute model with no container management, automatic scaling to zero, and pay-per-invocation pricing. Each API endpoint could be a Lambda function, and the background schedulers could use EventBridge-triggered Lambdas. However, Lambda introduces cold start latency (problematic for periodic schedulers that should fire promptly), a 15-minute execution time limit (potentially problematic for large ingestion cycles), and a fundamentally different deployment model (ZIP packages or Lambda container images with specific base images). Lambda also does not align with the learning objective of practicing container-based deployment on ECS.

## Consequences

- Both services are deployed as Fargate tasks within a single ECS cluster.
- Docker images are stored in Amazon ECR and pulled by Fargate at task launch.
- Task definitions specify CPU/memory allocations, environment variables, and secrets (database credentials from Secrets Manager).
- The ALB routes traffic to Fargate tasks and provides health checking.
- CloudWatch Logs receives container stdout/stderr via the `awslogs` log driver.
- Fargate tasks in public subnets have public IPs but are protected by security group rules.

## Pros

- Zero server management: no EC2 instances to provision, patch, or scale.
- Pay-per-task pricing with no idle compute cost when tasks are not running (relevant for future cost optimization).
- Native integration with ALB, CloudWatch, ECR, and Secrets Manager.
- Simpler than Kubernetes: no cluster management, no RBAC, no Helm charts.
- Stateless services map naturally to Fargate's ephemeral task model.
- Aligns with the container-first design principle established in the architecture.

## Cons

- Fargate tasks in public subnets with `assignPublicIp: true` is not a production best practice; this is an explicit cost trade-off (documented in the architecture overview).
- Fargate pricing is higher per vCPU-hour than EC2, though total cost is lower at low utilization.
- Less ecosystem flexibility compared to Kubernetes (no service mesh, no custom controllers, vendor lock-in to AWS).
- Cold start times for Fargate tasks (pulling images, starting containers) can take 30-60 seconds on first launch.

## References

- [Architecture Overview -- Section 9: Deployment Architecture](../architecture/overview.md#9-deployment-architecture)
- [Architecture Overview -- Section 12: Public Subnets vs. Private Subnets Trade-off](../architecture/overview.md#12-trade-offs)
- [AWS ECS Fargate documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
