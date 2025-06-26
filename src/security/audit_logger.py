import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class EventType(Enum):
    INSTRUCTION_RECEIVED = "instruction_received"
    ACTION_EXECUTED = "action_executed"
    SAFETY_CHECK = "safety_check"
    PERMISSION_CHECK = "permission_check"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_ACCESS = "system_access"
    SCREENSHOT_TAKEN = "screenshot_taken"
    OCR_PERFORMED = "ocr_performed"
    LLM_CALLED = "llm_called"

@dataclass
class AuditEvent:
    timestamp: str
    event_type: EventType
    level: LogLevel
    user_instruction: Optional[str]
    action_details: Dict[str, Any]
    result: Dict[str, Any]
    safety_assessment: Optional[Dict[str, Any]]
    session_id: str
    event_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        return data

class AuditLogger:
    """审计日志记录器 - 记录所有系统操作用于安全审计"""
    
    def __init__(self, log_directory: str = "logs", session_id: Optional[str] = None):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        self.session_id = session_id or self._generate_session_id()
        self.log_file = self.log_directory / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.session_file = self.log_directory / f"session_{self.session_id}.jsonl"
        
        # 事件计数器
        self.event_counter = 0
        self.events_per_session = 0
        
        # 内存中的事件缓存（用于分析）
        self.recent_events: List[AuditEvent] = []
        self.max_recent_events = 1000
        
        # 记录会话开始
        self._log_session_start()
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = str(time.time())
        return hashlib.md5(timestamp.encode()).hexdigest()[:16]
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        self.event_counter += 1
        self.events_per_session += 1
        return f"{self.session_id}_{self.event_counter:06d}"
    
    def _log_session_start(self):
        """记录会话开始"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.SYSTEM_ACCESS,
            level=LogLevel.INFO,
            user_instruction=None,
            action_details={"action": "session_start", "session_id": self.session_id},
            result={"status": "started"},
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_instruction_received(self, 
                               instruction: str, 
                               source: str = "user",
                               metadata: Optional[Dict[str, Any]] = None):
        """记录收到的用户指令"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.INSTRUCTION_RECEIVED,
            level=LogLevel.INFO,
            user_instruction=instruction,
            action_details={
                "source": source,
                "instruction_length": len(instruction),
                "metadata": metadata or {}
            },
            result={"status": "received"},
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_action_executed(self, 
                          action_type: str,
                          parameters: Dict[str, Any],
                          result: Dict[str, Any],
                          execution_time: float,
                          user_instruction: Optional[str] = None):
        """记录执行的动作"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.ACTION_EXECUTED,
            level=LogLevel.INFO if result.get("success", False) else LogLevel.WARNING,
            user_instruction=user_instruction,
            action_details={
                "action_type": action_type,
                "parameters": self._sanitize_parameters(parameters),
                "execution_time": execution_time
            },
            result=result,
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_safety_check(self, 
                        instruction: str,
                        action_type: str,
                        safety_result: Dict[str, Any],
                        risk_factors: Optional[List[str]] = None):
        """记录安全检查"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.SAFETY_CHECK,
            level=LogLevel.WARNING if not safety_result.get("allowed", True) else LogLevel.INFO,
            user_instruction=instruction,
            action_details={
                "action_type": action_type,
                "risk_factors": risk_factors or []
            },
            result=safety_result,
            safety_assessment=safety_result,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_permission_check(self, 
                           permission_type: str,
                           granted: bool,
                           details: Optional[Dict[str, Any]] = None):
        """记录权限检查"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.PERMISSION_CHECK,
            level=LogLevel.WARNING if not granted else LogLevel.INFO,
            user_instruction=None,
            action_details={
                "permission_type": permission_type,
                "details": details or {}
            },
            result={"granted": granted},
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_error(self, 
                 error_type: str,
                 error_message: str,
                 context: Optional[Dict[str, Any]] = None,
                 user_instruction: Optional[str] = None):
        """记录错误"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.ERROR_OCCURRED,
            level=LogLevel.ERROR,
            user_instruction=user_instruction,
            action_details={
                "error_type": error_type,
                "context": context or {}
            },
            result={"error_message": error_message},
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_screenshot_taken(self, 
                           screenshot_info: Dict[str, Any],
                           purpose: str = "user_request"):
        """记录截图操作"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.SCREENSHOT_TAKEN,
            level=LogLevel.INFO,
            user_instruction=None,
            action_details={
                "purpose": purpose,
                "screenshot_info": self._sanitize_screenshot_info(screenshot_info)
            },
            result={"status": "completed"},
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_ocr_performed(self, 
                        text_found: bool,
                        confidence: float,
                        text_length: int,
                        language: Optional[str] = None):
        """记录OCR操作"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.OCR_PERFORMED,
            level=LogLevel.INFO,
            user_instruction=None,
            action_details={
                "language": language,
                "processing_mode": "auto"
            },
            result={
                "text_found": text_found,
                "confidence": confidence,
                "text_length": text_length
            },
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def log_llm_call(self, 
                    provider: str,
                    model: str,
                    prompt_length: int,
                    response_length: int,
                    success: bool,
                    usage: Optional[Dict[str, Any]] = None):
        """记录LLM调用"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.LLM_CALLED,
            level=LogLevel.INFO if success else LogLevel.WARNING,
            user_instruction=None,
            action_details={
                "provider": provider,
                "model": model,
                "prompt_length": prompt_length
            },
            result={
                "success": success,
                "response_length": response_length,
                "usage": usage or {}
            },
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)
    
    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """清理参数中的敏感信息"""
        sanitized = parameters.copy()
        
        # 清理可能包含敏感信息的字段
        sensitive_keys = ["password", "token", "key", "secret", "auth"]
        
        for key, value in sanitized.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 0:
                    sanitized[key] = "***REDACTED***"
            elif key == "text" and isinstance(value, str):
                # 对输入文本进行部分隐藏
                if len(value) > 50:
                    sanitized[key] = value[:20] + "..." + value[-10:]
        
        return sanitized
    
    def _sanitize_screenshot_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """清理截图信息"""
        sanitized = info.copy()
        
        # 移除实际的图像数据，只保留元数据
        if "image_data" in sanitized:
            del sanitized["image_data"]
        
        return sanitized
    
    def _write_event(self, event: AuditEvent):
        """写入事件到日志文件"""
        try:
            # 写入主日志文件
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
            
            # 写入会话日志文件
            with open(self.session_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
            
            # 添加到内存缓存
            self.recent_events.append(event)
            if len(self.recent_events) > self.max_recent_events:
                self.recent_events.pop(0)
                
        except Exception as e:
            # 如果日志写入失败，至少打印到控制台
            print(f"审计日志写入失败: {e}")
            print(f"事件: {event.to_dict()}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        event_counts = {}
        safety_violations = 0
        errors = 0
        
        for event in self.recent_events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            if event.event_type == EventType.SAFETY_CHECK and not event.result.get("allowed", True):
                safety_violations += 1
            
            if event.level == LogLevel.ERROR:
                errors += 1
        
        return {
            "session_id": self.session_id,
            "events_count": self.events_per_session,
            "event_types": event_counts,
            "safety_violations": safety_violations,
            "errors": errors,
            "duration": self._calculate_session_duration()
        }
    
    def _calculate_session_duration(self) -> float:
        """计算会话持续时间"""
        if not self.recent_events:
            return 0.0
        
        first_event = self.recent_events[0]
        last_event = self.recent_events[-1]
        
        try:
            first_time = datetime.fromisoformat(first_event.timestamp.replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(last_event.timestamp.replace('Z', '+00:00'))
            return (last_time - first_time).total_seconds()
        except Exception:
            return 0.0
    
    def search_events(self, 
                     event_type: Optional[EventType] = None,
                     level: Optional[LogLevel] = None,
                     since: Optional[datetime] = None,
                     limit: int = 100) -> List[AuditEvent]:
        """搜索事件"""
        filtered_events = []
        
        for event in reversed(self.recent_events):  # 最新的在前
            if len(filtered_events) >= limit:
                break
            
            # 应用过滤条件
            if event_type and event.event_type != event_type:
                continue
            
            if level and event.level != level:
                continue
            
            if since:
                try:
                    event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                    if event_time < since:
                        continue
                except Exception:
                    continue
            
            filtered_events.append(event)
        
        return filtered_events
    
    def get_security_alerts(self) -> List[Dict[str, Any]]:
        """获取安全警告"""
        alerts = []
        
        # 查找安全违规
        safety_events = self.search_events(event_type=EventType.SAFETY_CHECK, limit=50)
        for event in safety_events:
            if not event.result.get("allowed", True):
                alerts.append({
                    "type": "safety_violation",
                    "timestamp": event.timestamp,
                    "instruction": event.user_instruction,
                    "reason": event.result.get("blocked_reason", "Unknown"),
                    "risk_level": event.safety_assessment.get("risk_level", "unknown")
                })
        
        # 查找权限问题
        permission_events = self.search_events(event_type=EventType.PERMISSION_CHECK, limit=20)
        for event in permission_events:
            if not event.result.get("granted", True):
                alerts.append({
                    "type": "permission_denied",
                    "timestamp": event.timestamp,
                    "permission": event.action_details.get("permission_type", "unknown")
                })
        
        # 查找频繁错误
        error_events = self.search_events(level=LogLevel.ERROR, limit=30)
        if len(error_events) > 10:  # 如果错误过多
            alerts.append({
                "type": "frequent_errors",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_count": len(error_events),
                "details": "系统在短时间内出现多次错误"
            })
        
        return alerts
    
    def export_logs(self, 
                   output_file: str,
                   format: str = "json",
                   event_type: Optional[EventType] = None,
                   since: Optional[datetime] = None) -> bool:
        """导出日志"""
        try:
            events = self.search_events(event_type=event_type, since=since, limit=10000)
            
            if format == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump([event.to_dict() for event in events], f, 
                             ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    if events:
                        writer = csv.DictWriter(f, fieldnames=events[0].to_dict().keys())
                        writer.writeheader()
                        for event in events:
                            writer.writerow(event.to_dict())
            
            return True
        except Exception:
            return False
    
    def close_session(self):
        """关闭会话"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=EventType.SYSTEM_ACCESS,
            level=LogLevel.INFO,
            user_instruction=None,
            action_details={
                "action": "session_end",
                "session_summary": self.get_session_summary()
            },
            result={"status": "ended"},
            safety_assessment=None,
            session_id=self.session_id,
            event_id=self._generate_event_id()
        )
        self._write_event(event)