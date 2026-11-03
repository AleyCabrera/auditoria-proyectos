from auditor.secrets import redact_text, scan_secrets


def test_aws_key_detected():
    hits = scan_secrets("key = 'AKIAIOSFODNN7EXAMPLE'")
    assert any(h.rule == "aws_access_key" for h in hits)


def test_placeholder_ignored():
    hits = scan_secrets('password = "your_password_here"')
    assert not any(h.rule == "generic_password" for h in hits)


def test_redaction_keeps_shape():
    text = "AKIAIOSFODNN7EXAMPLE"
    hits = scan_secrets(text)
    redacted = redact_text(text, hits)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert redacted.startswith("AKIA")


def test_private_key_detected():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
    hits = scan_secrets(text)
    assert any(h.rule == "private_key" for h in hits)
    
def test_aws_secret_key_with_short_variable_name():
    # AWS_SECRET también debe detectarse (no solo aws_secret_access_key)
    hits = scan_secrets('AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"')
    assert any(h.rule == "aws_secret_key" for h in hits)