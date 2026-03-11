"""
阈值策略使用示例

from core.strategies import get_strategy, CandidateScore

# 获取策略
strategy = get_strategy("rule_based")

# 创建评分
score = CandidateScore(
    risk_score=25,
    risk_level="low",
    value_score=60,
    reason_codes=["DEFAULT_LOW"]
)

# 获取决策
decision = strategy.decide(score)
print(decision.action)  # "auto_pool"
print(decision.priority)  # "medium"

# 切换策略
# strategy = get_strategy("ml_v0_1")  # 未来可能的 ML 策略
"""

# 导出
from core.strategies import (
    ThresholdStrategy,
    ThresholdDecision,
    CandidateScore,
    get_strategy,
    list_strategies,
    register_strategy,
)

__all__ = [
    "ThresholdStrategy",
    "ThresholdDecision", 
    "CandidateScore",
    "get_strategy",
    "list_strategies",
    "register_strategy",
]
