import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..executor.command_parser import ParsedAction, ActionType

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SafetyResult:
    allowed: bool
    risk_level: RiskLevel
    warnings: List[str]
    blocked_reason: Optional[str] = None

class SafetyChecker:
    """安全检查器 - 防止恶意或危险操作"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_execution_time = config.get("max_execution_time", 30)
        self.allowed_actions = set(config.get("allowed_actions", [
            "click", "type", "scroll", "screenshot", "wait", "find_text"
        ]))
        
        # 危险关键词和模式
        self.dangerous_keywords = {
            "system": ["rm", "del", "format", "shutdown", "reboot", "kill", "sudo", "chmod"],
            "financial": ["bank", "credit", "password", "social security", "ssn"],
            "personal": ["private", "confidential", "secret", "personal"],
            "network": ["hack", "exploit", "virus", "malware", "crack"]
        }
        
        # 危险文件路径模式
        self.dangerous_paths = [
            r"/etc/.*",
            r"/sys/.*", 
            r"/proc/.*",
            r".*\.exe$",
            r".*\.bat$",
            r".*\.sh$",
            r".*\.scr$"
        ]
        
        # 敏感URL模式
        self.sensitive_urls = [
            r".*://.*password.*",
            r".*://.*login.*",
            r".*://.*admin.*",
            r".*://.*bank.*",
            r".*://.*payment.*"
        ]
        
        # 执行频率限制
        self.action_history = []
        self.max_actions_per_minute = 60
        
        # 坐标范围限制
        self.coordinate_limits = {
            "max_x": 3840,  # 4K屏幕宽度
            "max_y": 2160,  # 4K屏幕高度
            "min_x": 0,
            "min_y": 0
        }
    
    def check_action_safety(self, action: ParsedAction) -> SafetyResult:
        """检查单个动作的安全性"""
        warnings = []
        risk_level = RiskLevel.LOW
        
        # 1. 检查动作类型是否允许
        if action.action_type.value not in self.allowed_actions:
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                warnings=[],
                blocked_reason=f"动作类型 '{action.action_type.value}' 不在允许列表中"
            )
        
        # 2. 检查执行频率
        freq_check = self._check_execution_frequency()
        if not freq_check:
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.MEDIUM,
                warnings=[],
                blocked_reason="执行频率过高，请稍后重试"
            )
        
        # 3. 根据动作类型进行具体检查
        if action.action_type == ActionType.TYPE:
            type_result = self._check_type_safety(action)
            if not type_result.allowed:
                return type_result
            warnings.extend(type_result.warnings)
            risk_level = max(risk_level, type_result.risk_level, key=lambda x: list(RiskLevel).index(x))
        
        elif action.action_type == ActionType.CLICK:
            click_result = self._check_click_safety(action)
            if not click_result.allowed:
                return click_result
            warnings.extend(click_result.warnings)
            risk_level = max(risk_level, click_result.risk_level, key=lambda x: list(RiskLevel).index(x))
        
        elif action.action_type == ActionType.DRAG:
            drag_result = self._check_drag_safety(action)
            if not drag_result.allowed:
                return drag_result
            warnings.extend(drag_result.warnings)
            risk_level = max(risk_level, drag_result.risk_level, key=lambda x: list(RiskLevel).index(x))
        
        elif action.action_type == ActionType.WAIT:
            wait_result = self._check_wait_safety(action)
            if not wait_result.allowed:
                return wait_result
            warnings.extend(wait_result.warnings)
        
        # 4. 记录动作到历史
        self._record_action(action)
        
        return SafetyResult(
            allowed=True,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def _check_execution_frequency(self) -> bool:
        """检查执行频率"""
        current_time = time.time()
        # 清理1分钟前的记录
        self.action_history = [t for t in self.action_history if current_time - t < 60]
        
        # 检查是否超过频率限制
        return len(self.action_history) < self.max_actions_per_minute
    
    def _record_action(self, action: ParsedAction):
        """记录动作到历史"""
        self.action_history.append(time.time())
    
    def _check_type_safety(self, action: ParsedAction) -> SafetyResult:
        """检查输入动作的安全性"""
        text = action.parameters.get("text", "").lower()
        warnings = []
        risk_level = RiskLevel.LOW
        
        # 检查文本长度
        if len(text) > 1000:
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.MEDIUM,
                warnings=[],
                blocked_reason="输入文本过长，可能存在安全风险"
            )
        
        # 检查危险关键词
        for category, keywords in self.dangerous_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    if category in ["system", "network"]:
                        return SafetyResult(
                            allowed=False,
                            risk_level=RiskLevel.HIGH,
                            warnings=[],
                            blocked_reason=f"输入包含危险关键词: {keyword}"
                        )
                    else:
                        warnings.append(f"输入包含敏感词汇: {keyword}")
                        risk_level = RiskLevel.MEDIUM
        
        # 检查是否包含路径
        for pattern in self.dangerous_paths:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append("输入包含系统路径，请谨慎操作")
                risk_level = RiskLevel.MEDIUM
        
        # 检查是否包含URL
        for pattern in self.sensitive_urls:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append("输入包含敏感URL，请确认安全性")
                risk_level = RiskLevel.MEDIUM
        
        # 检查特殊字符
        special_chars = re.findall(r'[<>"|&;`$()]', text)
        if special_chars:
            warnings.append("输入包含特殊字符，可能存在注入风险")
            risk_level = RiskLevel.MEDIUM
        
        return SafetyResult(
            allowed=True,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def _check_click_safety(self, action: ParsedAction) -> SafetyResult:
        """检查点击动作的安全性"""
        warnings = []
        risk_level = RiskLevel.LOW
        
        # 检查坐标范围
        if action.parameters.get("use_coordinates", False):
            x = action.parameters.get("x", 0)
            y = action.parameters.get("y", 0)
            
            if not (self.coordinate_limits["min_x"] <= x <= self.coordinate_limits["max_x"] and
                    self.coordinate_limits["min_y"] <= y <= self.coordinate_limits["max_y"]):
                return SafetyResult(
                    allowed=False,
                    risk_level=RiskLevel.MEDIUM,
                    warnings=[],
                    blocked_reason=f"点击坐标超出安全范围: ({x}, {y})"
                )
        
        # 检查目标文本
        target = action.parameters.get("target", "").lower()
        if target:
            # 检查是否包含危险操作
            dangerous_targets = [
                "delete", "remove", "format", "uninstall", "shutdown", 
                "restart", "reset", "clear all", "factory reset"
            ]
            
            for dangerous in dangerous_targets:
                if dangerous in target:
                    warnings.append(f"点击目标可能执行危险操作: {dangerous}")
                    risk_level = RiskLevel.HIGH
        
        return SafetyResult(
            allowed=True,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def _check_drag_safety(self, action: ParsedAction) -> SafetyResult:
        """检查拖拽动作的安全性"""
        warnings = []
        risk_level = RiskLevel.LOW
        
        # 检查坐标范围
        if action.parameters.get("use_coordinates", False):
            coords = ["source_x", "source_y", "target_x", "target_y"]
            for coord_name in coords:
                coord_value = action.parameters.get(coord_name, 0)
                if coord_name.endswith("_x"):
                    if not (self.coordinate_limits["min_x"] <= coord_value <= self.coordinate_limits["max_x"]):
                        return SafetyResult(
                            allowed=False,
                            risk_level=RiskLevel.MEDIUM,
                            warnings=[],
                            blocked_reason=f"拖拽坐标超出安全范围: {coord_name}={coord_value}"
                        )
                else:  # _y
                    if not (self.coordinate_limits["min_y"] <= coord_value <= self.coordinate_limits["max_y"]):
                        return SafetyResult(
                            allowed=False,
                            risk_level=RiskLevel.MEDIUM,
                            warnings=[],
                            blocked_reason=f"拖拽坐标超出安全范围: {coord_name}={coord_value}"
                        )
        
        # 检查拖拽距离
        if action.parameters.get("use_coordinates", False):
            source_x = action.parameters.get("source_x", 0)
            source_y = action.parameters.get("source_y", 0)
            target_x = action.parameters.get("target_x", 0)
            target_y = action.parameters.get("target_y", 0)
            
            distance = ((target_x - source_x) ** 2 + (target_y - source_y) ** 2) ** 0.5
            if distance > 2000:  # 超过2000像素的拖拽
                warnings.append("拖拽距离较大，请确认操作意图")
                risk_level = RiskLevel.MEDIUM
        
        return SafetyResult(
            allowed=True,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def _check_wait_safety(self, action: ParsedAction) -> SafetyResult:
        """检查等待动作的安全性"""
        duration = action.parameters.get("duration", 0)
        
        if duration > self.max_execution_time:
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.MEDIUM,
                warnings=[],
                blocked_reason=f"等待时间过长: {duration}秒 (最大允许: {self.max_execution_time}秒)"
            )
        
        warnings = []
        if duration > 10:
            warnings.append("等待时间较长，请确认是否必要")
        
        return SafetyResult(
            allowed=True,
            risk_level=RiskLevel.LOW,
            warnings=warnings
        )
    
    def check_batch_actions_safety(self, actions: List[ParsedAction]) -> List[SafetyResult]:
        """检查批量动作的安全性"""
        results = []
        
        # 检查批量操作的总体安全性
        if len(actions) > 50:
            # 如果动作过多，标记为高风险
            for action in actions:
                results.append(SafetyResult(
                    allowed=False,
                    risk_level=RiskLevel.HIGH,
                    warnings=[],
                    blocked_reason="批量操作动作数量过多，存在安全风险"
                ))
            return results
        
        # 逐个检查每个动作
        for action in actions:
            result = self.check_action_safety(action)
            results.append(result)
            
            # 如果有任何动作被阻止，停止检查后续动作
            if not result.allowed:
                break
        
        return results
    
    def check_instruction_safety(self, instruction: str) -> SafetyResult:
        """检查原始指令的安全性"""
        instruction_lower = instruction.lower()
        warnings = []
        risk_level = RiskLevel.LOW
        
        # 检查指令长度
        if len(instruction) > 500:
            return SafetyResult(
                allowed=False,
                risk_level=RiskLevel.MEDIUM,
                warnings=[],
                blocked_reason="指令过长，可能存在安全风险"
            )
        
        # 检查危险关键词
        for category, keywords in self.dangerous_keywords.items():
            for keyword in keywords:
                if keyword in instruction_lower:
                    if category in ["system", "network"]:
                        return SafetyResult(
                            allowed=False,
                            risk_level=RiskLevel.HIGH,
                            warnings=[],
                            blocked_reason=f"指令包含危险关键词: {keyword}"
                        )
                    else:
                        warnings.append(f"指令包含敏感词汇: {keyword}")
                        risk_level = RiskLevel.MEDIUM
        
        # 检查是否试图执行系统命令
        system_patterns = [
            r'exec\s*\(',
            r'eval\s*\(',
            r'system\s*\(',
            r'shell\s*\(',
            r'subprocess\.',
            r'os\.',
            r'import\s+os',
            r'import\s+subprocess'
        ]
        
        for pattern in system_patterns:
            if re.search(pattern, instruction, re.IGNORECASE):
                return SafetyResult(
                    allowed=False,
                    risk_level=RiskLevel.CRITICAL,
                    warnings=[],
                    blocked_reason="指令试图执行系统级操作，已被阻止"
                )
        
        return SafetyResult(
            allowed=True,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def update_coordinate_limits(self, width: int, height: int):
        """更新坐标限制"""
        self.coordinate_limits.update({
            "max_x": width,
            "max_y": height
        })
    
    def add_dangerous_keyword(self, category: str, keyword: str):
        """添加危险关键词"""
        if category not in self.dangerous_keywords:
            self.dangerous_keywords[category] = []
        self.dangerous_keywords[category].append(keyword.lower())
    
    def remove_dangerous_keyword(self, category: str, keyword: str):
        """移除危险关键词"""
        if category in self.dangerous_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.dangerous_keywords[category]:
                self.dangerous_keywords[category].remove(keyword_lower)
    
    def get_safety_stats(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        current_time = time.time()
        recent_actions = [t for t in self.action_history if current_time - t < 300]  # 5分钟内
        
        return {
            "actions_last_minute": len([t for t in self.action_history if current_time - t < 60]),
            "actions_last_5_minutes": len(recent_actions),
            "max_actions_per_minute": self.max_actions_per_minute,
            "allowed_actions": list(self.allowed_actions),
            "coordinate_limits": self.coordinate_limits,
            "dangerous_keywords_count": sum(len(keywords) for keywords in self.dangerous_keywords.values())
        }