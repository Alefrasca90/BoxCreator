import sys
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QScrollArea, QPushButton, QLabel, 
                               QLineEdit, QFrame, QCheckBox, QSizePolicy)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF, QFont

# --- CONFIGURAZIONE COLORI (LOOK & FEEL) ---
THEME = {
    "bg_ui": "#2E2E2E",
    "bg_panel": "#3C3F41",
    "fg_text": "#F0F0F0",
    "canvas_bg": "#F5F5F5",
    "cardboard": "#E0C0A0",     # Colore unico per tutto il cartone
    "highlight": "#81D4FA",
    "line_cut": "#000000",
    "line_crease": "#00C853"
}

# ==========================================
# 1. WIDGET UTILS (Interfaccia)
# ==========================================
class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None, expanded=False):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.btn_toggle = QPushButton(f"▼ {title}" if expanded else f"▶ {title}")
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['bg_panel']};
                color: {THEME['fg_text']};
                text-align: left;
                padding: 5px;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {THEME['bg_ui']}; }}
        """)
        self.btn_toggle.clicked.connect(self.toggle)
        self.layout.addWidget(self.btn_toggle)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(self.content_area)

        self.expanded = expanded
        self.content_area.setVisible(expanded)
        self.title_text = title

    def toggle(self):
        self.expanded = not self.expanded
        self.btn_toggle.setText(f"▼ {self.title_text}" if self.expanded else f"▶ {self.title_text}")
        self.content_area.setVisible(self.expanded)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

# ==========================================
# 2. MOTORE GEOMETRICO
# ==========================================
class BoxModel:
    def __init__(self, params):
        self.p = params
        self.base_gap = 2.0 

    def _rotate_points(self, pts, orientation):
        L = self.p['L']; W = self.p['W']
        final = []
        for x, y in pts:
            if orientation == 'top': final.append((x, y))
            elif orientation == 'bottom': final.append((x, W - y))
            elif orientation == 'left': final.append((y, x))
            elif orientation == 'right': final.append((L - y, x))
            elif orientation == 'tl': final.append((-x, -y))
            elif orientation == 'tr': final.append((L + x, -y))
            elif orientation == 'bl': final.append((-x, W + y))
            elif orientation == 'br': final.append((L + x, W + y))
        return final

    def _get_fianco_geometry(self, L_base, H_full, orientation):
        has_platform = self.p.get('platform_active', False)
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        has_reinf = is_ferro and self.p.get('fianchi_r_active', False)
        
        notch_w, notch_h = 0, 0
        if has_platform:
            notch_h = self.p.get('plat_flap_w', 30) + self.p.get('plat_gap', 2)
            notch_w = self.p.get('fascia_h', 30) + self.p.get('plat_gap', 2)
            if notch_h > H_full: notch_h = H_full - 5

        h_low = self.p.get('fianchi_h_low', H_full * 0.6)
        if h_low > H_full: h_low = H_full
        shoulder = self.p.get('fianchi_shoulder', L_base * 0.2)
        min_shoulder = notch_w + 5
        if is_ferro and shoulder < min_shoulder: shoulder = min_shoulder
        if shoulder * 2 > L_base: shoulder = L_base / 2 - 1

        r_h = self.p.get('fianchi_r_h', 30)
        r_gap = self.p.get('fianchi_r_gap', 2)
        if r_h > h_low: r_h = h_low - 1
        avail_w = L_base - 2*shoulder
        if r_gap * 2 >= avail_w: r_gap = (avail_w / 2) - 5

        p_base_L = (0, 0); p_base_R = (L_base, 0)
        pts_poly, cuts, creases = [], [], []
        
        pts_poly.append(p_base_L); curr = p_base_L
        
        # SX
        path = [(0, -(H_full - notch_h)), (notch_w, -(H_full - notch_h)), (notch_w, -H_full)] if has_platform else [(0, -H_full)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        # TOP
        p_sh_sx = (shoulder, -H_full); p_u_sx = (shoulder, -h_low)
        p_u_dx = (L_base - shoulder, -h_low); p_sh_dx = (L_base - shoulder, -H_full)
        target_dx = (L_base - notch_w, -H_full) if has_platform else (L_base, -H_full)
        
        if is_ferro:
            cuts.append([curr, p_sh_sx]); curr = p_sh_sx; pts_poly.append(curr)
            cuts.append([curr, p_u_sx]); curr = p_u_sx; pts_poly.append(curr)
            
            if has_reinf:
                p_r_tl = (shoulder + r_gap, -h_low); p_r_bl = (shoulder + r_gap, -(h_low + r_h))
                p_r_br = (L_base - shoulder - r_gap, -(h_low + r_h)); p_r_tr = (L_base - shoulder - r_gap, -h_low)
                cuts.extend([[curr, p_r_tl], [p_r_tl, p_r_bl], [p_r_bl, p_r_br], [p_r_br, p_r_tr], [p_r_tr, p_u_dx]])
                creases.append([p_r_tl, p_r_tr])
                curr = p_u_dx; pts_poly.extend([p_r_tl, p_r_bl, p_r_br, p_r_tr, p_u_dx])
            else:
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
            
            cuts.append([curr, p_sh_dx]); curr = p_sh_dx; pts_poly.append(curr)
            cuts.append([curr, target_dx]); curr = target_dx; pts_poly.append(curr)
        else:
            cuts.append([curr, target_dx]); curr = target_dx; pts_poly.append(curr)
            
        # DX
        path = [(L_base - notch_w, -(H_full - notch_h)), (L_base, -(H_full - notch_h)), (L_base, 0)] if has_platform else [(L_base, 0)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        g_poly = self._rotate_points(pts_poly, orientation)
        g_cuts = [self._rotate_points(seg, orientation) for seg in cuts]
        g_creases = [self._rotate_points(seg, orientation) for seg in creases]
        return g_poly, g_cuts, g_creases

    def _get_testata_geometry(self, L_base, H_full, orientation):
        W = self.p['W']
        is_ferro = (self.p.get('testate_shape') == 'ferro')
        has_platform = self.p.get('platform_active', False)
        h_low = self.p.get('testate_h_low', H_full * 0.6)
        if h_low > H_full: h_low = H_full
        shoulder = self.p.get('testate_shoulder', W * 0.2)
        if shoulder * 2 > W: shoulder = W / 2 - 1
        
        has_reinf = is_ferro and self.p.get('testate_r_active', False)
        r_h = self.p.get('testate_r_h', 30)
        r_gap = self.p.get('testate_r_gap', 2)
        if r_h > h_low: r_h = h_low - 1
        avail_w = W - 2*shoulder
        if r_gap * 2 >= avail_w: r_gap = (avail_w / 2) - 5

        curr = (0, 0); pts_poly = [curr]
        cuts, creases = [], []
        
        target = (0, -H_full); creases.append([curr, target]); curr = target; pts_poly.append(curr)
        
        if is_ferro:
            p_sh_sx = (shoulder, -H_full); p_u_sx = (shoulder, -h_low)
            p_u_dx = (W - shoulder, -h_low); p_sh_dx = (W - shoulder, -H_full)
            
            if not has_platform:
                cuts.append([curr, p_sh_sx])
            # Se platform attiva, questo segmento è gestito da create_unit
            
            curr = p_sh_sx; pts_poly.append(curr)
            
            cuts.append([curr, p_u_sx]); curr = p_u_sx; pts_poly.append(curr)
            
            if has_reinf:
                p_r_tl = (shoulder + r_gap, -h_low); p_r_bl = (shoulder + r_gap, -(h_low + r_h))
                p_r_br = (W - shoulder - r_gap, -(h_low + r_h)); p_r_tr = (W - shoulder - r_gap, -h_low)
                cuts.extend([[curr, p_r_tl], [p_r_tl, p_r_bl], [p_r_bl, p_r_br], [p_r_br, p_r_tr], [p_r_tr, p_u_dx]])
                creases.append([p_r_tl, p_r_tr])
                curr = p_u_dx; pts_poly.extend([p_r_tl, p_r_bl, p_r_br, p_r_tr, p_u_dx])
            else:
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
            
            cuts.append([curr, p_sh_dx]); curr = p_sh_dx; pts_poly.append(curr)
            
            target = (W, -H_full)
            if not has_platform:
                cuts.append([curr, target])
            
            curr = target; pts_poly.append(curr)
        else:
            target = (W, -H_full)
            if not has_platform:
                cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
            
        creases.append([curr, (W, 0)]); curr = (W, 0); pts_poly.append(curr)
        
        g_poly = self._rotate_points(pts_poly, orientation)
        g_cuts = [self._rotate_points(seg, orientation) for seg in cuts]
        g_creases = [self._rotate_points(seg, orientation) for seg in creases]
        
        if has_platform:
            plat_polys, plat_creases, plat_cuts = self._get_platform_assembly(orientation, H_full)
            return [{'coords': g_poly, 'type': 'testate'}] + plat_polys, g_cuts + plat_cuts, g_creases + plat_creases
        else:
            return [{'coords': g_poly, 'type': 'testata'}], g_cuts, g_creases

    def _get_platform_assembly(self, corner, H_t):
        W = self.p['W']
        Fascia_H = self.p.get('fascia_h', 30)
        Plat_W = self.p.get('plat_flap_w', 30)
        is_ferro = (self.p.get('testate_shape') == 'ferro')
        shoulder = self.p.get('testate_shoulder', W * 0.2)
        if shoulder * 2 > W: shoulder = W / 2 - 1

        parts = [] 
        
        def create_unit(u_s, u_e, left, right):
            v_b, v_t = -H_t, -(H_t + Fascia_H)
            f_poly = [(u_s, v_b), (u_s, v_t), (u_e, v_t), (u_e, v_b)]
            
            f_cr = [[(u_s, v_b), (u_e, v_b)]] 
            f_ct = [[(u_s, v_t), (u_e, v_t)]]
            
            if left:
                f_cr.append([(u_s, v_b), (u_s, v_t)])
                l_poly = [(u_s-Plat_W, v_b), (u_s-Plat_W, v_t), (u_s, v_t), (u_s, v_b)]
                l_ct = [
                    [(u_s-Plat_W, v_b), (u_s-Plat_W, v_t)], 
                    [(u_s-Plat_W, v_t), (u_s, v_t)],        
                    [(u_s, v_b), (u_s-Plat_W, v_b)]         
                ]
                parts.append((l_poly, [], l_ct, 'platform_flap'))
            else:
                f_ct.append([(u_s, v_b), (u_s, v_t)])
                
            if right:
                f_cr.append([(u_e, v_b), (u_e, v_t)])
                r_poly = [(u_e, v_b), (u_e, v_t), (u_e+Plat_W, v_t), (u_e+Plat_W, v_b)]
                r_ct = [
                    [(u_e, v_t), (u_e+Plat_W, v_t)],        
                    [(u_e+Plat_W, v_t), (u_e+Plat_W, v_b)], 
                    [(u_e+Plat_W, v_b), (u_e, v_b)]         
                ]
                parts.append((r_poly, [], r_ct, 'platform_flap'))
            else:
                f_ct.append([(u_e, v_b), (u_e, v_t)])
            
            parts.append((f_poly, f_cr, f_ct, 'platform'))

        if is_ferro:
            create_unit(0, shoulder, True, False)
            create_unit(W-shoulder, W, False, True)
        else:
            create_unit(0, W, True, True)

        g_polys, g_cr, g_ct = [], [], []
        for poly, cr, ct, typ in parts:
            g_polys.append({'coords': self._rotate_points(poly, corner), 'type': typ})
            g_cr.extend([self._rotate_points(s, corner) for s in cr])
            g_ct.extend([self._rotate_points(s, corner) for s in ct])
        return g_polys, g_cr, g_ct

    def _get_flap_geo(self, corner, h_testata, f_len):
        T = self.p.get('thickness', 3.0)
        gap = self.base_gap + T 
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        shoulder = self.p.get('fianchi_shoulder', 0)
        h_fianco_full = self.p.get('h_fianchi', h_testata)
        h_fianco_low = self.p.get('fianchi_h_low', h_fianco_full)
        has_platform = self.p.get('platform_active', False)
        
        cut_depth = h_fianco_full - h_fianco_low
        if cut_depth < 0: cut_depth = 0
        u_inner = gap
        gap_outer = gap if has_platform else 0
        u_outer = h_testata - gap_outer
        u_outer_low = u_outer - cut_depth
        if u_outer < u_inner: u_outer = u_inner + 1
        
        pts_local = []
        if is_ferro and f_len > shoulder:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer_low, f_len),
                         (u_outer_low, shoulder), (u_outer, shoulder), (u_outer, 0)]
        else:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer, f_len), (u_outer, 0)]

        final_pts = self._rotate_points(pts_local, corner)
        cuts = []
        for i in range(len(final_pts)-1): cuts.append([final_pts[i], final_pts[i+1]])
        
        # FIX PRINCIPALE:
        # Non restituiamo la "crease" (linea di piega) qui perché coincide con il bordo 
        # della Testata che ha già la sua linea. Questo evita la sovrapposizione.
        # crease = [final_pts[0], final_pts[-1]] 
        
        return final_pts, cuts, [] # Restituisci lista vuota per la piega

    def get_data(self):
        polygons, cut_lines, crease_lines = [], [], []
        L = self.p['L']; W = self.p['W']
        H_f = self.p['h_fianchi']; H_t = self.p['h_testate']; F = self.p['F']
        Fascia_H = self.p.get('fascia_h', 0) if self.p.get('platform_active') else 0
        Plat_W = self.p.get('plat_flap_w', 0) if self.p.get('platform_active') else 0
        
        ox = max(H_t + Fascia_H, H_f) + Plat_W + 50
        oy = max(H_t + Fascia_H, H_f) + F + 30 

        # FONDO
        base_pts = [(0, 0), (L, 0), (L, W), (0, W)]
        base_off = [(x+ox, y+oy) for x,y in base_pts]
        polygons.append({'id': 'poly_fondo', 'type': 'fondo', 'coords': base_off})
        for i in range(4): crease_lines.append([base_off[i], base_off[(i+1)%4]])

        # FIANCATE
        for orient in ['top', 'bottom']:
            g_poly, g_cuts, g_creases = self._get_fianco_geometry(L, H_f, orient)
            poly_off = [(x+ox, y+oy) for x,y in g_poly]
            polygons.append({'id': 'poly_fianchi', 'type': 'fianchi', 'coords': poly_off})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])

        # TESTATE
        for orient in ['left', 'right']:
            poly_items, g_cuts, g_creases = self._get_testata_geometry(W, H_t, orient)
            for item in poly_items:
                coords_off = [(x+ox, y+oy) for x,y in item['coords']]
                t_type = item.get('type', 'testate')
                polygons.append({'id': f'poly_{t_type}', 'type': t_type, 'coords': coords_off})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])

        # LEMBI
        for c in ['tl', 'tr', 'bl', 'br']:
            g_pts, g_cuts, g_crease = self._get_flap_geo(c, H_t, F)
            pts_off = [(x+ox, y+oy) for x,y in g_pts]
            cuts_off = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in g_cuts]
            
            # Gestione sicura nel caso g_crease sia vuoto
            if g_crease:
                crease_off = [(p[0]+ox, p[1]+oy) for p in g_crease]
                crease_lines.append(crease_off)
            
            polygons.append({'id': 'poly_lembi', 'type': 'lembi', 'coords': pts_off})
            cut_lines.extend(cuts_off)

        return polygons, cut_lines, crease_lines

# ==========================================
# 3. APP PRINCIPALE (UI Ported to Qt)
# ==========================================
class DrawingArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.model_data = ([], [], [])  # Polys, Cuts, Creases
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
        self.update() # Trigger paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Sfondo
        painter.fillRect(self.rect(), self.bg_color)
        
        cw, ch = self.width(), self.height()
        if cw < 50: return

        polygons, cut_lines, crease_lines = self.model_data
        
        # Logica di Scaling
        tot_w = self.params_L + self.params_HT*2 + 300
        tot_h = self.params_W + self.params_HF*2 + self.params_F*2 + 200
        
        if tot_w == 0: tot_w = 1
        if tot_h == 0: tot_h = 1

        scale = min(cw/tot_w, ch/tot_h) * 0.8
        
        ox_model = max(self.params_HT, self.params_HF) + 100
        oy_model = max(self.params_HT, self.params_HF) + self.params_F + 50
        
        dx = (cw/2) - (ox_model + self.params_L/2)*scale
        dy = (ch/2) - (oy_model + self.params_W/2)*scale

        # --- 1. Draw Polygons ---
        for p in polygons:
            pts = [QPointF(x*scale+dx, y*scale+dy) for x, y in p['coords']]
            qpoly = QPolygonF(pts)
            
            base_col = QColor(THEME["cardboard"])
            
            painter.setBrush(base_col)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(qpoly)

        # --- 2. Draw Creases ---
        crease_pen = QPen(QColor(THEME["line_crease"]))
        crease_pen.setWidthF(1.5)
        # Tratteggio fitto per linee corte
        crease_pen.setStyle(Qt.CustomDashLine) 
        crease_pen.setDashPattern([2, 3]) 
        
        painter.setPen(crease_pen)
        
        for line in crease_lines:
            pts = [QPointF(pt[0]*scale+dx, pt[1]*scale+dy) for pt in line]
            if len(pts) >= 2:
                painter.drawPolyline(pts)

        # --- 3. Draw Cuts ---
        cut_pen = QPen(QColor(THEME["line_cut"]))
        cut_pen.setWidthF(2.0)
        cut_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(cut_pen)
        
        for line in cut_lines:
             pts = [QPointF(pt[0]*scale+dx, pt[1]*scale+dy) for pt in line]
             if len(pts) >= 2:
                painter.drawPolyline(pts)

class PackagingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Packaging CAD Pro (Qt Version)")
        self.resize(1400, 950)
        self.setStyleSheet(f"QMainWindow {{ background-color: {THEME['bg_ui']}; }}")

        # Main Widget & Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # 1. Left Panel (Scrollable)
        scroll = QScrollArea()
        scroll.setFixedWidth(400)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {THEME['bg_ui']}; }}")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet(f"QWidget {{ background-color: {THEME['bg_ui']}; color: {THEME['fg_text']}; }}")
        self.panel_layout = QVBoxLayout(self.scroll_content)
        self.panel_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.scroll_content)
        
        main_layout.addWidget(scroll)

        # 2. Right Canvas
        self.canvas = DrawingArea()
        main_layout.addWidget(self.canvas)

        self.inputs = {}
        
        self.build_ui()
        self.refresh()

    def build_ui(self):
        header = QLabel("PARAMETRI PROGETTO")
        header.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {THEME['highlight']}; padding: 20px;")
        header.setAlignment(Qt.AlignCenter)
        self.panel_layout.addWidget(header)

        # FONDO
        sec = CollapsibleSection("1. Fondo", self.scroll_content, expanded=True)
        self.panel_layout.addWidget(sec)
        self.add_entry(sec, "Lunghezza (L)", "L", "400")
        self.add_entry(sec, "Larghezza (W)", "W", "300")
        self.add_entry(sec, "Spessore", "thickness", "5.0")

        # FIANCATE
        sec = CollapsibleSection("2. Fiancate", self.scroll_content, expanded=True)
        self.panel_layout.addWidget(sec)
        self.add_entry(sec, "Altezza", "h_fianchi", "100")
        
        self.cb_fianchi_shape = QCheckBox("Ferro di Cavallo")
        self.cb_fianchi_shape.setChecked(True)
        self.cb_fianchi_shape.toggled.connect(self.on_structure_change)
        sec.add_widget(self.cb_fianchi_shape)

        self.f_ferro_container = QWidget()
        f_ferro_layout = QVBoxLayout(self.f_ferro_container)
        f_ferro_layout.setContentsMargins(10,0,0,0)
        sec.add_widget(self.f_ferro_container)
        
        self.add_entry_to_layout(f_ferro_layout, "Altezza Min", "fianchi_h_low", "60")
        self.add_entry_to_layout(f_ferro_layout, "Spalla", "fianchi_shoulder", "80")
        
        self.cb_fianchi_r = QCheckBox("Raddoppio (Rinforzo)")
        self.cb_fianchi_r.setChecked(True)
        self.cb_fianchi_r.toggled.connect(self.refresh)
        f_ferro_layout.addWidget(self.cb_fianchi_r)
        
        self.add_entry_to_layout(f_ferro_layout, "Alt. Rinforzo", "fianchi_r_h", "40")
        self.add_entry_to_layout(f_ferro_layout, "Gap Lat. Rinf.", "fianchi_r_gap", "2")

        # TESTATE
        sec = CollapsibleSection("3. Testate", self.scroll_content, expanded=True)
        self.panel_layout.addWidget(sec)
        self.add_entry(sec, "Altezza", "h_testate", "100")
        
        self.cb_testate_shape = QCheckBox("Ferro di Cavallo")
        self.cb_testate_shape.setChecked(True)
        self.cb_testate_shape.toggled.connect(self.on_structure_change)
        sec.add_widget(self.cb_testate_shape)
        
        self.t_ferro_container = QWidget()
        t_ferro_layout = QVBoxLayout(self.t_ferro_container)
        t_ferro_layout.setContentsMargins(10,0,0,0)
        sec.add_widget(self.t_ferro_container)

        self.add_entry_to_layout(t_ferro_layout, "Altezza Min", "testate_h_low", "60")
        self.add_entry_to_layout(t_ferro_layout, "Spalla", "testate_shoulder", "50")
        
        self.cb_testate_r = QCheckBox("Raddoppio (Rinforzo)")
        self.cb_testate_r.setChecked(True)
        self.cb_testate_r.toggled.connect(self.refresh)
        t_ferro_layout.addWidget(self.cb_testate_r)
        
        self.add_entry_to_layout(t_ferro_layout, "Alt. Rinforzo", "testate_r_h", "30")
        self.add_entry_to_layout(t_ferro_layout, "Gap Rinforzo", "testate_r_gap", "2")

        # PLATFORM
        sec = CollapsibleSection("4. Platform", self.scroll_content)
        self.panel_layout.addWidget(sec)
        
        self.cb_plat_active = QCheckBox("Attiva Platform")
        self.cb_plat_active.setChecked(True)
        self.cb_plat_active.toggled.connect(self.refresh)
        sec.add_widget(self.cb_plat_active)
        
        self.add_entry(sec, "Altezza Fascia", "fascia_h", "35")
        self.add_entry(sec, "Larg. Lembo Ext", "plat_flap_w", "40")
        self.add_entry(sec, "Gap Platform", "plat_gap", "3")

        # LEMBI
        sec = CollapsibleSection("5. Lembi Interni", self.scroll_content)
        self.panel_layout.addWidget(sec)
        self.add_entry(sec, "Lunghezza", "F", "120")

        self.panel_layout.addStretch()

    def add_entry(self, section, label_text, key, default_val):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {THEME['fg_text']};")
        lbl.setFixedWidth(120)
        
        inp = QLineEdit(default_val)
        inp.setStyleSheet(f"background-color: #555555; color: white; border: none; padding: 3px;")
        inp.textChanged.connect(self.refresh)
        
        layout.addWidget(lbl)
        layout.addWidget(inp)
        section.add_widget(row)
        self.inputs[key] = inp

    def add_entry_to_layout(self, layout, label_text, key, default_val):
        row = QWidget()
        l = QHBoxLayout(row)
        l.setContentsMargins(0, 2, 0, 2)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {THEME['fg_text']};")
        lbl.setFixedWidth(120)
        
        inp = QLineEdit(default_val)
        inp.setStyleSheet(f"background-color: #555555; color: white; border: none; padding: 3px;")
        inp.textChanged.connect(self.refresh)
        
        l.addWidget(lbl)
        l.addWidget(inp)
        layout.addWidget(row)
        self.inputs[key] = inp

    def on_structure_change(self):
        self.f_ferro_container.setVisible(self.cb_fianchi_shape.isChecked())
        self.t_ferro_container.setVisible(self.cb_testate_shape.isChecked())
        self.refresh()

    def get_float(self, key, default=0.0):
        try:
            return float(self.inputs[key].text())
        except ValueError:
            return default

    def refresh(self):
        params = {}
        for k in self.inputs:
            params[k] = self.get_float(k)
        
        params['fianchi_shape'] = 'ferro' if self.cb_fianchi_shape.isChecked() else 'rect'
        params['fianchi_r_active'] = self.cb_fianchi_r.isChecked()
        params['testate_shape'] = 'ferro' if self.cb_testate_shape.isChecked() else 'rect'
        params['testate_r_active'] = self.cb_testate_r.isChecked()
        params['platform_active'] = self.cb_plat_active.isChecked()

        try:
            model = BoxModel(params)
            polygons, cut_lines, crease_lines = model.get_data()
            self.canvas.set_data(polygons, cut_lines, crease_lines, 
                                 params['L'], params['W'], 
                                 params['h_fianchi'], params['h_testate'], params['F'])
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PackagingApp()
    window.show()
    sys.exit(app.exec())