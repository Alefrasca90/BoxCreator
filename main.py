import sys
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QScrollArea, QPushButton, QLabel, 
                               QLineEdit, QFrame, QCheckBox, QTabWidget)
from PySide6.QtCore import Qt, QTimer

from config import THEME
from ui_utils import CollapsibleSection
from geometry_2d import BoxModel
from widgets_2d import DrawingArea2D
from widgets_3d import Viewer3D

class PackagingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Packaging CAD Pro (Qt Version)")
        self.resize(1400, 950)
        self.setStyleSheet(f"QMainWindow {{ background-color: {THEME['bg_ui']}; }}")

        # Main Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # 1. Left Panel
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

        # 2. Right Tabs (2D / 3D)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ background: {THEME['bg_panel']}; color: white; padding: 10px; }}
            QTabBar::tab:selected {{ background: {THEME['highlight']}; color: black; }}
        """)
        
        self.canvas_2d = DrawingArea2D()
        self.viewer_3d = Viewer3D()
        
        self.tabs.addTab(self.canvas_2d, "Progetto 2D")
        self.tabs.addTab(self.viewer_3d, "Animazione 3D")
        
        main_layout.addWidget(self.tabs)
        
        self.chk_transparency = QCheckBox("Trasparenza 3D")
        self.chk_transparency.setStyleSheet(f"color: {THEME['fg_text']}; font-weight: bold; margin-bottom: 10px;")
        self.chk_transparency.toggled.connect(self.viewer_3d.set_transparency)
        self.panel_layout.insertWidget(1, self.chk_transparency)

        self.inputs = {}
        self.build_ui()
        
        self.step_idx = 0
        self.anim_progress = 0.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.anim_angles = {'lembi':0, 'testate':0, 'fianchi':0, 'fasce':0, 'ext':0}
        self.target_key = ''
        self.is_animating = False
        
        self.is_combined_anim = False
        self.combined_phase = 0
        
        self.refresh()

    def build_ui(self):
        header = QLabel("PARAMETRI PROGETTO")
        header.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {THEME['highlight']}; padding: 20px;")
        header.setAlignment(Qt.AlignCenter)
        self.panel_layout.insertWidget(0, header) 

        sec = CollapsibleSection("1. Fondo", self.scroll_content, expanded=False)
        self.panel_layout.addWidget(sec)
        self.add_entry(sec, "Lunghezza (L)", "L", "400")
        self.add_entry(sec, "Larghezza (W)", "W", "300")
        self.add_entry(sec, "Spessore", "thickness", "5.0")

        sec = CollapsibleSection("2. Fiancate", self.scroll_content, expanded=False)
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

        sec = CollapsibleSection("3. Testate", self.scroll_content, expanded=False)
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

        sec = CollapsibleSection("4. Platform", self.scroll_content, expanded=False)
        self.panel_layout.addWidget(sec)
        self.cb_plat_active = QCheckBox("Attiva Platform")
        self.cb_plat_active.setChecked(True)
        self.cb_plat_active.toggled.connect(self.refresh)
        sec.add_widget(self.cb_plat_active)
        self.add_entry(sec, "Altezza Fascia", "fascia_h", "35")
        self.add_entry(sec, "Larg. Lembo Ext", "plat_flap_w", "40")
        self.add_entry(sec, "Gap Platform", "plat_gap", "3")

        sec = CollapsibleSection("5. Lembi Interni", self.scroll_content, expanded=False)
        self.panel_layout.addWidget(sec)
        self.add_entry(sec, "Lunghezza", "F", "120")
        
        self.btn_play = QPushButton("▶ STEP-BY-STEP (1/5)")
        self.btn_play.setStyleSheet(f"background-color: {THEME['line_crease']}; color: white; padding: 15px; font-weight: bold; border-radius: 5px;")
        self.btn_play.clicked.connect(self.next_animation_step)
        self.panel_layout.addSpacing(20)
        self.panel_layout.addWidget(self.btn_play)
        
        self.btn_anim_all = QPushButton("▶ ANIMAZIONE COMPLETA")
        self.btn_anim_all.setStyleSheet(f"background-color: #FF9800; color: black; padding: 15px; font-weight: bold; border-radius: 5px; margin-top: 10px;")
        self.btn_anim_all.clicked.connect(self.start_combined_animation)
        self.panel_layout.addWidget(self.btn_anim_all)
        
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

    def on_tab_change(self, idx):
        if idx == 1: self.refresh()

    def refresh(self):
        params = {}
        for k in self.inputs: params[k] = self.get_float(k)
        params['fianchi_shape'] = 'ferro' if self.cb_fianchi_shape.isChecked() else 'rect'
        params['fianchi_r_active'] = self.cb_fianchi_r.isChecked()
        params['testate_shape'] = 'ferro' if self.cb_testate_shape.isChecked() else 'rect'
        params['testate_r_active'] = self.cb_testate_r.isChecked()
        params['platform_active'] = self.cb_plat_active.isChecked()

        try:
            model = BoxModel(params)
            polygons, cut_lines, crease_lines = model.get_data()
            self.canvas_2d.set_data(polygons, cut_lines, crease_lines, 
                                 params['L'], params['W'], 
                                 params['h_fianchi'], params['h_testate'], params['F'])
            self.viewer_3d.set_params(params)
            self.viewer_3d.update_angles(self.anim_angles)
        except Exception:
            traceback.print_exc()

    def next_animation_step(self):
        if self.is_animating: return
        self.is_combined_anim = False
        self.tabs.setCurrentIndex(1)
        steps = ['lembi', 'testate', 'fianchi', 'fasce', 'ext']
        if self.step_idx >= len(steps):
            self.step_idx = 0
            self.anim_angles = {k:0 for k in self.anim_angles}
            self.refresh()
            self.btn_play.setText(f"▶ STEP-BY-STEP (1/{len(steps)})")
            return
        self.target_key = steps[self.step_idx]
        self.anim_progress = 0.0
        self.is_animating = True
        self.timer.start(20) 

    def start_combined_animation(self):
        if self.is_animating: return
        self.tabs.setCurrentIndex(1)
        self.anim_angles = {k:0 for k in self.anim_angles}
        self.is_combined_anim = True
        self.anim_progress = 0.0
        self.is_animating = True
        self.timer.start(20)

    def get_interp_angle(self, t, start_t, end_t):
        if t < start_t: return 0.0
        if t > end_t: return 90.0
        ratio = (t - start_t) / (end_t - start_t)
        return ratio * 90.0

    def update_frame(self):
        if self.is_combined_anim:
            self.anim_progress += 0.01
            t = self.anim_progress
            self.anim_angles['lembi'] = self.get_interp_angle(t, 0.0, 1.0)
            self.anim_angles['testate'] = self.get_interp_angle(t, 0.0, 1.0)
            self.anim_angles['fianchi'] = self.get_interp_angle(t, 0.5, 1.5)
            self.anim_angles['fasce'] = self.get_interp_angle(t, 1.5, 2.5)
            self.anim_angles['ext'] = self.get_interp_angle(t, 2.5, 3.5)
            
            if self.anim_progress >= 3.5:
                self.timer.stop()
                self.is_animating = False
                self.is_combined_anim = False
                
            self.viewer_3d.update_angles(self.anim_angles)
            return

        self.anim_progress += 0.05
        if self.anim_progress >= 1.0:
            self.anim_progress = 1.0
            self.timer.stop()
            self.is_animating = False
            self.step_idx += 1
            steps = ['lembi', 'testate', 'fianchi', 'fasce', 'ext']
            if self.step_idx >= len(steps):
                self.btn_play.setText("↺ RESET ANIMAZIONE")
            else:
                self.btn_play.setText(f"▶ STEP-BY-STEP ({self.step_idx + 1}/{len(steps)})")
        
        self.anim_angles[self.target_key] = self.anim_progress * 90
        self.viewer_3d.update_angles(self.anim_angles)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PackagingApp()
    window.show()
    sys.exit(app.exec())