from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtCore import Qt, QPointF
import math
from config import THEME
from geometry_3d import Scene3D

class Viewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = Scene3D()
        self.cam_pitch = 30
        self.cam_yaw = 45
        self.scale = 1.0
        self.drag_start = None
        self.bg_color = QColor(THEME["bg_ui"])
        self.transparency_mode = False

    def set_params(self, p):
        self.scene.build_box(p)
        self.update()
        
    def set_transparency(self, enabled):
        self.transparency_mode = enabled
        self.update()

    def update_angles(self, angles):
        for p in self.scene.parts:
            if "Fianco" in p.name:
                p.angle = angles.get('fianchi', 0) * p.fold_sign
            elif "Testata" in p.name:
                p.angle = angles.get('testate', 0) * p.fold_sign
            elif "Lembo" in p.name:
                p.angle = angles.get('lembi', 0) * p.fold_sign
            elif "Fascia" in p.name:
                p.angle = angles.get('fasce', 0) * p.fold_sign
            elif "PFlap" in p.name:
                p.angle = angles.get('ext', 0) * p.fold_sign
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        w, h = self.width(), self.height()
        rad_p = math.radians(self.cam_pitch)
        rad_y = math.radians(self.cam_yaw)
        cp, sp = math.cos(rad_p), math.sin(rad_p)
        cy, sy = math.cos(rad_y), math.sin(rad_y)
        
        def world_to_view(v):
            x, y, z = v
            rx = x*cy - y*sy
            ry = x*sy + y*cy
            y_view = ry*cp - z*sp
            z_view = ry*sp + z*cp
            return (rx, y_view, z_view)

        world_polys = self.scene.get_world_polygons()
        render_list = []
        for verts, name in world_polys:
            view_verts = [world_to_view(v) for v in verts]
            if view_verts:
                # Ordinamento stabile per media Z
                z_sort_key = sum(v[2] for v in view_verts) / len(view_verts)
            else:
                z_sort_key = 0
            
            is_flap = ("Lembo" in name or "PFlap" in name or "Fascia" in name)
            
            # Bias per evitare sfarfallio sui lembi interni che sono molto vicini
            if is_flap:
                z_sort_key += 2000.0 

            render_list.append((z_sort_key, view_verts, is_flap))
            
        render_list.sort(key=lambda x: x[0], reverse=True)
        
        for z_depth, v_verts, is_flap in render_list:
            pts_2d = []
            for vx, vy, vz in v_verts:
                factor = 1000 / (1000 + vz) if (1000 + vz) != 0 else 1
                sx = vx * factor * self.scale + w/2
                sy = -vy * factor * self.scale + h/2
                pts_2d.append(QPointF(sx, sy))
            
            area = 0.0
            for i in range(len(pts_2d)):
                p1 = pts_2d[i]
                p2 = pts_2d[(i+1) % len(pts_2d)]
                area += (p2.x() - p1.x()) * (p2.y() + p1.y())
            is_front = area < 0 
            
            if is_front:
                base_c = THEME["brown_alpha"] if self.transparency_mode else THEME["brown_opaque"]
            else:
                base_c = THEME["white_alpha"] if self.transparency_mode else THEME["white_opaque"]
            
            shade = max(0, min(40, int(z_depth * 0.1 + 10)))
            r, g, b, a = base_c.red(), base_c.green(), base_c.blue(), base_c.alpha()
            final_c = QColor(max(0, r - shade), max(0, g - shade), max(0, b - shade), a)
            
            painter.setBrush(final_c)
            painter.setPen(QPen(Qt.black, 1.5))
            painter.drawPolygon(QPolygonF(pts_2d))

    def mousePressEvent(self, e):
        self.drag_start = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self.drag_start:
            curr = e.position().toPoint()
            delta = curr - self.drag_start
            self.cam_yaw -= delta.x() * 0.5
            self.cam_pitch -= delta.y() * 0.5
            self.drag_start = curr
            self.update()
            
    def mouseReleaseEvent(self, e):
        self.drag_start = None
        
    def wheelEvent(self, e):
        if e.angleDelta().y() > 0: self.scale *= 1.1
        else: self.scale *= 0.9
        self.update()