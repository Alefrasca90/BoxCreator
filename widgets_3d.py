from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QPoint
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
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glLightfv(GL_LIGHT0, GL_POSITION, [500, 500, 1000, 1])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.7, 0.7, 0.7, 1.0])

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

    def paintGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if not self.manager: return
        glLoadIdentity()
        glTranslatef(0, 0, -self.camera_dist * (1.0/self.scale))
        glRotatef(self.cam_pitch - 90, 1, 0, 0)
        glRotatef(self.cam_yaw, 0, 0, 1)

        faces = self.manager.get_3d_faces()
        
        glEnable(GL_POLYGON_OFFSET_FILL)
        
        for face in faces:
            is_reinf = "Reinf" in face.get('name', '')
            # Selezione colori
            c_type = face.get('col', 'cardboard')
            
            if c_type == 'white': 
                col = THEME["gl_white"] # Hinge Skin
            elif c_type == 'cardboard': 
                col = THEME["gl_brown"]
            else: 
                col = THEME["gl_white"] # Fallback

            if face['type'] == 'side': col = THEME["gl_brown_dark"]
            
            if is_reinf: glPolygonOffset(-1.0, -1.0)
            else: glPolygonOffset(1.0, 1.0)

            alpha = 0.6 if self.transparency_mode else 1.0
            glColor4f(col[0], col[1], col[2], alpha)
            
            # Rendering: Tessellator per facce grandi, Polygon per strisce piccole
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
        
        glDisable(GL_POLYGON_OFFSET_FILL)

        # Rendering Bordi Tecnici
        glDisable(GL_LIGHTING)
        glLineWidth(1.5)
        glColor4f(0, 0, 0, 1.0)
        glEnable(GL_POLYGON_OFFSET_LINE)
        glPolygonOffset(-2.0, -2.0)

        for face in faces:
            # Le facce 'hinge' non hanno bisogno di outline pesante, le saltiamo o le facciamo sottili
            if face['type'] == 'hinge': continue

            glBegin(GL_LINE_LOOP)
            for v in face['verts']: glVertex3f(v[0], v[1], v[2])
            glEnd()
            
        glDisable(GL_POLYGON_OFFSET_LINE)
        glEnable(GL_LIGHTING)

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