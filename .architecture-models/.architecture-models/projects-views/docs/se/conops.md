---
document: ConOps
system: Projects (views)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:32Z
generator_version: 0.3.0
model_hash: a4f321da275c
edition: 3
---

# Concept of Operations: Projects (views)

## System Overview

Projects (views) provides 28 capabilities implemented across 15 components.

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
- **Csrf**
- **Debug**
- **Cache**
- **Clickjacking**
- **Csp**
- **Http**
- **Vary**
- **Defaults**
- **Dates**
- **Detail**
- **Edit**
- **List**
- **I18N**
- **Static**

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
- **GET login/**: 
- **GET logout/**: 
- **GET password_change/**: 
- **GET password_change/done/**: 
- **GET password_reset/**: 
- **GET password_reset/done/**: 
- **GET reset/<uidb64>/<token>/**: 
- **GET reset/done/**: 
- **GET <path:url>**: flatpage
- **TemplateView**: get
- **RedirectView**: get_redirect_url -> get -> head -> post -> options
- *...and 15 more workflows*

## System Context

*No interfaces defined in the model.*

## Operational Constraints

*No constraints defined in the model.*
