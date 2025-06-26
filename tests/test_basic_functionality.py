import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import tempfile
import os

from src.config import ConfigManager
from src.capture import ScreenCapture
from src.vision import OCREngine, ImageProcessor
from src.ai import LLMManager
from src.executor import CommandParser, ActionExecutor, InstructionProcessor
from src.executor.command_parser import ActionType

class TestBasicFunctionality(unittest.TestCase):
    """基础功能测试"""
    
    def setUp(self):
        """测试准备"""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
    
    def test_config_loading(self):
        """测试配置加载"""
        self.assertIsNotNone(self.config)
        self.assertIn("llm", self.config.model_dump())
        self.assertIn("capture", self.config.model_dump())
        self.assertIn("ocr", self.config.model_dump())
    
    def test_screen_capture_basic(self):
        """测试基础屏幕截图功能"""
        capture = ScreenCapture()
        
        # 测试获取屏幕尺寸
        size = capture.get_screen_size()
        self.assertIsInstance(size, tuple)
        self.assertEqual(len(size), 2)
        self.assertGreater(size[0], 0)
        self.assertGreater(size[1], 0)
    
    @patch('src.capture.screen_capture.ImageGrab.grab')
    def test_screen_capture_mock(self, mock_grab):
        """测试屏幕截图（模拟）"""
        # 创建模拟图像
        mock_image = Image.new('RGB', (100, 100), color='red')
        mock_grab.return_value = mock_image
        
        capture = ScreenCapture()
        screenshot = capture.capture_full_screen()
        
        self.assertEqual(screenshot.size, (100, 100))
        mock_grab.assert_called_once()
    
    def test_command_parser_basic(self):
        """测试基础指令解析"""
        parser = CommandParser()
        
        # 测试点击指令
        actions = parser.parse_instruction("点击登录按钮")
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0].action_type, ActionType.CLICK)
        self.assertIn("target", actions[0].parameters)
        
        # 测试输入指令
        actions = parser.parse_instruction("输入'hello world'")
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0].action_type, ActionType.TYPE)
        self.assertEqual(actions[0].parameters["text"], "hello world")
        
        # 测试滚动指令
        actions = parser.parse_instruction("向下滚动")
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0].action_type, ActionType.SCROLL)
        self.assertEqual(actions[0].parameters["direction"], "down")
    
    def test_command_parser_complex(self):
        """测试复杂指令解析"""
        parser = CommandParser()
        
        # 测试复合指令
        actions = parser.parse_instruction("点击登录按钮，然后输入'用户名'")
        self.assertGreaterEqual(len(actions), 2)
        
        # 测试坐标指令
        actions = parser.parse_instruction("点击坐标(100, 200)")
        self.assertGreater(len(actions), 0)
        action = actions[0]
        self.assertEqual(action.action_type, ActionType.CLICK)
        self.assertTrue(action.parameters["use_coordinates"])
        self.assertEqual(action.parameters["x"], 100)
        self.assertEqual(action.parameters["y"], 200)
    
    def test_image_processor_basic(self):
        """测试图像处理器基础功能"""
        processor = ImageProcessor()
        
        # 创建测试图像
        test_image = Image.new('RGB', (200, 100), color='white')
        
        # 测试快速预处理
        processed = processor.preprocess_for_ocr(test_image, fast_mode=True)
        self.assertIsInstance(processed, Image.Image)
        
        # 测试尺寸调整
        resized = processor.resize_for_performance(test_image, max_dimension=150)
        self.assertLessEqual(max(resized.size), 150)
        
        # 测试缓存
        cache_stats = processor.get_cache_stats()
        self.assertIn("cache_size", cache_stats)
        self.assertIn("max_cache_size", cache_stats)
    
    @patch('src.vision.ocr_engine.pytesseract.image_to_string')
    def test_ocr_engine_mock(self, mock_ocr):
        """测试OCR引擎（模拟）"""
        mock_ocr.return_value = "Test text content"
        
        ocr = OCREngine()
        test_image = Image.new('RGB', (200, 100), color='white')
        
        # 测试快速文本提取
        result = ocr.extract_text_fast(test_image)
        self.assertEqual(result.text, "Test text content")
        self.assertGreater(result.confidence, 0)
        
        mock_ocr.assert_called()
    
    def test_llm_manager_initialization(self):
        """测试LLM管理器初始化"""
        llm_config = self.config.llm.model_dump()
        manager = LLMManager(llm_config)
        
        self.assertIsNotNone(manager.providers)
        self.assertIsInstance(manager.get_available_providers(), list)
        
        # 测试状态获取
        status = manager.get_all_status()
        self.assertIsInstance(status, dict)
    
    @patch('src.executor.action_executor.pyautogui.click')
    def test_action_executor_mock(self, mock_click):
        """测试动作执行器（模拟）"""
        executor = ActionExecutor(safety_mode=True)
        
        from src.executor.command_parser import ParsedAction
        
        # 创建点击动作
        action = ParsedAction(
            action_type=ActionType.CLICK,
            parameters={"x": 100, "y": 100, "use_coordinates": True},
            confidence=0.9,
            original_text="点击(100, 100)",
            description="点击坐标"
        )
        
        result = executor.execute_action(action)
        self.assertTrue(result.success)
        mock_click.assert_called_with(100, 100)
    
    def test_action_executor_safety(self):
        """测试动作执行器安全检查"""
        executor = ActionExecutor(safety_mode=True)
        
        from src.executor.command_parser import ParsedAction
        
        # 测试超出屏幕范围的点击
        action = ParsedAction(
            action_type=ActionType.CLICK,
            parameters={"x": 99999, "y": 99999, "use_coordinates": True},
            confidence=0.9,
            original_text="点击(99999, 99999)",
            description="超范围点击"
        )
        
        result = executor.execute_action(action)
        self.assertFalse(result.success)
        self.assertIn("安全检查失败", result.message)
    
    def test_instruction_processor_integration(self):
        """测试指令处理器集成"""
        config_dict = self.config.model_dump()
        processor = InstructionProcessor(config_dict)
        
        # 测试系统状态
        status = processor.get_system_status()
        self.assertIn("screen_capture", status)
        self.assertIn("ocr_engine", status)
        self.assertIn("llm_manager", status)
        self.assertIn("action_executor", status)
        
        # 测试屏幕分析
        analysis = processor.get_screen_analysis()
        self.assertIsInstance(analysis, dict)

class TestAsyncFunctionality(unittest.IsolatedAsyncioTestCase):
    """异步功能测试"""
    
    async def asyncSetUp(self):
        """异步测试准备"""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.processor = InstructionProcessor(self.config.model_dump())
    
    @patch('src.ai.providers.ollama_provider.requests.get')
    async def test_llm_provider_mock(self, mock_get):
        """测试LLM提供商（模拟）"""
        # 模拟Ollama健康检查
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        from src.ai.providers.ollama_provider import OllamaProvider
        
        provider = OllamaProvider({
            "base_url": "http://localhost:11434",
            "model": "test-model"
        })
        
        self.assertTrue(provider.is_available())
    
    @patch.object(InstructionProcessor, '_ai_analyze_and_plan')
    async def test_instruction_processing_mock(self, mock_ai_analyze):
        """测试指令处理（模拟）"""
        # 模拟AI分析结果
        mock_ai_analyze.return_value = {
            "analysis": "测试分析",
            "intent": "测试意图",
            "actions": [{
                "action": "screenshot",
                "parameters": {},
                "description": "截图测试",
                "confidence": 0.9
            }],
            "explanation": "测试解释"
        }
        
        result = await self.processor.process_instruction(
            "截图", 
            use_ai_analysis=True, 
            take_screenshot=False
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.ai_analysis)

class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def test_invalid_config_handling(self):
        """测试无效配置处理"""
        # 测试不存在的配置文件
        config_manager = ConfigManager("nonexistent_config.yaml")
        config = config_manager.load_config()
        
        # 应该回退到默认配置
        self.assertIsNotNone(config)
    
    def test_command_parser_invalid_input(self):
        """测试指令解析器错误输入处理"""
        parser = CommandParser()
        
        # 测试空指令
        actions = parser.parse_instruction("")
        self.assertEqual(len(actions), 0)
        
        # 测试无法识别的指令
        actions = parser.parse_instruction("这是一个无法识别的指令")
        # 应该尝试推断或返回空列表
        self.assertIsInstance(actions, list)
    
    def test_ocr_error_handling(self):
        """测试OCR错误处理"""
        ocr = OCREngine()
        
        # 测试空图像
        try:
            empty_image = Image.new('RGB', (1, 1), color='white')
            result = ocr.extract_text_fast(empty_image)
            self.assertIsInstance(result.text, str)
            self.assertGreaterEqual(result.confidence, 0)
        except Exception as e:
            self.fail(f"OCR should handle empty images gracefully: {e}")

class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_image_processing_performance(self):
        """测试图像处理性能"""
        processor = ImageProcessor()
        
        # 创建大图像
        large_image = Image.new('RGB', (1920, 1080), color='white')
        
        import time
        start_time = time.time()
        
        # 测试快速预处理
        processed = processor.preprocess_for_ocr(large_image, fast_mode=True)
        
        processing_time = time.time() - start_time
        
        # 快速模式应该在合理时间内完成
        self.assertLess(processing_time, 2.0)  # 2秒内
        self.assertIsInstance(processed, Image.Image)
    
    def test_command_parsing_performance(self):
        """测试指令解析性能"""
        parser = CommandParser()
        
        import time
        start_time = time.time()
        
        # 解析多个指令
        test_instructions = [
            "点击登录按钮",
            "输入'用户名'",
            "向下滚动",
            "等待3秒",
            "截图"
        ]
        
        for instruction in test_instructions:
            actions = parser.parse_instruction(instruction)
            self.assertIsInstance(actions, list)
        
        parsing_time = time.time() - start_time
        
        # 解析应该很快
        self.assertLess(parsing_time, 0.1)  # 100ms内

if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestBasicFunctionality))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncFunctionality))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
    else:
        print(f"\n❌ {len(result.failures)} 个测试失败, {len(result.errors)} 个错误")
        for test, traceback in result.failures + result.errors:
            print(f"  - {test}: {traceback}")