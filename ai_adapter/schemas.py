import uuid
from typing import Any, Dict, List, Literal, NotRequired, TypedDict, Union

from pydantic import BaseModel, Field

# --- 配置管理模型 ---


class ModelParams(BaseModel):
    """AI模型参数配置。

    定义了AI模型的基本参数，包括模型列表、使用索引、温度设置等。
    """

    model_list: List[str] = Field(..., description="可用的模型列表")
    model_use: int = Field(default=0, description="当前使用的模型索引")
    temperature: float = Field(..., description="模型生成的温度参数")
    vision_capable_indices: List[int] = Field(
        ..., description="支持视觉功能的模型索引列表"
    )


class SharedModelConfig(BaseModel):
    """共享模型配置基类。

    所有AI模型配置的基类，包含通用的配置项。
    """

    enabled: bool = Field(default=False, description="是否启用此模型")
    priority: int = Field(..., description="模型优先级，数值越小优先级越高")
    model_params: ModelParams = Field(..., description="模型参数配置")


class GeminiConfig(SharedModelConfig):
    """Gemini模型配置。

    Google Gemini AI模型的配置参数。
    """

    provider: Literal["gemini"] = Field(default="gemini", description="模型提供商")
    api_key_env: str = Field(..., description="API密钥的环境变量名")


class OpenAIConfig(SharedModelConfig):
    """OpenAI模型配置。

    OpenAI API模型的配置参数。
    """

    provider: Literal["openai"] = Field(default="openai", description="模型提供商")
    api_key_env: str = Field(..., description="API密钥的环境变量名")
    base_url: str = Field(..., description="API基础URL")


class OllamaConfig(SharedModelConfig):
    """Ollama模型配置。

    本地Ollama模型的配置参数。
    """

    provider: Literal["ollama"] = Field(default="ollama", description="模型提供商")
    base_url: str = Field(..., description="Ollama服务的基础URL")


# 联合类型，表示可以是任意一种模型配置
ModelConfigUnion = Union[GeminiConfig, OpenAIConfig, OllamaConfig]


class AppConfig(BaseModel):
    """应用程序配置模型。

    包含所有AI模型配置和提示词模板的完整应用配置。
    """

    models: Dict[str, ModelConfigUnion] = Field(..., description="所有AI模型的配置字典")
    prototype_identification_prompt: str = Field(..., description="原型识别提示词模板")
    analysis_prompt: str = Field(..., description="分析提示词模板")
    follow_up_prompt: str = Field(..., description="追问生成提示词模板")
    spell_checker_prompt: str = Field(..., description="拼写检查提示词模板")
    intelligent_search_prompt: str = Field(..., description="智能搜索提示词模板")


# --- 消息块模式 ---


class TextBlock(BaseModel):
    """文本消息块。

    用于表示纯文本内容的消息块。
    """

    type: Literal["text"] = Field(default="text", description="消息块类型")
    text: str = Field(..., description="文本内容")


class ImageBlock(BaseModel):
    """图像消息块。

    用于表示图像内容的消息块，支持多模态AI交互。
    """

    type: Literal["image"] = Field(default="image", description="消息块类型")
    mime_type: str = Field(..., description="图像的MIME类型")
    image_data: bytes = Field(..., description="图像的二进制数据")


class ToolCallRequestBlock(BaseModel):
    """工具调用请求消息块。

    用于表示AI请求调用工具的消息块。
    """

    type: Literal["tool_request"] = Field(
        default="tool_request", description="消息块类型"
    )
    id: str = Field(..., description="工具调用的唯一标识符")
    tool_name: str = Field(..., description="要调用的工具名称")
    arguments_json: str = Field(..., description="工具参数的JSON字符串")


class ToolResultBlock(BaseModel):
    """工具调用结果消息块。

    用于表示工具执行结果的消息块。
    """

    type: Literal["tool_result"] = Field(
        default="tool_result", description="消息块类型"
    )
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="结果消息的唯一标识符"
    )
    tool_call_id: str = Field(..., description="对应的工具调用请求ID")
    tool_name: str = Field(..., description="执行的工具名称")
    result: str = Field(..., description="工具执行的结果")


# --- 角色消息模式 ---


class SystemInternalMessage(BaseModel):
    """系统角色消息。

    用于表示系统指令和配置信息。
    """

    role: Literal["system"] = Field(default="system", description="消息角色")
    content: List[TextBlock] = Field(..., description="系统消息内容列表")


class UserInternalMessage(BaseModel):
    """用户角色消息。

    用于表示用户的输入，支持文本和图像。
    """

    role: Literal["user"] = Field(default="user", description="消息角色")
    content: List[Union[TextBlock, ImageBlock]] = Field(
        ..., description="用户消息内容列表"
    )


class AssistantInternalMessage(BaseModel):
    """助手角色消息。

    用于表示AI助手的回复，支持文本和工具调用。
    """

    role: Literal["assistant"] = Field(default="assistant", description="消息角色")
    content: List[Union[TextBlock, ToolCallRequestBlock]] = Field(
        ..., description="助手消息内容列表"
    )


class ToolInternalMessage(BaseModel):
    """工具角色消息。

    用于表示工具执行结果的返回消息。
    """

    role: Literal["tool"] = Field(default="tool", description="消息角色")
    content: List[ToolResultBlock] = Field(..., description="工具结果消息内容列表")


# 联合类型，表示可以是任意一种内部消息
InternalMessageUnion = Union[
    SystemInternalMessage,
    UserInternalMessage,
    AssistantInternalMessage,
    ToolInternalMessage,
]

# 类型别名，用于表示对话历史
ConversationHistory = List[InternalMessageUnion]


class InternalTool(BaseModel):
    """内部工具定义模型。

    用于描述可被AI调用的内部工具。
    """

    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters_schema: Dict[str, Any] = Field(..., description="工具参数的JSON Schema")
    tags: List[str] = Field(
        default_factory=list, description="工具标签列表，用于分类和筛选"
    )
