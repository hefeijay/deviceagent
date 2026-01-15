"""
LLM管理器
负责LLM调用和Agent构建
"""
from typing import List, Any, Optional, Dict
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from config.settings import settings
from utils.logger import logger


class LLMManager:
    """LLM管理器"""
    
    def __init__(self):
        """初始化LLM管理器"""
        self.llm = None
        self._init_llm()
    
    def _init_llm(self):
        """初始化LLM"""
        try:
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                temperature=settings.LLM_TEMPERATURE,
            )
            logger.info(f"LLM初始化成功: {settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            raise
    
    def get_llm(self) -> ChatOpenAI:
        """获取LLM实例"""
        if self.llm is None:
            self._init_llm()
        return self.llm
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        加载提示词
        
        Args:
            prompt_name: 提示词文件名（不含.md后缀）
            
        Returns:
            str: 提示词内容
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.md"
        
        if not prompt_path.exists():
            logger.warning(f"提示词文件不存在: {prompt_path}")
            return ""
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"加载提示词: {prompt_name}")
            return content
        except Exception as e:
            logger.error(f"加载提示词失败: {e}")
            return ""
    
    async def invoke_with_tools(
        self,
        messages: List[Any],
        tools: List[Any],
        system_prompt: Optional[str] = None
    ) -> Any:
        """
        使用工具调用LLM
        
        Args:
            messages: 消息列表
            tools: 工具列表
            system_prompt: 系统提示词
            
        Returns:
            LLM响应
        """
        try:
            llm = self.get_llm()
            
            # 绑定工具
            if tools:
                llm_with_tools = llm.bind_tools(tools)
            else:
                llm_with_tools = llm
            
            # 构建消息
            full_messages = []
            if system_prompt:
                full_messages.append(SystemMessage(content=system_prompt))
            full_messages.extend(messages)
            
            # 调用LLM
            response = await llm_with_tools.ainvoke(full_messages)
            
            return response
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise
    
    async def invoke_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        简单的LLM调用
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示词
            
        Returns:
            str: LLM响应文本
        """
        try:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            
            llm = self.get_llm()
            response = await llm.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            logger.error(f"LLM简单调用失败: {e}", exc_info=True)
            raise


# 全局LLM管理器实例
llm_manager = LLMManager()

