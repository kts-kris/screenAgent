import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
import pytesseract
from PIL import Image
import cv2
import numpy as np
from dataclasses import dataclass
from .image_processor import ImageProcessor

@dataclass
class OCRResult:
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    language: Optional[str] = None

class OCREngine:
    """高性能OCR引擎"""
    
    def __init__(self, languages: str = "eng+chi_sim", tesseract_path: Optional[str] = None):
        self.languages = languages
        self.image_processor = ImageProcessor()
        self._thread_local = threading.local()
        
        # 设置tesseract路径（macOS通常需要）
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif os.path.exists('/opt/homebrew/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        elif os.path.exists('/usr/local/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
        
        # 性能优化配置
        self.fast_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz \t\n'
        self.detailed_config = r'--oem 3 --psm 3'
        
    def _get_tesseract_config(self, mode: str = "fast") -> str:
        """获取tesseract配置"""
        if mode == "fast":
            return self.fast_config
        elif mode == "detailed":
            return self.detailed_config
        else:
            return r'--oem 3 --psm 6'
    
    def extract_text_fast(self, image: Image.Image, preprocess: bool = True) -> OCRResult:
        """快速文本提取（优化速度）"""
        start_time = time.time()
        
        if preprocess:
            # 使用快速预处理
            processed_image = self.image_processor.preprocess_for_ocr(image, fast_mode=True)
        else:
            processed_image = image
        
        try:
            # 使用快速配置
            text = pytesseract.image_to_string(
                processed_image, 
                lang=self.languages,
                config=self._get_tesseract_config("fast")
            ).strip()
            
            # 快速置信度估算
            confidence = self._estimate_confidence_fast(text)
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=text,
                confidence=confidence,
                language=self.languages
            )
            
        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                language=self.languages
            )
    
    def extract_text_detailed(self, image: Image.Image) -> OCRResult:
        """详细文本提取（优化准确性）"""
        start_time = time.time()
        
        # 使用详细预处理
        processed_image = self.image_processor.preprocess_for_ocr(image, fast_mode=False)
        
        try:
            # 获取详细信息
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.languages,
                config=self._get_tesseract_config("detailed"),
                output_type=pytesseract.Output.DICT
            )
            
            # 过滤高置信度文本
            words = []
            confidences = []
            bboxes = []
            
            for i, conf in enumerate(data['conf']):
                if int(conf) > 30:  # 置信度阈值
                    word = data['text'][i].strip()
                    if word:
                        words.append(word)
                        confidences.append(int(conf))
                        bboxes.append((
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ))
            
            text = ' '.join(words)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return OCRResult(
                text=text,
                confidence=avg_confidence,
                bbox=bboxes[0] if bboxes else None,
                language=self.languages
            )
            
        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                language=self.languages
            )
    
    def extract_text_parallel(self, images: List[Image.Image], max_workers: int = 4) -> List[OCRResult]:
        """并行处理多张图像"""
        if not images:
            return []
        
        # 根据CPU核心数调整工作线程数
        max_workers = min(max_workers, len(images), os.cpu_count() or 1)
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_image = {
                executor.submit(self.extract_text_fast, img): i 
                for i, img in enumerate(images)
            }
            
            # 收集结果
            for future in as_completed(future_to_image):
                try:
                    result = future.result()
                    image_index = future_to_image[future]
                    results.append((image_index, result))
                except Exception as e:
                    image_index = future_to_image[future]
                    results.append((image_index, OCRResult("", 0.0, language=self.languages)))
        
        # 按原始顺序排序
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]
    
    def extract_text_smart(self, image: Image.Image, strategy: str = "auto") -> OCRResult:
        """智能文本提取：根据图像特征选择最佳策略"""
        width, height = image.size
        pixel_count = width * height
        
        if strategy == "auto":
            # 根据图像大小自动选择策略
            if pixel_count > 2000000:  # 大图像
                strategy = "crop_parallel"
            elif pixel_count > 500000:  # 中等图像
                strategy = "fast"
            else:  # 小图像
                strategy = "detailed"
        
        if strategy == "fast":
            return self.extract_text_fast(image)
        
        elif strategy == "detailed":
            return self.extract_text_detailed(image)
        
        elif strategy == "crop_parallel":
            # 裁剪并并行处理
            crops = self.image_processor.smart_crop(image)
            if len(crops) == 1:
                return self.extract_text_fast(crops[0])
            
            results = self.extract_text_parallel(crops)
            
            # 合并结果
            combined_text = []
            total_confidence = 0.0
            valid_results = 0
            
            for result in results:
                if result.text.strip():
                    combined_text.append(result.text.strip())
                    total_confidence += result.confidence
                    valid_results += 1
            
            avg_confidence = total_confidence / valid_results if valid_results > 0 else 0.0
            
            return OCRResult(
                text=' '.join(combined_text),
                confidence=avg_confidence,
                language=self.languages
            )
        
        else:
            return self.extract_text_fast(image)
    
    def _estimate_confidence_fast(self, text: str) -> float:
        """快速置信度估算"""
        if not text.strip():
            return 0.0
        
        # 基于文本特征的简单置信度估算
        confidence = 50.0  # 基础置信度
        
        # 包含常见单词加分
        common_words = ['the', 'and', 'or', 'is', 'to', 'of', 'in', 'a', 'an']
        for word in common_words:
            if word in text.lower():
                confidence += 5.0
        
        # 包含数字和字母组合加分
        if any(c.isdigit() for c in text) and any(c.isalpha() for c in text):
            confidence += 10.0
        
        # 文本长度合理性
        if 10 <= len(text.strip()) <= 200:
            confidence += 10.0
        
        # 特殊字符过多减分
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if special_chars > len(text) * 0.3:
            confidence -= 20.0
        
        return min(100.0, max(0.0, confidence))
    
    def check_tesseract_installation(self) -> bool:
        """检查tesseract是否正确安装"""
        try:
            version = pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def get_available_languages(self) -> List[str]:
        """获取可用的语言包"""
        try:
            langs = pytesseract.get_languages()
            return langs
        except Exception:
            return []
    
    def benchmark_performance(self, test_image: Image.Image, iterations: int = 5) -> Dict:
        """性能基准测试"""
        results = {
            "fast_mode": [],
            "detailed_mode": [],
            "smart_mode": []
        }
        
        for i in range(iterations):
            # 测试快速模式
            start_time = time.time()
            self.extract_text_fast(test_image)
            results["fast_mode"].append(time.time() - start_time)
            
            # 测试详细模式
            start_time = time.time()
            self.extract_text_detailed(test_image)
            results["detailed_mode"].append(time.time() - start_time)
            
            # 测试智能模式
            start_time = time.time()
            self.extract_text_smart(test_image)
            results["smart_mode"].append(time.time() - start_time)
        
        # 计算平均时间
        for mode in results:
            avg_time = sum(results[mode]) / len(results[mode])
            results[mode] = {
                "average_time": avg_time,
                "times": results[mode]
            }
        
        return results
    
    def cleanup(self):
        """清理资源"""
        self.image_processor.clear_cache()