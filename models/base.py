"""
SQLAlchemy Base 模型
"""
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass

