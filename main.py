import sys
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QScrollArea, QPushButton, QLabel, 
                               QLineEdit, QCheckBox, QTabWidget)
from PySide6.QtCore import Qt, QTimer

from config import THEME
from ui_utils import CollapsibleSection
from widgets_2d import DrawingArea2D
from widgets_3d import Viewer3D
from geometry_oop import BoxManager

class PackagingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Packaging CAD Pro (OOP Final)")
        self.resize(1400, 950)
        self.setStyleSheet(f"QMainWindow {{ background-color: {THEME['bg_ui']}; }}")

        self.box_manager = BoxManager()

        main_w = QWidget()
        self.setCentralWidget(main_w)
        layout = QHBoxLayout(main_w)
        layout.setContentsMargins(0,0,0,0)

        # Pannello Sinistro
        scroll = QScrollArea()
        scroll.setFixedWidth(400)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        self.scroll_content = QWidget()
        self.panel_layout = QVBoxLayout(self.scroll_content)
        self.panel_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        # Tabs 2D/3D
        self.tabs = QTabWidget()
        self.canvas_2d = DrawingArea2D()
        self.viewer_3d = Viewer3D()
        self.tabs.addTab(self.canvas_2d, "Progetto 2D")
        self.tabs.addTab(self.viewer_3d, "Animazione 3D")
        layout.addWidget(self.tabs)
        
        # Checkbox Trasparenza
        self.chk_transp = QCheckBox("Trasparenza 3D")
        self.chk_transp.setStyleSheet(f"color: {THEME['fg_text']}; margin-bottom: 10px;")
        self.chk_transp.toggled.connect(self.viewer_3d.set_transparency)
        self.panel_layout.addWidget(self.chk_transp)

        self.inputs = {}
        self.build_ui()
        
        # Variabili animazione
        self.anim_vars = {'idx': 0, 'prog': 0.0, 'angles': {}, 'key': '', 'active': False, 'comb': False}
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        self.refresh()

    def build_ui(self):
        lbl = QLabel("PARAMETRI")
        lbl.setStyleSheet(f"color: {THEME['highlight']}; font-size: 16px; font-weight: bold; padding: 20px;")
        lbl.setAlignment(Qt.AlignCenter)
        self.panel_layout.insertWidget(0, lbl)

        # 1. Fondo
        self.add_sec("1. Fondo", [("Lunghezza", "L", 400), ("Larghezza", "W", 300), ("Spessore", "thickness", 5)])
        
        # 2. Fianchi
        s2 = self.add_sec("2. Fianchi", [("Altezza", "h_fianchi", 100)])
        self.cb_f_shape = QCheckBox("Ferro di Cavallo"); self.cb_f_shape.setChecked(True)
        self.cb_f_shape.toggled.connect(self.refresh); s2.add_widget(self.cb_f_shape)
        
        # Parametri ferro/raddoppio
        # ORA SI USA 'fianchi_cutout_w' (Largh. Scasso) INVECE DI SPALLA
        self.add_inps(s2, [("H Min", "fianchi_h_low", 60), ("Largh. Scasso", "fianchi_cutout_w", 220)])
        
        self.cb_f_reinf = QCheckBox("Raddoppio"); self.cb_f_reinf.setChecked(True)
        self.cb_f_reinf.toggled.connect(self.refresh); s2.add_widget(self.cb_f_reinf)
        self.add_inps(s2, [("H Raddoppio", "fianchi_r_h", 40)])
        
        # 3. Testate
        s3 = self.add_sec("3. Testate", [("Altezza", "h_testate", 100)])
        self.cb_t_shape = QCheckBox("Ferro di Cavallo"); self.cb_t_shape.setChecked(True)
        self.cb_t_shape.toggled.connect(self.refresh); s3.add_widget(self.cb_t_shape)
        
        # Parametri ferro/raddoppio
        # ORA SI USA 'testate_cutout_w' (Largh. Scasso) INVECE DI SPALLA
        self.add_inps(s3, [("H Min", "testate_h_low", 60), ("Largh. Scasso", "testate_cutout_w", 180)])
        
        self.cb_t_reinf = QCheckBox("Raddoppio"); self.cb_t_reinf.setChecked(True)
        self.cb_t_reinf.toggled.connect(self.refresh); s3.add_widget(self.cb_t_reinf)
        self.add_inps(s3, [("H Raddoppio", "testate_r_h", 30)])
        
        # 4. Platform
        s4 = self.add_sec("4. Platform", [])
        self.cb_plat = QCheckBox("Attiva"); self.cb_plat.setChecked(True)
        self.cb_plat.toggled.connect(self.refresh); s4.add_widget(self.cb_plat)
        self.add_inps(s4, [("H Fascia", "fascia_h", 35), ("W Lembo", "plat_flap_w", 40)])
        
        # 5. Lembi
        self.add_sec("5. Lembi", [("Lunghezza", "F", 120)])
        
        # Bottoni
        btn_step = QPushButton("▶ STEP"); btn_step.clicked.connect(self.anim_step)
        btn_step.setStyleSheet(f"background: {THEME['line_crease']}; padding: 10px;")
        self.panel_layout.addWidget(btn_step)
        
        btn_all = QPushButton("▶ ALL"); btn_all.clicked.connect(self.anim_all)
        btn_all.setStyleSheet("background: #FF9800; padding: 10px;")
        self.panel_layout.addWidget(btn_all)
        self.panel_layout.addStretch()

    def add_sec(self, title, fields):
        s = CollapsibleSection(title, self.scroll_content); self.panel_layout.addWidget(s)
        self.add_inps(s, fields)
        return s
    
    def add_inps(self, sec, fields):
        for l, k, v in fields:
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,2,0,2)
            lb = QLabel(l); lb.setFixedWidth(100); lb.setStyleSheet(f"color:{THEME['fg_text']}")
            i = QLineEdit(str(v)); i.setStyleSheet("background:#555; color:white; border:none;")
            i.textChanged.connect(self.refresh)
            h.addWidget(lb); h.addWidget(i); sec.add_widget(w)
            self.inputs[k] = i

    def get_val(self, k):
        try: return float(self.inputs[k].text())
        except: return 0.0

    def refresh(self):
        p = {k: self.get_val(k) for k in self.inputs}
        p['fianchi_shape'] = 'ferro' if self.cb_f_shape.isChecked() else 'rect'
        p['fianchi_r_active'] = self.cb_f_reinf.isChecked() 
        
        p['testate_shape'] = 'ferro' if self.cb_t_shape.isChecked() else 'rect'
        p['testate_r_active'] = self.cb_t_reinf.isChecked() 
        
        p['platform_active'] = self.cb_plat.isChecked()
        
        try:
            self.box_manager.build(p)
            self.viewer_3d.set_scene(self.box_manager)
            self.viewer_3d.update_angles(self.anim_vars.get('angles', {}))
            
            polys, cuts, creases = self.box_manager.get_2d_diagram()
            ox, oy = p['L']/2 + 50, p['W']/2 + 50
            off_p = [{'coords':[(x+ox, y+oy) for x,y in poly['coords']], 'type': poly['type']} for poly in polys]
            off_c = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in cuts]
            off_cr = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in creases]
            
            self.canvas_2d.set_data(off_p, off_c, off_cr, p['L'], p['W'], 0,0,0)
        except Exception: traceback.print_exc()

    def anim_step(self):
        if self.anim_vars['active']: return
        self.tabs.setCurrentIndex(1)
        st = ['lembi', 'testate', 'fianchi', 'fasce', 'ext']
        if self.anim_vars['idx'] >= len(st):
            self.anim_vars['idx'] = 0
            self.anim_vars['angles'] = {}
            self.refresh(); return
        
        self.anim_vars.update({'key': st[self.anim_vars['idx']], 'prog': 0.0, 'active': True, 'comb': False})
        self.timer.start(20)

    def anim_all(self):
        if self.anim_vars['active']: return
        self.tabs.setCurrentIndex(1)
        self.anim_vars.update({'angles': {}, 'prog': 0.0, 'active': True, 'comb': True})
        self.timer.start(20)

    def update_frame(self):
        v = self.anim_vars
        if v['comb']:
            v['prog'] += 0.02
            t = v['prog']
            ang = v['angles']
            def lerp(t, s, e): return 0 if t<s else (90 if t>e else (t-s)/(e-s)*90)
            ang['lembi'] = lerp(t, 0, 1)
            ang['testate'] = lerp(t, 0, 1)
            ang['fianchi'] = lerp(t, 0.5, 1.5)
            ang['fasce'] = lerp(t, 1.5, 2.5)
            ang['ext'] = lerp(t, 2.5, 3.5)
            if t >= 3.5: self.timer.stop(); v['active'] = False
        else:
            v['prog'] += 0.05
            if v['prog'] >= 1.0:
                v['prog'] = 1.0; self.timer.stop(); v['active'] = False; v['idx'] += 1
            v['angles'][v['key']] = v['prog'] * 90
        self.viewer_3d.update_angles(v['angles'])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PackagingApp()
    window.show()
    sys.exit(app.exec())