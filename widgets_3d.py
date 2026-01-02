from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtCore import Qt, QPointF
import math
from config import THEME

class Viewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        self.cam_pitch = 30
        self.cam_yaw = 45
        self.scale = 0.8
        self.drag_start = None
        self.bg_color = QColor(THEME["bg_ui"])
        self.transparency_mode = False

    def set_scene(self, manager):
        self.manager = manager
        self.update()
        
    def set_transparency(self, enabled):
        self.transparency_mode = enabled
        self.update()

    def update_angles(self, angles):
        if self.manager: self.manager.set_angles(angles)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        
        if not self.manager: return
        
        w, h = self.width(), self.height()
        rad_p = math.radians(self.cam_pitch)
        rad_y = math.radians(self.cam_yaw)
        cp, sp = math.cos(rad_p), math.sin(rad_p)
        cy, sy = math.cos(rad_y), math.sin(rad_y)
        
        def world_to_view(v):
            x, y, z = v
            rx = x*cy - z*sy
            rz = x*sy + z*cy
            return (rx, y*cp - rz*sp, y*sp + rz*cp)

        faces = self.manager.get_3d_faces()
        render_list = []
        
        for face in faces:
            verts = face['verts']
            v_view = [world_to_view(v) for v in verts]
            z_cent = sum(v[2] for v in v_view) / len(v_view) if v_view else 0
            
            cname = face.get('col', 'cardboard')
            if cname == 'cardboard': col = QColor(THEME["cardboard"])
            elif cname == 'white': col = QColor(THEME["white_opaque"])
            elif cname == 'dark': col = QColor(THEME["cardboard"]).darker(130)
            else: col = QColor(THEME["cardboard"])
            
            if face['type'] == 'side': col = col.darker(120)
            render_list.append((z_cent, v_view, col))
            
        render_list.sort(key=lambda x: x[0]) 

        for _, verts, col in render_list:
            pts = []
            for vx, vy, vz in verts:
                dist = 2000
                if dist + vz <= 10: continue
                f = dist / (dist + vz)
                pts.append(QPointF(vx*f*self.scale + w/2, -vy*f*self.scale + h/2))
            
            if len(pts) < 3: continue
            
            if self.transparency_mode:
                col.setAlpha(150)
                painter.setPen(QPen(Qt.black, 0.5))
            else:
                col.setAlpha(255)
                painter.setPen(QPen(col.darker(120), 0.5))
            
            painter.setBrush(col)
            painter.drawPolygon(QPolygonF(pts))

    def mousePressEvent(self, e): self.drag_start = e.position().toPoint()
    def mouseReleaseEvent(self, e): self.drag_start = None
    def mouseMoveEvent(self, e):
        if self.drag_start:
            delta = e.position().toPoint() - self.drag_start
            self.cam_yaw -= delta.x() * 0.5
            self.cam_pitch -= delta.y() * 0.5
            self.drag_start = e.position().toPoint()
            self.update()
    def wheelEvent(self, e):
        self.scale *= 1.1 if e.angleDelta().y() > 0 else 0.9
        self.update()