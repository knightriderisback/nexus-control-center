from core.secrets import secret_manager

def test_secret_masking():
    assert secret_manager.mask_value(None) == "[UNSET]"
    assert secret_manager.mask_value("") == "[UNSET]"
    assert secret_manager.mask_value("short") == "******"
    masked = secret_manager.mask_value("sk-proj-secrettoken998877")
    assert masked.startswith("sk")
    assert masked.endswith("877")
    assert "secrettoken" not in masked

def test_secret_metadata_has_zero_leakage():
    meta = secret_manager.list_secrets_metadata()
    assert len(meta) >= 4
    for m in meta:
        assert "name" in m
        assert "preview" in m
        assert "secret_value" not in m
