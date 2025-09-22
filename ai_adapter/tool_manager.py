import datetime
import json
import inspect
from typing import Dict, List, Callable, Any, Literal, get_type_hints

# 数据库和模型依赖
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db import models

from .schemas import InternalTool


# ==============================================================================
# 1. 暴露给 LLM 的工具函数 (Agent-Facing Tools)
# ==============================================================================

def get_current_time() -> str:
    """
    获取当前的日期和时间。此函数不需要任何参数。
    当用户询问“现在几点”、“今天是什么日子”等相关问题时使用。

    Returns:
        str: 格式为 'YYYY-MM-DD HH:MM:SS' 的当前日期和时间字符串。
    """
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_entry_details(query_text: str) -> str:
    """
    在个人知识库中精确查找一个德语知识条目（原型或别名），并返回其完整的分析报告。
    当需要在回答中引用其他已知单词的准确信息时使用此工具。

    Args:
        query_text (str): 需要在知识库中查找其详细分析的单词或短语。

    Returns:
        str: 一个 JSON 字符串，包含该条目的 "query_text" (原型) 和 "analysis_markdown"。如果找不到，则返回 "null"。
    """
    db = SessionLocal()
    try:
        # 1. 尝试直接作为知识条目原型查找
        entry = db.query(models.KnowledgeEntry).filter(
            models.KnowledgeEntry.query_text == query_text
        ).first()
        if entry:
            output_data = {"query_text": entry.query_text, "analysis_markdown": entry.analysis_markdown}
            print(f"--- [Tool: get_entry_details] 成功检索到知识条目 '{query_text}' 的详细信息。")
            return json.dumps(output_data, ensure_ascii=False)

        # 2. 如果作为原型找不到，尝试作为别名查找
        alias = db.query(models.EntryAlias).options(
            joinedload(models.EntryAlias.entry)
        ).filter(models.EntryAlias.alias_text == query_text).first()
        
        if alias and alias.entry:
            entry = alias.entry
            output_data = {"query_text": entry.query_text, "analysis_markdown": entry.analysis_markdown}
            print(f"--- [Tool: get_entry_details] 通过别名 '{query_text}' 成功检索到知识条目 '{entry.query_text}'。")
            return json.dumps(output_data, ensure_ascii=False)

        # 3. 如果都找不到
        print(f"--- [Tool: get_entry_details] 未能在知识库中找到 '{query_text}'。")
        return "null"
    finally:
        db.close()


# ==============================================================================
# 2. 工具列表和管理器 (Tool List & Manager)
# ==============================================================================

Tool_dict: Dict[Callable[..., Any], List[str]] = {
    get_current_time: [],
    get_entry_details: ["database"],
}


class ToolManager:
    def __init__(self):
        self.tools: Dict[str, Callable[..., Any]] = {}
        self.internal_tools: List[InternalTool] = []
        self._register_all_tools()
        self.router = None # 由 LLMRouter 注入

    def _register_all_tools(self):
        """
        [自动注册机] 遍历函数列表，使用 inspect 提取信息，
        并动态创建 InternalTool 对象。
        """
        print("--- [ToolManager] 开始自动注册工具... ---")
        for func, tags in Tool_dict.items():
            func_name = func.__name__
            self.tools[func_name] = func

            docstring = inspect.getdoc(func) or ""
            lines = docstring.split('\n')
            
            # ... (解析逻辑保持不变)
            index = {}
            for i, line in enumerate(lines):
                if line.strip().startswith("Args:"):
                    index["Args"] = i
                elif line.strip().startswith("Returns:"):
                    index["Returns"] = i
                    break
            
            subline = lines[:index.get("Args", index.get("Returns", len(lines)))]
            description = "\n".join(line.strip() for line in subline).strip()
            
            param_descs = {}
            if "Args" in index:
                subline = lines[index["Args"]+1:index.get("Returns", len(lines))]
                for line in subline:
                    stripped_line = line.strip()
                    if ':' in stripped_line:
                        param_name_part, desc = stripped_line.split(':', 1)
                        param_name = param_name_part.split(' ')[0]
                        param_descs[param_name] = desc.strip()

            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            parameters_schema = {"type": "object", "properties": {}, "required": []}

            for param in sig.parameters.values():
                param_name = param.name
                param_type = type_hints.get(param_name, str)
                json_type = "string"
                if param_type in (int, float): json_type = "number"
                elif param_type == bool: json_type = "boolean"
                
                parameters_schema["properties"][param_name] = {
                    "type": json_type,
                    "description": param_descs.get(param_name, "")
                }
                
                if param.default is inspect.Parameter.empty:
                    parameters_schema["required"].append(param_name)

            self.internal_tools.append(InternalTool(
                name=func_name,
                description=description,
                parameters_schema=parameters_schema,
                tags=tags
            ))
        
        print(f"--- [ToolManager] 成功从 {len(self.internal_tools)} 个函数自动注册工具。 ---")

    def set_router(self, router):
        self.router = router
        print(f"信息：ToolManager 已成功设置 LLMRouter。")

    def get_tool(self, tool_name: str) -> Callable[..., Any] | None:
        return self.tools.get(tool_name)

    def pack_tools(self, adapter: Literal["Gemini", "Openai", "Ollama"], tools_to_format: List[InternalTool]) -> Any:
        # ... (此函数保持不变)
        if adapter in ["Openai", "Ollama"]:
            specs = []
            for tool in tools_to_format:
                specs.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema
                    }
                })
            return specs
        
        if adapter == "Gemini":
            from google.genai import types
            specs = []
            for tool in tools_to_format:
                specs.append(
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.parameters_schema
                    )
                )
            return [types.Tool(function_declarations=specs)] if specs else None
        
        return None

tool_manager = ToolManager()
