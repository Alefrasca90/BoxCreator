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
        self.extra_lines = [] # Linee di debug/sfregamento (Rosse)
        self.glue_lines = []  # Linee colla (Multicolore/Grigie)

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
        
    def set_extra_lines(self, lines):
        """Imposta linee extra da disegnare (sfregamento, rosso)"""
        self.extra_lines = lines
        self.update()

    def set_glue_lines(self, lines):
        """Imposta linee colla da disegnare.
           Formato: lista di (p1, p2, color_tuple, normal_vector)
        """
        self.glue_lines = lines
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
        glEnable(GL_LIGHT0) 
        glEnable(GL_LIGHT1) 
        
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.75, 0.75, 0.75, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0]) 
        
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.55, 0.55, 0.60, 1.0])
        glLightfv(GL_LIGHT1, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])
        
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
        glClearColor(0.25, 0.25, 0.25, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if not self.manager: return
        glLoadIdentity()
        
        glLightfv(GL_LIGHT0, GL_POSITION, [800.0, 1200.0, 1200.0, 1.0]) 
        glLightfv(GL_LIGHT1, GL_POSITION, [-800.0, -500.0, 500.0, 1.0]) 

        glTranslatef(0, 0, -self.camera_dist * (1.0/self.scale))
        glRotatef(self.cam_pitch - 90, 1, 0, 0)
        glRotatef(self.cam_yaw, 0, 0, 1)

        # --- FUNZIONI DI DISEGNO LOCALI ---
        def draw_faces():
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

        def draw_glue():
            if not self.glue_lines: return
            
            glEnable(GL_LIGHTING)
            glEnable(GL_COLOR_MATERIAL)
            
            for item in self.glue_lines:
                if len(item) == 4:
                    p1, p2, col, normal = item
                    glColor4f(col[0], col[1], col[2], 1.0)
                    self.draw_glue_dome(p1, p2, normal)
                else:
                    # Fallback
                    p1, p2, col = item
                    glColor4f(col[0], col[1], col[2], 1.0)
                    glBegin(GL_LINES)
                    glVertex3f(p1[0], p1[1], p1[2])
                    glVertex3f(p2[0], p2[1], p2[2])
                    glEnd()

        # --- LOGICA DI DISEGNO BASATA SULLA TRASPARENZA ---
        if self.transparency_mode:
            # 1. Disegna PRIMA la colla (opaca, scrive nel Depth Buffer)
            draw_glue()
            # 2. Disegna DOPO le facce (trasparenti, blendano sopra la colla)
            # Nota: Manteniamo DepthMask TRUE per avere l'occlusione corretta tra le facce stesse (frontale copre posteriore)
            draw_faces()
        else:
            # Modalità Opaca Standard: Prima le facce (occludono l'interno), poi la colla (se visibile)
            draw_faces()
            draw_glue()

        # --- DISEGNO LINEE EXTRA (Es. Sfregamento Gessetto) ---
        # NASCOSTO SU RICHIESTA UTENTE
        # if self.extra_lines:
        #     glDisable(GL_LIGHTING)
        #     glLineWidth(2.5)
        #     glColor4f(1.0, 0.2, 0.2, 1.0) # Rosso Gessetto
        #     glBegin(GL_LINES)
        #     for p1, p2 in self.extra_lines:
        #         glVertex3f(p1[0], p1[1], p1[2])
        #         glVertex3f(p2[0], p2[1], p2[2])
        #     glEnd()
        #     glEnable(GL_LIGHTING)

    def draw_glue_dome(self, p1, p2, normal):
        """
        Disegna un semicilindro (cupola) lungo il vettore p2-p1.
        Larghezza = 3mm (R=1.5), Altezza = 2mm (R=2.0).
        Orientato lungo la normale della superficie.
        """
        # 1. Calcola il vettore tangente T = P2 - P1
        tx, ty, tz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
        
        # 2. Calcola il vettore binormale B (perpendicolare a T e N) -> asse della larghezza
        nx, ny, nz = normal
        bx = ty*nz - tz*ny
        by = tz*nx - tx*nz
        bz = tx*ny - ty*nx
        
        # Normalizza B
        l_b = math.sqrt(bx*bx + by*by + bz*bz)
        if l_b > 0:
            bx, by, bz = bx/l_b, by/l_b, bz/l_b
        else:
            return 

        # Dimensioni
        R_width = 1.5  # Larghezza 3mm -> raggio 1.5
        R_height = 2.0 # Altezza 2mm
        
        steps = 12
        glBegin(GL_TRIANGLE_STRIP)
        
        for i in range(steps + 1):
            theta = math.pi * i / steps
            c = math.cos(theta) 
            s = math.sin(theta) 
            
            off_x = bx * (R_width * c) + nx * (R_height * s)
            off_y = by * (R_width * c) + ny * (R_height * s)
            off_z = bz * (R_width * c) + nz * (R_height * s)
            
            l_off = math.sqrt(off_x*off_x + off_y*off_y + off_z*off_z)
            if l_off > 0:
                norm_v = (off_x/l_off, off_y/l_off, off_z/l_off)
            else:
                norm_v = (0, 0, 1)
            
            glNormal3f(norm_v[0], norm_v[1], norm_v[2])
            glVertex3f(p1[0] + off_x, p1[1] + off_y, p1[2] + off_z)
            glVertex3f(p2[0] + off_x, p2[1] + off_y, p2[2] + off_z)
            
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