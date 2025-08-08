"""Agent configuration."""

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent configuration"""
    
    # Model configuration
    model: str = Field(default="claude-3-5-sonnet-20241022", description="Model name")
    max_tokens: int = Field(default=4096, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Temperature for generation")
    top_p: Optional[float] = Field(default=None, description="Top-p sampling")
    top_k: Optional[int] = Field(default=None, description="Top-k sampling")
    stop_sequences: Optional[List[str]] = Field(default=None, description="Stop sequences")
    
    # API configuration
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Base URL for API")
    
    # System configuration
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    cache_system_prompt: bool = Field(default=False, description="Whether to cache system prompt")
    
    # Advanced features
    thinking: Optional[Dict[str, Any]] = Field(default=None, description="Thinking mode configuration")
    beta: bool = Field(default=False, description="Enable beta features")
    fine_grained_tool_streaming: bool = Field(default=False, description="Enable fine-grained tool streaming")
    
    # Timeout configuration
    timeout: int = Field(default=120, description="Request timeout in seconds")
    
    @classmethod
    def from_env(cls, **kwargs) -> "AgentConfig":
        """Create config from environment variables"""
        # Get from environment with fallbacks
        api_key = os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_API_BASE")
        
        # Merge with provided kwargs
        config_dict = {
            "api_key": api_key,
            "base_url": base_url,
            **kwargs
        }
        
        return cls(**config_dict)
    
    def betas(self) -> List[str]:
        """Get beta features list"""
        betas = []
        if self.beta:
            # Add beta features
            if self.fine_grained_tool_streaming:
                betas.append("fine-grained-tool-streaming-2025-05-14")
            if self.thinking:
                betas.append("thinking-2024-11-05")
        return betas
    
    def get_request_params(self) -> Dict[str, Any]:
        """Get request parameters for API calls"""
        params: Dict[str, Any] = {
            "max_tokens": self.max_tokens
        }
        
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.top_k is not None:
            params["top_k"] = self.top_k
        if self.stop_sequences:
            params["stop_sequences"] = self.stop_sequences
        if self.thinking:
            params["thinking"] = self.thinking
            
        if self.system_prompt:
            params["system"] = self.system_prompt
            if self.cache_system_prompt:
                params["system"] = {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
        
        return params