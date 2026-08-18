---
document: Logical Architecture
system: Projects (core)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:33Z
generator_version: 0.3.0
model_hash: 7aeb15531ff4
edition: 6
---

# Logical Architecture: Projects (core)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | web | — | — |
| 0 | data | — | — |
| 0 | infra | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Asgi (COMP-2) | service | 3 files | — |
| Db (COMP-3) | service | 1 files | — |
| Dummy (COMP-4) | service | 2 files | — |
| Filebased (COMP-5) | service | 2 files | — |
| Locmem (COMP-6) | service | 2 files | — |
| Memcached (COMP-7) | service | 1 files | — |
| Redis (COMP-8) | service | 1 files | — |
| Async Checks (COMP-9) | service | 1 files | — |
| Caches (COMP-10) | service | 1 files | — |
| Commands (COMP-11) | service | 1 files | — |
| Django 4 0 (COMP-12) | service | 1 files | — |
| Database (COMP-13) | service | 1 files | — |
| Files (COMP-14) | service | 1 files | — |
| Mail (COMP-15) | service | 1 files | — |
| Messages (COMP-16) | service | 1 files | — |
| Model Checks (COMP-17) | service | 1 files | — |
| Registry (COMP-18) | service | 1 files | — |
| Csrf (COMP-19) | service | 1 files | — |
| Sessions (COMP-20) | service | 1 files | — |
| Templates (COMP-21) | service | 2 files | — |
| Translation (COMP-22) | service | 1 files | — |
| Urls (COMP-23) | service | 1 files | — |
| Exceptions (COMP-24) | service | 4 files | — |
| Images (COMP-25) | service | 1 files | — |
| Move (COMP-26) | service | 1 files | — |
| Filesystem (COMP-27) | service | 1 files | — |
| Handler (COMP-28) | service | 2 files | — |
| Memory (COMP-29) | service | 1 files | — |
| Mixins (COMP-30) | service | 1 files | — |
| Uploadedfile (COMP-31) | service | 1 files | — |
| Uploadhandler (COMP-32) | service | 1 files | — |
| Exception (COMP-33) | service | 1 files | — |
| Wsgi (COMP-34) | service | 2 files | — |
| Console (COMP-35) | service | 1 files | — |
| Smtp (COMP-36) | service | 1 files | — |
| Deprecation (COMP-37) | service | 1 files | — |
| Message (COMP-38) | service | 1 files | — |
| Color (COMP-39) | service | 1 files | — |
| Check (COMP-40) | service | 1 files | — |
| Compilemessages (COMP-41) | service | 1 files | — |
| Createcachetable (COMP-42) | service | 1 files | — |
| Dbshell (COMP-43) | service | 1 files | — |
| Diffsettings (COMP-44) | service | 1 files | — |
| Dumpdata (COMP-45) | service | 1 files | — |
| Flush (COMP-46) | service | 1 files | — |
| Inspectdb (COMP-47) | service | 1 files | — |
| Listurls (COMP-48) | service | 1 files | — |
| Loaddata (COMP-49) | service | 1 files | — |
| Makemessages (COMP-50) | service | 1 files | — |
| Makemigrations (COMP-51) | service | 1 files | — |
| Migrate (COMP-52) | service | 1 files | — |
| Optimizemigration (COMP-53) | service | 1 files | — |
| Runserver (COMP-54) | service | 1 files | — |
| Sendtestemail (COMP-55) | service | 1 files | — |
| Shell (COMP-56) | service | 1 files | — |
| Showmigrations (COMP-57) | service | 1 files | — |
| Sqlflush (COMP-58) | service | 1 files | — |
| Sqlmigrate (COMP-59) | service | 1 files | — |
| Sqlsequencereset (COMP-60) | service | 1 files | — |
| Squashmigrations (COMP-61) | service | 1 files | — |
| Startapp (COMP-62) | service | 1 files | — |
| Startproject (COMP-63) | service | 1 files | — |
| Test (COMP-64) | service | 1 files | — |
| Testserver (COMP-65) | service | 1 files | — |
| Sql (COMP-66) | service | 1 files | — |
| Paginator (COMP-67) | service | 1 files | — |
| Json (COMP-68) | service | 1 files | — |
| Jsonl (COMP-69) | service | 1 files | — |
| Python (COMP-70) | service | 1 files | — |
| Pyyaml (COMP-71) | service | 1 files | — |
| Xml Serializer (COMP-72) | service | 1 files | — |
| Basehttp (COMP-73) | service | 1 files | — |
| Signing (COMP-74) | service | 1 files | — |
| Validators (COMP-75) | service | 1 files | — |
| CLI Base (COMP-76) | service | 9 files | — |
| Infrastructure (COMP-78) | service | 3 files | — |

## Inter-Component Interfaces

| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| base CLI | internal | — | — | — |
| templates CLI | internal | — | — | — |

## Dependency Graph

```mermaid
graph TD
    COMP-6["Locmem"]
    COMP-67["Paginator"]
    COMP-6 --> COMP-67
    COMP-20["Sessions"]
    COMP-17["Model Checks"]
    COMP-20 --> COMP-17
    COMP-52["Migrate"]
    COMP-52 --> COMP-67
    COMP-15["Mail"]
    COMP-34["Wsgi"]
    COMP-15 --> COMP-34
    COMP-43["Dbshell"]
    COMP-3["Db"]
    COMP-43 --> COMP-3
    COMP-75["Validators"]
    COMP-43 --> COMP-75
    COMP-53["Optimizemigration"]
    COMP-39["Color"]
    COMP-53 --> COMP-39
    COMP-5["Filebased"]
    COMP-28["Handler"]
    COMP-5 --> COMP-28
    COMP-21["Templates"]
    COMP-43 --> COMP-21
    COMP-47["Inspectdb"]
    COMP-74["Signing"]
    COMP-47 --> COMP-74
    COMP-63["Startproject"]
    COMP-11["Commands"]
    COMP-63 --> COMP-11
    COMP-64["Test"]
    COMP-2["Asgi"]
    COMP-64 --> COMP-2
    COMP-49["Loaddata"]
    COMP-66["Sql"]
    COMP-49 --> COMP-66
    COMP-59["Sqlmigrate"]
    COMP-59 --> COMP-34
    COMP-60["Sqlsequencereset"]
    COMP-60 --> COMP-74
    COMP-46["Flush"]
    COMP-46 --> COMP-39
    COMP-18["Registry"]
    COMP-78["Infrastructure"]
    COMP-18 --> COMP-78
    COMP-44["Diffsettings"]
    COMP-76["CLI Base"]
    COMP-44 --> COMP-76
    COMP-71["Pyyaml"]
    COMP-24["Exceptions"]
    COMP-71 --> COMP-24
    COMP-26["Move"]
    COMP-26 --> COMP-74
    COMP-33["Exception"]
    COMP-28 --> COMP-33
    COMP-47 --> COMP-75
    COMP-47 --> COMP-3
    COMP-39 --> COMP-24
    COMP-20 --> COMP-15
    COMP-47 --> COMP-21
    COMP-28 --> COMP-24
    COMP-10["Caches"]
    COMP-20 --> COMP-10
    COMP-57["Showmigrations"]
    COMP-57 --> COMP-24
    COMP-60 --> COMP-3
    COMP-60 --> COMP-75
    COMP-73["Basehttp"]
    COMP-73 --> COMP-33
    COMP-17 --> COMP-78
    COMP-40["Check"]
    COMP-40 --> COMP-2
    COMP-58["Sqlflush"]
    COMP-58 --> COMP-39
    COMP-60 --> COMP-21
    COMP-73 --> COMP-24
    COMP-35["Console"]
    COMP-6 --> COMP-35
    COMP-13["Database"]
    COMP-20 --> COMP-13
    COMP-35 --> COMP-28
    COMP-45["Dumpdata"]
    COMP-45 --> COMP-78
    COMP-12["Django 4 0"]
    COMP-12 --> COMP-24
    COMP-48["Listurls"]
    COMP-48 --> COMP-39
    COMP-52 --> COMP-35
    COMP-75 --> COMP-67
    COMP-8["Redis"]
    COMP-8 --> COMP-5
    COMP-50["Makemessages"]
    COMP-50 --> COMP-26
    COMP-34 --> COMP-33
    COMP-26 --> COMP-2
    COMP-63 --> COMP-2
    COMP-71 --> COMP-74
    COMP-54["Runserver"]
    COMP-54 --> COMP-67
    COMP-5 --> COMP-67
    COMP-7["Memcached"]
    COMP-3 --> COMP-7
    COMP-22["Translation"]
    COMP-12 --> COMP-22
    COMP-4["Dummy"]
    COMP-4 --> COMP-67
    COMP-34 --> COMP-24
    COMP-8 --> COMP-78
    COMP-68["Json"]
    COMP-68 --> COMP-78
    COMP-28 --> COMP-74
    COMP-57 --> COMP-74
    COMP-24 --> COMP-33
    COMP-42["Createcachetable"]
    COMP-36["Smtp"]
    COMP-42 --> COMP-36
    COMP-56["Shell"]
    COMP-56 --> COMP-24
    COMP-7 --> COMP-2
    COMP-10 --> COMP-5
    COMP-71 --> COMP-75
    COMP-73 --> COMP-74
    COMP-27["Filesystem"]
    COMP-27 --> COMP-24
    COMP-61["Squashmigrations"]
    COMP-61 --> COMP-34
    COMP-12 --> COMP-74
    COMP-15 --> COMP-28
    COMP-28 --> COMP-75
    COMP-10 --> COMP-78
    COMP-3 --> COMP-76
    COMP-36 --> COMP-6
    COMP-2 --> COMP-78
    COMP-34 --> COMP-74
    COMP-44 --> COMP-39
    COMP-35 --> COMP-36
    COMP-38["Message"]
    COMP-36 --> COMP-38
    COMP-50 --> COMP-2
    COMP-8 --> COMP-3
    COMP-8 --> COMP-75
    COMP-57 --> COMP-2
    COMP-68 --> COMP-75
    COMP-12 --> COMP-75
    COMP-22 --> COMP-24
    COMP-41["Compilemessages"]
    COMP-41 --> COMP-39
    COMP-37["Deprecation"]
    COMP-67 --> COMP-37
    COMP-12 --> COMP-21
    COMP-24 --> COMP-74
    COMP-73 --> COMP-2
    COMP-5 --> COMP-35
    COMP-5 --> COMP-15
    COMP-27 --> COMP-74
    COMP-4 --> COMP-35
    COMP-34 --> COMP-75
    COMP-42 --> COMP-6
    COMP-43 --> COMP-66
    COMP-25["Images"]
    COMP-76 --> COMP-25
    COMP-42 --> COMP-8
    COMP-15 --> COMP-40
    COMP-11 --> COMP-17
    COMP-32["Uploadhandler"]
    COMP-25 --> COMP-32
    COMP-24 --> COMP-75
    COMP-2 --> COMP-75
    COMP-20 --> COMP-24
    COMP-27 --> COMP-75
    COMP-55["Sendtestemail"]
    COMP-55 --> COMP-78
    COMP-63 --> COMP-34
    COMP-56 --> COMP-2
    COMP-21 --> COMP-24
    COMP-35 --> COMP-6
    COMP-49 --> COMP-39
    COMP-9["Async Checks"]
    COMP-15 --> COMP-9
    COMP-20 --> COMP-22
    COMP-38 --> COMP-18
    COMP-47 --> COMP-66
    COMP-23["Urls"]
    COMP-23 --> COMP-67
    COMP-8 --> COMP-4
    COMP-35 --> COMP-8
    COMP-7 --> COMP-34
    COMP-35 --> COMP-15
    COMP-60 --> COMP-66
    COMP-21 --> COMP-78
    COMP-15 --> COMP-17
    COMP-53 --> COMP-78
    COMP-65["Testserver"]
    COMP-65 --> COMP-78
    COMP-35 --> COMP-37
    COMP-41 --> COMP-67
    COMP-20 --> COMP-74
    COMP-64 --> COMP-76
    COMP-62["Startapp"]
    COMP-62 --> COMP-34
    COMP-76 --> COMP-67
    COMP-10 --> COMP-4
    COMP-46 --> COMP-78
    COMP-21 --> COMP-74
    COMP-11 --> COMP-13
    COMP-17 --> COMP-23
    COMP-65 --> COMP-74
    COMP-69["Jsonl"]
    COMP-69 --> COMP-68
    COMP-50 --> COMP-34
    COMP-29["Memory"]
    COMP-29 --> COMP-34
    COMP-26 --> COMP-32
    COMP-51["Makemigrations"]
    COMP-51 --> COMP-24
    COMP-19["Csrf"]
    COMP-19 --> COMP-34
    COMP-21 --> COMP-75
    COMP-15 --> COMP-10
    COMP-58 --> COMP-78
    COMP-47 --> COMP-76
    COMP-40 --> COMP-76
    COMP-20 --> COMP-2
    COMP-53 --> COMP-75
    COMP-49 --> COMP-67
    COMP-53 --> COMP-3
    COMP-65 --> COMP-75
    COMP-65 --> COMP-3
    COMP-65 --> COMP-21
    COMP-15 --> COMP-37
    COMP-38 --> COMP-78
    COMP-60 --> COMP-76
    COMP-67 --> COMP-22
    COMP-15 --> COMP-13
    COMP-48 --> COMP-78
    COMP-36 --> COMP-5
    COMP-46 --> COMP-75
    COMP-46 --> COMP-3
    COMP-67 --> COMP-78
    COMP-70["Python"]
    COMP-70 --> COMP-68
    COMP-26 --> COMP-76
    COMP-46 --> COMP-21
    COMP-74 --> COMP-76
    COMP-52 --> COMP-2
    COMP-36 --> COMP-78
    COMP-51 --> COMP-74
    COMP-76 --> COMP-10
    COMP-42 --> COMP-24
    COMP-7 --> COMP-76
    COMP-2 --> COMP-23
    COMP-5 --> COMP-26
    COMP-51 --> COMP-3
    COMP-51 --> COMP-75
    COMP-64 --> COMP-39
    COMP-71 --> COMP-76
    COMP-43 --> COMP-39
    COMP-51 --> COMP-21
    COMP-69 --> COMP-34
    COMP-44 --> COMP-78
    COMP-72["Xml Serializer"]
    COMP-72 --> COMP-33
    COMP-35 --> COMP-24
    COMP-39 --> COMP-76
    COMP-36 --> COMP-3
    COMP-36 --> COMP-75
    COMP-57 --> COMP-76
    COMP-72 --> COMP-24
    COMP-32 --> COMP-24
    COMP-11 --> COMP-24
    COMP-42 --> COMP-74
    COMP-63 --> COMP-40
    COMP-73 --> COMP-76
    COMP-75 --> COMP-2
    COMP-33 --> COMP-67
    COMP-47 --> COMP-39
    COMP-11 --> COMP-22
    COMP-2 --> COMP-32
    COMP-27 --> COMP-32
    COMP-5 --> COMP-2
    COMP-60 --> COMP-39
    COMP-16["Messages"]
    COMP-12 --> COMP-16
    COMP-4 --> COMP-2
    COMP-32 --> COMP-26
    COMP-70 --> COMP-34
    COMP-34 --> COMP-76
    COMP-71 --> COMP-69
    COMP-25 --> COMP-67
    COMP-42 --> COMP-21
    COMP-7 --> COMP-36
    COMP-35 --> COMP-74
    COMP-72 --> COMP-74
    COMP-6 --> COMP-34
    COMP-15 --> COMP-24
    COMP-42 --> COMP-2
    COMP-32 --> COMP-74
    COMP-11 --> COMP-74
    COMP-56 --> COMP-76
    COMP-63 --> COMP-17
    COMP-52 --> COMP-34
    COMP-24 --> COMP-76
    COMP-68 --> COMP-72
    COMP-15 --> COMP-22
    COMP-59 --> COMP-24
    COMP-36 --> COMP-4
    COMP-31["Uploadedfile"]
    COMP-26 --> COMP-31
    COMP-3 --> COMP-5
    COMP-14["Files"]
    COMP-40 --> COMP-14
    COMP-62 --> COMP-67
    COMP-21 --> COMP-66
    COMP-72 --> COMP-75
    COMP-72 --> COMP-3
    COMP-65 --> COMP-66
    COMP-11 --> COMP-75
    COMP-19 --> COMP-40
    COMP-31 --> COMP-67
    COMP-11 --> COMP-21
    COMP-35 --> COMP-2
    COMP-3 --> COMP-78
    COMP-40 --> COMP-13
    COMP-15 --> COMP-74
    COMP-22 --> COMP-76
    COMP-26 --> COMP-14
    COMP-32 --> COMP-2
    COMP-46 --> COMP-66
    COMP-7 --> COMP-6
    COMP-57 --> COMP-39
    COMP-19 --> COMP-9
    COMP-69 --> COMP-71
    COMP-48 --> COMP-68
    COMP-59 --> COMP-74
    COMP-74 --> COMP-37
    COMP-63 --> COMP-13
    COMP-7 --> COMP-8
    COMP-76 --> COMP-11
    COMP-48 --> COMP-23
    COMP-76 --> COMP-26
    COMP-52 --> COMP-7
    COMP-72 --> COMP-70
    COMP-75 --> COMP-34
    COMP-15 --> COMP-21
    COMP-19 --> COMP-17
    COMP-50 --> COMP-31
    COMP-54 --> COMP-34
    COMP-15 --> COMP-2
    COMP-5 --> COMP-34
    COMP-51 --> COMP-66
    COMP-4 --> COMP-34
    COMP-20 --> COMP-16
    COMP-23 --> COMP-2
    COMP-70 --> COMP-71
    COMP-59 --> COMP-2
    COMP-61 --> COMP-24
    COMP-30["Mixins"]
    COMP-27 --> COMP-30
    COMP-17 --> COMP-67
    COMP-6 --> COMP-28
    COMP-19 --> COMP-15
    COMP-2 --> COMP-25
    COMP-19 --> COMP-10
    COMP-12 --> COMP-14
    COMP-27 --> COMP-25
    COMP-45 --> COMP-67
    COMP-42 --> COMP-66
    COMP-64 --> COMP-78
    COMP-8 --> COMP-67
    COMP-43 --> COMP-78
    COMP-68 --> COMP-67
    COMP-61 --> COMP-74
    COMP-3 --> COMP-4
    COMP-5 --> COMP-7
    COMP-51 --> COMP-76
    COMP-27 --> COMP-14
    COMP-55 --> COMP-28
    COMP-40 --> COMP-22
    COMP-42 --> COMP-7
    COMP-10 --> COMP-67
    COMP-6 --> COMP-36
    COMP-40 --> COMP-78
    COMP-47 --> COMP-78
    COMP-63 --> COMP-24
    COMP-74 --> COMP-24
    COMP-61 --> COMP-21
    COMP-52 --> COMP-36
    COMP-2 --> COMP-67
    COMP-17 --> COMP-10
    COMP-60 --> COMP-78
    COMP-5 --> COMP-76
    COMP-21 --> COMP-39
    COMP-61 --> COMP-2
    COMP-64 --> COMP-75
    COMP-63 --> COMP-22
    COMP-65 --> COMP-39
    COMP-64 --> COMP-21
    COMP-12 --> COMP-18
    COMP-26 --> COMP-78
    COMP-7 --> COMP-24
    COMP-23 --> COMP-34
    COMP-4 --> COMP-28
    COMP-40 --> COMP-74
    COMP-35 --> COMP-7
    COMP-74 --> COMP-78
    COMP-7 --> COMP-5
    COMP-42 --> COMP-76
    COMP-54 --> COMP-73
    COMP-8 --> COMP-35
    COMP-63 --> COMP-74
    COMP-41 --> COMP-34
    COMP-40 --> COMP-3
    COMP-40 --> COMP-75
    COMP-50 --> COMP-33
    COMP-20 --> COMP-14
    COMP-40 --> COMP-21
    COMP-50 --> COMP-24
    COMP-76 --> COMP-34
    COMP-55 --> COMP-67
    COMP-29 --> COMP-24
    COMP-52 --> COMP-6
    COMP-35 --> COMP-76
    COMP-71 --> COMP-78
    COMP-7 --> COMP-74
    COMP-10 --> COMP-35
    COMP-26 --> COMP-75
    COMP-63 --> COMP-75
    COMP-6 --> COMP-8
    COMP-50 --> COMP-22
    COMP-19 --> COMP-24
    COMP-32 --> COMP-76
    COMP-6 --> COMP-15
    COMP-39 --> COMP-78
    COMP-28 --> COMP-78
    COMP-51 --> COMP-39
    COMP-52 --> COMP-8
    COMP-33 --> COMP-2
    COMP-38 --> COMP-28
    COMP-57 --> COMP-78
    COMP-63 --> COMP-21
    COMP-31 --> COMP-26
    COMP-11 --> COMP-16
    COMP-5 --> COMP-36
    COMP-6 --> COMP-37
    COMP-29 --> COMP-26
    COMP-4 --> COMP-36
    COMP-49 --> COMP-34
    COMP-7 --> COMP-3
    COMP-7 --> COMP-75
    COMP-53 --> COMP-67
    COMP-65 --> COMP-67
    COMP-19 --> COMP-11
    COMP-73 --> COMP-78
    COMP-56 --> COMP-33
    COMP-12 --> COMP-78
    COMP-50 --> COMP-74
    COMP-29 --> COMP-74
    COMP-46 --> COMP-67
    COMP-34 --> COMP-78
    COMP-72 --> COMP-69
    COMP-15 --> COMP-16
    COMP-57 --> COMP-3
    COMP-50 --> COMP-75
    COMP-42 --> COMP-39
    COMP-55 --> COMP-15
    COMP-56 --> COMP-78
    COMP-57 --> COMP-75
    COMP-59 --> COMP-76
    COMP-24 --> COMP-78
    COMP-50 --> COMP-21
    COMP-57 --> COMP-21
    COMP-62 --> COMP-2
    COMP-5 --> COMP-31
    COMP-27 --> COMP-78
    COMP-58 --> COMP-67
    COMP-73 --> COMP-75
    COMP-73 --> COMP-3
    COMP-5 --> COMP-6
    COMP-31 --> COMP-2
    COMP-4 --> COMP-6
    COMP-69 --> COMP-24
    COMP-29 --> COMP-2
    COMP-56 --> COMP-74
    COMP-38 --> COMP-67
    COMP-61 --> COMP-66
    COMP-5 --> COMP-38
    COMP-48 --> COMP-67
    COMP-17 --> COMP-11
    COMP-5 --> COMP-8
    COMP-19 --> COMP-2
    COMP-4 --> COMP-8
    COMP-4 --> COMP-15
    COMP-64 --> COMP-66
    COMP-76 --> COMP-28
    COMP-22 --> COMP-78
    COMP-36 --> COMP-67
    COMP-5 --> COMP-37
    COMP-4 --> COMP-37
    COMP-56 --> COMP-75
    COMP-40 --> COMP-23
    COMP-56 --> COMP-21
    COMP-33 --> COMP-34
    COMP-70 --> COMP-24
    COMP-32 --> COMP-31
    COMP-40 --> COMP-66
    COMP-6 --> COMP-24
    COMP-25 --> COMP-34
    COMP-20 --> COMP-78
    COMP-35 --> COMP-38
    COMP-44 --> COMP-67
    COMP-52 --> COMP-24
    COMP-38 --> COMP-15
    COMP-61 --> COMP-76
    COMP-17 --> COMP-2
    COMP-32 --> COMP-14
    COMP-11 --> COMP-14
    COMP-76 --> COMP-40
    COMP-36 --> COMP-18
    COMP-63 --> COMP-66
    COMP-66 --> COMP-3
    COMP-59 --> COMP-39
    COMP-69 --> COMP-2
    COMP-45 --> COMP-2
    COMP-70 --> COMP-74
    COMP-36 --> COMP-35
    COMP-76 --> COMP-9
    COMP-31 --> COMP-34
    COMP-6 --> COMP-74
    COMP-20 --> COMP-75
    COMP-52 --> COMP-74
    COMP-15 --> COMP-38
    COMP-20 --> COMP-21
    COMP-15 --> COMP-14
    COMP-76 --> COMP-17
    COMP-75 --> COMP-33
    COMP-70 --> COMP-2
    COMP-75 --> COMP-24
    COMP-12 --> COMP-23
    COMP-40 --> COMP-16
    COMP-50 --> COMP-66
    COMP-51 --> COMP-78
    COMP-52 --> COMP-75
    COMP-5 --> COMP-33
    COMP-10 --> COMP-2
    COMP-33 --> COMP-76
    COMP-52 --> COMP-3
    COMP-52 --> COMP-21
    COMP-57 --> COMP-66
    COMP-54 --> COMP-24
    COMP-6 --> COMP-2
    COMP-5 --> COMP-24
    COMP-63 --> COMP-76
    COMP-34 --> COMP-23
    COMP-4 --> COMP-24
    COMP-75 --> COMP-22
    COMP-11 --> COMP-18
    COMP-63 --> COMP-16
    COMP-3 --> COMP-67
    COMP-76 --> COMP-15
    COMP-50 --> COMP-32
    COMP-61 --> COMP-39
    COMP-42 --> COMP-5
    COMP-76 --> COMP-37
    COMP-29 --> COMP-32
    COMP-75 --> COMP-74
    COMP-17 --> COMP-34
    COMP-76 --> COMP-13
    COMP-56 --> COMP-66
    COMP-42 --> COMP-78
    COMP-54 --> COMP-74
    COMP-5 --> COMP-74
    COMP-45 --> COMP-34
    COMP-4 --> COMP-74
    COMP-15 --> COMP-18
    COMP-62 --> COMP-76
    COMP-55 --> COMP-2
    COMP-50 --> COMP-76
    COMP-69 --> COMP-70
    COMP-35 --> COMP-5
    COMP-29 --> COMP-76
    COMP-8 --> COMP-34
    COMP-68 --> COMP-34
    COMP-5 --> COMP-3
    COMP-5 --> COMP-75
    COMP-4 --> COMP-75
    COMP-19 --> COMP-76
    COMP-35 --> COMP-78
    COMP-40 --> COMP-39
    COMP-54 --> COMP-21
    COMP-3 --> COMP-35
    COMP-72 --> COMP-78
    COMP-54 --> COMP-2
    COMP-32 --> COMP-78
    COMP-11 --> COMP-78
    COMP-71 --> COMP-72
    COMP-72 --> COMP-76
    COMP-42 --> COMP-3
    COMP-42 --> COMP-75
    COMP-20 --> COMP-23
    COMP-10 --> COMP-34
    COMP-63 --> COMP-39
    COMP-2 --> COMP-34
    COMP-23 --> COMP-33
    COMP-26 --> COMP-25
    COMP-23 --> COMP-24
    COMP-64 --> COMP-67
    COMP-43 --> COMP-67
    COMP-35 --> COMP-3
    COMP-35 --> COMP-75
    COMP-15 --> COMP-78
    COMP-32 --> COMP-75
    COMP-58 --> COMP-2
    COMP-41 --> COMP-24
    COMP-76 --> COMP-33
    COMP-59 --> COMP-78
    COMP-52 --> COMP-66
    COMP-38 --> COMP-2
    COMP-69 --> COMP-76
    COMP-76 --> COMP-24
    COMP-63 --> COMP-14
    COMP-48 --> COMP-2
    COMP-47 --> COMP-67
    COMP-40 --> COMP-67
    COMP-50 --> COMP-39
    COMP-42 --> COMP-4
    COMP-23 --> COMP-74
    COMP-55 --> COMP-34
    COMP-10 --> COMP-7
    COMP-76 --> COMP-22
    COMP-60 --> COMP-67
    COMP-6 --> COMP-7
    COMP-26 --> COMP-67
    COMP-15 --> COMP-75
    COMP-41 --> COMP-74
    COMP-49 --> COMP-24
    COMP-68 --> COMP-71
    COMP-23 --> COMP-75
    COMP-35 --> COMP-4
    COMP-29 --> COMP-31
    COMP-59 --> COMP-3
    COMP-59 --> COMP-75
    COMP-76 --> COMP-74
    COMP-53 --> COMP-34
    COMP-65 --> COMP-34
    COMP-70 --> COMP-76
    COMP-59 --> COMP-21
    COMP-17 --> COMP-40
    COMP-40 --> COMP-18
    COMP-56 --> COMP-39
    COMP-6 --> COMP-76
    COMP-44 --> COMP-2
    COMP-50 --> COMP-14
    COMP-46 --> COMP-34
    COMP-29 --> COMP-14
    COMP-52 --> COMP-76
    COMP-2 --> COMP-28
    COMP-71 --> COMP-67
    COMP-17 --> COMP-9
    COMP-41 --> COMP-2
    COMP-19 --> COMP-14
    COMP-54 --> COMP-66
    COMP-76 --> COMP-21
    COMP-63 --> COMP-18
    COMP-28 --> COMP-67
    COMP-61 --> COMP-78
    COMP-57 --> COMP-67
    COMP-76 --> COMP-2
    COMP-13 --> COMP-3
    COMP-58 --> COMP-34
    COMP-70 --> COMP-69
    COMP-19 --> COMP-13
    COMP-8 --> COMP-36
    COMP-73 --> COMP-67
    COMP-37 --> COMP-24
    COMP-38 --> COMP-34
    COMP-12 --> COMP-67
    COMP-48 --> COMP-34
    COMP-12 --> COMP-9
    COMP-4 --> COMP-7
    COMP-5 --> COMP-32
    COMP-55 --> COMP-76
    COMP-11 --> COMP-23
    COMP-34 --> COMP-67
    COMP-49 --> COMP-2
    COMP-36 --> COMP-34
    COMP-10 --> COMP-36
    COMP-33 --> COMP-24
    COMP-61 --> COMP-3
    COMP-61 --> COMP-75
    COMP-56 --> COMP-67
    COMP-75 --> COMP-76
    COMP-17 --> COMP-15
    COMP-24 --> COMP-67
    COMP-54 --> COMP-76
    COMP-27 --> COMP-67
    COMP-4 --> COMP-76
    COMP-25 --> COMP-24
    COMP-33 --> COMP-78
    COMP-28 --> COMP-15
    COMP-3 --> COMP-2
    COMP-8 --> COMP-6
    COMP-63 --> COMP-78
    COMP-17 --> COMP-13
    COMP-15 --> COMP-23
    COMP-52 --> COMP-39
    COMP-44 --> COMP-34
    COMP-33 --> COMP-74
    COMP-12 --> COMP-15
    COMP-25 --> COMP-26
    COMP-12 --> COMP-10
    COMP-7 --> COMP-78
    COMP-62 --> COMP-24
    COMP-10 --> COMP-6
    COMP-31 --> COMP-24
    COMP-25 --> COMP-74
    COMP-58 --> COMP-76
    COMP-59 --> COMP-66
    COMP-33 --> COMP-75
    COMP-10 --> COMP-8
    COMP-6 --> COMP-38
    COMP-62 --> COMP-78
    COMP-38 --> COMP-76
    COMP-20 --> COMP-67
    COMP-50 --> COMP-78
    COMP-29 --> COMP-78
    COMP-21 --> COMP-67
    COMP-19 --> COMP-22
    COMP-76 --> COMP-66
    COMP-62 --> COMP-74
    COMP-19 --> COMP-78
    COMP-25 --> COMP-2
    COMP-31 --> COMP-74
    COMP-36 --> COMP-28
    COMP-54 --> COMP-39
    COMP-18 --> COMP-24
    COMP-19 --> COMP-74
    COMP-62 --> COMP-75
    COMP-5 --> COMP-25
    COMP-3 --> COMP-34
    COMP-55 --> COMP-38
    COMP-23 --> COMP-76
    COMP-62 --> COMP-21
    COMP-43 --> COMP-2
    COMP-76 --> COMP-32
    COMP-20 --> COMP-18
    COMP-31 --> COMP-75
    COMP-29 --> COMP-75
    COMP-17 --> COMP-24
    COMP-55 --> COMP-37
    COMP-19 --> COMP-75
    COMP-41 --> COMP-76
    COMP-45 --> COMP-24
    COMP-19 --> COMP-21
    COMP-17 --> COMP-22
    COMP-51 --> COMP-67
    COMP-7 --> COMP-4
    COMP-4 --> COMP-38
    COMP-47 --> COMP-2
    COMP-5 --> COMP-14
    COMP-8 --> COMP-24
    COMP-60 --> COMP-2
    COMP-76 --> COMP-16
    COMP-68 --> COMP-24
    COMP-69 --> COMP-78
    COMP-18 --> COMP-3
    COMP-17 --> COMP-74
    COMP-72 --> COMP-71
    COMP-32 --> COMP-25
    COMP-69 --> COMP-74
    COMP-45 --> COMP-74
    COMP-49 --> COMP-76
    COMP-12 --> COMP-11
    COMP-33 --> COMP-23
    COMP-74 --> COMP-68
    COMP-2 --> COMP-33
    COMP-10 --> COMP-24
    COMP-63 --> COMP-23
    COMP-42 --> COMP-67
    COMP-17 --> COMP-75
    COMP-2 --> COMP-24
    COMP-17 --> COMP-21
    COMP-8 --> COMP-74
    COMP-6 --> COMP-5
    COMP-68 --> COMP-74
    COMP-70 --> COMP-78
    COMP-69 --> COMP-75
    COMP-45 --> COMP-3
    COMP-45 --> COMP-75
    COMP-52 --> COMP-5
    COMP-71 --> COMP-2
    COMP-45 --> COMP-21
    COMP-6 --> COMP-78
    COMP-64 --> COMP-34
    COMP-43 --> COMP-34
    COMP-11 --> COMP-40
    COMP-2 --> COMP-26
    COMP-38 --> COMP-37
    COMP-28 --> COMP-2
    COMP-52 --> COMP-78
    COMP-27 --> COMP-26
    COMP-35 --> COMP-67
    COMP-71 --> COMP-68
    COMP-36 --> COMP-8
    COMP-36 --> COMP-15
    COMP-10 --> COMP-74
    COMP-72 --> COMP-67
    COMP-32 --> COMP-67
    COMP-11 --> COMP-67
    COMP-2 --> COMP-74
    COMP-11 --> COMP-9
    COMP-8 --> COMP-2
    COMP-36 --> COMP-37
    COMP-68 --> COMP-2
    COMP-37 --> COMP-76
    COMP-12 --> COMP-2
    COMP-76 --> COMP-39
    COMP-70 --> COMP-3
    COMP-55 --> COMP-24
    COMP-47 --> COMP-34
    COMP-40 --> COMP-34
    COMP-70 --> COMP-75
    COMP-10 --> COMP-3
    COMP-10 --> COMP-75
    COMP-34 --> COMP-2
    COMP-62 --> COMP-66
    COMP-42 --> COMP-35
    COMP-60 --> COMP-34
    COMP-6 --> COMP-3
    COMP-6 --> COMP-75
    COMP-19 --> COMP-23
    COMP-63 --> COMP-19
    COMP-26 --> COMP-34
    COMP-76 --> COMP-31
    COMP-53 --> COMP-33
    COMP-15 --> COMP-67
    COMP-24 --> COMP-2
    COMP-53 --> COMP-24
    COMP-65 --> COMP-24
    COMP-27 --> COMP-2
    COMP-3 --> COMP-36
    COMP-75 --> COMP-78
    COMP-20 --> COMP-11
    COMP-4 --> COMP-5
    COMP-76 --> COMP-38
    COMP-55 --> COMP-74
    COMP-59 --> COMP-67
    COMP-25 --> COMP-76
    COMP-76 --> COMP-14
    COMP-46 --> COMP-24
    COMP-54 --> COMP-78
    COMP-5 --> COMP-78
    COMP-4 --> COMP-78
    COMP-11 --> COMP-15
    COMP-31 --> COMP-32
    COMP-11 --> COMP-10
    COMP-71 --> COMP-34
    COMP-55 --> COMP-75
    COMP-43 --> COMP-76
    COMP-55 --> COMP-21
    COMP-53 --> COMP-74
    COMP-28 --> COMP-34
    COMP-6 --> COMP-4
    COMP-57 --> COMP-34
    COMP-58 --> COMP-24
    COMP-71 --> COMP-70
    COMP-52 --> COMP-4
    COMP-31 --> COMP-76
    COMP-38 --> COMP-24
    COMP-73 --> COMP-34
    COMP-46 --> COMP-74
    COMP-3 --> COMP-6
    COMP-48 --> COMP-24
    COMP-54 --> COMP-3
    COMP-54 --> COMP-75
    COMP-67 --> COMP-24
    COMP-12 --> COMP-34
    COMP-4 --> COMP-3
    COMP-53 --> COMP-21
    COMP-3 --> COMP-8
    COMP-45 --> COMP-66
    COMP-36 --> COMP-24
    COMP-21 --> COMP-2
    COMP-68 --> COMP-70
    COMP-19 --> COMP-16
    COMP-53 --> COMP-2
    COMP-65 --> COMP-2
    COMP-76 --> COMP-18
    COMP-58 --> COMP-74
    COMP-56 --> COMP-34
    COMP-61 --> COMP-67
    COMP-24 --> COMP-34
    COMP-38 --> COMP-74
    COMP-46 --> COMP-2
    COMP-18 --> COMP-76
    COMP-48 --> COMP-74
    COMP-27 --> COMP-34
    COMP-58 --> COMP-3
    COMP-58 --> COMP-75
    COMP-44 --> COMP-24
    COMP-58 --> COMP-21
    COMP-36 --> COMP-74
    COMP-8 --> COMP-7
    COMP-38 --> COMP-75
    COMP-48 --> COMP-75
    COMP-5 --> COMP-4
    COMP-23 --> COMP-78
    COMP-48 --> COMP-21
    COMP-25 --> COMP-31
    COMP-62 --> COMP-39
    COMP-17 --> COMP-16
    COMP-45 --> COMP-76
    COMP-51 --> COMP-2
    COMP-28 --> COMP-76
    COMP-67 --> COMP-2
    COMP-40 --> COMP-9
    COMP-41 --> COMP-78
    COMP-29 --> COMP-30
    COMP-25 --> COMP-14
    COMP-44 --> COMP-74
    COMP-50 --> COMP-25
    COMP-36 --> COMP-2
    COMP-8 --> COMP-76
    COMP-31 --> COMP-25
    COMP-76 --> COMP-78
    COMP-68 --> COMP-76
    COMP-29 --> COMP-25
    COMP-49 --> COMP-33
    COMP-63 --> COMP-67
    COMP-73 --> COMP-28
    COMP-20 --> COMP-34
    COMP-40 --> COMP-17
    COMP-63 --> COMP-9
    COMP-21 --> COMP-34
    COMP-69 --> COMP-72
    COMP-44 --> COMP-75
    COMP-55 --> COMP-66
    COMP-34 --> COMP-28
    COMP-7 --> COMP-67
    COMP-44 --> COMP-21
    COMP-10 --> COMP-76
    COMP-49 --> COMP-78
    COMP-41 --> COMP-75
    COMP-2 --> COMP-76
    COMP-31 --> COMP-14
    COMP-27 --> COMP-76
    COMP-41 --> COMP-21
    COMP-3 --> COMP-24
    COMP-76 --> COMP-3
    COMP-76 --> COMP-75
    COMP-68 --> COMP-69
    COMP-15 --> COMP-11
    COMP-40 --> COMP-15
    COMP-40 --> COMP-10
    COMP-49 --> COMP-74
    COMP-53 --> COMP-66
    COMP-50 --> COMP-67
    COMP-70 --> COMP-72
    COMP-12 --> COMP-40
    COMP-29 --> COMP-67
    COMP-72 --> COMP-2
    COMP-11 --> COMP-2
    COMP-63 --> COMP-15
    COMP-45 --> COMP-39
    COMP-63 --> COMP-10
    COMP-19 --> COMP-67
    COMP-49 --> COMP-3
    COMP-49 --> COMP-75
    COMP-51 --> COMP-34
    COMP-72 --> COMP-68
    COMP-3 --> COMP-74
    COMP-49 --> COMP-21
    COMP-7 --> COMP-35
    COMP-37 --> COMP-78
    COMP-58 --> COMP-66
    COMP-12 --> COMP-17
    COMP-3 --> COMP-75
    COMP-17 --> COMP-14
    COMP-48 --> COMP-66
    COMP-21 --> COMP-76
    COMP-28 --> COMP-38
    COMP-53 --> COMP-76
    COMP-65 --> COMP-76
    COMP-19 --> COMP-18
    COMP-42 --> COMP-34
    COMP-28 --> COMP-37
    COMP-46 --> COMP-76
    COMP-25 --> COMP-78
    COMP-64 --> COMP-24
    COMP-69 --> COMP-67
    COMP-43 --> COMP-24
    COMP-63 --> COMP-20
    COMP-2 --> COMP-31
    COMP-36 --> COMP-7
    COMP-35 --> COMP-34
    COMP-27 --> COMP-31
    COMP-12 --> COMP-13
    COMP-20 --> COMP-40
    COMP-44 --> COMP-66
    COMP-72 --> COMP-34
    COMP-32 --> COMP-34
    COMP-11 --> COMP-34
    COMP-76 --> COMP-23
    COMP-47 --> COMP-24
    COMP-40 --> COMP-24
    COMP-2 --> COMP-14
    COMP-48 --> COMP-76
    COMP-55 --> COMP-39
    COMP-17 --> COMP-18
    COMP-41 --> COMP-66
    COMP-31 --> COMP-78
    COMP-67 --> COMP-76
    COMP-64 --> COMP-74
    COMP-20 --> COMP-9
    COMP-60 --> COMP-24
    COMP-43 --> COMP-74
    COMP-25 --> COMP-75
    COMP-70 --> COMP-67
    COMP-36 --> COMP-76
    COMP-26 --> COMP-24
    COMP-40 --> COMP-11
```
