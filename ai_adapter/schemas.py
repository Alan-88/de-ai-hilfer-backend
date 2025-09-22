from typing import Dict, List, Literal, TypedDict, Any, Union
from typing import NotRequired
from pydantic import BaseModel, Field
import uuid # 导入 uuid

class ModelParams(BaseModel):
    model_list: List[str]
    model_use: int = 0
    temperature: float
    vision_capable_indices: List[int]

class SharedModelConfig(BaseModel):
    enabled: bool = False
    priority: int
    model_params: ModelParams

class GeminiConfig(SharedModelConfig):
    provider: Literal["gemini"]
    api_key_env: str

class OpensourceAIConfig(SharedModelConfig):
    provider: Literal["openai"]
    api_key_env: str
    base_url: str

class OllamaConfig(SharedModelConfig):
    provider: Literal["ollama"]
    base_url: str

AnyModelConfig = Union[GeminiConfig, OpensourceAIConfig, OllamaConfig]

class AppConfig(BaseModel):
    models: Dict[str, AnyModelConfig]
    prototype_identification_prompt: str
    analysis_prompt: str
    follow_up_prompt: str
    spell_checker_prompt: str
    intelligent_search_prompt: str

# --- 内部消息块模式 ---
class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str

class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    mime_type: str
    image_data: bytes

class ToolCallRequestBlock(BaseModel):
    type: Literal["tool_request"] = "tool_request"
    id: str
    tool_name: str
    arguments_json: str

class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_call_id: str
    tool_name: str
    result: str

# --- 特定角色的消息模式 ---
class SystemInternalMessage(BaseModel):
    role: Literal["system"] = "system"
    content: List[TextBlock]

class UserInternalMessage(BaseModel):
    role: Literal["user"] = "user"
    content: List[Union[TextBlock, ImageBlock]]

class AssistantInternalMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextBlock, ToolCallRequestBlock]]

class ToolInternalMessage(BaseModel):
    role: Literal["tool"] = "tool"
    content: List[ToolResultBlock]

AnyInternalMessage = Union[
    SystemInternalMessage,
    UserInternalMessage,
    AssistantInternalMessage,
    ToolInternalMessage
]
ConversationHistory = List[AnyInternalMessage]

class InternalTool(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    tags: List[str] = []
