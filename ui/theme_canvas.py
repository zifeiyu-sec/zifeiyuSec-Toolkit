from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
    QPixmap,
)
from PyQt5.QtWidgets import QWidget


class ThemedWindowCanvas(QWidget):
    """Window canvas that can paint theme-specific atmospheric backgrounds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_name = "dark_green"
        self._dark_green_background_path = self._resolve_dark_green_background_path()
        self._celadon_background_path = self._resolve_celadon_background_path()
        self._blue_white_background_path = self._resolve_blue_white_background_path()
        self._dark_green_background_pixmap = QPixmap()
        self._celadon_background_pixmap = QPixmap()
        self._blue_white_background_pixmap = QPixmap()
        self._image_background_paths = {
            "purple_neon": self._resolve_named_background_path("\u7d2b\u91d1.png"),
            "red_orange": self._resolve_named_background_path("\u7ea2\u8272.png"),
        }
        self._image_background_pixmaps = {
            theme_name: QPixmap()
            for theme_name in self._image_background_paths
        }

    def set_theme(self, theme_name):
        self._theme_name = theme_name or "dark_green"
        self.update()

    def paintEvent(self, event):
        if self._theme_name == "dark_green":
            if not self._load_dark_green_background():
                super().paintEvent(event)
                return
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            self._paint_dark_green(painter)
            painter.end()
            return

        if self._theme_name == "blue_white":
            if not self._load_blue_white_background():
                super().paintEvent(event)
                return
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            self._paint_blue_white(painter)
            painter.end()
            return

        if self._theme_name in self._image_background_paths:
            pixmap = self._load_image_background(self._theme_name)
            if pixmap.isNull():
                super().paintEvent(event)
                return
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            self._paint_cover_pixmap(painter, pixmap)
            self._paint_theme_image_tint(painter, self._theme_name)
            painter.end()
            return

        if self._theme_name != "celadon_mist":
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self._paint_celadon_mist(painter)
        painter.end()

    def _resolve_dark_green_background_path(self):
        repo_root = Path(__file__).resolve().parents[1]
        candidates = (
            repo_root / "images" / "background" / "\u9ed1\u5ba2.png",
            repo_root / "images" / "background" / "dark_green.png",
            repo_root / "imges" / "background" / "\u9ed1\u5ba2.png",
            repo_root / "imges" / "background" / "dark_green.png",
        )
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    def _resolve_celadon_background_path(self):
        repo_root = Path(__file__).resolve().parents[1]
        preferred = repo_root / "images" / "background" / "\u56fd\u98ce.png"
        if preferred.exists():
            return preferred
        candidates = (
            repo_root / "images" / "background" / "国风.png",
            repo_root / "imges" / "background" / "国风.png",
        )
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    def _resolve_blue_white_background_path(self):
        repo_root = Path(__file__).resolve().parents[1]
        candidates = (
            repo_root / "images" / "background" / "blue_white.png",
            repo_root / "images" / "background" / "blue_write.png",
            repo_root / "imges" / "background" / "blue_white.png",
            repo_root / "imges" / "background" / "blue_write.png",
        )
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    def _resolve_named_background_path(self, image_name):
        repo_root = Path(__file__).resolve().parents[1]
        candidates = (
            repo_root / "images" / "background" / image_name,
            repo_root / "imges" / "background" / image_name,
        )
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    def _load_celadon_background(self):
        if self._celadon_background_pixmap.isNull() and self._celadon_background_path.exists():
            self._celadon_background_pixmap = QPixmap(str(self._celadon_background_path))
        return not self._celadon_background_pixmap.isNull()

    def _load_blue_white_background(self):
        if self._blue_white_background_pixmap.isNull() and self._blue_white_background_path.exists():
            self._blue_white_background_pixmap = QPixmap(str(self._blue_white_background_path))
        return not self._blue_white_background_pixmap.isNull()

    def _load_image_background(self, theme_name):
        pixmap = self._image_background_pixmaps.get(theme_name)
        path = self._image_background_paths.get(theme_name)
        if pixmap is None or path is None:
            return QPixmap()
        if pixmap.isNull() and path.exists():
            pixmap = QPixmap(str(path))
            self._image_background_pixmaps[theme_name] = pixmap
        return pixmap

    def _load_dark_green_background(self):
        if self._dark_green_background_pixmap.isNull() and self._dark_green_background_path.exists():
            self._dark_green_background_pixmap = QPixmap(str(self._dark_green_background_path))
        return not self._dark_green_background_pixmap.isNull()

    def _paint_dark_green(self, painter):
        self._paint_cover_pixmap(painter, self._dark_green_background_pixmap)
        self._paint_theme_image_tint(painter, "dark_green")

    def _paint_blue_white(self, painter):
        self._paint_cover_pixmap(painter, self._blue_white_background_pixmap)
        self._paint_blue_white_image_glass_tint(painter)

    def _paint_celadon_mist(self, painter):
        if self._load_celadon_background():
            self._paint_cover_pixmap(painter, self._celadon_background_pixmap)
            self._paint_celadon_image_glass_tint(painter)
            return

        width = max(1, self.width())
        height = max(1, self.height())
        sx = width / 1600.0
        sy = height / 900.0

        painter.save()
        painter.scale(sx, sy)
        self._paint_celadon_base(painter)
        self._paint_celadon_mountains(painter)
        self._paint_celadon_lake(painter)
        self._paint_celadon_bamboo(painter)
        self._paint_celadon_border(painter)
        painter.restore()

    def _paint_cover_pixmap(self, painter, pixmap):
        target = QRectF(0, 0, self.width(), self.height())
        if target.width() <= 0 or target.height() <= 0:
            return

        image_width = pixmap.width()
        image_height = pixmap.height()
        if image_width <= 0 or image_height <= 0:
            return

        target_ratio = target.width() / target.height()
        image_ratio = image_width / image_height
        if image_ratio > target_ratio:
            source_height = image_height
            source_width = source_height * target_ratio
            source_x = (image_width - source_width) / 2
            source_y = 0
        else:
            source_width = image_width
            source_height = source_width / target_ratio
            source_x = 0
            source_y = (image_height - source_height) / 2

        painter.drawPixmap(target, pixmap, QRectF(source_x, source_y, source_width, source_height))

    def _paint_celadon_image_glass_tint(self, painter):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        soft_light = QLinearGradient(QPointF(0, 0), QPointF(width, height))
        soft_light.setColorAt(0.00, QColor(255, 255, 255, 42))
        soft_light.setColorAt(0.42, QColor(255, 255, 255, 18))
        soft_light.setColorAt(1.00, QColor(81, 177, 181, 18))
        painter.fillRect(QRectF(0, 0, width, height), soft_light)

        painter.setPen(QPen(QColor(255, 255, 255, 176), 1))
        painter.setBrush(Qt.NoBrush)
        radius = max(16, min(width, height) * 0.032)
        painter.drawRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), radius, radius)
        painter.setPen(QPen(QColor(19, 133, 142, 36), 1))
        painter.drawRoundedRect(QRectF(6.5, 6.5, width - 13, height - 13), max(12, radius - 4), max(12, radius - 4))

    def _paint_blue_white_image_glass_tint(self, painter):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        soft_light = QLinearGradient(QPointF(0, 0), QPointF(width, height))
        soft_light.setColorAt(0.00, QColor(255, 255, 255, 22))
        soft_light.setColorAt(0.44, QColor(255, 255, 255, 10))
        soft_light.setColorAt(1.00, QColor(73, 166, 232, 14))
        painter.fillRect(QRectF(0, 0, width, height), soft_light)

        painter.setPen(QPen(QColor(255, 255, 255, 184), 1))
        painter.setBrush(Qt.NoBrush)
        radius = max(16, min(width, height) * 0.032)
        painter.drawRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), radius, radius)
        painter.setPen(QPen(QColor(80, 171, 224, 42), 1))
        painter.drawRoundedRect(QRectF(6.5, 6.5, width - 13, height - 13), max(12, radius - 4), max(12, radius - 4))

    def _paint_theme_image_tint(self, painter, theme_name):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        theme_tints = {
            "dark_green": (
                QColor(0, 0, 0, 4),
                QColor(0, 255, 65, 8),
                QColor(0, 255, 65, 146),
                QColor(0, 229, 255, 68),
            ),
            "purple_neon": (
                QColor(255, 207, 92, 5),
                QColor(189, 58, 255, 12),
                QColor(255, 232, 147, 136),
                QColor(189, 58, 255, 76),
            ),
            "red_orange": (
                QColor(255, 210, 96, 12),
                QColor(176, 24, 12, 18),
                QColor(255, 232, 147, 168),
                QColor(220, 48, 28, 96),
            ),
        }
        start_tint, end_tint, outer_border, inner_border = theme_tints.get(
            theme_name,
            (QColor(255, 255, 255, 8), QColor(255, 255, 255, 10), QColor(255, 255, 255, 90), QColor(255, 255, 255, 46)),
        )

        soft_light = QLinearGradient(QPointF(0, 0), QPointF(width, height))
        soft_light.setColorAt(0.00, start_tint)
        soft_light.setColorAt(0.48, QColor(start_tint.red(), start_tint.green(), start_tint.blue(), max(0, start_tint.alpha() // 2)))
        soft_light.setColorAt(1.00, end_tint)
        painter.fillRect(QRectF(0, 0, width, height), soft_light)

        painter.setPen(QPen(outer_border, 1))
        painter.setBrush(Qt.NoBrush)
        radius = max(16, min(width, height) * 0.032)
        painter.drawRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), radius, radius)
        painter.setPen(QPen(inner_border, 1))
        painter.drawRoundedRect(QRectF(6.5, 6.5, width - 13, height - 13), max(12, radius - 4), max(12, radius - 4))
        if theme_name == "dark_green":
            red_pen = QPen(QColor(255, 51, 102, 112), 2)
            painter.setPen(red_pen)
            painter.drawLine(QPointF(width - 42, 1.5), QPointF(width - 1.5, 42))
            painter.drawLine(QPointF(width - 58, height - 1.5), QPointF(width - 1.5, height - 58))
            painter.setPen(QPen(QColor(255, 51, 102, 48), 1))
            painter.drawLine(QPointF(20, height - 2.5), QPointF(92, height - 2.5))
            painter.drawLine(QPointF(width - 116, 2.5), QPointF(width - 30, 2.5))
        elif theme_name == "red_orange":
            painter.setPen(QPen(QColor(255, 220, 112, 118), 1))
            painter.drawLine(QPointF(28, 2.5), QPointF(130, 2.5))
            painter.drawLine(QPointF(width - 150, height - 2.5), QPointF(width - 34, height - 2.5))
            painter.setPen(QPen(QColor(190, 24, 12, 92), 1))
            painter.drawLine(QPointF(width - 70, 1.5), QPointF(width - 1.5, 70))
            painter.drawLine(QPointF(1.5, height - 72), QPointF(72, height - 1.5))

    def _paint_celadon_base(self, painter):
        base = QLinearGradient(QPointF(0, 0), QPointF(1600, 900))
        base.setColorAt(0.00, QColor("#fbfffe"))
        base.setColorAt(0.26, QColor("#e9f7f6"))
        base.setColorAt(0.58, QColor("#cbe8e8"))
        base.setColorAt(1.00, QColor("#9ed2d2"))
        painter.fillRect(QRectF(0, 0, 1600, 900), base)

        washes = [
            (QPointF(100, 470), 450, QColor(31, 154, 161, 64), QColor(255, 255, 255, 0)),
            (QPointF(1360, 520), 520, QColor(25, 145, 153, 54), QColor(255, 255, 255, 0)),
            (QPointF(760, 160), 620, QColor(255, 255, 255, 160), QColor(255, 255, 255, 0)),
            (QPointF(820, 820), 760, QColor(74, 184, 188, 38), QColor(255, 255, 255, 0)),
        ]
        for center, radius, inner, outer in washes:
            glow = QRadialGradient(center, radius)
            glow.setColorAt(0.0, inner)
            glow.setColorAt(0.68, QColor(inner.red(), inner.green(), inner.blue(), max(0, inner.alpha() // 3)))
            glow.setColorAt(1.0, outer)
            painter.fillRect(QRectF(0, 0, 1600, 900), glow)

        self._draw_soft_cloud(painter, 1140, 86, 290, 72, 76)
        self._draw_soft_cloud(painter, 1298, 132, 240, 58, 52)
        self._draw_soft_cloud(painter, 360, 94, 330, 76, 50)

    def _paint_celadon_mountains(self, painter):
        painter.setPen(Qt.NoPen)

        left_far = QPainterPath()
        left_far.moveTo(0, 220)
        left_far.cubicTo(58, 150, 142, 132, 226, 170)
        left_far.cubicTo(314, 210, 358, 318, 332, 486)
        left_far.cubicTo(252, 420, 178, 448, 112, 560)
        left_far.cubicTo(66, 638, 28, 728, 0, 842)
        left_far.closeSubpath()
        painter.fillPath(left_far, QColor(31, 139, 148, 54))

        left_near = QPainterPath()
        left_near.moveTo(0, 390)
        left_near.cubicTo(86, 282, 188, 250, 286, 294)
        left_near.cubicTo(382, 338, 436, 466, 440, 660)
        left_near.cubicTo(348, 580, 258, 616, 178, 746)
        left_near.cubicTo(104, 838, 48, 892, 0, 900)
        left_near.closeSubpath()
        painter.fillPath(left_near, QColor(21, 129, 139, 58))

        painter.setPen(QPen(QColor(255, 255, 255, 78), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._ridge_path([(14, 402), (116, 330), (226, 366), (328, 520), (438, 654)]))
        painter.setPen(QPen(QColor(15, 121, 130, 45), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._ridge_path([(18, 604), (132, 522), (248, 558), (348, 698), (448, 824)]))

        right_far = QPainterPath()
        right_far.moveTo(1190, 200)
        right_far.cubicTo(1290, 120, 1402, 118, 1510, 196)
        right_far.cubicTo(1578, 246, 1608, 374, 1600, 560)
        right_far.lineTo(1600, 900)
        right_far.lineTo(1260, 900)
        right_far.cubicTo(1234, 704, 1206, 492, 1190, 200)
        right_far.closeSubpath()
        painter.fillPath(right_far, QColor(36, 145, 153, 42))

        right_near = QPainterPath()
        right_near.moveTo(1300, 356)
        right_near.cubicTo(1398, 286, 1500, 304, 1600, 414)
        right_near.lineTo(1600, 900)
        right_near.lineTo(1398, 900)
        right_near.cubicTo(1354, 704, 1326, 526, 1300, 356)
        right_near.closeSubpath()
        painter.fillPath(right_near, QColor(19, 126, 136, 56))

        painter.setPen(QPen(QColor(255, 255, 255, 92), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._ridge_path([(1176, 268), (1272, 208), (1370, 242), (1466, 360), (1576, 520)]))
        painter.setPen(QPen(QColor(14, 118, 128, 42), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._ridge_path([(1260, 464), (1368, 388), (1480, 446), (1584, 650)]))

        for x, y, rx, ry, alpha in (
            (520, 188, 230, 58, 28),
            (850, 236, 300, 70, 26),
            (1260, 248, 330, 74, 30),
            (1380, 360, 260, 62, 26),
        ):
            self._draw_soft_cloud(painter, x, y, rx, ry, alpha)

    def _paint_celadon_lake(self, painter):
        lake = QPainterPath()
        lake.moveTo(0, 620)
        lake.cubicTo(210, 590, 402, 630, 608, 674)
        lake.cubicTo(842, 724, 1086, 660, 1300, 620)
        lake.cubicTo(1410, 600, 1510, 616, 1600, 646)
        lake.lineTo(1600, 900)
        lake.lineTo(0, 900)
        lake.closeSubpath()

        lake_gradient = QLinearGradient(QPointF(0, 620), QPointF(1600, 900))
        lake_gradient.setColorAt(0.00, QColor(218, 247, 246, 130))
        lake_gradient.setColorAt(0.42, QColor(98, 190, 194, 72))
        lake_gradient.setColorAt(1.00, QColor(232, 252, 251, 118))
        painter.fillPath(lake, lake_gradient)

        waves = [
            ([(0, 664), (170, 646), (350, 700), (520, 688), (720, 622), (950, 610), (1160, 650), (1390, 702), (1608, 662)], QColor(255, 255, 255, 128), 4),
            ([(0, 724), (190, 704), (376, 750), (590, 736), (818, 670), (1050, 664), (1260, 716), (1448, 756), (1608, 724)], QColor(18, 132, 142, 44), 8),
            ([(120, 804), (320, 770), (530, 804), (748, 840), (980, 796), (1200, 754), (1420, 772), (1608, 804)], QColor(255, 255, 255, 112), 4),
            ([(170, 858), (354, 842), (570, 858), (780, 846), (1000, 806), (1260, 806), (1508, 846)], QColor(12, 118, 128, 38), 7),
        ]
        for points, color, width in waves:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(self._ridge_path(points))

        painter.setPen(QPen(QColor(255, 255, 255, 148), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._ridge_path([(1370, 776), (1414, 728), (1480, 728), (1524, 774), (1572, 732), (1624, 744)]))
        painter.setPen(QPen(QColor(18, 132, 142, 48), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._ridge_path([(1318, 812), (1390, 772), (1460, 782), (1526, 830), (1586, 790), (1646, 820)]))

        self._draw_boat(painter, 236, 782, 0.82)
        self._draw_boat(painter, 436, 774, 0.62)
        self._draw_pavilion(painter, 32, 736, 0.76)

    def _paint_celadon_bamboo(self, painter):
        painter.save()
        painter.translate(1374, 24)
        painter.rotate(-10)
        painter.setPen(QPen(QColor(14, 101, 108, 66), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(QPointF(132, -40), QPointF(216, 318))
        painter.drawLine(QPointF(206, -48), QPointF(314, 290))
        painter.drawLine(QPointF(284, -60), QPointF(420, 246))
        painter.setPen(Qt.NoPen)
        for x, y, scale, angle in (
            (28, 18, 1.00, 8),
            (126, 68, 0.98, -4),
            (226, 16, 0.94, 6),
            (318, 88, 0.90, -8),
            (394, 24, 0.82, 4),
            (472, 112, 0.72, -6),
        ):
            self._draw_leaf(painter, x, y, scale, angle)
        painter.restore()

        painter.save()
        painter.translate(18, 452)
        painter.rotate(-20)
        painter.setPen(Qt.NoPen)
        for x, y, scale, angle in ((0, 32, 0.72, 8), (58, 100, 0.66, -6), (22, 168, 0.58, 10)):
            self._draw_leaf(painter, x, y, scale, angle, QColor(14, 122, 130, 82))
        painter.restore()

    def _paint_celadon_border(self, painter):
        painter.setPen(QPen(QColor(255, 255, 255, 178), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(1, 1, 1598, 898), 28, 28)
        painter.setPen(QPen(QColor(17, 128, 138, 34), 1))
        painter.drawRoundedRect(QRectF(6, 6, 1588, 888), 24, 24)

    def _draw_leaf(self, painter, x, y, scale, angle, color=None):
        painter.save()
        painter.translate(x, y)
        painter.rotate(angle)
        painter.scale(scale, scale)
        path = QPainterPath()
        path.moveTo(0, 20)
        path.cubicTo(54, -10, 118, -2, 186, 50)
        path.cubicTo(128, 54, 66, 46, 0, 20)
        painter.fillPath(path, color or QColor(8, 114, 122, 96))
        painter.setPen(QPen(QColor(255, 255, 255, 36), 1))
        painter.drawPath(path)
        painter.restore()

    def _draw_boat(self, painter, x, y, scale):
        painter.save()
        painter.translate(x, y)
        painter.scale(scale, scale)
        painter.setPen(QPen(QColor(255, 255, 255, 118), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QColor(10, 101, 110, 104))
        hull = QPainterPath()
        hull.moveTo(-78, 18)
        hull.cubicTo(-34, 40, 40, 40, 90, 18)
        hull.cubicTo(42, 4, -26, 2, -78, 18)
        painter.drawPath(hull)
        painter.fillPath(hull, QColor(10, 101, 110, 104))
        painter.setBrush(QColor(12, 118, 128, 94))
        roof = QPolygonF([QPointF(-20, -16), QPointF(24, -16), QPointF(8, -44), QPointF(-8, -44)])
        painter.drawPolygon(roof)
        painter.drawLine(QPointF(0, -44), QPointF(0, -78))
        painter.drawLine(QPointF(0, -78), QPointF(26, -46))
        painter.setPen(QPen(QColor(10, 101, 110, 52), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(-112, 34), QPointF(130, 30))
        painter.restore()

    def _draw_pavilion(self, painter, x, y, scale):
        painter.save()
        painter.translate(x, y)
        painter.scale(scale, scale)
        painter.setPen(QPen(QColor(255, 255, 255, 112), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QColor(8, 100, 110, 96))
        painter.drawRect(QRectF(0, 58, 84, 18))
        painter.drawRect(QRectF(16, 14, 52, 44))
        roof = QPolygonF([QPointF(-8, 14), QPointF(42, -20), QPointF(94, 14)])
        painter.drawPolygon(roof)
        painter.drawLine(QPointF(28, 14), QPointF(28, 58))
        painter.drawLine(QPointF(56, 14), QPointF(56, 58))
        painter.restore()

    def _draw_soft_cloud(self, painter, x, y, rx, ry, alpha):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, alpha))
        painter.drawEllipse(QRectF(x - rx, y - ry, rx * 2, ry * 2))
        painter.setBrush(QColor(48, 151, 158, max(0, alpha // 4)))
        painter.drawEllipse(QRectF(x - rx * 0.72, y - ry * 0.52, rx * 1.46, ry * 1.05))

    def _ridge_path(self, points):
        path = QPainterPath(QPointF(points[0][0], points[0][1]))
        for index in range(1, len(points) - 1):
            current = QPointF(points[index][0], points[index][1])
            next_point = QPointF(points[index + 1][0], points[index + 1][1])
            mid = QPointF((current.x() + next_point.x()) / 2, (current.y() + next_point.y()) / 2)
            path.quadTo(current, mid)
        path.lineTo(QPointF(points[-1][0], points[-1][1]))
        return path
