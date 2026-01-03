import sys
import math
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
        self.setWindowTitle("Packaging CAD Pro (Final Sequence)")
        self.resize(1400, 950)
        self.setStyleSheet(f"QMainWindow {{ background-color: {THEME['bg_ui']}; }}")

        self.box_manager = BoxManager()

        main_w = QWidget()
        self.setCentralWidget(main_w)
        layout = QHBoxLayout(main_w)
        layout.setContentsMargins(0,0,0,0)

        scroll = QScrollArea()
        scroll.setFixedWidth(400)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        self.scroll_content = QWidget()
        self.panel_layout = QVBoxLayout(self.scroll_content)
        self.panel_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        self.tabs = QTabWidget()
        self.canvas_2d = DrawingArea2D()
        self.viewer_3d = Viewer3D()
        self.tabs.addTab(self.canvas_2d, "Progetto 2D")
        self.tabs.addTab(self.viewer_3d, "Animazione 3D")
        layout.addWidget(self.tabs)
        
        self.chk_transp = QCheckBox("Trasparenza 3D")
        self.chk_transp.setStyleSheet(f"color: {THEME['fg_text']}; margin-bottom: 10px;")
        self.chk_transp.toggled.connect(self.viewer_3d.set_transparency)
        self.panel_layout.addWidget(self.chk_transp)

        self.inputs = {}
        self.build_ui()
        
        # Setup Animazione
        self.anim_vars = {'idx': 0, 'prog': 0.0, 'angles': {}, 'key': '', 'active': False, 'comb': False}
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Traccia dello sfregamento
        self.traces = {} 
        
        self.refresh()

    def build_ui(self):
        lbl = QLabel("PARAMETRI")
        lbl.setStyleSheet(f"color: {THEME['highlight']}; font-size: 16px; font-weight: bold; padding: 20px;")
        lbl.setAlignment(Qt.AlignCenter)
        self.panel_layout.insertWidget(0, lbl)

        self.add_sec("1. Fondo", [("Lunghezza", "L", 400), ("Larghezza", "W", 300), ("Spessore", "thickness", 5)])
        
        s2 = self.add_sec("2. Fianchi", [("Altezza", "h_fianchi", 100)])
        self.cb_f_shape = QCheckBox("Ferro di Cavallo"); self.cb_f_shape.setChecked(True)
        self.cb_f_shape.toggled.connect(self.refresh); s2.add_widget(self.cb_f_shape)
        self.add_inps(s2, [("H Min", "fianchi_h_low", 60), ("Largh. Scasso", "fianchi_cutout_w", 220)])
        self.cb_f_reinf = QCheckBox("Raddoppio"); self.cb_f_reinf.setChecked(True)
        self.cb_f_reinf.toggled.connect(self.refresh); s2.add_widget(self.cb_f_reinf)
        self.add_inps(s2, [("H Raddoppio", "fianchi_r_h", 40)])
        
        s3 = self.add_sec("3. Testate", [("Altezza", "h_testate", 100)])
        self.cb_t_shape = QCheckBox("Ferro di Cavallo"); self.cb_t_shape.setChecked(True)
        self.cb_t_shape.toggled.connect(self.refresh); s3.add_widget(self.cb_t_shape)
        self.add_inps(s3, [("H Min", "testate_h_low", 60), ("Largh. Scasso", "testate_cutout_w", 180)])
        self.cb_t_reinf = QCheckBox("Raddoppio"); self.cb_t_reinf.setChecked(True)
        self.cb_t_reinf.toggled.connect(self.refresh); s3.add_widget(self.cb_t_reinf)
        self.add_inps(s3, [("H Raddoppio", "testate_r_h", 30)])
        
        s4 = self.add_sec("4. Platform", [])
        self.cb_plat = QCheckBox("Attiva"); self.cb_plat.setChecked(True)
        self.cb_plat.toggled.connect(self.refresh); s4.add_widget(self.cb_plat)
        self.add_inps(s4, [("H Fascia", "fascia_h", 35), ("W Lembo", "plat_flap_w", 40)])
        
        self.add_sec("5. Lembi", [("Lunghezza", "F", 120)])
        
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
            
            polys, cuts, creases, glues = self.box_manager.get_2d_diagram(p)
            
            ox, oy = p['L']/2 + 50, p['W']/2 + 50
            off_p = [{'coords':[(x+ox, y+oy) for x,y in poly['coords']], 'type': poly['type']} for poly in polys]
            off_c = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in cuts]
            off_cr = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in creases]
            
            # Gestione offset per coppie (Coordinate, Indice)
            off_gl = []
            for lines, idx in glues:
                p1, p2 = lines
                p1_off = (p1[0]+ox, p1[1]+oy)
                p2_off = (p2[0]+ox, p2[1]+oy)
                off_gl.append( ([p1_off, p2_off], idx) )
            
            self.canvas_2d.set_data(off_p, off_c, off_cr, off_gl, p['L'], p['W'], 0,0,0)
        except Exception: traceback.print_exc()

    def reset_traces(self):
        self.traces = {}
        self.viewer_3d.set_extra_lines([])

    def anim_step(self):
        if self.anim_vars['active']: return
        self.reset_traces()
        self.tabs.setCurrentIndex(1)
        st = ['lembi', 'testate', 'fianchi', 'fasce', 'ext', 'reinf']
        if self.anim_vars['idx'] >= len(st):
            self.anim_vars['idx'] = 0
            self.anim_vars['angles'] = {}
            self.refresh(); return
        
        self.anim_vars.update({'key': st[self.anim_vars['idx']], 'prog': 0.0, 'active': True, 'comb': False})
        self.timer.start(20)

    def anim_all(self):
        if self.anim_vars['active']: return
        self.reset_traces()
        self.tabs.setCurrentIndex(1)
        self.anim_vars.update({'angles': {}, 'prog': 0.0, 'active': True, 'comb': True})
        self.timer.start(20)

    def update_frame(self):
        v = self.anim_vars
        if v['comb']:
            v['prog'] += 0.015
            t = v['prog']
            ang = v['angles']
            def lerp(t, s, e, max_a=90): return 0 if t<s else (max_a if t>e else (t-s)/(e-s)*max_a)
            
            target_lembi   = lerp(t, 0.0, 1.0)
            target_testate = lerp(t, 0.0, 1.0) 
            target_fianchi = lerp(t, 0.5, 1.0)
            
            ang['testate'] = target_testate
            ang['fianchi'] = target_fianchi
            ang['fasce']   = lerp(t, 1.0, 1.5)
            ang['ext']     = lerp(t, 1.5, 2.5)
            ang['reinf']   = lerp(t, 2.0, 3.0, 180)

            rad_t = math.radians(target_testate)
            rad_f = math.radians(target_fianchi)
            if rad_t > 1.55: rad_t = 1.55
            
            min_lembo_rad = math.atan(math.tan(rad_f) / math.cos(rad_t))
            min_lembo_deg = math.degrees(min_lembo_rad)
            
            actual_lembo_deg = max(target_lembi, min_lembo_deg)
            ang['lembi'] = actual_lembo_deg
            
            is_pushing = (min_lembo_deg > target_lembi + 0.2)
            
            if is_pushing and self.box_manager.root:
                self.record_traces()

            if t >= 3.0: 
                self.timer.stop(); v['active'] = False
        else:
            v['prog'] += 0.05
            if v['prog'] >= 1.0:
                v['prog'] = 1.0; self.timer.stop(); v['active'] = False; v['idx'] += 1
            target = 180 if v['key'] == 'reinf' else 90
            v['angles'][v['key']] = v['prog'] * target
            
        self.viewer_3d.update_angles(v['angles'])
        self.draw_traces()

    def get_absolute_transform(self, comp):
        chain = []
        curr = comp
        while curr:
            chain.append(curr)
            curr = curr.parent
        chain.reverse() 
        
        tm = None 
        for c in chain:
            tm = c.get_world_transform_3d(parent_tm=tm)
        return tm

    def record_traces(self):
        parts = {}
        def traverse(node):
            parts[node.name] = node
            for c in node.children: traverse(c)
        traverse(self.box_manager.root)

        lembi = [n for n in parts.values() if getattr(n, 'label', '') == 'lembi']
        fianchi = [n for n in parts.values() if getattr(n, 'label', '') == 'fianchi' or n.name.startswith('Fianco')]
        
        for lembo in lembi:
            tm_l = self.get_absolute_transform(lembo)
            tips_local = [
                ((lembo.width/2, -lembo.height, 0), 0),
                ((-lembo.width/2, -lembo.height, 0), 1)
            ]
            
            for pt_local, tip_idx in tips_local:
                tip_world = tm_l(pt_local)
                
                for fianco in fianchi:
                    p_loc = self.world_to_local(fianco, tip_world)
                    
                    if abs(p_loc[2]) < 10.0 or abs(p_loc[2] + fianco.thickness) < 10.0:
                        if (-fianco.width/2 <= p_loc[0] <= fianco.width/2) and \
                           (-fianco.height <= p_loc[1] <= 10.0):
                            
                            trace_key = (fianco.name, lembo.name, tip_idx)
                            
                            if trace_key not in self.traces: self.traces[trace_key] = []
                            
                            add_point = True
                            if self.traces[trace_key]:
                                last = self.traces[trace_key][-1]
                                dist = math.sqrt((last[0]-p_loc[0])**2 + (last[1]-p_loc[1])**2)
                                if dist < 2.0: add_point = False
                            
                            if add_point:
                                self.traces[trace_key].append(p_loc)

    def world_to_local(self, comp, p_world):
        px, py, pz = comp.pivot_3d
        vx, vy, vz = p_world[0] - px, p_world[1] - py, p_world[2] - pz
        
        rad_f = math.radians(comp.fold_angle * comp.fold_multiplier)
        cf, sf = math.cos(rad_f), math.sin(rad_f)
        
        if comp.fold_axis == 'x':
            lx = vx
            ly = vy * cf + vz * sf
            lz = -vy * sf + vz * cf
        else: # y axis
            lx = vx * cf - vz * sf
            ly = vy
            lz = vx * sf + vz * cf
            
        rad_p = math.radians(comp.pre_rot_z)
        cp, sp = math.cos(rad_p), math.sin(rad_p)
        
        final_x = lx * cp + ly * sp
        final_y = -lx * sp + ly * cp
        final_z = lz
        
        return (final_x, final_y, final_z)

    def draw_traces(self):
        if not self.traces: return
        
        lines = []
        parts = {}
        def traverse(node):
            parts[node.name] = node
            for c in node.children: traverse(c)
        traverse(self.box_manager.root)
        
        for (fname, lname, tidx), points in self.traces.items():
            if fname in parts:
                fianco = parts[fname]
                tm = self.get_absolute_transform(fianco)
                
                world_pts = [tm(p) for p in points]
                for i in range(len(world_pts) - 1):
                    lines.append((world_pts[i], world_pts[i+1]))
                    
        self.viewer_3d.set_extra_lines(lines)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PackagingApp()
    window.show()
    sys.exit(app.exec())