"""
专家咨询工具
"""
from langchain_core.tools import tool
from services.expert_service import expert_service
from utils.logger import logger


@tool
async def consult_expert(query: str, session_id: str) -> str:
    """
    咨询日本养殖专家
    
    用于需要数据查询、分析判断的场景
    例如：查看喂食记录、判断是否需要喂食、分析水质等
    
    Args:
        query: 咨询问题
        session_id: 会话ID
        
    Returns:
        str: 专家建议
    """
    logger.info(f"工具调用: consult_expert, query={query[:50]}...")
    
    result = await expert_service.consult(
        query=query,
        session_id=session_id
    )
    
    if result.get("success"):
        answer = result.get("answer", "")
        return f"🧑‍🏫 专家建议:\n{answer}"
    else:
        error = result.get("error", "未知错误")
        logger.error(f"专家咨询失败: {error}")
        return f"❌ 专家咨询失败: {error}"

