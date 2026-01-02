from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtCore import Qt, QPointF
from config import THEME

class DrawingArea2D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_color = QColor(THEME["bg_draw"]) # Ora esiste
        self.polygons = []
        self.cut_lines = []
        self.crease_lines = []
        self.L = 100
        self.W = 100

    def set_data(self, polygons, cut_lines, crease_lines, L, W, h_f, h_t, F):
        self.polygons = polygons
        self.cut_lines = cut_lines
        self.crease_lines = crease_lines
        self.L = L
        self.W = W
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        
        all_coords = []
        for p in self.polygons: all_coords.extend(p['coords'])
        if not all_coords: return

        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        w_bb, h_bb = max_x - min_x, max_y - min_y
        scale = min((self.width()-60)/w_bb, (self.height()-60)/h_bb) if w_bb>0 else 1
        cx, cy = (min_x+max_x)/2, (min_y+max_y)/2
        
        def to_s(x, y):
            return QPointF((x-cx)*scale + self.width()/2, (y-cy)*scale + self.height()/2)

        # Poligoni
        for p in self.polygons:
            pts = [to_s(x,y) for x,y in p['coords']]
            col = QColor(THEME["cardboard"])
            if p['type'] == 'fondo': col = col.darker(110)
            elif p['type'] == 'lembi': col = col.lighter(110)
            painter.setBrush(col)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(QPolygonF(pts))

        # Linee
        painter.setPen(QPen(QColor(THEME["line_cut"]), 2))
        for p1, p2 in self.cut_lines:
            painter.drawLine(to_s(*p1), to_s(*p2))
            
        pen_cr = QPen(QColor(THEME["line_crease"]), 2)
        pen_cr.setStyle(Qt.DashLine)
        painter.setPen(pen_cr)
        for p1, p2 in self.crease_lines:
            painter.drawLine(to_s(*p1), to_s(*p2))