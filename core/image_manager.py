import os
import shutil
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt5.QtCore import Qt

class ImageManager:
    """图片管理器，负责处理工具背景图片"""
    
    def __init__(self, config_dir=None, images_dir="images"):
        # 初始化图片目录
        if config_dir is not None:
            # 使用配置目录下的images文件夹
            self.images_dir = os.path.join(config_dir, "images")
        else:
            self.images_dir = images_dir
        
        self.ensure_images_directory()
    
    def ensure_images_directory(self):
        """确保图片目录存在"""
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
    
    def save_image(self, source_path, image_name):
        """保存图片到图片目录
        
        Args:
            source_path: 源图片路径
            image_name: 保存的图片名称（包含扩展名）
            
        Returns:
            保存后的相对路径，如果失败返回None
        """
        try:
            # 生成目标路径
            dest_path = os.path.join(self.images_dir, image_name)
            
            # 复制图片文件
            shutil.copy2(source_path, dest_path)
            
            # 返回相对路径
            return image_name
        except Exception as e:
            print(f"保存图片失败: {e}")
            return None
    
    def delete_image(self, image_name):
        """删除图片
        
        Args:
            image_name: 要删除的图片名称
            
        Returns:
            是否删除成功
        """
        try:
            image_path = os.path.join(self.images_dir, image_name)
            if os.path.exists(image_path):
                os.remove(image_path)
                return True
            return False
        except Exception as e:
            print(f"删除图片失败: {e}")
            return False
    
    def get_image_path(self, image_name):
        """获取图片的完整路径
        
        Args:
            image_name: 图片名称
            
        Returns:
            完整路径，如果图片不存在返回None
        """
        image_path = os.path.join(self.images_dir, image_name)
        if os.path.exists(image_path):
            return image_path
        return None
    
    def list_images(self):
        """列出所有可用的图片
        
        Returns:
            图片名称列表
        """
        try:
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
            images = []
            
            for file in os.listdir(self.images_dir):
                ext = os.path.splitext(file)[1].lower()
                if ext in image_extensions:
                    images.append(file)
            
            return images
        except Exception as e:
            print(f"列出图片失败: {e}")
            return []
    
    def create_thumbnail(self, image_name, size=(100, 100)):
        """创建图片缩略图
        
        Args:
            image_name: 原始图片名称
            size: 缩略图大小
            
        Returns:
            QPixmap对象，如果失败返回None
        """
        try:
            image_path = self.get_image_path(image_name)
            if not image_path:
                return None
            
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return None
            
            return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            print(f"创建缩略图失败: {e}")
            return None
    
    def create_default_backgrounds(self):
        """创建默认的背景图片
        
        Returns:
            创建的背景图片名称列表
        """
        created_images = []
        
        # 创建一些默认背景图片
        background_colors = [
            ("background1.png", QColor(66, 133, 244)),  # Google蓝
            ("background2.png", QColor(234, 67, 53)),   # Google红
            ("background3.png", QColor(52, 168, 83)),   # Google绿
            ("background4.png", QColor(251, 188, 5)),   # Google黄
            ("background5.png", QColor(156, 39, 176)),  # 紫色
        ]
        
        for image_name, color in background_colors:
            image_path = os.path.join(self.images_dir, image_name)
            if not os.path.exists(image_path):
                # 创建200x150的纯色背景图片
                image = QImage(200, 150, QImage.Format_RGB32)
                painter = QPainter(image)
                painter.fillRect(image.rect(), color)
                
                # 添加半透明的网格效果
                grid_color = QColor(255, 255, 255, 50)
                painter.setPen(grid_color)
                
                # 绘制水平线
                for y in range(0, 150, 20):
                    painter.drawLine(0, y, 200, y)
                
                # 绘制垂直线
                for x in range(0, 200, 20):
                    painter.drawLine(x, 0, x, 150)
                
                painter.end()
                
                if image.save(image_path):
                    created_images.append(image_name)
        
        return created_images
    
    def validate_image(self, image_path):
        """验证图片是否有效
        
        Args:
            image_path: 图片路径
            
        Returns:
            是否有效
        """
        try:
            pixmap = QPixmap(image_path)
            return not pixmap.isNull()
        except:
            return False
    
    def resize_image(self, image_name, new_width, new_height):
        """调整图片大小
        
        Args:
            image_name: 图片名称
            new_width: 新宽度
            new_height: 新高度
            
        Returns:
            是否成功
        """
        try:
            image_path = self.get_image_path(image_name)
            if not image_path:
                return False
            
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return False
            
            resized_pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return resized_pixmap.save(image_path)
        except Exception as e:
            print(f"调整图片大小失败: {e}")
            return False

