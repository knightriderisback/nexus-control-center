import sys
import os

# Add backend to sys.path
sys.path.insert(0, "/root/control-center/backend")

# Isolate environment for zero-cost and unconfigured provider assertions
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
