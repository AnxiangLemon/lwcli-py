# lwapi/models/__init__.py  或单独一个文件
from pydantic import ConfigDict,BaseModel
# 全局默认配置
class BaseConfig:
    alias_generator = lambda s: s          # 字段名不变
    extra = "ignore"                       # 推荐 ignore，不要 allow（容易掩盖 bug）
    populate_by_name = True                # 允许用 alias 赋值（兼容老接口）
    arbitrary_types_allowed = True

# 然后所有模型继承一个基类
class BaseModelWithConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda s: s,
        extra="ignore",
        populate_by_name=True,
        
    )