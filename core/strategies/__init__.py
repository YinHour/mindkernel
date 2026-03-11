"""
MindKernel 记忆候选阈值策略接口

设计原则：
1. 阈值固化是当前阶段的务实选择
2. 策略逻辑隔离，方便未来用 ML/LLM 替换
3. 接口稳定，支持热切换
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CandidateScore:
    """候选评分"""
    risk_score: int
    risk_level: str  # low/medium/high
    value_score: int
    reason_codes: list[str]


@dataclass
class ThresholdDecision:
    """阈值决策结果"""
    action: str  # "auto_pool" | "review_queue" | "discard"
    priority: str  # low/medium/high
    confidence: float  # 0.0-1.0
    note: str


class ThresholdStrategy(ABC):
    """阈值策略基类"""
    
    @abstractmethod
    def decide(self, score: CandidateScore, session_context: Optional[dict] = None) -> ThresholdDecision:
        """
        根据候选评分决定处理方式
        
        Args:
            score: 候选评分
            session_context: 会话上下文（可选）
            
        Returns:
            ThresholdDecision: 处理决策
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """策略名称"""
        pass


# 策略注册表
_STRATEGIES: dict[str, type[ThresholdStrategy]] = {}


def register_strategy(name: str, strategy_class: type[ThresholdStrategy]):
    """注册阈值策略"""
    _STRATEGIES[name] = strategy_class


def get_strategy(name: str) -> ThresholdStrategy:
    """获取策略实例"""
    if name not in _STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(_STRATEGIES.keys())}")
    return _STRATEGIES[name]()


def list_strategies() -> list[str]:
    """列出可用策略"""
    return list(_STRATEGIES.keys())


# 默认注册
from core.strategies.rule_based_v0_1 import RuleBasedStrategy  # noqa: E402
register_strategy("rule_based", RuleBasedStrategy)
