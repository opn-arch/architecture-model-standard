---
document: ConOps
system: Src (manifest)
system_id: SYS-unknown
generated_at: 2026-08-18T20:06:06Z
generator_version: 0.3.0
model_hash: 43ce18da3e69
edition: 4
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 17/17 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Concept of Operations: Src (manifest)

## System Overview

Src (manifest) provides 33 capabilities implemented across 17 components.

**Core Capabilities:**

- **Root Management**
- **Bookmarklet Management**
- **Tag Management**
- **Filter Management**
- **View Management**
- **Model Management**
- **^Model Management**
- **Template Management**
- **Login Management**
- **Logout Management**
- **Password Change Management**
- **Password Reset Management**
- **Reset Management**
- **<Path:Url> Management**
- **gRPC Services**
- **Behavior**
- **Blocks**
- **Body Hints**
- **Call Graph**
- **Chains**
- **Display**
- **Generator**
- **Grouping**
- **Interfaces**
- **Kt Scanner**
- **Metrics**
- **Multi Scanner**
- **Protocol**
- **Recursive**
- **Scan Cache**
- **Scanner**
- **Slicers**
- **Ts Scanner**

## Stakeholders

| Actor | Type | Goals |
|-------|------|-------|
| API Consumer | human | — |

## Operational Scenarios

### System Workflows

- **GET **: 
- **GET bookmarklets/**: 
- **GET tags/**: 
- **GET filters/**: 
- **GET views/**: 
- **GET views/<view>/**: 
- **GET models/**: 
- **GET ^models/(?P<app_label>[^.]+)\.(?P<model_name>[^/]+)/$**: 
- **GET templates/<path:template>/**: 
- **GET password_change/**: 
- **GET password_change/done/**: 
- **GET password_reset/**: 
- **GET password_reset/done/**: 
- **GET login/**: 
- **GET logout/**: 
- **GET reset/<uidb64>/<token>/**: 
- **GET reset/done/**: 
- **GET <path:url>**: flatpage

## System Context

*No interfaces defined in the model.*

## Operational Constraints

*No constraints defined in the model.*
