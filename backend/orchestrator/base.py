"""
NEXUS Provider-Neutral AI Orchestration Layer.
Maintains full backward compatibility with Phase 6-9 interfaces while bridging
directly to the production-grade Phase 10 providers subsystem in `orchestrator.providers`.

Standardized interface:
AIProvider / BaseLLMProvider
├── generate()
├── stream()
├── health()
└── metadata()

Adapters:
- GeminiProvider
- OpenAIProvider
- AnthropicProvider
- OllamaProvider
- LocalASTProvider
- MockProvider

Features:
- Provider registry
- Dynamic routing with fallback cascade
- Timeout, circuit breaker, and retry handling
- Explicit NOT_CONFIGURED status for unconfigured real providers
- Model metadata & token/cost accounting ($0.00 zero-cost guardrail)
"""

import os
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator, List, Tuple

from orchestrator.providers import (
    BaseLLMProvider,
    AIProvider,
    AIProviderAdapter,
    GeminiProvider,
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    LocalASTProvider,
    MockProvider,
    MockProviderAdapter,
    ProviderRouter,
    provider_router,
    usage_tracker
)


# =============================================================================
# Provider Registry & Factory
# =============================================================================

class AIProviderRegistry:
    """Registry coordinating available AI providers and status resolution."""

    def __init__(self):
        self._providers: Dict[str, AIProvider] = {
            "mock": MockProvider(),
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "ollama": OllamaProvider(),
            "local": LocalASTProvider()
        }

    def get_provider(self, name: str) -> Optional[AIProvider]:
        return self._providers.get(name.lower().strip())

    def list_providers(self) -> List[Dict[str, Any]]:
        results = []
        for name, p in self._providers.items():
            h = p.health()
            m = p.metadata()
            results.append({
                "name": name,
                "health": h.model_dump() if hasattr(h, "model_dump") else (h.dict() if hasattr(h, "dict") else h),
                "metadata": m.model_dump() if hasattr(m, "model_dump") else (m.dict() if hasattr(m, "dict") else m)
            })
        return results

    def resolve_provider(self, preference: Optional[str] = None) -> AIProvider:
        """Resolves preferred provider if ready, else falls back cleanly to MockProvider."""
        if preference:
            p = self.get_provider(preference)
            if p:
                h = p.health()
                is_avail = h.get("available", False) if hasattr(h, "get") else getattr(h, "available", False)
                if is_avail:
                    return p

        # Check for configured real providers
        for p_name in ["gemini", "openai", "anthropic", "ollama"]:
            p = self._providers.get(p_name)
            if p:
                h = p.health()
                is_avail = h.get("available", False) if hasattr(h, "get") else getattr(h, "available", False)
                if is_avail:
                    return p

        return self._providers["mock"]

provider_registry = AIProviderRegistry()

def get_ai_adapter(provider_name: Optional[str] = None) -> AIProvider:
    """Convenience accessor resolving configured provider with safe mock fallback."""
    return provider_registry.resolve_provider(provider_name)


# =============================================================================
# AI Router with Intent Classification
# =============================================================================

class AIRouter:
    """
    Provider-neutral AI Router.
    Routes high-level directives to appropriate models or deterministic mock synthesis.
    """
    def __init__(self, default_provider: Optional[str] = None):
        self.default_provider = default_provider

    async def route_directive(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        provider = provider_registry.resolve_provider(self.default_provider)
        try:
            response = await asyncio.wait_for(provider.generate(prompt, context=context), timeout=30.0)
        except Exception as e:
            # Fallback to mock on timeout or failure
            fallback = provider_registry.get_provider("mock")
            response = await fallback.generate(prompt, context=context)
            response["fallback_triggered"] = True
            response["fallback_reason"] = str(e)

        # Classify intent for agent mapping
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["search", "find", "grep", "ast", "research"]):
            target_agent = "agent-research"
            suggested_tool = "codebase_search"
        elif any(w in prompt_lower for w in ["refactor", "code", "dev", "fix", "modify", "patch", "feature"]):
            target_agent = "agent-dev"
            suggested_tool = "generate_git_diff"
        elif any(w in prompt_lower for w in ["test", "verify", "qa", "pytest"]):
            target_agent = "agent-qa"
            suggested_tool = "test.pytest"
        elif any(w in prompt_lower for w in ["security", "secret", "scan", "cve"]):
            target_agent = "agent-security"
            suggested_tool = "security.secret_scan"
        elif any(w in prompt_lower for w in ["doc", "adr", "markdown", "chronicler"]):
            target_agent = "agent-docs"
            suggested_tool = "create_adr"
        else:
            target_agent = "agent-research"
            suggested_tool = "read_file"

        return {
            "provider": response.get("provider", "MockEngine"),
            "model": response.get("model", "nexus-mock-v1"),
            "target_agent": target_agent,
            "suggested_tool": suggested_tool,
            "synthesized_response": response.get("content", ""),
            "tokens_used": response.get("tokens_used", 0),
            "estimated_cost_usd": response.get("estimated_cost_usd", 0.0)
        }

ai_router = AIRouter()
