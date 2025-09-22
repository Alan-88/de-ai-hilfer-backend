from abc import ABC, abstractmethod
import copy
import json
import uuid
from .schemas import *
from .tool_manager import tool_manager
from .utils import create_message
from typing import Callable, Dict, List, Union, Any
from os import getenv
import base64

class BaseLLMAdapter(ABC):
    """
    所有大语言模型适配器的抽象基类。
    它定义了一个统一的接口，确保 LLMRouter 可以用同样的方式与任何模型交互。
    """
    def __init__(self, model: str, api_key_env: str, base_url: str, model_params: ModelParams):
        """
        初始化适配器。

        :param model: 模型的名称, e.g., 'gpt-4o', 'gemini-1.5-pro'.
        :param api_key: 访问模型所需的 API 密钥。
        :param base_url: API 的基础 URL (对于自托管或兼容API很有用)。
        :param kwargs: 其他特定于模型的参数。
        """
        self.model = model
        self.api_key_env = api_key_env
        self.api_key = getenv(api_key_env) if api_key_env else None
        self.base_url = base_url
        self.model_params = model_params
        self.internal_tools = tool_manager.internal_tools
    
    def _select_tools(self, tool_tags: str | List[str] | None) -> List[InternalTool]:
        """
        [统一的新方法] 从 ToolManager 的内部工具列表中，根据标签筛选出需要启用的工具。
        这个方法现在对于所有 Adapter 都是通用的。
        """
        if tool_tags is None:
            return []
        if tool_tags == "all":
            return self.internal_tools

        tool_tag_set = set(tool_tags) if isinstance(tool_tags, list) else {tool_tags}
        tool_tag_set.add("") # 总是包含默认（无标签）的工具

        enabled_tools = []
        for tool in self.internal_tools:
            # 如果工具的标签集合与要启用的标签集合有交集
            if tool_tag_set.intersection(tool.tags or [""]):
                enabled_tools.append(tool)
        
        return enabled_tools

    @staticmethod
    def get_system_prompt(messages: list) -> str | None:
        """从对话历史中获取system_prompt"""
        for msg in messages:
            if isinstance(msg, SystemInternalMessage):
                return msg.content[0].text
        return None
    
    @staticmethod
    @abstractmethod
    def pack_history(history: ConversationHistory) -> Any:
        """
        [抽象静态方法] 将内部 ConversationHistory 格式打包成特定于 API 的格式。
        返回值的类型是 Any，因为每个 API 的格式都不同。
        """
        pass

    @staticmethod
    @abstractmethod
    def unpack_response(response: Any) -> AnyInternalMessage | None:
        """
        [抽象静态方法] 将特定于 API 的响应解包成内部 AnyInternalMessage 格式。
        输入值的类型是 Any，因为每个 API 的响应对象都不同。
        """
        pass

    @abstractmethod
    def chat(self, messages: ConversationHistory, tool_tags: str | List[str] = [], **kwargs) -> AnyInternalMessage | None:  
        """
        与大语言模型进行对话。
        
        :param messages: 对话历史。
        :param model_use, temperature: 可选的模型配置参数
        :param tools: 可选的工具列表，遵循OpenAI的JSON Schema格式。
        :param kwargs: 其他API参数。
        :return: 字符串（最终答案）或列表（工具调用请求）。
        """
        pass

    def check_api_key(self):
        if self.api_key is None:
            print(f"警告：环境变量 '{self.api_key_env}' 未设置，模型 '{self.model}' 可能无法使用。")




from google import genai
from google.genai import types

class GeminiAdapter(BaseLLMAdapter):
    """
    适配器，用于处理 Google Gemini 系列模型。
    """
    def __init__(self, model: str, api_key_env: str, model_params: ModelParams):
        def init_client() -> genai.Client | None:
            try:
                return genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"错误：初始化 Gemini 客户端失败 ({self.model}): {e}")
            return None
        
        super().__init__(model, api_key_env, None, model_params)
        super().check_api_key()
        self.client = init_client()
    
    @staticmethod
    def pack_history(history: ConversationHistory) -> List[types.Content]:
        """
        [翻译机] 将我们的内部 ConversationHistory 转换为 Gemini SDK 的格式。
        """
        gemini_history = []
        for message in history:
            # 1. 确定 Gemini 的 role ('user' 或 'model')
            # system prompt 会被单独处理，这里可以先跳过
            if message.role == "system":
                continue
            # Gemini 中, assistant 和 tool 都属于 'model' role
            role = "model" if message.role in ["assistant", "tool"] else "user"

            # 2. 根据 content 中的 block 类型，创建 Gemini 的 parts 列表
            parts = []
            for block in message.content:
                if isinstance(block, TextBlock):
                    parts.append(types.Part(text=block.text))
                elif isinstance(block, ImageBlock):
                    parts.append(types.Part.from_bytes(data=block.image_data, mime_type=block.mime_type))
                elif isinstance(block, ToolCallRequestBlock):
                    # 将我们的 Block 转换为 Gemini 的 FunctionCall
                    args = json.loads(block.arguments_json)
                    parts.append(types.Part.from_function_call(name=block.tool_name, args=args))
                elif isinstance(block, ToolResultBlock):
                    # 将我们的 Block 转换为 Gemini 的 FunctionResponse
                    parts.append(types.Part.from_function_response(
                        name=block.tool_name,
                        response={'content': block.result}
                    ))
            
            if parts:
                gemini_history.append(types.Content(role=role, parts=parts))

        return gemini_history

    @staticmethod
    def unpack_response(response: types.GenerateContentResponse) -> AssistantInternalMessage | None:
        """
        [翻译机] 将 Gemini SDK 的响应转换为我们的内部 AssistantInternalMessage。
        """
        try:
            if not response.candidates:
                print("警告：Gemini 响应中没有候选内容。")
                return create_message(role="assistant", text="模型没有返回任何有效内容。")

            candidate = response.candidates[0]
            content_blocks = []
            tool_requests = []
            text_parts = []

            # **核心修复：遍历所有部分，而不是只看第一个**
            for part in candidate.content.parts:
                # 尝试提取工具调用
                if fc := getattr(part, "function_call", None):
                    tool_requests.append(
                        ToolCallRequestBlock(
                            id=str(uuid.uuid4()), # Gemini不提供ID，我们自己生成
                            tool_name=fc.name,
                            arguments_json=json.dumps({k: v for k, v in fc.args.items()}, ensure_ascii=False)
                        )
                    )
                # **新的健壮文本提取逻辑**
                # 检查 part 是否有 text 属性且不为空
                elif hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
            
            # 如果有工具调用，将它们添加到内容块中
            if tool_requests:
                content_blocks.extend(tool_requests)
            
            # 将所有文本部分连接成最终答案
            final_text = "".join(text_parts).strip()
            # 只有当最终文本不为空时，才将其添加为文本块
            if final_text:
                 content_blocks.append(TextBlock(text=final_text))
            
            # 如果最终什么内容都没有，返回None
            if not content_blocks:
                return None

            return AssistantInternalMessage(content=content_blocks)

        except Exception as e:
            print(f"错误：解析 Gemini 响应时出错: {e}")
            return create_message(role="assistant", text=f"处理模型响应时出错: {e}")

    
    def chat(self, messages: ConversationHistory, tool_tags: str | List[str] = [], **kwargs) -> AnyInternalMessage | None:
        # 配置模型参数
        model_use = kwargs.get('model_use', self.model_params.model_use)
        temperature = kwargs.get('temperature', self.model_params.temperature)
        model_selected = self.model_params.model_list[model_use]
        tools_enabled = self._select_tools(tool_tags)

        # 转换消息格式
        system_prompt: str|None = super().get_system_prompt(messages)
        history = GeminiAdapter.pack_history(messages)

        # 动态创建 GenerationConfig
        config = types.GenerateContentConfig(
            system_instruction = system_prompt,
            temperature = temperature,
            tools = tool_manager.pack_tools("Gemini", tools_enabled)
        )

        # 【在这里加入诊断代码】
        # print("\n" + "="*50)
        # print(">>> [DEBUG] PAYLOAD TO GEMINI API:")
        # print(history)
        # print("="*50 + "\n")
        # 【诊断代码结束】

        try:
            response = self.client.models.generate_content(
                model = model_selected, 
                contents = history,
                config = config,
            )
            return GeminiAdapter.unpack_response(response)

        except Exception as e:
            print(f"错误：调用 Gemini API 时出错 ({self.model}: {model_selected}) -> {e}")
            raise e
    

import openai

class OpenAIAdapter(BaseLLMAdapter):
    """
    适配器，用于处理所有与 OpenAI API 兼容的模型。
    """
    def __init__(self, model: str, api_key_env: str, base_url: str, model_params: ModelParams):
        def init_client() -> openai.OpenAI | None:
            try:
                return openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                print(f"错误：初始化 OpenAI 客户端失败 ({self.model}): {e}")
            return None
        
        super().__init__(model, api_key_env, base_url, model_params)
        super().check_api_key()
        self.client = init_client()

    @staticmethod
    def pack_history(history: ConversationHistory) -> List[Dict[str, Any]]:
        """
        [翻译机] 将内部 ConversationHistory 格式打包成 OpenAI API 所需的字典列表格式。
        """
        openai_messages = []
        for msg in history:
            if isinstance(msg, SystemInternalMessage):
                openai_messages.append({"role": "system", "content": msg.content[0].text})
            
            elif isinstance(msg, UserInternalMessage):
                # 需要特别处理图文混合内容
                content_parts = []
                has_image = any(isinstance(block, ImageBlock) for block in msg.content)
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # 如果有图片，文本也需要打包成字典
                        content_parts.append({"type": "text", "text": block.text})
                    elif isinstance(block, ImageBlock):
                        b64_image = base64.b64encode(block.image_data).decode('utf-8')
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{block.mime_type};base64,{b64_image}"}
                        })
                # 如果只有文本，content 是字符串；如果图文混合，content 是列表
                final_content = content_parts if has_image else "".join(p['text'] for p in content_parts)
                openai_messages.append({"role": "user", "content": final_content})

            elif isinstance(msg, AssistantInternalMessage):
                # 助手消息可能包含文本回复或工具调用
                text_content = " ".join(block.text for block in msg.content if isinstance(block, TextBlock))
                tool_requests = [block for block in msg.content if isinstance(block, ToolCallRequestBlock)]
                
                msg_dict = {"role": "assistant"}
                if text_content:
                    msg_dict["content"] = text_content
                if tool_requests:
                    msg_dict["tool_calls"] = [
                        {
                            "id": req.id,
                            "type": "function",
                            "function": {"name": req.tool_name, "arguments": req.arguments_json}
                        } for req in tool_requests
                    ]
                openai_messages.append(msg_dict)
            
            elif isinstance(msg, ToolInternalMessage):
                for block in msg.content:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": block.tool_call_id,
                        "content": block.result
                    })
        return openai_messages

    @staticmethod
    def unpack_response(response: openai.types.chat.ChatCompletion) -> AnyInternalMessage | None:
        """
        [翻译机] 将 OpenAI API 的响应解包成内部 AnyInternalMessage 格式。
        """
        choice_message = response.choices[0].message

        # 情况 1: 模型请求调用工具
        if choice_message.tool_calls:
            tool_requests = [
                ToolCallRequestBlock(
                    id=tc.id,
                    tool_name=tc.function.name,
                    arguments_json=tc.function.arguments
                ) for tc in choice_message.tool_calls
            ]
            return AssistantInternalMessage(content=tool_requests)
        
        # 情况 2: 模型返回纯文本
        if choice_message.content:
            return create_message(role="assistant", text=choice_message.content)
            
        return None

    def chat(self, messages: ConversationHistory, tool_tags: str | List[str] = [], **kwargs) -> AnyInternalMessage | None:
        model_use = kwargs.get('model_use', self.model_params.model_use)
        temperature = kwargs.get('temperature', self.model_params.temperature)
        model_selected = self.model_params.model_list[model_use]
        tools_enabled = self._select_tools(tool_tags)

        history = OpenAIAdapter.pack_history(messages)

        request_params = {
            "model": model_selected,
            "temperature": temperature,
            "messages": history,
        }
        if tools_enabled:
            request_params["tools"] = tool_manager.pack_tools("Openai", tools_enabled)
            request_params["tool_choice"] = "auto"
        
        try:
            response = self.client.chat.completions.create(**request_params)
            return OpenAIAdapter.unpack_response(response)
        except Exception as e:
            print(f"错误：调用 OpenAI API 时出错 ({self.model}: {model_selected}) -> {e}")
            raise e
        




import ollama

class OllamaAdapter(BaseLLMAdapter):
    """
    适配器，用于处理通过 Ollama 运行的本地模型。
    """
    def __init__(self, model: str, base_url: str, model_params: ModelParams, **kwargs):
        def init_client() -> ollama.Client | None:
            try:
                return ollama.Client(host=self.base_url)
            except Exception as e:
                print(f"错误：初始化 Ollama 客户端失败 ({self.model}): {e}")
            return None
        
        super().__init__(model, None, base_url, model_params)
        self.client = init_client()

    @staticmethod
    def pack_history(history: ConversationHistory) -> List[Dict[str, Any]]:
        """
        [翻译机] 将内部 ConversationHistory 格式打包成 Ollama API 所需的字典列表格式。
        注意：此函数与 OpenAIAdapter.pack_history 完全相同！
        """
        # 为了代码简洁，我们可以直接调用 OpenAIAdapter 的实现
        return OpenAIAdapter.pack_history(history)

    @staticmethod
    def unpack_response(response: dict) -> AnyInternalMessage | None:
        """
        [翻译机] 将 Ollama API 返回的字典响应解包成内部 AnyInternalMessage 格式。
        """
        message_dict = response.get('message', {})
        
        # 情况 1: 模型请求调用工具
        if tool_calls := message_dict.get('tool_calls'):
            tool_requests = []
            for tc in tool_calls:
                # Ollama 返回的 arguments 是字典，我们需要转为 JSON 字符串
                # Ollama 也不提供 ID, 我们自己生成
                tool_requests.append(
                    ToolCallRequestBlock(
                        id=str(uuid.uuid4()),
                        tool_name=tc.get('function', {}).get('name'),
                        arguments_json=json.dumps(tc.get('function', {}).get('arguments', {}), ensure_ascii=False)
                    )
                )
            return AssistantInternalMessage(content=tool_requests)

        # 情况 2: 模型返回纯文本
        if content := message_dict.get('content'):
            return create_message(role="assistant", text=content.strip())
            
        return None
    def chat(self, messages: ConversationHistory, tool_tags: str | List[str] = [], **kwargs) -> AnyInternalMessage | None:
        model_use = kwargs.get('model_use', self.model_params.model_use)
        temperature = kwargs.get('temperature', self.model_params.temperature)
        model_selected = self.model_params.model_list[model_use]
        tools_enabled = self._select_tools(tool_tags)

        history = OllamaAdapter.pack_history(messages)

        request_params = {
            "model": model_selected,
            "messages": history,
            "options": {"temperature": temperature},
        }
        if tools_enabled:
            request_params["tools"] = tool_manager.pack_tools("Ollama", tools_enabled)
        
        try:
            response = self.client.chat(**request_params)
            return OllamaAdapter.unpack_response(response)
        except Exception as e:
            print(f"错误：调用 Ollama API 时出错 ({self.model}: {model_selected}) -> {e}")
            raise e