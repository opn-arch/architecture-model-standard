from architecture_model.lifecycle.versions import SchemaVersions, ContractKind

def test_schema_versions_expose_all_contracts():
    assert SchemaVersions.MODEL == "2.1.0"
    assert SchemaVersions.PACKAGE == "1.0.0"
    assert SchemaVersions.MANIFEST == "1.0.0"
    assert SchemaVersions.MODEL_SLICE == "1.0.0"
    assert SchemaVersions.VIEW_SPEC == "1.0.0"
    assert SchemaVersions.ARTIFACT_SPEC == "1.0.0"
    assert SchemaVersions.AI_WORK_ORDER == "1.0.0"
    assert SchemaVersions.DIGEST_ALGO == "sha256-v1"

def test_contract_kind_covers_every_persisted_artifact():
    kinds = {k.value for k in ContractKind}
    assert kinds == {
        "model", "package", "manifest", "model-slice",
        "view-spec", "artifact-spec", "ai-work-order",
    }

def test_version_for_kind_lookup():
    assert SchemaVersions.for_kind(ContractKind.MODEL) == "2.1.0"
    assert SchemaVersions.for_kind(ContractKind.VIEW_SPEC) == "1.0.0"
    assert SchemaVersions.for_kind(ContractKind.AI_WORK_ORDER) == "1.0.0"

def test_lifecycle_package_reexports():
    from architecture_model.lifecycle import SchemaVersions as SV, ContractKind as CK
    assert SV is SchemaVersions
    assert CK is ContractKind
