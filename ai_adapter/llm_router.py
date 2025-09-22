# ai_adapter/llm_router.py

import asyncio
import inspect
import yaml
import json
import uuid
from typing import *
from ai_adapter.schemas import *
from pydantic import ValidationError
from .llm_adapters import *
from .tool_manager import tool_manager
from .utils import create_message

class ChatSession:
    """
    管理一个独立的对话会话。
    """
    def __init__(self, adapters: List[BaseLLMAdapter], system_prompt: str, router: 'LLMRouter'):
        self.adapters = adapters
        self.router = router
        # 每个会话都以 System Prompt 开始
        self.conversation_history: ConversationHistory = [
            SystemInternalMessage(content=[TextBlock(text=system_prompt)])
        ]

    async def run(self, message: str, max_turns: int = 5, enabled_tags: List[str] | str = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        执行一个完整的、可能包含工具调用的 ReAct 交互流程。
        """
        async def reason() -> Union[AnyInternalMessage, None]:
            # 注意：我们传递的是 self.conversation_history 的一个副本
            return await LLMRouter.chat_with_failover(
                self.adapters, 
                list(self.conversation_history), # 传递副本
                tool_tags=enabled_tags, 
                **kwargs
            )

        async def execute_tool_calls(tool_requests: List[ToolCallRequestBlock]) -> List[ToolResultBlock]:
            tool_result_blocks: List[ToolResultBlock] = []
            for request_block in tool_requests:
                tool_name = request_block.tool_name
                tool_args_str = request_block.arguments_json
                print(f"--- [Agent] 执行工具: {tool_name}({tool_args_str})")
                tool_function = tool_manager.get_tool(tool_name)
                if tool_function:
                    try:
                        tool_args = json.loads(tool_args_str)
                        tool_result = ""
                        if inspect.iscoroutinefunction(tool_function):
                            tool_result = await tool_function(**tool_args)
                        else:
                            tool_result = await asyncio.to_thread(tool_function, **tool_args)
                    except Exception as e:
                        tool_result = f"错误：执行工具 '{tool_name}' 时出错: {e}"
                else:
                    tool_result = f"错误：Agent 尝试调用一个不存在的工具 '{tool_name}'。"
                
                tool_result_blocks.append(
                    ToolResultBlock(
                        tool_call_id=request_block.id,
                        tool_name=tool_name,
                        result=str(tool_result)
                    )
                )
            return tool_result_blocks

        if not self.adapters:
            print("错误：此会话中没有任何可用的模型适配器。")
            return

        user_message = create_message(role="user", text=message)
        self.conversation_history.append(user_message)

        for i in range(max_turns):
            response: AnyInternalMessage = await reason()
            if response is None:
                print("错误：所有模型均调用失败。")
                break

            self.conversation_history.append(response)

            if isinstance(response, AssistantInternalMessage):
                tool_requests = [block for block in response.content if isinstance(block, ToolCallRequestBlock)]
                
                if tool_requests:
                    tool_results: List[ToolResultBlock] = await execute_tool_calls(tool_requests)
                    self.conversation_history.append(ToolInternalMessage(content=tool_results))
                    continue # 继续下一轮循环，让模型看到工具结果
                else:
                    # 如果没有工具调用，说明是最终答案
                    break 
            else:
                # 如果不是助手消息，也直接退出
                break
        
        # 这个生成器现在只是为了保持接口一致性，但实际上我们只关心最终的 history
        yield json.dumps({"status": "completed"})


class LLMRouter:
    def __init__(self, config_path: str = 'config.yaml'):
        self.adapter_map = {"gemini": GeminiAdapter, "openai": OpenAIAdapter, "ollama": OllamaAdapter}
        self.config = self._load_config(config_path)
        if self.config is None:
            raise ValueError("Configuration could not be loaded.")
        self.models = self._init_models()
        self.adapters = self._get_sorted_adapters()
        self.sessions: Dict[str, ChatSession] = {}
        tool_manager.set_router(self)
        print("\n--- LLMRouter 初始化完成 ---")

    def _load_config(self, config_path: str) -> Optional[AppConfig]:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                return AppConfig.model_validate(raw_config)
        except (FileNotFoundError, ValidationError) as e:
            print(f"错误：加载或验证配置文件失败: {e}")
            return None

    def _init_models(self) -> Dict[str, BaseLLMAdapter]:
        result_models: Dict[str, BaseLLMAdapter] = {}
        for model, config in self.config.models.items():
            if not config.enabled: continue
            if config.provider in self.adapter_map:
                AdapterClass = self.adapter_map[config.provider]
                try:
                    adapter_args = {'model': model, 'api_key_env': getattr(config, 'api_key_env', None), 'base_url': getattr(config, 'base_url', None), 'model_params': config.model_params}
                    result_models[model] = AdapterClass(**{k: v for k, v in adapter_args.items() if v is not None})
                    print(f"信息：成功初始化模型 '{model}' (Provider: {config.provider})。")
                except Exception as e:
                    print(f"错误：初始化模型 '{model}' 失败: {e}")
        return result_models
        
    def _get_sorted_adapters(self) -> List[BaseLLMAdapter]:
        if not self.config or not self.config.models: return []
        enabled_models = [(n, c) for n, c in self.config.models.items() if c.enabled and n in self.models]
        sorted_models = sorted(enabled_models, key=lambda item: item[1].priority)
        return [self.models[name] for name, _ in sorted_models]
    
    def get_session(self, session_id: str, system_prompt_override: str = None) -> ChatSession:
        """
        获取或创建一个会话。
        如果提供了 system_prompt_override，则会话将使用这个临时的系统指令。
        """
        # 始终创建一个新会话以使用动态 prompt
        prompt = system_prompt_override if system_prompt_override else self.config.system_prompt
        session = ChatSession(self.adapters, prompt, self)
        self.sessions[session_id] = session
        return session

    def get_session_id(self, session: ChatSession) -> Optional[str]:
        for sid, s in self.sessions.items():
            if s is session: return sid
        return None

    @staticmethod
    async def chat_with_failover(adapters: List[BaseLLMAdapter], messages: ConversationHistory, **kwargs) -> Optional[AnyInternalMessage]:
        if not adapters: return None
        for adapter in adapters:
            try:
                # 使用 to_thread 确保即使是同步的 chat 方法也能在异步上下文中运行而不会阻塞
                response = await asyncio.to_thread(adapter.chat, messages, **kwargs)
                if response:
                    print(f"<<< [Failover] 成功! 由 '{adapter.model}' 返回响应。")
                    return response
            except Exception as e:
                print(f"!!! [Failover] 模型 '{adapter.model}' 调用失败: {e}。尝试下一个...")
                continue
        print("\n错误：[Failover] 所有可用模型均调用失败。")
        return None