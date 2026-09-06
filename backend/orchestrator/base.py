from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AIProviderAdapter(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        pass

class MockProviderAdapter(AIProviderAdapter):
    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        return {
            "provider": "MockEngine",
            "content": f"[NEXUS Synthesizer] Processed directive: '{prompt[:80]}...'. Plan compiled according to policy rules.",
            "tokens_used": 120,
            "finish_reason": "STOP"
        }

class GeminiProviderAdapter(AIProviderAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            # Fallback to local heuristic engine if API key not mounted
            return await MockProviderAdapter().generate_response(prompt, system_instruction, **kwargs)
        # Production Gemini REST call placeholder
        return {
            "provider": "Google Gemini",
            "content": f"[Gemini 2.5 Flash] Reasoning trace complete for prompt: '{prompt[:60]}'.",
            "tokens_used": 240,
            "finish_reason": "STOP"
        }

def get_ai_adapter() -> AIProviderAdapter:
    import os
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return GeminiProviderAdapter(api_key=api_key)
    return MockProviderAdapter()
