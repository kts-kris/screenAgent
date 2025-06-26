import re
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

class ActionType(Enum):
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    PRESS_KEY = "press_key"
    DRAG = "drag"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    FIND_TEXT = "find_text"
    FIND_ELEMENT = "find_element"

@dataclass
class ParsedAction:
    action_type: ActionType
    parameters: Dict[str, Any]
    confidence: float
    original_text: str
    description: str

class CommandParser:
    """智能指令解析器"""
    
    def __init__(self):
        self.action_patterns = {
            ActionType.CLICK: [
                r"点击\s*[\"']?([^\"']*)[\"']?",
                r"click\s+(?:on\s+)?[\"']?([^\"']*)[\"']?",
                r"tap\s+(?:on\s+)?[\"']?([^\"']*)[\"']?",
                r"按\s*[\"']?([^\"']*)[\"']?",
                r"选择\s*[\"']?([^\"']*)[\"']?",
            ],
            ActionType.TYPE: [
                r"输入\s*[\"']([^\"']*)[\"']",
                r"type\s+[\"']([^\"']*)[\"']",
                r"写\s*[\"']([^\"']*)[\"']",
                r"填写\s*[\"']([^\"']*)[\"']",
                r"enter\s+[\"']([^\"']*)[\"']",
            ],
            ActionType.SCROLL: [
                r"滚动\s*(上|下|左|右)?",
                r"scroll\s*(up|down|left|right)?",
                r"向(上|下|左|右)滚动",
                r"上滑|下滑|左滑|右滑",
            ],
            ActionType.PRESS_KEY: [
                r"按\s*(回车|空格|删除|退格|Tab|Esc|Enter|Space|Delete|Backspace)",
                r"press\s+(enter|space|delete|backspace|tab|esc|return)",
                r"键盘按\s*([A-Za-z0-9]+)",
            ],
            ActionType.DRAG: [
                r"拖拽\s*[\"']?([^\"']*)[\"']?\s*到\s*[\"']?([^\"']*)[\"']?",
                r"drag\s+[\"']?([^\"']*)[\"']?\s+to\s+[\"']?([^\"']*)[\"']?",
                r"拖动\s*从\s*\((\d+),\s*(\d+)\)\s*到\s*\((\d+),\s*(\d+)\)",
            ],
            ActionType.SCREENSHOT: [
                r"截图|截屏",
                r"screenshot",
                r"capture\s+screen",
                r"take\s+screenshot",
            ],
            ActionType.WAIT: [
                r"等待\s*(\d+)\s*秒?",
                r"wait\s+(\d+)\s*seconds?",
                r"暂停\s*(\d+)\s*秒?",
                r"sleep\s+(\d+)",
            ],
            ActionType.FIND_TEXT: [
                r"查找\s*[\"']([^\"']*)[\"']",
                r"find\s+[\"']([^\"']*)[\"']",
                r"搜索\s*[\"']([^\"']*)[\"']",
                r"寻找\s*[\"']([^\"']*)[\"']",
            ]
        }
        
        self.coordinate_patterns = [
            r"\((\d+),\s*(\d+)\)",
            r"坐标\s*\((\d+),\s*(\d+)\)",
            r"位置\s*\((\d+),\s*(\d+)\)",
            r"at\s+\((\d+),\s*(\d+)\)",
        ]
        
        self.direction_mapping = {
            "上": "up", "下": "down", "左": "left", "右": "right",
            "up": "up", "down": "down", "left": "left", "right": "right"
        }
        
        self.key_mapping = {
            "回车": "Return", "空格": "space", "删除": "Delete", 
            "退格": "BackSpace", "Tab": "Tab", "Esc": "Escape",
            "enter": "Return", "space": "space", "delete": "Delete",
            "backspace": "BackSpace", "tab": "Tab", "esc": "Escape",
            "return": "Return"
        }
    
    def parse_instruction(self, instruction: str) -> List[ParsedAction]:
        """解析用户指令为可执行的动作序列"""
        instruction = instruction.strip()
        actions = []
        
        # 分割复合指令
        sub_instructions = self._split_compound_instruction(instruction)
        
        for sub_instruction in sub_instructions:
            action = self._parse_single_instruction(sub_instruction)
            if action:
                actions.append(action)
        
        return actions
    
    def _split_compound_instruction(self, instruction: str) -> List[str]:
        """分割复合指令"""
        # 使用常见的分隔符分割指令
        separators = [r"[，,]然后", r"[，,]接着", r"[，,]再", r"[，,]and then", r"[，,]then", r"[；;]", r"[，,]"]
        
        parts = [instruction]
        for separator in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(re.split(separator, part))
            parts = new_parts
        
        return [part.strip() for part in parts if part.strip()]
    
    def _parse_single_instruction(self, instruction: str) -> Optional[ParsedAction]:
        """解析单个指令"""
        instruction = instruction.strip()
        
        # 尝试匹配各种动作类型
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, instruction, re.IGNORECASE)
                if match:
                    return self._create_action(action_type, match, instruction)
        
        # 如果没有匹配到明确的动作，尝试推断
        return self._infer_action(instruction)
    
    def _create_action(self, action_type: ActionType, match: re.Match, instruction: str) -> ParsedAction:
        """根据匹配结果创建动作"""
        parameters = {}
        confidence = 0.9
        
        if action_type == ActionType.CLICK:
            target = match.group(1) if match.groups() else ""
            parameters = {"target": target.strip()}
            
            # 检查是否有坐标信息
            coord_match = re.search(r"\((\d+),\s*(\d+)\)", instruction)
            if coord_match:
                parameters["x"] = int(coord_match.group(1))
                parameters["y"] = int(coord_match.group(2))
                parameters["use_coordinates"] = True
            else:
                parameters["use_coordinates"] = False
        
        elif action_type == ActionType.TYPE:
            text = match.group(1) if match.groups() else ""
            parameters = {"text": text}
        
        elif action_type == ActionType.SCROLL:
            direction = match.group(1) if match.groups() else "down"
            direction = self.direction_mapping.get(direction, "down")
            parameters = {"direction": direction, "amount": 3}
            
            # 检查滚动距离
            distance_match = re.search(r"(\d+)", instruction)
            if distance_match:
                parameters["amount"] = int(distance_match.group(1))
        
        elif action_type == ActionType.PRESS_KEY:
            key = match.group(1) if match.groups() else ""
            key = self.key_mapping.get(key.lower(), key)
            parameters = {"key": key}
        
        elif action_type == ActionType.DRAG:
            if len(match.groups()) >= 2:
                source = match.group(1).strip()
                target = match.group(2).strip()
                parameters = {"source": source, "target": target}
            elif len(match.groups()) >= 4:
                # 坐标形式的拖拽
                parameters = {
                    "source_x": int(match.group(1)),
                    "source_y": int(match.group(2)),
                    "target_x": int(match.group(3)),
                    "target_y": int(match.group(4)),
                    "use_coordinates": True
                }
        
        elif action_type == ActionType.WAIT:
            duration = int(match.group(1)) if match.groups() else 1
            parameters = {"duration": duration}
        
        elif action_type == ActionType.FIND_TEXT:
            text = match.group(1) if match.groups() else ""
            parameters = {"text": text}
        
        elif action_type == ActionType.SCREENSHOT:
            parameters = {"save_path": None}
        
        return ParsedAction(
            action_type=action_type,
            parameters=parameters,
            confidence=confidence,
            original_text=instruction,
            description=f"{action_type.value}: {parameters}"
        )
    
    def _infer_action(self, instruction: str) -> Optional[ParsedAction]:
        """推断动作类型"""
        instruction_lower = instruction.lower()
        
        # 简单的关键词推断
        if any(keyword in instruction_lower for keyword in ["打开", "启动", "运行", "open", "launch", "run"]):
            return ParsedAction(
                action_type=ActionType.CLICK,
                parameters={"target": instruction, "use_coordinates": False},
                confidence=0.6,
                original_text=instruction,
                description=f"推断为点击动作: {instruction}"
            )
        
        # 如果包含引号中的文本，可能是输入操作
        quote_match = re.search(r'["\']([^"\']*)["\']', instruction)
        if quote_match:
            return ParsedAction(
                action_type=ActionType.TYPE,
                parameters={"text": quote_match.group(1)},
                confidence=0.7,
                original_text=instruction,
                description=f"推断为输入动作: {quote_match.group(1)}"
            )
        
        return None
    
    def validate_action(self, action: ParsedAction) -> bool:
        """验证动作的有效性"""
        if action.action_type == ActionType.CLICK:
            return "target" in action.parameters
        
        elif action.action_type == ActionType.TYPE:
            return "text" in action.parameters and action.parameters["text"]
        
        elif action.action_type == ActionType.SCROLL:
            return "direction" in action.parameters
        
        elif action.action_type == ActionType.PRESS_KEY:
            return "key" in action.parameters
        
        elif action.action_type == ActionType.DRAG:
            return ("source" in action.parameters and "target" in action.parameters) or \
                   ("source_x" in action.parameters and "source_y" in action.parameters and 
                    "target_x" in action.parameters and "target_y" in action.parameters)
        
        elif action.action_type == ActionType.WAIT:
            return "duration" in action.parameters and action.parameters["duration"] > 0
        
        elif action.action_type == ActionType.FIND_TEXT:
            return "text" in action.parameters and action.parameters["text"]
        
        elif action.action_type == ActionType.SCREENSHOT:
            return True
        
        return False
    
    def parse_json_instruction(self, json_str: str) -> List[ParsedAction]:
        """解析JSON格式的指令"""
        try:
            data = json.loads(json_str)
            actions = []
            
            if isinstance(data, list):
                for item in data:
                    action = self._parse_json_action(item)
                    if action:
                        actions.append(action)
            elif isinstance(data, dict):
                action = self._parse_json_action(data)
                if action:
                    actions.append(action)
            
            return actions
        
        except json.JSONDecodeError:
            return []
    
    def _parse_json_action(self, data: Dict[str, Any]) -> Optional[ParsedAction]:
        """解析JSON动作"""
        try:
            action_type_str = data.get("action", "").lower()
            action_type = None
            
            for at in ActionType:
                if at.value == action_type_str:
                    action_type = at
                    break
            
            if not action_type:
                return None
            
            parameters = data.get("parameters", {})
            
            return ParsedAction(
                action_type=action_type,
                parameters=parameters,
                confidence=data.get("confidence", 0.9),
                original_text=json.dumps(data),
                description=data.get("description", f"{action_type.value}: {parameters}")
            )
        
        except Exception:
            return None
    
    def get_action_suggestions(self, partial_instruction: str) -> List[str]:
        """根据部分指令提供建议"""
        suggestions = []
        partial_lower = partial_instruction.lower()
        
        # 基于已输入的内容提供建议
        if "点击" in partial_lower or "click" in partial_lower:
            suggestions.extend([
                "点击确定按钮",
                "点击取消",
                "点击(100, 200)",
                "click on submit button"
            ])
        
        elif "输入" in partial_lower or "type" in partial_lower:
            suggestions.extend([
                "输入'用户名'",
                "输入密码",
                "type 'hello world'"
            ])
        
        elif "滚动" in partial_lower or "scroll" in partial_lower:
            suggestions.extend([
                "向下滚动",
                "向上滚动5次",
                "scroll down"
            ])
        
        else:
            # 提供常用指令建议
            suggestions.extend([
                "点击登录按钮",
                "输入'用户名'",
                "向下滚动",
                "截图",
                "等待3秒",
                "按回车键"
            ])
        
        return suggestions[:5]  # 限制建议数量