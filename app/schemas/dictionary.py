from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, List, Union
from enum import Enum # 1. 导入 Enum

# --- Suggestion Schemas (V3.1 - 智能提示版) ---

class SuggestionType(str, Enum): # 2. 让它继承自 str 和 Enum
    """定义了建议类型的常量，方便前后端统一。"""
    DB_MATCH = "db_match"
    SPELL_CORRECTION = "spell_correction"
    NEW_WORD = "new_word"

class IntelligentSearchRequest(BaseModel):
    """/intelligent_search 端点的请求体模型。"""
    term: str = Field(..., description="用户输入的德语术语，可能拼写不正确。")
    hint: str = Field("", description="用户提供的可选的中文提示。")

class BaseSuggestion(BaseModel):
    """所有建议类型的基类，确保都有 suggestion_type 字段。"""
    suggestion_type: str

class SuggestionItem(BaseModel):
    """这是数据库匹配建议的核心数据模型，包含了完整的条目信息。"""
    entry_id: int
    query_text: str
    preview: str
    analysis_markdown: str
    source: Literal["generated", "知识库"]
    follow_ups: List['FollowUpItem'] = []
    model_config = ConfigDict(from_attributes=True)

class DBSuggestion(SuggestionItem, BaseSuggestion):
    """用于数据库匹配的建议类型。它继承了 SuggestionItem 的所有字段。"""
    suggestion_type: Literal[SuggestionType.DB_MATCH] = SuggestionType.DB_MATCH

class SpellCorrectionSuggestion(BaseSuggestion):
    """用于拼写错误修正的建议类型。"""
    suggestion_type: Literal[SuggestionType.SPELL_CORRECTION] = SuggestionType.SPELL_CORRECTION
    original_query: str
    corrected_query: str

class NewWordSuggestion(BaseSuggestion):
    """用于提示这是一个新词的建议类型。"""
    suggestion_type: Literal[SuggestionType.NEW_WORD] = SuggestionType.NEW_WORD
    query_text: str

# AnySuggestion 是一个联合类型，表示一个建议可以是以上三种中的任意一种
AnySuggestion = Union[DBSuggestion, SpellCorrectionSuggestion, NewWordSuggestion]

class SuggestionResponse(BaseModel):
    """/suggestions 端点的响应体模型，现在包含一个 AnySuggestion 列表。"""
    suggestions: List[AnySuggestion]


# --- Other Schemas (保持不变) ---

class RecentItem(BaseModel):
    """用于在 /recent 端点中展示单个最近查询条目。"""
    query_text: str
    preview: str

class FollowUpItem(BaseModel):
    """用于在响应中展示单个追问条目。"""
    id: int
    question: str
    answer: str
    model_config = ConfigDict(from_attributes=True)

class FollowUpCreateRequest(BaseModel):
    """创建新追问的请求体。"""
    entry_id: int = Field(..., description="追问所属的核心知识条目ID。")
    question: str = Field(..., description="用户提出的追问问题。")

class AnalyzeRequest(BaseModel):
    """/analyze 端点的请求体模型。"""
    query_text: str = Field(..., description="用户输入的查询文本（单词、短语等）。")
    entry_type: str = Field("WORD", description="条目类型, 例如 'WORD', 'PHRASE'。")

class AnalyzeResponse(BaseModel):
    """/analyze 端点的响应体模型。"""
    entry_id: int
    query_text: str
    analysis_markdown: str
    source: Literal["generated", "知识库"]
    follow_ups: List[FollowUpItem] = []
    model_config = ConfigDict(from_attributes=True)

class AliasCreateRequest(BaseModel):
    """/aliases 端点的请求体模型。"""
    alias_text: str = Field(..., description="要创建的别名。")
    entry_query_text: str = Field(..., description="别名应指向的核心知识条目查询文本。")

class DatabaseImportRequest(BaseModel):
    """/database/import 端点的请求体模型。"""
    file_path: str = Field(..., description="用户提供的备份数据库文件的完整路径。")