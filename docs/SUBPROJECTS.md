# KServe Subprojects

This document outlines the subprojects under the KServe umbrella, their maintainers, contribution guidelines, and maturity status.

## Current Subprojects

### 1. KServe ModelMesh

**Description**: A high-performance, high-density serving layer for ML models on Kubernetes.

**Status**: Incubating
**Repository**: [kserve/modelmesh-serving](https://github.com/kserve/modelmesh-serving)

**Maintainers**: [List of maintainers from MAINTAINERS.md]

**Contribution Guidelines**:
- Follow the main [KServe Contributing Guidelines](../CONTRIBUTING.md)
- Additional project-specific guidelines can be found in the [modelmesh-serving repository](https://github.com/kserve/modelmesh-serving/blob/main/CONTRIBUTING.md)

### 2. KServe Open Inference Protocol

**Description**: A standardized protocol for model serving that enables interoperability between different serving runtimes.

**Status**: Incubating
**Repository**: [kserve/open-inference-protocol](https://github.com/kserve/open-inference-protocol)

**Maintainers**: [List of maintainers from MAINTAINERS.md]

**Contribution Guidelines**:
- Follow the main [KServe Contributing Guidelines](../CONTRIBUTING.md)
- Additional project-specific guidelines can be found in the [open-inference-protocol repository](https://github.com/kserve/open-inference-protocol/blob/main/CONTRIBUTING.md)

## Subproject Maturity Levels

Each subproject can be in one of the following maturity levels:

1. **Incubating**: New projects that are being developed and tested
2. **Graduated**: Projects that have demonstrated stability and adoption
3. **Archived**: Projects that are no longer actively maintained

## Process for Adding New Subprojects

1. Create a proposal document that includes:
   - Project name and description
   - Initial maintainers
   - Technical scope and goals
   - Repository structure
   - Integration plan with KServe

2. Submit the proposal to the Technical Steering Committee (TSC)

3. The TSC will review the proposal and vote on its acceptance

4. Upon acceptance:
   - Create the repository under the KServe organization
   - Set up initial project structure
   - Add project documentation
   - Update this document

## Process for Removing Subprojects

1. A proposal to remove a subproject must be submitted to the TSC, including:
   - Reason for removal
   - Impact assessment
   - Migration plan for users
   - Timeline for deprecation

2. The TSC will review the proposal and vote on the removal

3. Upon approval:
   - Archive the repository
   - Update documentation
   - Remove from this document
   - Communicate the change to the community

## Subproject Requirements

All subprojects must:

1. Follow the KServe [Code of Conduct](../CODE_OF_CONDUCT.md)
2. Adhere to the [Contributing Guidelines](../CONTRIBUTING.md)
3. Maintain clear documentation
4. Have at least two maintainers
5. Follow the project's technical charter and governance model
6. Participate in regular TSC updates

## Updating This Document

This document should be updated whenever:
- A new subproject is added
- A subproject is removed
- Leadership changes occur
- Maturity status changes
- Contribution guidelines are modified

All changes to this document require TSC approval. 
