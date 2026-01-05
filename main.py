import sys
import math
import traceback
import json
import time  # Import necessario per il Delta Time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QScrollArea, QPushButton, QLabel, 
                               QLineEdit, QCheckBox, QTabWidget, QColorDialog, QFileDialog, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from config import THEME
from ui_utils import CollapsibleSection
from widgets_2d import DrawingArea2D
from widgets_3d import Viewer3D
from widgets_table import GlueTableWidget
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
        
        self.main_layout = QVBoxLayout(main_w)
        self.main_layout.setContentsMargins(0,0,0,0)

        self.canvas_2d = DrawingArea2D()
        self.viewer_3d = Viewer3D()
        self.glue_table = GlueTableWidget()
        
        self.inputs = {} 
        self.step_checks = {} 
        
        # Variabile Velocità Animazione (Default 1.0x)
        self.anim_speed_val = 1.0
        
        # Cache per ottimizzare le performance 3D
        self.tm_cache = {} 
        self.last_time = 0.0

        self.tabs = QTabWidget()
        
        self.tab_fustellato = self.build_tab_fustellato()
        self.tabs.addTab(self.tab_fustellato, "Fustellato")
        
        self.tab_3d = self.build_tab_3d()
        self.tabs.addTab(self.tab_3d, "Vista 3D")
        
        self.tabs.addTab(self.glue_table, "Tratti Colla")
        
        self.main_layout.addWidget(self.tabs)
        
        self.current_angles = {
            'lembi': 0.0, 'lembi_3': 0.0, 'lembi_2': 0.0, 
            'testate': 0.0, 'fianchi': 0.0,
            'fasce': 0.0, 'ext': 0.0, 'reinf': 0.0
        }
        self.manual_targets = self.current_angles.copy()

        self.anim_vars = {'prog': 0.0, 'running': False}
        self.timer_seq = QTimer()
        self.timer_seq.timeout.connect(self.update_sequence_frame)
        
        self.timer_manual = QTimer()
        self.timer_manual.timeout.connect(self.update_manual_frame)
        
        self.traces = {} 
        self.glue_lines_local = [] 

        self.update_testate_logic()
        self.update_fiancate_logic()
        self.refresh()

    def build_tab_fustellato(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setFixedWidth(400)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; border-right: 1px solid #444;")
        
        self.params_content = QWidget()
        self.params_layout = QVBoxLayout(self.params_content)
        self.params_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.params_content)
        
        self.build_params_ui()
        
        layout.addWidget(scroll)
        layout.addWidget(self.canvas_2d)
        return container

    def build_tab_3d(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #444;")
        v_layout = QVBoxLayout(sidebar)
        v_layout.setAlignment(Qt.AlignTop)
        v_layout.setSpacing(15)
        v_layout.setContentsMargins(10, 20, 10, 20)
        
        lbl = QLabel("CONTROLLI 3D")
        lbl.setStyleSheet(f"color: {THEME['highlight']}; font-weight: bold; font-size: 14px;")
        lbl.setAlignment(Qt.AlignCenter)
        v_layout.addWidget(lbl)
        
        self.chk_transp = QCheckBox("Trasparenza")
        self.chk_transp.setStyleSheet(f"color: {THEME['fg_text']}; font-size: 14px;")
        self.chk_transp.toggled.connect(self.viewer_3d.set_transparency)
        v_layout.addWidget(self.chk_transp)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #555;")
        v_layout.addWidget(line)
        
        # --- SEZIONE VELOCITÀ ---
        lbl_spd = QLabel("Velocità Animazione")
        lbl_spd.setStyleSheet(f"color: {THEME['fg_text']}; font-weight: bold;")
        lbl_spd.setAlignment(Qt.AlignCenter)
        v_layout.addWidget(lbl_spd)

        h_speed = QHBoxLayout()
        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(30, 30)
        btn_minus.setStyleSheet("background: #444; color: white; border-radius: 15px; font-weight: bold;")
        btn_minus.clicked.connect(self.decrease_speed)
        
        self.lbl_speed_val = QLabel(f"{self.anim_speed_val:.1f}x")
        self.lbl_speed_val.setStyleSheet(f"color: {THEME['highlight']}; font-weight: bold; font-size: 14px;")
        self.lbl_speed_val.setAlignment(Qt.AlignCenter)
        
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(30, 30)
        btn_plus.setStyleSheet("background: #444; color: white; border-radius: 15px; font-weight: bold;")
        btn_plus.clicked.connect(self.increase_speed)
        
        h_speed.addWidget(btn_minus)
        h_speed.addWidget(self.lbl_speed_val)
        h_speed.addWidget(btn_plus)
        
        w_speed = QWidget()
        w_speed.setLayout(h_speed)
        v_layout.addWidget(w_speed)

        line_spd = QFrame()
        line_spd.setFrameShape(QFrame.HLine)
        line_spd.setFrameShadow(QFrame.Sunken)
        line_spd.setStyleSheet("color: #555;")
        v_layout.addWidget(line_spd)

        # --- SEZIONE ANIMAZIONE MANUALE ---
        lbl_anim = QLabel("Controllo Manuale")
        lbl_anim.setStyleSheet(f"color: {THEME['fg_text']}; font-weight: bold;")
        v_layout.addWidget(lbl_anim)

        steps_info = [
            ("1. Lembi Incollaggio", "lembi"),
            ("   -> Angolo: Base", "lembi_3"),      
            ("   -> Angolo: Ipo.", "lembi_2"),      
            ("2. Testate", "testate"),
            ("3. Fiancate", "fianchi"),
            ("4. Fasce Platform", "fasce"),
            ("5. Lembi Platform", "ext"),
            ("6. Raddoppi", "reinf")
        ]

        for label_text, key in steps_info:
            cb = QCheckBox(label_text)
            cb.setChecked(False)
            cb.setStyleSheet(f"color: {THEME['fg_text']}; margin-left: 10px;")
            cb.toggled.connect(self.on_manual_checkbox_toggle)
            self.step_checks[key] = cb
            v_layout.addWidget(cb)
            if key in ['lembi_2', 'lembi_3']:
                cb.setVisible(False)

        v_layout.addSpacing(15)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        line2.setStyleSheet("color: #555;")
        v_layout.addWidget(line2)

        self.btn_anim = QPushButton("Animazione Auto")
        self.btn_anim.clicked.connect(self.toggle_sequence_animation)
        self.btn_anim.setStyleSheet("background: #FF9800; padding: 10px; color: white; font-weight: bold;")
        v_layout.addWidget(self.btn_anim)
        
        v_layout.addStretch()
        
        layout.addWidget(sidebar)
        layout.addWidget(self.viewer_3d)
        
        return container

    def increase_speed(self):
        self.anim_speed_val += 0.25
        if self.anim_speed_val > 5.0: self.anim_speed_val = 5.0
        self.lbl_speed_val.setText(f"{self.anim_speed_val:.1f}x")

    def decrease_speed(self):
        self.anim_speed_val -= 0.25
        if self.anim_speed_val < 0.25: self.anim_speed_val = 0.25
        self.lbl_speed_val.setText(f"{self.anim_speed_val:.1f}x")

    def build_params_ui(self):
        h_file = QHBoxLayout()
        btn_save = QPushButton("💾 Salva")
        btn_save.clicked.connect(self.save_project)
        btn_save.setStyleSheet(f"background: {THEME['bg_panel']}; color: {THEME['fg_text']}; padding: 8px; border: 1px solid #555;")
        
        btn_load = QPushButton("📂 Carica")
        btn_load.clicked.connect(self.load_project)
        btn_load.setStyleSheet(f"background: {THEME['bg_panel']}; color: {THEME['fg_text']}; padding: 8px; border: 1px solid #555;")
        
        h_file.addWidget(btn_save)
        h_file.addWidget(btn_load)
        
        w_file = QWidget()
        w_file.setLayout(h_file)
        self.params_layout.addWidget(w_file)

        lbl = QLabel("PARAMETRI")
        lbl.setStyleSheet(f"color: {THEME['highlight']}; font-size: 16px; font-weight: bold; padding: 20px;")
        lbl.setAlignment(Qt.AlignCenter)
        self.params_layout.addWidget(lbl)
        
        s_cartone = self.add_sec("1. Cartone", [("Spessore", "thickness", 5)])
        
        v_cols = QVBoxLayout()
        v_cols.setSpacing(10)
        v_cols.setContentsMargins(5, 5, 5, 5)

        h_int = QHBoxLayout()
        lbl_int = QLabel("Colore Lato Interno")
        lbl_int.setStyleSheet(f"color: {THEME['fg_text']}")
        self.btn_col_int = QPushButton()
        self.btn_col_int.setFixedSize(24, 24)
        self.btn_col_int.setCursor(Qt.PointingHandCursor)
        self.btn_col_int.clicked.connect(self.change_color_out)
        h_int.addWidget(lbl_int)
        h_int.addWidget(self.btn_col_int)
        h_int.addStretch()
        v_cols.addLayout(h_int)

        h_ext = QHBoxLayout()
        lbl_ext = QLabel("Colore Lato Esterno")
        lbl_ext.setStyleSheet(f"color: {THEME['fg_text']}")
        self.btn_col_ext = QPushButton()
        self.btn_col_ext.setFixedSize(24, 24)
        self.btn_col_ext.setCursor(Qt.PointingHandCursor)
        self.btn_col_ext.clicked.connect(self.change_color_in)
        h_ext.addWidget(lbl_ext)
        h_ext.addWidget(self.btn_col_ext)
        h_ext.addStretch()
        v_cols.addLayout(h_ext)

        w_col = QWidget()
        w_col.setLayout(v_cols)
        s_cartone.add_widget(w_col)
        
        self.update_color_buttons()

        self.add_sec("2. Dimensioni Scatola", [("Lunghezza", "L", 400), ("Larghezza", "W", 300)])
        
        s_lembi = self.add_sec("3. Lembi Interni", [("Lunghezza Totale (F)", "F", 120)])
        
        self.cb_lembi_angle = QCheckBox("Angolo (3 Sezioni)")
        self.cb_lembi_angle.setStyleSheet(f"color: {THEME['fg_text']}")
        self.cb_lembi_angle.toggled.connect(self.toggle_angle_inputs)
        self.cb_lembi_angle.toggled.connect(self.refresh)
        s_lembi.add_widget(self.cb_lembi_angle)

        self.w_ang_h = QWidget()
        hl_h = QHBoxLayout(self.w_ang_h)
        hl_h.setContentsMargins(0,2,0,2)
        lbl_ang_h = QLabel("H Angolo (S1)")
        lbl_ang_h.setFixedWidth(100)
        lbl_ang_h.setStyleSheet(f"color:{THEME['fg_text']}")
        self.inputs['angle_h'] = QLineEdit("40")
        self.inputs['angle_h'].setStyleSheet("background:#555; color:white; border:none;")
        self.inputs['angle_h'].textChanged.connect(self.refresh)
        hl_h.addWidget(lbl_ang_h)
        hl_h.addWidget(self.inputs['angle_h'])
        s_lembi.add_widget(self.w_ang_h)

        self.w_ang_b = QWidget()
        hl_b = QHBoxLayout(self.w_ang_b)
        hl_b.setContentsMargins(0,2,0,2)
        lbl_ang_b = QLabel("Base Angolo (S3)")
        lbl_ang_b.setFixedWidth(100)
        lbl_ang_b.setStyleSheet(f"color:{THEME['fg_text']}")
        self.inputs['angle_b'] = QLineEdit("40")
        self.inputs['angle_b'].setStyleSheet("background:#555; color:white; border:none;")
        self.inputs['angle_b'].textChanged.connect(self.refresh)
        hl_b.addWidget(lbl_ang_b)
        hl_b.addWidget(self.inputs['angle_b'])
        s_lembi.add_widget(self.w_ang_b)

        self.toggle_angle_inputs()

        s_testate = self.add_sec("4. Testate", [("Altezza", "h_testate", 100)])
        
        self.cb_t_shape = QCheckBox("Attiva Scasso")
        self.cb_t_shape.setChecked(True)
        self.cb_t_shape.toggled.connect(self.update_testate_logic) 
        self.cb_t_shape.toggled.connect(self.refresh)
        s_testate.add_widget(self.cb_t_shape)
        
        self.add_inps(s_testate, [("H Min", "testate_h_low", 60), ("Largh. Scasso", "testate_cutout_w", 180)])
        
        self.cb_t_reinf = QCheckBox("Raddoppio")
        self.cb_t_reinf.setChecked(True)
        self.cb_t_reinf.toggled.connect(self.refresh)
        s_testate.add_widget(self.cb_t_reinf)
        
        self.add_inps(s_testate, [("H Raddoppio", "testate_r_h", 30)])
        
        s_fiancate = self.add_sec("5. Fiancate", [("Altezza", "h_fianchi", 100)])
        
        self.cb_f_shape = QCheckBox("Attiva Scasso")
        self.cb_f_shape.setChecked(True)
        self.cb_f_shape.toggled.connect(self.update_fiancate_logic) 
        self.cb_f_shape.toggled.connect(self.refresh)
        s_fiancate.add_widget(self.cb_f_shape)
        
        self.add_inps(s_fiancate, [("H Min", "fianchi_h_low", 60), ("Largh. Scasso", "fianchi_cutout_w", 220)])
        
        self.cb_f_reinf = QCheckBox("Raddoppio")
        self.cb_f_reinf.setChecked(True)
        self.cb_f_reinf.toggled.connect(self.refresh)
        s_fiancate.add_widget(self.cb_f_reinf)
        
        self.add_inps(s_fiancate, [("H Raddoppio", "fianchi_r_h", 40)])
        
        s_plat = self.add_sec("6. Platform", [])
        self.cb_plat = QCheckBox("Attiva")
        self.cb_plat.setChecked(True)
        self.cb_plat.toggled.connect(self.refresh)
        s_plat.add_widget(self.cb_plat)
        
        self.add_inps(s_plat, [("Larghezza Fasce", "fascia_h", 35), ("Lunghezza Lembi", "plat_flap_w", 40)])
        
        self.params_layout.addStretch()

    def toggle_angle_inputs(self):
        show = self.cb_lembi_angle.isChecked()
        self.w_ang_h.setVisible(show)
        self.w_ang_b.setVisible(show)

    def update_color_buttons(self):
        def to_css_rgb(rgba):
            r, g, b = int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255)
            return f"background-color: rgb({r},{g},{b}); border: 1px solid #888; border-radius: 3px;"

        if hasattr(self, 'btn_col_int'):
            self.btn_col_int.setStyleSheet(to_css_rgb(THEME['gl_brown']))
        if hasattr(self, 'btn_col_ext'):
            self.btn_col_ext.setStyleSheet(to_css_rgb(THEME['gl_white']))

    def update_testate_logic(self):
        is_scasso_active = self.cb_t_shape.isChecked()
        self.cb_t_reinf.setEnabled(is_scasso_active)
        if not is_scasso_active:
            self.cb_t_reinf.setChecked(False)

    def update_fiancate_logic(self):
        is_scasso_active = self.cb_f_shape.isChecked()
        self.cb_f_reinf.setEnabled(is_scasso_active)
        if not is_scasso_active:
            self.cb_f_reinf.setChecked(False)

    def save_project(self):
        data = {}
        for k, inp in self.inputs.items():
            data[k] = inp.text()
        
        data['cb_f_shape'] = self.cb_f_shape.isChecked()
        data['cb_f_reinf'] = self.cb_f_reinf.isChecked()
        data['cb_t_shape'] = self.cb_t_shape.isChecked()
        data['cb_t_reinf'] = self.cb_t_reinf.isChecked()
        data['cb_plat']    = self.cb_plat.isChecked()
        data['cb_lembi_angle'] = self.cb_lembi_angle.isChecked()
        
        data['theme_brown'] = THEME['gl_brown']
        data['theme_white'] = THEME['gl_white']

        filename, _ = QFileDialog.getSaveFileName(self, "Salva Fustella", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"Salvataggio completato: {filename}")
            except Exception as e:
                print(f"Errore salvataggio: {e}")

    def load_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Carica Fustella", "", "JSON Files (*.json)")
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            for k, val in data.items():
                if k in self.inputs:
                    self.inputs[k].setText(str(val))
            
            if 'cb_f_shape' in data: self.cb_f_shape.setChecked(data['cb_f_shape'])
            if 'cb_f_reinf' in data: self.cb_f_reinf.setChecked(data['cb_f_reinf'])
            if 'cb_t_shape' in data: self.cb_t_shape.setChecked(data['cb_t_shape'])
            if 'cb_t_reinf' in data: self.cb_t_reinf.setChecked(data['cb_t_reinf'])
            if 'cb_plat'    in data: self.cb_plat.setChecked(data['cb_plat'])
            if 'cb_lembi_angle' in data: self.cb_lembi_angle.setChecked(data['cb_lembi_angle'])

            if 'theme_brown' in data: THEME['gl_brown'] = tuple(data['theme_brown'])
            if 'theme_white' in data: THEME['gl_white'] = tuple(data['theme_white'])
            self.update_color_buttons() 
            
            self.update_testate_logic()
            self.update_fiancate_logic()
            self.toggle_angle_inputs()
            self.refresh()
            print(f"Caricamento completato: {filename}")
            
        except Exception as e:
            print(f"Errore caricamento: {e}")
            traceback.print_exc()

    def change_color_out(self):
        col = QColorDialog.getColor()
        if col.isValid():
            THEME['gl_brown'] = (col.redF(), col.greenF(), col.blueF(), 1.0)
            self.viewer_3d.update()
            self.update_color_buttons()

    def change_color_in(self):
        col = QColorDialog.getColor()
        if col.isValid():
            THEME['gl_white'] = (col.redF(), col.greenF(), col.blueF(), 1.0)
            self.viewer_3d.update()
            self.update_color_buttons()

    def add_sec(self, title, fields):
        s = CollapsibleSection(title, self.params_content); self.params_layout.addWidget(s)
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

    def calculate_triangle_targets(self):
        try:
            t = self.get_val('thickness')
            h_raw = self.get_val('angle_h')
            b_raw = self.get_val('angle_b')
            
            # Dimensioni nette
            h = max(0.1, h_raw - t)
            b = max(0.1, b_raw - t)
            
            hypotenuse = math.hypot(h, b)
            
            if hypotenuse <= h: 
                return 90.0, 90.0
            
            ratio = h / hypotenuse
            if ratio > 1.0: 
                ratio = 1.0
            
            angle_b_rad = math.acos(ratio)
            angle_b_deg = math.degrees(angle_b_rad)
            
            t2 = 180.0 - angle_b_deg
            
            angle_c_deg = 90.0 - angle_b_deg
            t3 = 180.0 - angle_c_deg
            
            return t2, t3
        except:
            return 90.0, 90.0

    def refresh(self):
        p = {k: self.get_val(k) for k in self.inputs}
        p['fianchi_shape'] = 'ferro' if self.cb_f_shape.isChecked() else 'rect'
        p['fianchi_r_active'] = self.cb_f_reinf.isChecked() 
        p['testate_shape'] = 'ferro' if self.cb_t_shape.isChecked() else 'rect'
        p['testate_r_active'] = self.cb_t_reinf.isChecked() 
        p['platform_active'] = self.cb_plat.isChecked()
        p['lembi_angle'] = self.cb_lembi_angle.isChecked()
        p['angle_h'] = self.get_val('angle_h')
        p['angle_b'] = self.get_val('angle_b')
        
        is_angle = p['lembi_angle']
        if 'lembi_2' in self.step_checks:
            self.step_checks['lembi_2'].setVisible(is_angle)
        if 'lembi_3' in self.step_checks:
            self.step_checks['lembi_3'].setVisible(is_angle)
        
        try:
            self.box_manager.build(p)
            self.viewer_3d.set_scene(self.box_manager)
            
            self.viewer_3d.update_angles(self.current_angles)
            
            polys, cuts, creases, glues = self.box_manager.get_2d_diagram(p)

            self.glue_table.update_data(glues, polys)
            
            ox, oy = p['L']/2 + 50, p['W']/2 + 50
            
            off_p = [{'coords':[(x+ox, y+oy) for x,y in poly['coords']], 'type': poly['type']} for poly in polys]
            off_c = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in cuts]
            off_cr = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in creases]
            
            off_gl = []
            for lines, idx, pid in glues:
                p1, p2 = lines
                off_gl.append( ([ (p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy) ], idx) )
            
            self.canvas_2d.set_data(off_p, off_c, off_cr, off_gl, p['L'], p['W'], 0,0,0)

            self.glue_lines_local = []
            
            comp_map = {}
            layout_transforms = {} 

            def map_layout(node, p_pos=(0,0), p_rot=0):
                comp_map[node.name] = node
                my_pos, my_rot = node.get_layout_transform_2d(p_pos, p_rot)
                layout_transforms[node.name] = (my_pos, my_rot)
                for c in node.children:
                    map_layout(c, my_pos, my_rot)
            
            if self.box_manager.root:
                map_layout(self.box_manager.root)
            
            glue_color_gray = (0.6, 0.6, 0.6)

            for lines, idx, pid in glues:
                if pid in comp_map:
                    comp = comp_map[pid]
                    l_pos, l_rot = layout_transforms[pid]
                    rad = math.radians(l_rot); c, s = math.cos(rad), math.sin(rad)
                    def to_local(gpt):
                        gx_t = gpt[0] - l_pos[0]
                        gy_t = gpt[1] - l_pos[1]
                        return (gx_t * c + gy_t * s, -gx_t * s + gy_t * c)
                    
                    self.glue_lines_local.append({
                        'comp': comp,
                        'p1': to_local(lines[0]),
                        'p2': to_local(lines[1]),
                        'col': glue_color_gray
                    })
            
            self.update_3d_glue_lines()

        except Exception:
            traceback.print_exc()

    def update_3d_glue_lines(self):
        lines_3d = []
        for g in self.glue_lines_local:
            tm = self.get_absolute_transform(g['comp'])
            
            p1_3d = tm((g['p1'][0], g['p1'][1], 0.2)) 
            p2_3d = tm((g['p2'][0], g['p2'][1], 0.2))
            
            p_zero = tm((0,0,0))
            p_up = tm((0,0,1))
            
            dx, dy, dz = p_up[0]-p_zero[0], p_up[1]-p_zero[1], p_up[2]-p_zero[2]
            length = math.sqrt(dx*dx + dy*dy + dz*dz)
            if length > 0:
                normal_3d = (dx/length, dy/length, dz/length)
            else:
                normal_3d = (0, 0, 1)

            lines_3d.append( (p1_3d, p2_3d, g['col'], normal_3d) )
            
        self.viewer_3d.set_glue_lines(lines_3d)

    def reset_traces(self):
        self.traces = {}
        self.viewer_3d.set_extra_lines([])

    def on_manual_checkbox_toggle(self):
        if self.anim_vars['running']:
            self.timer_seq.stop()
            self.anim_vars['running'] = False
            self.reset_traces()

        def set_target(k, val_true, val_false=0.0):
            if self.step_checks[k].isChecked():
                self.manual_targets[k] = val_true
            else:
                self.manual_targets[k] = val_false

        set_target('lembi', 90.0)
        
        if self.cb_lembi_angle.isChecked():
            t2, t3 = self.calculate_triangle_targets()
            if self.step_checks['lembi_2'].isChecked():
                self.manual_targets['lembi_2'] = t2
            else:
                self.manual_targets['lembi_2'] = 0.0
                
            if self.step_checks['lembi_3'].isChecked():
                self.manual_targets['lembi_3'] = t3
            else:
                self.manual_targets['lembi_3'] = 0.0
        else:
            set_target('lembi_2', 90.0)
            set_target('lembi_3', 90.0)
        
        set_target('testate', 90.0)
        set_target('fianchi', 90.0)
        set_target('fasce', 90.0)
        set_target('ext', 90.0)
        set_target('reinf', 180.0)

        self.timer_manual.start(20)

    def update_manual_frame(self):
        all_reached = True
        base_speed = 0.15 
        # Modifica velocità anche nel manuale
        speed = base_speed * self.anim_speed_val 

        for key in self.current_angles:
            curr = self.current_angles[key]
            targ = self.manual_targets[key]
            
            diff = targ - curr
            if abs(diff) > 0.5:
                all_reached = False
                new_val = curr + diff * speed
                self.current_angles[key] = new_val
            else:
                self.current_angles[key] = targ

        self.viewer_3d.update_angles(self.current_angles)
        self.update_3d_glue_lines()

        if all_reached:
            self.timer_manual.stop()

    def toggle_sequence_animation(self):
        if self.anim_vars['running']:
            self.reset_sequence_animation()
        else:
            if self.anim_vars['prog'] >= 3.0:
                self.anim_vars['prog'] = 0.0
                self.current_angles = {k:0.0 for k in self.current_angles}
                self.viewer_3d.update_angles(self.current_angles)
            
            self.reset_traces()
            self.anim_vars.update({'prog': 0.0, 'running': True})
            self.last_time = time.time() # Inizializza tempo
            self.timer_manual.stop()
            self.timer_seq.start(20)

    def reset_sequence_animation(self):
        self.timer_seq.stop()
        self.anim_vars['running'] = False
        self.anim_vars['prog'] = 0.0
        self.reset_traces()
        
        self.current_angles = {k:0.0 for k in self.current_angles}
        self.viewer_3d.update_angles(self.current_angles)
        self.update_3d_glue_lines()

    def update_sequence_frame(self):
        # DELTA TIME LOGIC
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Pulizia Cache trasformazioni ad ogni frame
        self.tm_cache = {} 

        # Avanzamento basato sul tempo (approx 0.75 units/sec = similar to original speed)
        self.anim_vars['prog'] += 0.75 * dt * self.anim_speed_val
        t = self.anim_vars['prog']
        
        def lerp(t, s, e, max_a=90): 
            return 0 if t<s else (max_a if t>e else (t-s)/(e-s)*max_a)
        
        seq = {}
        is_angle = self.cb_lembi_angle.isChecked()
        
        # 1. Lembi di Incollaggio
        seq['lembi'] = lerp(t, 0.0, 1.0)
        
        t_next = 1.0 
        
        if is_angle:
            t2_target, t3_target = self.calculate_triangle_targets()
            # 2. Angolo: Base
            seq['lembi_3'] = lerp(t, 1.0, 2.0, t3_target)
            # 3. Angolo: Ipotenusa
            seq['lembi_2'] = lerp(t, 2.0, 3.0, t2_target)
            t_next = 3.0
        else:
            seq['lembi_3'] = 0.0
            seq['lembi_2'] = 0.0

        # 4. Tutto il resto
        seq['testate'] = lerp(t, t_next, t_next + 1.0)
        seq['fianchi'] = lerp(t, t_next + 0.5, t_next + 1.5)
        seq['fasce']   = lerp(t, t_next + 1.0, t_next + 2.0)
        seq['ext']     = lerp(t, t_next + 1.5, t_next + 2.5)
        seq['reinf']   = lerp(t, t_next + 2.0, t_next + 3.0, 180)

        # Logica collisione Lembi
        target_lembi = seq['lembi']
        rad_t = math.radians(seq['testate'])
        rad_f = math.radians(seq['fianchi'])
        if rad_t > 1.55: 
            rad_t = 1.55
        
        min_lembo_deg = math.degrees(math.atan(math.tan(rad_f) / math.cos(rad_t)))
        seq['lembi'] = max(target_lembi, min_lembo_deg)
        
        # Controllo collisione solo se necessario
        if (min_lembo_deg > target_lembi + 0.2) and self.box_manager.root:
            self.record_traces()

        self.current_angles = seq
        self.viewer_3d.update_angles(self.current_angles)
        self.update_3d_glue_lines() 
        self.draw_traces()

        if t >= 7.0: 
            self.timer_seq.stop()
            self.anim_vars['running'] = False 

    # --- Metodi Helper ---
    def anim_step(self): pass
    def anim_all(self): pass

    def get_absolute_transform(self, comp):
        # Implementazione CACHE per ottimizzazione performance
        if comp.name in self.tm_cache:
            return self.tm_cache[comp.name]

        # Calcolo standard se non in cache
        chain = []
        curr = comp
        while curr:
            chain.append(curr)
            curr = curr.parent
        chain.reverse()
        
        tm = None 
        for c in chain:
            tm = c.get_world_transform_3d(parent_tm=tm)
        
        # Salva in cache
        self.tm_cache[comp.name] = tm
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