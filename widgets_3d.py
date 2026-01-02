from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF, QBrush, QLinearGradient
from PySide6.QtCore import Qt, QPointF
import math
from config import THEME

class Viewer3D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        
        # Angoli Camera iniziali
        self.cam_pitch = 45 
        self.cam_yaw = 45   
        self.scale = 1.2 
        self.drag_start = None
        self.bg_color = QColor(THEME["bg_ui"])
        self.transparency_mode = False
        
        # Parametri Rendering
        self.camera_dist = 1200  # Focale naturale
        
        # Luce direzionale
        self.ambient_light = 0.4
        self.diffuse_light = 0.6

    def normalize_vec(self, v):
        l = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
        if l == 0: return (0,0,0)
        return (v[0]/l, v[1]/l, v[2]/l)

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
        
        # Sfondo
        painter.fillRect(self.rect(), self.bg_color)
        
        if not self.manager: return
        
        w, h = self.width(), self.height()
        
        # --- 1. MATRICE CAMERA (Rotazione Z-UP) ---
        rad_y = math.radians(self.cam_yaw)
        cy, sy = math.cos(rad_y), math.sin(rad_y)
        
        rad_p = math.radians(self.cam_pitch)
        cp, sp = math.cos(rad_p), math.sin(rad_p)
        
        # Funzione World -> Camera View
        def world_to_view(v):
            x, y, z = v
            # Yaw (attorno Z)
            x1 = x*cy - y*sy
            y1 = x*sy + y*cy
            z1 = z
            # Pitch (Tilt attorno X locale)
            # Asse Y entra nello schermo (Profondità)
            y2 = y1*cp - z1*sp
            z2 = y1*sp + z1*cp
            return (x1, y2, z2) # X_view, Depth_view, Y_view(invertita)

        faces = self.manager.get_3d_faces()
        render_list = []
        
        # --- 2. ELABORAZIONE FACCE ---
        for face in faces:
            verts = face['verts']
            v_view = [world_to_view(v) for v in verts]
            
            if len(v_view) < 3: continue
            
            # Centroide Z (profondità Y nella nostra vista) per ordinamento base
            depth_cent = sum(v[1] for v in v_view) / len(v_view)
            
            # --- 3. NORMALE E CULLING (LA SOLUZIONE) ---
            p0, p1, p2 = v_view[0], v_view[1], v_view[2]
            
            # Vettori lati nello spazio vista
            ux, uy, uz = p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]
            vx, vy, vz = p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]
            
            # Cross Product per la normale (Nx, Ny, Nz)
            # Sistema: X destra, Y dentro schermo, Z alto
            nx = uy*vz - uz*vy
            ny = uz*vx - ux*vz
            nz = ux*vy - uy*vx
            
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            if length == 0: continue
            normal = (nx/length, ny/length, nz/length)
            
            # --- BACK-FACE CULLING ---
            # Se non siamo in modalità trasparenza, controlliamo dove punta la faccia.
            # Nel nostro sistema vista, Y positivo va DENTRO lo schermo (lontano).
            # Se la normale Y è positiva (> 0), la faccia punta via da noi. Non disegnarla.
            if not self.transparency_mode and normal[1] > 0:
                continue
            # --------------------------

            # --- 4. CALCOLO LUCE ---
            # Luce "Top-Left" standard da studio fissa rispetto alla camera
            light_dir = self.normalize_vec((-0.5, -0.5, 1.0)) 
            
            # Dot Product Normal * Light
            dot = normal[0]*light_dir[0] + normal[1]*light_dir[1] + normal[2]*light_dir[2]
            
            # Intensità finale
            intensity = self.ambient_light + self.diffuse_light * max(0, dot)
            intensity = min(1.0, max(0.2, intensity))
            
            # Colore Base
            cname = face.get('col', 'cardboard')
            if self.transparency_mode:
                base_col = THEME["brown_alpha"] if cname == 'cardboard' else THEME["white_alpha"]
            else:
                if cname == 'cardboard': base_col = THEME["brown_opaque"]
                elif cname == 'white': base_col = THEME["white_opaque"]
                else: base_col = THEME["brown_opaque"]
                
            # Scurisci i lati per contrasto
            if face['type'] == 'side': intensity *= 0.8
            
            # Applica luce
            r, g, b, a = base_col.red(), base_col.green(), base_col.blue(), base_col.alpha()
            final_color = QColor(int(r * intensity), int(g * intensity), int(b * intensity), a)
            
            render_list.append((depth_cent, v_view, final_color))
            
        # Ordina: dal più lontano (Y grande) al più vicino
        render_list.sort(key=lambda x: x[0], reverse=True) 

        # --- 5. PROIEZIONE E DISEGNO ---
        center_x, center_y = w/2, h/2
        
        for _, verts, color in render_list:
            pts_2d = []
            
            for vx, vy, vz in verts:
                # Proiezione Prospettica
                dist_z = self.camera_dist + vy # vy è la profondità
                
                if dist_z <= 10: continue # Clipping vicino
                
                fov_factor = self.camera_dist / dist_z
                
                # Proietta X e Z (che è la Y dello schermo invertita)
                sx = vx * fov_factor * self.scale + center_x
                sy = -vz * fov_factor * self.scale + center_y 
                
                pts_2d.append(QPointF(sx, sy))
            
            if len(pts_2d) < 3: continue
            
            # Stile disegno
            painter.setBrush(QBrush(color))
            
            if self.transparency_mode:
                painter.setPen(QPen(Qt.black, 0.5))
            else:
                # Bordo tono su tono per realismo
                edge_col = color.darker(150) 
                pen = QPen(edge_col, 0.7)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)
            
            painter.drawPolygon(QPolygonF(pts_2d))

    # --- CONTROLLI MOUSE ---
    def mousePressEvent(self, e):
        self.drag_start = e.position().toPoint()

    def mouseReleaseEvent(self, e):
        self.drag_start = None

    def mouseMoveEvent(self, e):
        if self.drag_start:
            delta = e.position().toPoint() - self.drag_start
            self.cam_yaw -= delta.x() * 0.5
            self.cam_pitch -= delta.y() * 0.5
            self.drag_start = e.position().toPoint()
            self.update()
            
    def wheelEvent(self, e):
        if e.angleDelta().y() > 0: self.scale *= 1.1
        else: self.scale *= 0.9
        self.update()