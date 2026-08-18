---
document: Functional Analysis
system: Projects (core)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:33Z
generator_version: 0.3.0
model_hash: 7aeb15531ff4
edition: 6
---

# Functional Analysis: Projects (core)

## Capability Inventory

| ID | Capability | Priority | Status | Description |
|----|-----------|----------|--------|-------------|
| CAP-1 | Web Routes | medium | ACTIVE | — |
| CAP-2 | Asgi | medium | ACTIVE | — |
| CAP-3 | Db | medium | ACTIVE | — |
| CAP-4 | Dummy | medium | ACTIVE | — |
| CAP-5 | Filebased | medium | ACTIVE | — |
| CAP-6 | Locmem | medium | ACTIVE | — |
| CAP-7 | Memcached | medium | ACTIVE | — |
| CAP-8 | Redis | medium | ACTIVE | — |
| CAP-9 | Async Checks | medium | ACTIVE | — |
| CAP-10 | Caches | medium | ACTIVE | — |
| CAP-11 | Commands | medium | ACTIVE | — |
| CAP-12 | Django 4 0 | medium | ACTIVE | — |
| CAP-13 | Database | medium | ACTIVE | — |
| CAP-14 | Files | medium | ACTIVE | — |
| CAP-15 | Mail | medium | ACTIVE | — |
| CAP-16 | Messages | medium | ACTIVE | — |
| CAP-17 | Model Checks | medium | ACTIVE | — |
| CAP-18 | Registry | medium | ACTIVE | — |
| CAP-19 | Csrf | medium | ACTIVE | — |
| CAP-20 | Sessions | medium | ACTIVE | — |
| CAP-21 | Templates | medium | ACTIVE | — |
| CAP-22 | Translation | medium | ACTIVE | — |
| CAP-23 | Urls | medium | ACTIVE | — |
| CAP-24 | Exceptions | medium | ACTIVE | — |
| CAP-25 | Images | medium | ACTIVE | — |
| CAP-26 | Move | medium | ACTIVE | — |
| CAP-27 | Filesystem | medium | ACTIVE | — |
| CAP-28 | Handler | medium | ACTIVE | — |
| CAP-29 | Memory | medium | ACTIVE | — |
| CAP-30 | Mixins | medium | ACTIVE | — |
| CAP-31 | Uploadedfile | medium | ACTIVE | — |
| CAP-32 | Uploadhandler | medium | ACTIVE | — |
| CAP-33 | Exception | medium | ACTIVE | — |
| CAP-34 | Wsgi | medium | ACTIVE | — |
| CAP-35 | Console | medium | ACTIVE | — |
| CAP-36 | Smtp | medium | ACTIVE | — |
| CAP-37 | Deprecation | medium | ACTIVE | — |
| CAP-38 | Message | medium | ACTIVE | — |
| CAP-39 | Color | medium | ACTIVE | — |
| CAP-40 | Check | medium | ACTIVE | — |
| CAP-41 | Compilemessages | medium | ACTIVE | — |
| CAP-42 | Createcachetable | medium | ACTIVE | — |
| CAP-43 | Dbshell | medium | ACTIVE | — |
| CAP-44 | Diffsettings | medium | ACTIVE | — |
| CAP-45 | Dumpdata | medium | ACTIVE | — |
| CAP-46 | Flush | medium | ACTIVE | — |
| CAP-47 | Inspectdb | medium | ACTIVE | — |
| CAP-48 | Listurls | medium | ACTIVE | — |
| CAP-49 | Loaddata | medium | ACTIVE | — |
| CAP-50 | Makemessages | medium | ACTIVE | — |
| CAP-51 | Makemigrations | medium | ACTIVE | — |
| CAP-52 | Migrate | medium | ACTIVE | — |
| CAP-53 | Optimizemigration | medium | ACTIVE | — |
| CAP-54 | Runserver | medium | ACTIVE | — |
| CAP-55 | Sendtestemail | medium | ACTIVE | — |
| CAP-56 | Shell | medium | ACTIVE | — |
| CAP-57 | Showmigrations | medium | ACTIVE | — |
| CAP-58 | Sqlflush | medium | ACTIVE | — |
| CAP-59 | Sqlmigrate | medium | ACTIVE | — |
| CAP-60 | Sqlsequencereset | medium | ACTIVE | — |
| CAP-61 | Squashmigrations | medium | ACTIVE | — |
| CAP-62 | Startapp | medium | ACTIVE | — |
| CAP-63 | Startproject | medium | ACTIVE | — |
| CAP-64 | Test | medium | ACTIVE | — |
| CAP-65 | Testserver | medium | ACTIVE | — |
| CAP-66 | Sql | medium | ACTIVE | — |
| CAP-67 | Paginator | medium | ACTIVE | — |
| CAP-68 | Json | medium | ACTIVE | — |
| CAP-69 | Jsonl | medium | ACTIVE | — |
| CAP-70 | Python | medium | ACTIVE | — |
| CAP-71 | Pyyaml | medium | ACTIVE | — |
| CAP-72 | Xml Serializer | medium | ACTIVE | — |
| CAP-73 | Basehttp | medium | ACTIVE | — |
| CAP-74 | Signing | medium | ACTIVE | — |
| CAP-75 | Validators | medium | ACTIVE | — |
| CAP-76 | CLI Base | medium | ACTIVE | — |
| CAP-77 | CLI Templates | medium | ACTIVE | — |

## Functional Decomposition

```mermaid
graph TD
    CAP-1["Web Routes"]
    CAP-2["Asgi"]
    CAP-3["Db"]
    CAP-4["Dummy"]
    CAP-5["Filebased"]
    CAP-6["Locmem"]
    CAP-7["Memcached"]
    CAP-8["Redis"]
    CAP-9["Async Checks"]
    CAP-10["Caches"]
    CAP-11["Commands"]
    CAP-12["Django 4 0"]
    CAP-13["Database"]
    CAP-14["Files"]
    CAP-15["Mail"]
    CAP-16["Messages"]
    CAP-17["Model Checks"]
    CAP-18["Registry"]
    CAP-19["Csrf"]
    CAP-20["Sessions"]
    CAP-21["Templates"]
    CAP-22["Translation"]
    CAP-23["Urls"]
    CAP-24["Exceptions"]
    CAP-25["Images"]
    CAP-26["Move"]
    CAP-27["Filesystem"]
    CAP-28["Handler"]
    CAP-29["Memory"]
    CAP-30["Mixins"]
    CAP-31["Uploadedfile"]
    CAP-32["Uploadhandler"]
    CAP-33["Exception"]
    CAP-34["Wsgi"]
    CAP-35["Console"]
    CAP-36["Smtp"]
    CAP-37["Deprecation"]
    CAP-38["Message"]
    CAP-39["Color"]
    CAP-40["Check"]
    CAP-41["Compilemessages"]
    CAP-42["Createcachetable"]
    CAP-43["Dbshell"]
    CAP-44["Diffsettings"]
    CAP-45["Dumpdata"]
    CAP-46["Flush"]
    CAP-47["Inspectdb"]
    CAP-48["Listurls"]
    CAP-49["Loaddata"]
    CAP-50["Makemessages"]
    CAP-51["Makemigrations"]
    CAP-52["Migrate"]
    CAP-53["Optimizemigration"]
    CAP-54["Runserver"]
    CAP-55["Sendtestemail"]
    CAP-56["Shell"]
    CAP-57["Showmigrations"]
    CAP-58["Sqlflush"]
    CAP-59["Sqlmigrate"]
    CAP-60["Sqlsequencereset"]
    CAP-61["Squashmigrations"]
    CAP-62["Startapp"]
    CAP-63["Startproject"]
    CAP-64["Test"]
    CAP-65["Testserver"]
    CAP-66["Sql"]
    CAP-67["Paginator"]
    CAP-68["Json"]
    CAP-69["Jsonl"]
    CAP-70["Python"]
    CAP-71["Pyyaml"]
    CAP-72["Xml Serializer"]
    CAP-73["Basehttp"]
    CAP-74["Signing"]
    CAP-75["Validators"]
    CAP-76["CLI Base"]
    CAP-77["CLI Templates"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Web Routes | *unrealized* | — |
| Asgi | Asgi (COMP-2) | service |
| Db | Db (COMP-3) | service |
| Dummy | Dummy (COMP-4) | service |
| Filebased | Filebased (COMP-5) | service |
| Locmem | Locmem (COMP-6) | service |
| Memcached | Memcached (COMP-7) | service |
| Redis | Redis (COMP-8) | service |
| Async Checks | Async Checks (COMP-9) | service |
| Caches | Caches (COMP-10) | service |
| Commands | Commands (COMP-11) | service |
| Django 4 0 | Django 4 0 (COMP-12) | service |
| Database | Database (COMP-13) | service |
| Files | Files (COMP-14) | service |
| Mail | Mail (COMP-15) | service |
| Messages | Messages (COMP-16) | service |
| Model Checks | Model Checks (COMP-17) | service |
| Registry | Registry (COMP-18) | service |
| Csrf | Csrf (COMP-19) | service |
| Sessions | Sessions (COMP-20) | service |
| Templates | Templates (COMP-21) | service |
| Translation | Translation (COMP-22) | service |
| Urls | Urls (COMP-23) | service |
| Exceptions | Exceptions (COMP-24) | service |
| Images | Images (COMP-25) | service |
| Move | Move (COMP-26) | service |
| Filesystem | Filesystem (COMP-27) | service |
| Handler | Handler (COMP-28) | service |
| Memory | Memory (COMP-29) | service |
| Mixins | Mixins (COMP-30) | service |
| Uploadedfile | Uploadedfile (COMP-31) | service |
| Uploadhandler | Uploadhandler (COMP-32) | service |
| Exception | Exception (COMP-33) | service |
| Wsgi | Wsgi (COMP-34) | service |
| Console | Console (COMP-35) | service |
| Smtp | Smtp (COMP-36) | service |
| Deprecation | Deprecation (COMP-37) | service |
| Message | Message (COMP-38) | service |
| Color | Color (COMP-39) | service |
| Check | Check (COMP-40) | service |
| Compilemessages | Compilemessages (COMP-41) | service |
| Createcachetable | Createcachetable (COMP-42) | service |
| Dbshell | Dbshell (COMP-43) | service |
| Diffsettings | Diffsettings (COMP-44) | service |
| Dumpdata | Dumpdata (COMP-45) | service |
| Flush | Flush (COMP-46) | service |
| Inspectdb | Inspectdb (COMP-47) | service |
| Listurls | Listurls (COMP-48) | service |
| Loaddata | Loaddata (COMP-49) | service |
| Makemessages | Makemessages (COMP-50) | service |
| Makemigrations | Makemigrations (COMP-51) | service |
| Migrate | Migrate (COMP-52) | service |
| Optimizemigration | Optimizemigration (COMP-53) | service |
| Runserver | Runserver (COMP-54) | service |
| Sendtestemail | Sendtestemail (COMP-55) | service |
| Shell | Shell (COMP-56) | service |
| Showmigrations | Showmigrations (COMP-57) | service |
| Sqlflush | Sqlflush (COMP-58) | service |
| Sqlmigrate | Sqlmigrate (COMP-59) | service |
| Sqlsequencereset | Sqlsequencereset (COMP-60) | service |
| Squashmigrations | Squashmigrations (COMP-61) | service |
| Startapp | Startapp (COMP-62) | service |
| Startproject | Startproject (COMP-63) | service |
| Test | Test (COMP-64) | service |
| Testserver | Testserver (COMP-65) | service |
| Sql | Sql (COMP-66) | service |
| Paginator | Paginator (COMP-67) | service |
| Json | Json (COMP-68) | service |
| Jsonl | Jsonl (COMP-69) | service |
| Python | Python (COMP-70) | service |
| Pyyaml | Pyyaml (COMP-71) | service |
| Xml Serializer | Xml Serializer (COMP-72) | service |
| Basehttp | Basehttp (COMP-73) | service |
| Signing | Signing (COMP-74) | service |
| Validators | Validators (COMP-75) | service |
| CLI Base | CLI Base (COMP-76) | service |
| CLI Templates | *unrealized* | — |

## Behavioral Coverage

Total behaviors: 52

**Untraced behaviors:** 52
- GET  (BEH-1)
- GET bookmarklets/ (BEH-2)
- GET tags/ (BEH-3)
- GET filters/ (BEH-4)
- GET views/ (BEH-5)
- GET views/<view>/ (BEH-6)
- GET models/ (BEH-7)
- GET ^models/(?P<app_label>[^.]+)\.(?P<model_name>[^/]+)/$ (BEH-8)
- GET templates/<path:template>/ (BEH-9)
- GET login/ (BEH-10)
- *...and 42 more*
