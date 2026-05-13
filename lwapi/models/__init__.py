from pydantic import BaseModel, ConfigDict


class BaseModelWithConfig(BaseModel):
    """
    SDK 内部模型统一基类。
    - extra="ignore"：服务端字段变化时尽量向后兼容
    - populate_by_name=True：兼容别名字段读写
    """

    model_config = ConfigDict(
        alias_generator=lambda s: s,
        extra="ignore",
        populate_by_name=True,
    )