from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtCore import Qt, QPointF
from config import THEME

class DrawingArea2D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.model_data = ([], [], []) 
        self.params_L = 100
        self.params_W = 100
        self.params_HF = 10
        self.params_HT = 10
        self.params_F = 10
        self.bg_color = QColor(THEME["canvas_bg"])
    
    def set_data(self, polys, cuts, creases, L, W, h_f, h_t, F):
        self.model_data = (polys, cuts, creases)
        self.params_L = L
        self.params_W = W
        self.params_HF = h_f
        self.params_HT = h_t
        self.params_F = F
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        cw, ch = self.width(), self.height()
        if cw < 50: return

        polygons, cut_lines, crease_lines = self.model_data
        
        tot_w = self.params_L + self.params_HT*2 + 300
        tot_h = self.params_W + self.params_HF*2 + self.params_F*2 + 200
        if tot_w == 0: tot_w = 1
        if tot_h == 0: tot_h = 1

        scale = min(cw/tot_w, ch/tot_h) * 0.8
        ox_model = max(self.params_HT, self.params_HF) + 100
        oy_model = max(self.params_HT, self.params_HF) + self.params_F + 50
        dx = (cw/2) - (ox_model + self.params_L/2)*scale
        dy = (ch/2) - (oy_model + self.params_W/2)*scale

        for p in polygons:
            pts = [QPointF(x*scale+dx, y*scale+dy) for x, y in p['coords']]
            qpoly = QPolygonF(pts)
            painter.setBrush(QColor(THEME["cardboard"]))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(qpoly)

        crease_pen = QPen(QColor(THEME["line_crease"]))
        crease_pen.setWidthF(1.5)
        crease_pen.setStyle(Qt.CustomDashLine) 
        crease_pen.setDashPattern([2, 3]) 
        painter.setPen(crease_pen)
        for line in crease_lines:
            pts = [QPointF(pt[0]*scale+dx, pt[1]*scale+dy) for pt in line]
            if len(pts) >= 2: painter.drawPolyline(pts)

        cut_pen = QPen(QColor(THEME["line_cut"]))
        cut_pen.setWidthF(2.0)
        cut_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(cut_pen)
        for line in cut_lines:
             pts = [QPointF(pt[0]*scale+dx, pt[1]*scale+dy) for pt in line]
             if len(pts) >= 2: painter.drawPolyline(pts)