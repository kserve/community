# KServe Self-Assessment

Security reviewers: Dan Sun, Yuan Tang, Sivanantham Chinnaiyan, Andrews Arokiam, Filippe Spolti

This document is a self-assessment of the security of the KServe project.

## Table of Contents

- [Metadata](#metadata)
  - [Security links](#security-links)
  - [Software Bill of Materials](#software-bill-of-materials)
- [Overview](#overview)
  - [Background](#background)
  - [Actors](#actors)
  - [Actions](#actions)
  - [Goals](#goals)
  - [Non-goals](#non-goals)
- [Self-assessment use](#self-assessment-use)
- [Security functions and features](#security-functions-and-features)
- [Project compliance](#project-compliance)
- [Secure development practices](#secure-development-practices)
  - [Development pipeline](#development-pipeline)
  - [Communication channels](#communication-channels)
  - [Ecosystem](#ecosystem)
- [Security issue resolution](#security-issue-resolution)
  - [Responsible disclosure practice](#responsible-disclosure-practice)
  - [Incident response](#incident-response)
- [Appendix](#appendix)

## Metadata

| Assessment Stage   | Incomplete |
|--------------------|---------------------------------------------------|
| Software           | https://github.com/kserve/kserve |
| Security Provider? | No. KServe is not a security provider; its primary function is to support scalable serving of machine learning and large language models (LLMs) on Kubernetes. |
| Languages          | Python, Go           |

### Security links

- KServe security policy: https://github.com/kserve/kserve/blob/master/SECURITY.md

- Configuration details for serving including default configmaps: https://github.com/kserve/kserve/blob/master/config/configmap/inferenceservice.yaml

### Software Bill of Materials

- The go.mod files for each component can be found in the root directory of KServe repo, linked below.
  - https://github.com/kserve/kserve/blob/master/go.mod
  - https://github.com/kserve/kserve/blob/master/qpext/go.mod

- For each Python serving runtime, dependency lock files are found under the `python` directory of their respective package folder in KServe repo, linked below.
    - https://github.com/kserve/kserve/blob/master/python/kserve/pyproject.toml
    - https://github.com/kserve/kserve/blob/master/python/huggingfaceserver/pyproject.toml
    - https://github.com/kserve/kserve/blob/master/python/sklearnserver/pyproject.toml
    - https://github.com/kserve/kserve/blob/master/python/lgbserver/pyproject.toml
    - https://github.com/kserve/kserve/blob/master/python/paddleserver/pyproject.toml
    - https://github.com/kserve/kserve/blob/master/python/pmmlserver/pyproject.toml
    - https://github.com/kserve/kserve/blob/master/python/xgbserver/pyproject.toml

- SBOMs for all components are not yet available; automated generation of SBOMs is currently underway.

## Overview

KServe is a highly scalable and standards-based Model Inference Platform for serving predictive and generative AI models on Kubernetes, built for highly scalable use cases. It provides serverless model inference, autoscaling, advanced deployments, and integrates with a wide range of Machine Learning frameworks. It is designed to simplify the deployment and management of Machine Learning models in production environments, enabling organizations to leverage the power of Kubernetes for their AI workloads.

It supports a wide range of popular frameworks such as TensorFlow, PyTorch, XGBoost, scikit-learn, and Hugging Face Transformers/LLMs, and adopts standardized data plane protocols to ensure consistency and interoperability. 

KServe abstracts the operational complexity of model deployment by handling autoscaling, networking, health checks, and server configurations. It enables advanced serving features like GPU autoscaling, scale-to-zero, and canary rollouts. Moreover, KServe provides a complete and extensible solution for production ML serving, including support for prediction, pre-processing, post-processing, and model explainability, thereby offering a high-level, pluggable interface for scalable and reliable ML inference workflows.

KServe also introduces Inference Graphs, a powerful feature that enables users to define multi-step inference pipelines. With inference graphs, users can chain together multiple models and transformation components using a simple and declarative graph-based specification. This is particularly useful for complex AI workflows such as ensemble models, sequential processing.

### Background

In cloud-native environments, deploying Machine Learning (ML) models at scale poses many of the same challenges traditionally seen with Serverless applications—such as managing scaling, updates, and event-driven workflows across diverse workloads. While Kubernetes provides a robust foundation for container orchestration, it was not originally designed with native support for ML-specific workloads. This gap led to fragmented solutions that required developers and ML engineers to manually handle autoscaling, networking, monitoring, and rollout strategies, often resulting in operational complexity and inefficiencies.

KServe addresses these challenges by building on top of Kubernetes and leveraging Knative, a framework specifically created to bring serverless capabilities to Kubernetes. By introducing a Kubernetes Custom Resource Definition (CRD) for InferenceService, KServe provides a standardized and auditable interface for deploying and managing ML models. This abstraction allows users to focus on their models rather than the underlying infrastructure, enabling them to deploy, scale, and manage their models with ease.

KServe is designed to be extensible and framework-agnostic, supporting a wide range of ML frameworks and custom runtimes. It provides a pluggable architecture that allows users to integrate their own pre-processing, post-processing, and model management components. This flexibility enables organizations to tailor KServe to their specific needs while benefiting from the core features and capabilities it offers.

By leveraging Kubernetes-native components like Knative and modern ingress solutions like Kubernetes Gateway API using implementations such as Istio or Envoy Gateway, KServe abstracts much of the operational complexity involved in model inference workflows, making it an effective solution for organizations looking to operationalize machine learning at scale.

### Actors

1. **KServe Control Plane**: 

    - **KServe Controller**: Responsible for reconciling the InferenceService, InferenceGraph and underlying kubernetes related resources (E.g. Deployment, Service). It creates the Knative Service in Serverless deployment for predictor, transformer, explainer to enable autoscaling based on incoming request workload including scaling down to zero when no traffic is received. When Raw Deployment mode (vanilla Kubernetes) is enabled, the control plane creates Kubernetes deployment, service, ingress, HPA and other resources to allow smooth communication between the internal components. It is also responsible for creating model agent containers for request/response logging, batching and model pulling.
    
    - **KServe Webhook**: Validates and mutates CRD resources to ensure they conform to KServe's standards and best practices. It also handles the creation of default configurations for various components. 
    
    - **Model Cache Controller**: Manages the lifecycle of model caches, ensuring that models are efficiently loaded and unloaded. It helps optimize resource utilization and performance by caching models and reducing the overhead of launching new instances during auto-scaling especially for LLMs.

2. **KServe Data Plane**: 
  
   The InferenceService Data Plane architecture consists of a static graph of components which coordinate requests for a single model. Advanced features such as Ensembling, A/B testing, and Multi-Arm-Bandits should compose InferenceServices together.
  
   **Component**: Each endpoint is composed of multiple components: "predictor", "explainer", and "transformer". The only required component is the predictor, which is the core of the system. As KServe evolves, we plan to increase the number of supported components to enable use cases like Outlier Detection.

   **Predictor**: The predictor is the workhorse of the InferenceService. It is simply a model and a model server that makes it available at a network endpoint.

   **Explainer**: The explainer enables an optional alternate data plane that provides model explanations in addition to predictions. Users may define their own explanation container, which configures with relevant environment variables like prediction endpoint. For common use cases, KServe provides out-of-the-box explainers like Alibi.

   **Transformer**: The transformer enables users to define a pre and post processing step before the prediction and explanation workflows. Like the explainer, it is configured with relevant environment variables too. For common use cases, KServe provides out-of-the-box transformers like Feast.
  
   **Router**: The ensemble component enables users to define a static graph of components that can be chained together. This allows for more complex workflows, such as ensembling multiple models or combining predictions from different sources.
  
   **Model Agent**: The model agent is a lightweight container that runs alongside the predictor and is responsible for managing request batching, request/response logging.
   
   **Storage Initializer**: The storage initializer is a init container that runs before the predictor and is responsible for downloading the model artifacts or providing the cached model to the predictor. It ensures that the model is available and ready for inference before the predictor starts serving requests.


3. **External Integrations**: Other Kubernetes components (e.g., Knative, Istio, ModelMesh, Envoy, KEDA), monitoring systems.

### Actions

The control plane reconciles these resources, deploying model servers and configuring autoscaling, networking, and monitoring. The data plane receives inference requests, processes them, and returns predictions. Monitoring and logging components collect metrics and logs for observability and troubleshooting.

- **Model Deployment**: Users define an InferenceService CRD, specifying the model, runtime, and configuration.
- **Autoscaling**: KServe automatically scales the model server based on incoming traffic, including scaling down to zero when idle in Serverless Mode. In Raw Deployment mode (vanilla Kubernetes), KServe utilizes Kubernetes HPA to scale the deployment based on CPU/Memory usage or KEDA for advanced scaling options with custom metrics.
- **Monitoring and Logging**: KServe integrates with monitoring and logging systems to provide observability into model performance and usage.
- **Model Management**: KServe manages the lifecycle of models, including versioning, canary rollouts, and A/B testing.
- **Security and Access Control**: KServe leverages Kubernetes RBAC and network policies to secure access to model endpoints and resources. KServe also supports TLS encryption for secure communication between components using Istio's service mesh and external clients using Authorization policy.
- **Custom Runtimes**: Users can define custom runtimes for specific ML frameworks or use cases, enabling flexibility and extensibility.
- **Pre/Post Processing**: Users can define pre-processing and post-processing steps for their models, allowing for custom data transformations and handling.
- **Ensembling**: Users can create complex inference workflows by chaining multiple models together using InferenceGraph CRD, enabling advanced use cases like ensembling and A/B testing.
- **Model Explainability**: KServe provides built-in support for model explainability, allowing users to understand and interpret model predictions.
- **Batching**: KServe supports request batching to optimize resource utilization and improve throughput for inference requests.
- **Multi-Model Serving**: KServe can serve multiple models simultaneously, enabling high-density deployments and efficient resource utilization.
- **Canary Rollouts**: KServe supports canary rollouts for safe and controlled deployment of new model versions, allowing users to test changes with a subset of traffic before full rollout.
- **Scale-to-Zero**: In Serverless mode, KServe can scale down to zero using Knative when no traffic is received, reducing resource consumption and costs.
- **Model Caching**: KServe supports model caching to optimize resource utilization and performance, reducing the overhead of launching new instances during auto-scaling.
- **Payload Logging**: KServe supports request/response logging for monitoring and debugging purposes, allowing users to track the performance and behavior of their models.


### Goals

- **Standard ML Platform on Kubernetes**: Provide a standard, cloud-agnostic platform for serving ML models on Kubernetes.
- **Abstracting Complexity**: Simplify the deployment and management of ML models by abstracting operational complexity. Developers can focus on their models rather than the underlying infrastructure.
- **Serverless Model Inference**: Enable serverless model inference with autoscaling, including scale-to-zero capabilities using Knative.
- **Advanced Deployment Patterns**: Support advanced deployment patterns such as canary rollouts, A/B testing, and multi-arm bandits.
- **Model Management**: Provide a complete and extensible solution for model management, including canary rollouts, and A/B testing.
- **Monitoring and Observability**: Integrate with monitoring and logging systems for observability and incident response.
- **AutoScaling**: Enable secure, scalable, and reliable model inference with support for autoscaling, canary rollouts, and advanced deployment patterns.
- **Out of the Box ML framework Support**: Support a wide range of ML frameworks including TensorFlow, PyTorch, XGBoost, scikit-learn, and Hugging Face Transformers/LLMs to simplify model serving.
- **Custom Runtimes**: Support custom runtimes for specific ML frameworks or use cases, enabling flexibility and extensibility.
- **Pre/Post Processing**: Enable users to define pre-processing and post-processing steps for their models, allowing for custom data transformations and handling.
- **Ensembling**: Support complex inference workflows by chaining multiple models together using InferenceGraph CRD, enabling advanced use cases like ensembling and A/B testing.
- **Model Explainability**: Provide built-in support for model explainability, allowing users to understand and interpret model predictions.
- **Model Caching**: Support model caching to optimize resource utilization and performance, reducing the overhead of launching new instances during auto-scaling especially for LLMs.

### Non-Goals

- KServe does not provide model training or data labeling capabilities.
- KServe does not validate the security of user-supplied models or custom containers.
- KServe does not manage the security of external dependencies or third-party plugins beyond standard Kubernetes best practices.
- KServe may not aim to offer fine-grained network security policy management at the application level. Users are encouraged to leverage Kubernetes Network Policies or other networking solutions for such requirements.
- KServe might not aim to expose all the intricacies of Kubernetes resource management directly to end-users. The abstraction provided by KServe is designed to shield users from low-level Kubernetes operations.

## Self-assessment Use

This self-assessment is created by the KServe team to perform an internal analysis of the project's security. It is not intended to provide a security audit of KServe, or function as an independent assessment or attestation of KServe's security health.

This document serves to provide KServe users and stakeholders with an initial understanding of KServe's security, where to find existing security documentation, KServe's plans for security, and a general overview of KServe security practices, both for development and operation.

This document provides the CNCF TAG-Security with an initial understanding of KServe to assist in a joint-assessment, necessary for projects under incubation. Taken together, this document and the joint-assessment serve as a cornerstone for if and when KServe seeks graduation and is preparing for a security audit.

## Security functions and features

| Component                          | Applicability | Description of Importance                                                                                      |
| ---------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------- |
| Kubernetes RBAC & Network Policies | Critical      | Leverages Kubernetes RBAC and network policies to restrict access to resources and isolate workloads.          |
| Secure Defaults                    | Relevant      | Default configurations are designed to minimize exposure and follow Kubernetes security best practices.        |
| Monitoring & Logging               | Relevant      | Integrates with Prometheus, Grafana, and logging systems for observability and incident response.              |

## Project Compliance

KServe does not currently claim compliance with specific security standards (e.g., PCI-DSS, ISO, GDPR). The project follows open source and Kubernetes security best practices and is following the OpenSSF Best Practices. KServe has achieved A+ grade in [Go Report Card](https://goreportcard.com/report/github.com/kserve/kserve).

## Secure Development Practices

### Development pipeline
 - Committers are required to agree to the Developer Certificate of Origin (DCO) for each and every commit by simply stating you have a legal right to make the contribution.
- At least one reviewer is required for a pull request to be approved.
- Automated CI/CD with vulnerability scanning and static analysis.
- Automated tests for unit, integration, and end-to-end testing.
- Automated code quality checks and linting.
- Publicly documented contribution and code review guidelines ([CONTRIBUTING.md](https://github.com/kserve/kserve/blob/master/CONTRIBUTING.md)).
- KServe's release process is mostly automated, with a focus on ensuring that all changes are thoroughly tested and validated before being released to users. The release process is documented in the [RELEASE.md](https://github.com/kserve/kserve/blob/master/release/RELEASE_PROCESS_v2.md):
  1. Check that all dependencies for the repository are up-to-date and aligned with release version
  2. Generate release artifacts and automated testing of all changes in the CI/CD pipeline.
  3. Verify that all builds on the master branch are passing.
  4. Creating a release branch of the form release-X.Y.Z from the master
  5. Tagging and versioning of releases in the Git repository.
  6. Build and Publish images to the KServe Docker registry.
  7. Publishing of release artifacts to the KServe GitHub repository and publish Python SDK to PyPI.
  8. Generation of release notes and changelogs.

### Communication Channels
1. **Internal:**
    - KServe has a dedicated CNCF Slack channel `kserve-contributors` used primarily for dev-to-dev communication in addition to developer-specific announcements.
    - KServe also has a dedicated Slack channel `kserve-tsc` for technical steering committee discussions.

2. **Inbound:**
    - KServe uses the CNCF Slack channel `kserve` for user-to-user, developers communication and user-specific announcements.
    - KServe has a dedicated mailing list `kserve-security@lists.lfaidata.foundation` and Github Security Advisory in KServe repo for security issues and discussions, which is monitored by the KServe security team.
    - KServe also has Githb Discussions for user-to-user, developer communication

3. **Outbound:**
    - KServe uses the CNCF Slack channel `kserve` for user-to-user, developer communication and user-specific announcements.

### Ecosystem
KServe is built on the existing Kubernetes framework, another open source project hosted by CNCF, Knative a serverless platform on Kubernetes, KEDA a event driven auto scaler on Kubernetes and provides components to serve ML models on Kubernetes. For more information on Kubernetes see the documentation here https://kubernetes.io/docs/home/

Other projects have been using KServe as ML serving platform, including [Red Hat OpenShift AI](https://www.redhat.com/en/products/ai/openshift-ai), a platform for managing the lifecycle of predictive and generative AI models; [Kubeflow](https://github.com/kubeflow/kubeflow) a Kubernetes-native machine learning toolkit;


## Security Issue Resolution

The KServe security policy is maintained in the [SECURITY.md](https://github.com/kserve/kserve/blob/master/SECURITY.md) file.

### Responsible Disclosure Practice

Vulnerability reports are accepted via GitHub's private vulnerability reporting tool or via a dedicated mailing list `kserve-security@lists.lfaidata.foundation`. Maintainers collaborate with reporters to triage and resolve issues, and advisories are published as needed.

### Incident Response

Upon receiving a vulnerability report, the KServe security team triages the issue, determines impact, and works to release a patch for supported versions. Users are notified via release notes, documentation, and community channels. This team is kept small to avoid excessive disclosure of vulnerabilities.

## Appendix

- *Known Issues Over Time*: Issues and vulnerabilities are tracked in GitHub Issues and Security Advisories. No critical vulnerabilities are currently open.
- *OpenSSF Best Practices*: KServe achieved the [passing level criteria](https://www.bestpractices.dev/en/projects/6643) and is in the process of working towards attaining a silver badge in Open Source Security Foundation (OpenSSF) best practices badge; the project is actively working to improve its security posture and practices.
- *Case Studies*: KServe is used by organizations such as Bloomberg, Red Hat, Nutanix, Cloudera, SAP, Intuit, Zillow and others for production ML model serving.
- *Related Projects / Vendors*: Related projects include Kubeflow, Envoy AI Gateway, KEDA, Knative, Istio, Envoy Gateway.
- *Competitive projects*: MLFlow, Seldon Core, Ray Serve, TensorFlow Serving, Triton Inference Server, and others. KServe differentiates by providing a Standard Kubernetes-native, extensible platform with advanced deployment patterns, model caching and scaling capabilities. It is also designed to be framework-agnostic, allowing users to define custom runtimes as well.
