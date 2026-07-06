from typing import Optional
from app.llm.base_llm import BaseLLM
from app.core.logger import get_logger

logger = get_logger(__name__)

# Make litellm optional
try:
    import litellm
    from litellm import Router
    LITELLETM_AVAILABLE = True
except ImportError:
    litellm = None
    Router = None
    LITELLETM_AVAILABLE = False


class LiteLLMProvider(BaseLLM):
    def __init__(self, api_keys: dict[str, str]) -> None:
        if not LITELLETM_AVAILABLE:
            logger.warning("litellm not installed, using mock mode")
            self.router = None
            self.primary_model = None
            return

        model_list = []
        available_tiers = []
        
        # Register models dynamically if keys are provided
        if api_keys.get("groq"):
            model_list.append({
                "model_name": "tier_1",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": api_keys["groq"]
                }
            })
            available_tiers.append("tier_1")
            
        if api_keys.get("gemini"):
            model_list.append({
                "model_name": "tier_2",
                "litellm_params": {
                    "model": "gemini/gemini-2.5-flash",
                    "api_key": api_keys["gemini"]
                }
            })
            available_tiers.append("tier_2")
            
        if api_keys.get("openrouter"):
            model_list.append({
                "model_name": "tier_3",
                "litellm_params": {
                    "model": "openrouter/google/gemma-4-31b-it:free",
                    "api_key": api_keys["openrouter"],
                    "extra_headers": {
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "DataPilot"
                    }
                }
            })
            available_tiers.append("tier_3")
            
        if not model_list:
            logger.warning("No valid API keys found for LiteLLM router.")
            self.router = None
            self.primary_model = None
            return

        self.primary_model = available_tiers[0]
        fallbacks = available_tiers[1:]
        fallback_config = [{self.primary_model: fallbacks}] if fallbacks else []
        
        self.router = Router(
            model_list=model_list,
            fallbacks=fallback_config,
            timeout=30,
            num_retries=0,
        )

    def generate(self, prompt: str, system_message: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        if not self.router or not self.primary_model:
            return "ERROR: No API keys configured in settings."
            
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self.primary_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_tokens or 1024,
        }

            
        try:
            logger.debug(f"Calling litellm latency router")
            response = self.router.completion(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.exception("LiteLLM router completion failed")
            raise e