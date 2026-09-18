# Synthetic test file for Phase 18 SecOps validation
AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE12345"
GITHUB_PAT = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"

def handle_rpc(user_command, raw_payload):
    import os, pickle
    # Dangerous execution
    os.system(user_command)
    return pickle.loads(raw_payload)
