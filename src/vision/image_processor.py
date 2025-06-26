import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Optional
import functools
import time

class ImageProcessor:
    """高性能图像处理器，专门为OCR优化"""
    
    def __init__(self):
        self._cache = {}
        self._cache_size = 100  # 缓存最近处理的100张图片
    
    def _cache_key(self, image_hash: str, operation: str, params: str) -> str:
        """生成缓存键"""
        return f"{image_hash}_{operation}_{params}"
    
    def _get_image_hash(self, image: Image.Image) -> str:
        """快速获取图像哈希"""
        # 使用图像尺寸和像素采样作为简单哈希
        width, height = image.size
        # 只采样几个像素点来生成哈希，避免全图遍历
        sample_pixels = []
        for x in range(0, width, width//10 + 1):
            for y in range(0, height, height//10 + 1):
                try:
                    sample_pixels.append(image.getpixel((x, y)))
                except:
                    pass
        return f"{width}x{height}_{hash(tuple(sample_pixels[:20]))}"
    
    def _manage_cache(self):
        """管理缓存大小"""
        if len(self._cache) > self._cache_size:
            # 删除最旧的缓存项
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
    
    def preprocess_for_ocr(self, image: Image.Image, fast_mode: bool = True) -> Image.Image:
        """为OCR预处理图像，优化性能"""
        img_hash = self._get_image_hash(image)
        cache_key = self._cache_key(img_hash, "preprocess", f"fast_{fast_mode}")
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        processed_image = image.copy()
        
        if fast_mode:
            # 快速模式：只做基本处理
            processed_image = self._fast_preprocess(processed_image)
        else:
            # 详细模式：全面处理
            processed_image = self._detailed_preprocess(processed_image)
        
        # 缓存结果
        self._cache[cache_key] = processed_image
        self._manage_cache()
        
        return processed_image
    
    def _fast_preprocess(self, image: Image.Image) -> Image.Image:
        """快速预处理：只做必要的优化"""
        # 1. 转换为RGB（如果需要）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 2. 简单的对比度增强
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # 3. 转换为灰度（OCR通常在灰度图上效果更好）
        image = image.convert('L')
        
        return image
    
    def _detailed_preprocess(self, image: Image.Image) -> Image.Image:
        """详细预处理：全面优化"""
        # 转换为OpenCV格式进行高级处理
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 1. 降噪
        cv_image = cv2.fastNlMeansDenoising(cv_image)
        
        # 2. 锐化
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        cv_image = cv2.filter2D(cv_image, -1, kernel)
        
        # 3. 自适应直方图均衡化
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # 4. 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 转换回PIL格式
        return Image.fromarray(binary)
    
    def resize_for_performance(self, image: Image.Image, max_dimension: int = 1920) -> Image.Image:
        """调整图像大小以优化性能"""
        width, height = image.size
        
        # 如果图像已经足够小，直接返回
        if max(width, height) <= max_dimension:
            return image
        
        # 计算缩放比例
        scale = max_dimension / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # 使用高质量的重采样方法
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def extract_text_regions(self, image: Image.Image) -> list:
        """快速提取可能包含文本的区域"""
        # 转换为OpenCV格式
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # 使用MSER（最大稳定极值区域）快速检测文本区域
        mser = cv2.MSER_create(
            _min_area=100,
            _max_area=14400,
            _max_evolution=200,
            _edge_blur_size=5
        )
        
        regions, _ = mser.detectRegions(gray)
        
        # 转换为边界框
        bboxes = []
        for region in regions:
            x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
            # 过滤掉太小的区域
            if w > 10 and h > 10:
                bboxes.append((x, y, x+w, y+h))
        
        return bboxes
    
    def smart_crop(self, image: Image.Image, padding: int = 10) -> list:
        """智能裁剪：将图像分割成更小的区域进行并行OCR"""
        width, height = image.size
        
        # 如果图像较小，不需要裁剪
        if width <= 800 and height <= 600:
            return [image]
        
        # 提取文本区域
        text_regions = self.extract_text_regions(image)
        
        if not text_regions:
            # 如果没有检测到文本区域，使用网格分割
            return self._grid_crop(image, 2, 2)
        
        # 基于文本区域进行智能裁剪
        crops = []
        for x1, y1, x2, y2 in text_regions:
            # 添加边距
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(width, x2 + padding)
            y2 = min(height, y2 + padding)
            
            # 裁剪区域
            crop = image.crop((x1, y1, x2, y2))
            crops.append(crop)
        
        return crops
    
    def _grid_crop(self, image: Image.Image, rows: int, cols: int) -> list:
        """网格分割图像"""
        width, height = image.size
        crop_width = width // cols
        crop_height = height // rows
        
        crops = []
        for row in range(rows):
            for col in range(cols):
                x1 = col * crop_width
                y1 = row * crop_height
                x2 = x1 + crop_width
                y2 = y1 + crop_height
                
                # 确保最后一行/列包含剩余像素
                if col == cols - 1:
                    x2 = width
                if row == rows - 1:
                    y2 = height
                
                crop = image.crop((x1, y1, x2, y2))
                crops.append(crop)
        
        return crops
    
    def enhance_contrast_adaptive(self, image: Image.Image) -> Image.Image:
        """自适应对比度增强"""
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 计算图像的动态范围
        min_val = np.min(img_array)
        max_val = np.max(img_array)
        dynamic_range = max_val - min_val
        
        # 如果动态范围太小，增强对比度
        if dynamic_range < 128:
            alpha = 255.0 / dynamic_range
            beta = -min_val * alpha
            enhanced = cv2.convertScaleAbs(img_array, alpha=alpha, beta=beta)
            return Image.fromarray(enhanced)
        
        return image
    
    def batch_process(self, images: list, operation: str, **kwargs) -> list:
        """批量处理图像以提高效率"""
        results = []
        
        for image in images:
            if operation == "preprocess":
                result = self.preprocess_for_ocr(image, **kwargs)
            elif operation == "resize":
                result = self.resize_for_performance(image, **kwargs)
            elif operation == "enhance":
                result = self.enhance_contrast_adaptive(image)
            else:
                result = image
            
            results.append(result)
        
        return results
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._cache_size
        }