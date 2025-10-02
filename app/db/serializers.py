"""
数据序列化工具模块

提供统一的数据转换逻辑，替代重复的to_dict方法。
使用更高效的序列化方案，支持嵌套对象和日期时间处理。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Type

try:
    from sqlalchemy.orm import InstanceProxy
except ImportError:
    # 如果InstanceProxy不存在，使用占位符
    InstanceProxy = type("InstanceProxy", (), {})


def serialize_model(
    model_instance: Any,
    include_fields: Optional[Set[str]] = None,
    exclude_fields: Optional[Set[str]] = None,
    nested_relations: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    通用的模型序列化函数

    Args:
        model_instance: SQLAlchemy模型实例
        include_fields: 要包含的字段集合，如果为None则包含所有字段
        exclude_fields: 要排除的字段集合
        nested_relations: 嵌套关系的配置，格式为 {field_name: {config}}

    Returns:
        序列化后的字典
    """
    if model_instance is None:
        return {}

    result = {}

    # 获取模型的所有列
    columns = model_instance.__table__.columns.keys()

    # 确定要处理的字段
    if include_fields:
        fields_to_process = include_fields.intersection(columns)
    else:
        fields_to_process = set(columns)

    if exclude_fields:
        fields_to_process = fields_to_process - exclude_fields

    # 处理每个字段
    for field_name in fields_to_process:
        value = getattr(model_instance, field_name, None)

        # 处理不同类型的值
        if isinstance(value, datetime):
            result[field_name] = value.isoformat() if value else None
        elif isinstance(value, InstanceProxy):
            # 处理延迟加载的属性
            try:
                loaded_value = value
                if isinstance(loaded_value, datetime):
                    result[field_name] = loaded_value.isoformat() if loaded_value else None
                else:
                    result[field_name] = loaded_value
            except Exception:
                # 如果无法加载，设为None
                result[field_name] = None
        else:
            result[field_name] = value

    # 处理嵌套关系
    if nested_relations:
        for relation_name, relation_config in nested_relations.items():
            if hasattr(model_instance, relation_name):
                relation_value = getattr(model_instance, relation_name)

                if relation_value is None:
                    result[relation_name] = None
                elif isinstance(relation_value, list):
                    # 处理一对多关系
                    if relation_config.get("many", True):
                        result[relation_name] = [
                            serialize_model(
                                item,
                                include_fields=relation_config.get("include_fields"),
                                exclude_fields=relation_config.get("exclude_fields"),
                            )
                            for item in relation_value
                        ]
                    else:
                        # 如果配置为单个对象但实际是列表，取第一个
                        result[relation_name] = (
                            serialize_model(
                                relation_value[0],
                                include_fields=relation_config.get("include_fields"),
                                exclude_fields=relation_config.get("exclude_fields"),
                            )
                            if relation_value
                            else None
                        )
                else:
                    # 处理多对一或一对一关系
                    result[relation_name] = serialize_model(
                        relation_value,
                        include_fields=relation_config.get("include_fields"),
                        exclude_fields=relation_config.get("exclude_fields"),
                    )

    return result


def serialize_knowledge_entry(entry: Any) -> Dict[str, Any]:
    """
    序列化KnowledgeEntry模型的专用函数

    Args:
        entry: KnowledgeEntry实例

    Returns:
        序列化后的字典
    """
    return serialize_model(
        entry,
        nested_relations={
            "follow_ups": {
                "many": True,
                "include_fields": {"id", "question", "answer", "timestamp"},
            }
        },
    )


def serialize_entry_alias(alias: Any) -> Dict[str, Any]:
    """
    序列化EntryAlias模型的专用函数

    Args:
        alias: EntryAlias实例

    Returns:
        序列化后的字典
    """
    return serialize_model(alias)


def serialize_follow_up(follow_up: Any) -> Dict[str, Any]:
    """
    序列化FollowUp模型的专用函数

    Args:
        follow_up: FollowUp实例

    Returns:
        序列化后的字典
    """
    return serialize_model(follow_up)


def serialize_list(items: List[Any], serializer_func: callable) -> List[Dict[str, Any]]:
    """
    批量序列化列表中的对象

    Args:
        items: 要序列化的对象列表
        serializer_func: 序列化函数

    Returns:
        序列化后的字典列表
    """
    return [serializer_func(item) for item in items]


class ModelSerializer:
    """
    模型序列化器类，提供更高级的序列化功能
    """

    def __init__(self, model_class: Type[Any]):
        self.model_class = model_class
        self._default_include_fields = None
        self._default_exclude_fields = None
        self._default_nested_relations = None

    def set_defaults(
        self,
        include_fields: Optional[Set[str]] = None,
        exclude_fields: Optional[Set[str]] = None,
        nested_relations: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """设置默认序列化配置"""
        self._default_include_fields = include_fields
        self._default_exclude_fields = exclude_fields
        self._default_nested_relations = nested_relations

    def serialize(
        self,
        instance: Any,
        include_fields: Optional[Set[str]] = None,
        exclude_fields: Optional[Set[str]] = None,
        nested_relations: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """序列化单个实例"""
        return serialize_model(
            instance,
            include_fields=include_fields or self._default_include_fields,
            exclude_fields=exclude_fields or self._default_exclude_fields,
            nested_relations=nested_relations or self._default_nested_relations,
        )

    def serialize_many(
        self,
        instances: List[Any],
        include_fields: Optional[Set[str]] = None,
        exclude_fields: Optional[Set[str]] = None,
        nested_relations: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """批量序列化实例"""
        return [
            self.serialize(instance, include_fields, exclude_fields, nested_relations)
            for instance in instances
        ]


# 预配置的序列化器实例（延迟初始化）
knowledge_entry_serializer = None
entry_alias_serializer = None
follow_up_serializer = None


def initialize_serializers():
    """初始化序列化器实例，避免循环导入"""
    global knowledge_entry_serializer, entry_alias_serializer, follow_up_serializer

    if knowledge_entry_serializer is None:
        from .models import EntryAlias, FollowUp, KnowledgeEntry

        knowledge_entry_serializer = ModelSerializer(KnowledgeEntry)
        knowledge_entry_serializer.set_defaults(
            nested_relations={
                "follow_ups": {
                    "many": True,
                    "include_fields": {"id", "question", "answer", "timestamp"},
                }
            }
        )

        entry_alias_serializer = ModelSerializer(EntryAlias)

        follow_up_serializer = ModelSerializer(FollowUp)
