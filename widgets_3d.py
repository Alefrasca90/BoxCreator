from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QSurfaceFormat
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from config import THEME

class Viewer3D(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        self.cam_pitch = 45 
        self.cam_yaw = 45   
        self.scale = 1.8  
        self.drag_start = None
        self.transparency_mode = False
        self.camera_dist = 1400 

        # Antialiasing attivo per bordi lisci
        fmt = QSurfaceFormat()
        fmt.setSamples(16)
        self.setFormat(fmt)

    def set_scene(self, manager):
        self.manager = manager
        self.update()

    def set_transparency(self, enabled):
        self.transparency_mode = enabled
        self.update()

    def update_angles(self, angles):
        if self.manager: self.manager.set_angles(angles)
        self.update()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        
        glEnable(GL_MULTISAMPLE) 
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_NORMALIZE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # --- SETUP LUCI BILANCIATO ---
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0) # Key Light
        glEnable(GL_LIGHT1) # Fill Light
        
        # 1. LUCE PRINCIPALE (SOLE): Ridotta intensità
        # Prima era quasi 1.0 (troppo forte). Ora è 0.75 per evitare bianchi bruciati.
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.75, 0.75, 0.75, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0]) 
        
        # 2. LUCE DI RIEMPIMENTO: Aumentata intensità
        # Serve a schiarire le parti in ombra. Da 0.3 a 0.55.
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.55, 0.55, 0.60, 1.0])
        glLightfv(GL_LIGHT1, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])
        
        # 3. LUCE AMBIENTALE: Molto più alta
        # Garantisce che il marrone resti marrone e non diventi nero.
        # Da 0.4 a 0.65.
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.65, 0.65, 0.65, 1.0])
        
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        self.tess = gluNewTess()
        gluTessCallback(self.tess, GLU_TESS_BEGIN, glBegin)
        gluTessCallback(self.tess, GLU_TESS_VERTEX, glVertex3dv)
        gluTessCallback(self.tess, GLU_TESS_END, glEnd)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h if h > 0 else 1, 10, 8000)
        glMatrixMode(GL_MODELVIEW)

    def calc_normal(self, verts):
        if len(verts) < 3: return (0, 0, 1)
        p0, p1, p2 = verts[0], verts[1], verts[2]
        nx = (p1[1]-p0[1])*(p2[2]-p0[2]) - (p1[2]-p0[2])*(p2[1]-p0[1])
        ny = (p1[2]-p0[2])*(p2[0]-p0[0]) - (p1[0]-p0[0])*(p2[2]-p0[2])
        nz = (p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0])
        l = math.sqrt(nx*nx + ny*ny + nz*nz)
        if l == 0: return (0, 0, 1)
        return (nx/l, ny/l, nz/l)

    def paintGL(self):
        # Sfondo grigio leggermente più chiaro per ridurre il contrasto visivo
        glClearColor(0.25, 0.25, 0.25, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if not self.manager: return
        glLoadIdentity()
        
        # Luci Fisse
        glLightfv(GL_LIGHT0, GL_POSITION, [800.0, 1200.0, 1200.0, 1.0]) 
        glLightfv(GL_LIGHT1, GL_POSITION, [-800.0, -500.0, 500.0, 1.0]) 

        glTranslatef(0, 0, -self.camera_dist * (1.0/self.scale))
        glRotatef(self.cam_pitch - 90, 1, 0, 0)
        glRotatef(self.cam_yaw, 0, 0, 1)

        faces = self.manager.get_3d_faces()
        
        for face in faces:
            c_type = face.get('col', 'cardboard')
            
            if c_type == 'white': 
                col = THEME["gl_white"]
            elif c_type == 'cardboard': 
                col = THEME["gl_brown"]
            else: 
                col = THEME["gl_white"]

            if face['type'] == 'side': col = THEME["gl_brown_dark"]
            
            alpha = 0.55 if self.transparency_mode else 1.0
            glColor4f(col[0], col[1], col[2], alpha)
            
            nx, ny, nz = self.calc_normal(face['verts'])
            glNormal3f(nx, ny, nz)
            
            if face['type'] in ['front', 'back']:
                gluTessBeginPolygon(self.tess, None)
                gluTessBeginContour(self.tess)
                for v in face['verts']: gluTessVertex(self.tess, v, v)
                gluTessEndContour(self.tess)
                gluTessEndPolygon(self.tess)
            else:
                glBegin(GL_POLYGON)
                for v in face['verts']: glVertex3f(v[0], v[1], v[2])
                glEnd()

    def mousePressEvent(self, e): self.drag_start = e.position().toPoint()
    def mouseMoveEvent(self, e):
        if self.drag_start:
            delta = e.position().toPoint() - self.drag_start
            self.cam_yaw += delta.x() * 0.5
            self.cam_pitch += delta.y() * 0.5
            self.drag_start = e.position().toPoint()
            self.update()
    def wheelEvent(self, e):
        if e.angleDelta().y() > 0: self.scale *= 1.1
        else: self.scale *= 0.9
        self.update()