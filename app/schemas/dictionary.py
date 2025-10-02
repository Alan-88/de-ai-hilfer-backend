from enum import Enum
from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# --- Suggestion Schemas (V3.1 - 智能提示版) ---


class SuggestionType(str, Enum):
    """建议类型枚举，定义了所有可能的建议类型。

    用于前后端统一识别不同类型的建议：
    - DB_MATCH: 数据库匹配的建议
    - SPELL_CORRECTION: 拼写错误修正建议
    - NEW_WORD: 新词建议
    """

    DB_MATCH = "db_match"
    SPELL_CORRECTION = "spell_correction"
    NEW_WORD = "new_word"


class IntelligentSearchRequest(BaseModel):
    """智能搜索请求模型。

    用于 /intelligent_search 端点，支持模糊搜索和智能提示功能。
    """

    term: str = Field(..., description="用户输入的德语术语，可能拼写不正确。")
    hint: str = Field("", description="用户提供的可选的中文提示。")


class BaseSuggestion(BaseModel):
    """所有建议类型的基类。

    确保所有建议都有 suggestion_type 字段，便于前端统一处理。
    """

    suggestion_type: str


class SuggestionItem(BaseModel):
    """数据库匹配建议的核心数据模型。

    包含完整的知识条目信息，用于展示数据库中已存在的内容。
    """

    entry_id: int
    query_text: str
    preview: str
    analysis_markdown: str
    source: Literal["generated", "知识库"]
    follow_ups: List["FollowUpItem"] = []
    model_config = ConfigDict(from_attributes=True)


class DBSuggestion(SuggestionItem, BaseSuggestion):
    """数据库匹配建议类型。

    当在知识库中找到匹配项时返回此类型的建议。
    继承了 SuggestionItem 的所有字段，包含完整的条目信息。
    """

    suggestion_type: Literal[SuggestionType.DB_MATCH] = SuggestionType.DB_MATCH


class SpellCorrectionSuggestion(BaseSuggestion):
    """拼写错误修正建议类型。

    当检测到可能的拼写错误时返回此类型的建议。
    """

    suggestion_type: Literal[SuggestionType.SPELL_CORRECTION] = SuggestionType.SPELL_CORRECTION
    original_query: str = Field(..., description="用户输入的原始查询")
    corrected_query: str = Field(..., description="系统建议的修正后查询")


class NewWordSuggestion(BaseSuggestion):
    """新词建议类型。

    当无法找到匹配项且没有拼写修正建议时返回此类型的建议。
    """

    suggestion_type: Literal[SuggestionType.NEW_WORD] = SuggestionType.NEW_WORD
    query_text: str = Field(..., description="用户输入的查询文本")


# 联合类型，表示一个建议可以是以上三种中的任意一种
SuggestionUnion = Union[DBSuggestion, SpellCorrectionSuggestion, NewWordSuggestion]


class SuggestionResponse(BaseModel):
    """建议响应模型。

    用于 /suggestions 端点的响应体，包含智能建议列表。
    """

    suggestions: List[SuggestionUnion]


# --- 其他API模型 ---


class RecentItem(BaseModel):
    """最近查询条目模型。

    用于在 /recent 端点中展示单个最近查询的条目摘要。
    """

    query_text: str = Field(..., description="查询的文本内容")
    preview: str = Field(..., description="条目内容的预览")


class FollowUpItem(BaseModel):
    """追问条目模型。

    用于在响应中展示单个追问条目的完整信息。
    """

    id: int = Field(..., description="追问的唯一标识符")
    question: str = Field(..., description="追问的问题内容")
    answer: str = Field(..., description="追问的答案内容")
    model_config = ConfigDict(from_attributes=True)


class FollowUpCreateRequest(BaseModel):
    """创建追问请求模型。

    用于创建新追问的请求体，关联到特定的知识条目。
    """

    entry_id: int = Field(..., description="追问所属的核心知识条目ID。")
    question: str = Field(..., description="用户提出的追问问题。")


class AnalyzeRequest(BaseModel):
    """分析请求模型。

    用于 /analyze 端点的请求体，支持对德语文本进行智能分析。
    """

    query_text: str = Field(..., description="用户输入的查询文本（单词、短语等）。")
    entry_type: str = Field("WORD", description="条目类型, 例如 'WORD', 'PHRASE'。")


class AnalyzeResponse(BaseModel):
    """分析响应模型。

    用于 /analyze 端点的响应体，包含完整的分析结果。
    """

    entry_id: int = Field(..., description="知识条目的唯一标识符")
    query_text: str = Field(..., description="原始查询文本")
    analysis_markdown: str = Field(..., description="分析结果的Markdown格式内容")
    source: Literal["generated", "知识库"] = Field(..., description="条目来源")
    follow_ups: List[FollowUpItem] = Field(default_factory=list, description="相关的追问列表")
    model_config = ConfigDict(from_attributes=True)


class AliasCreateRequest(BaseModel):
    """创建别名请求模型。

    用于 /aliases 端点的请求体，为现有知识条目创建别名。
    """

    alias_text: str = Field(..., description="要创建的别名。")
    entry_query_text: str = Field(..., description="别名应指向的核心知识条目查询文本。")


class DatabaseImportRequest(BaseModel):
    """数据库导入请求模型。

    用于 /database/import 端点的请求体，支持从备份文件导入数据。
    """

    file_path: str = Field(..., description="用户提供的备份数据库文件的完整路径。")
