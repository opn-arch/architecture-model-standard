---
document: Use Cases
system: Projects (template)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:30Z
generator_version: 0.3.0
model_hash: 7f71c642a524
edition: 3
---

# Use Cases: Projects (template)

## Actor-Goal Matrix

| Actor | Goals |
|-------|-------|
| API Consumer | — |

## Use Case Specifications

### UC: GET 

**ID:** BEH-1
**Main Flow:**
  1. 

### UC: GET bookmarklets/

**ID:** BEH-2
**Main Flow:**
  1. 

### UC: GET tags/

**ID:** BEH-3
**Main Flow:**
  1. 

### UC: GET filters/

**ID:** BEH-4
**Main Flow:**
  1. 

### UC: GET views/

**ID:** BEH-5
**Main Flow:**
  1. 

### UC: GET views/<view>/

**ID:** BEH-6
**Main Flow:**
  1. 

### UC: GET models/

**ID:** BEH-7
**Main Flow:**
  1. 

### UC: GET ^models/(?P<app_label>[^.]+)\.(?P<model_name>[^/]+)/$

**ID:** BEH-8
**Main Flow:**
  1. 

### UC: GET templates/<path:template>/

**ID:** BEH-9
**Main Flow:**
  1. 

### UC: GET login/

**ID:** BEH-10
**Main Flow:**
  1. 

### UC: GET logout/

**ID:** BEH-11
**Main Flow:**
  1. 

### UC: GET password_change/

**ID:** BEH-12
**Main Flow:**
  1. 

### UC: GET password_change/done/

**ID:** BEH-13
**Main Flow:**
  1. 

### UC: GET password_reset/

**ID:** BEH-14
**Main Flow:**
  1. 

### UC: GET password_reset/done/

**ID:** BEH-15
**Main Flow:**
  1. 

### UC: GET reset/<uidb64>/<token>/

**ID:** BEH-16
**Main Flow:**
  1. 

### UC: GET reset/done/

**ID:** BEH-17
**Main Flow:**
  1. 

### UC: GET <path:url>

**ID:** BEH-18
**Main Flow:**
  1. flatpage

## Use Case Diagram

```mermaid
graph LR
    ACT-1(("API Consumer"))
    BEH-1["GET "]
    BEH-2["GET bookmarklets/"]
    BEH-3["GET tags/"]
    BEH-4["GET filters/"]
    BEH-5["GET views/"]
    BEH-6["GET views/<view>/"]
    BEH-7["GET models/"]
    BEH-8["GET ^models/(?P<app_label>[^.]+)\.(?P<model_name>[^/]+)/$"]
    BEH-9["GET templates/<path:template>/"]
    BEH-10["GET login/"]
    BEH-11["GET logout/"]
    BEH-12["GET password_change/"]
    BEH-13["GET password_change/done/"]
    BEH-14["GET password_reset/"]
    BEH-15["GET password_reset/done/"]
```
