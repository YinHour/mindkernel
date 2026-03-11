"""
基于规则的阈值策略 v0.1 (ThresholdStrategy 实现)

当前策略逻辑：
- 系统信号/消息 → 低价值，直接丢弃或压缩统计
- 高价值用户消息 → 入自动池
- 中等价值 → 入审核队列
- 低价值 → 丢弃

策略参数可通过配置注入
"""

from dataclasses import dataclass
from typing import Optional

from core.strategies import (  # noqa: E402
    CandidateScore,
    ThresholdDecision,
    ThresholdStrategy,
    register_strategy,
)


@dataclass
class RuleBasedConfig:
    """规则策略配置"""
    # 价值阈值
    value_auto_pool: int = 50  # >= 此值自动入池
    value_review_queue: int = 30  # >= 此值入审核队列
    
    # 风险阈值
    risk_high_threshold: int = 60  # >= 此值视为高风险
    
    # 系统消息处理
    discard_system_signals: bool = True  # 是否丢弃系统信号
    system_signal_action: str = "discard"  # discard/stats/queue


class RuleBasedStrategy(ThresholdStrategy):
    """基于规则的阈值策略"""
    
    def __init__(self, config: Optional[RuleBasedConfig] = None):
        self.config = config or RuleBasedConfig()
    
    def get_name(self) -> str:
        return "rule_based_v0_1"
    
    def decide(self, score: CandidateScore, session_context: Optional[dict] = None) -> ThresholdDecision:
        config = self.config
        
        # 1. 系统信号处理
        if "SYSTEM_REPEAT_ALERT" in score.reason_codes or "SYSTEM_MESSAGE" in score.reason_codes:
            if config.discard_system_signals:
                return ThresholdDecision(
                    action="discard",
                    priority="low",
                    confidence=0.95,
                    note="系统信号，按配置丢弃"
                )
            else:
                return ThresholdDecision(
                    action=config.system_signal_action,
                    priority="low",
                    confidence=0.8,
                    note="系统信号"
                )
        
        # 2. 系统噪音
        if "SYSTEM_NOISE" in score.reason_codes:
            return ThresholdDecision(
                action="discard",
                priority="low",
                confidence=0.95,
                note="系统噪音"
            )
        
        # 3. 高风险用户消息 → 入审核队列
        if score.risk_level == "high":
            return ThresholdDecision(
                action="review_queue",
                priority="high",
                confidence=0.9,
                note=f"高风险消息: {score.reason_codes}"
            )
        
        # 4. 价值判断
        if score.value_score >= config.value_auto_pool:
            # 高价值 → 自动入池
            return ThresholdDecision(
                action="auto_pool",
                priority="medium",
                confidence=0.85,
                note=f"价值 {score.value_score} >= {config.value_auto_pool}"
            )
        elif score.value_score >= config.value_review_queue:
            # 中等价值 → 审核队列
            return ThresholdDecision(
                action="review_queue",
                priority="medium",
                confidence=0.7,
                note=f"价值 {score.value_score} >= {config.value_review_queue}"
            )
        else:
            # 低价值 → 丢弃
            return ThresholdDecision(
                action="discard",
                priority="low",
                confidence=0.9,
                note=f"价值 {score.value_score} < {config.value_review_queue}"
            )


# 注册策略
register_strategy("rule_based", RuleBasedStrategy)
register_strategy("rule_based_v0_1", RuleBasedStrategy)
