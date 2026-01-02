from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                               QDoubleSpinBox, QComboBox, QCheckBox, QLabel, QScrollArea)
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtCore import Signal, Qt, QPointF
from config import THEME

# --- CLASSE DISEGNO 2D ---
class DrawingArea2D(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_color = QColor(THEME["bg_draw"])
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

        for p in self.polygons:
            pts = [to_s(x,y) for x,y in p['coords']]
            col = QColor(THEME["cardboard"])
            if p['type'] == 'fondo': col = col.darker(110)
            elif p['type'] == 'lembi': col = col.lighter(110)
            painter.setBrush(col)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(QPolygonF(pts))

        painter.setPen(QPen(QColor(THEME["line_cut"]), 2))
        for p1, p2 in self.cut_lines: painter.drawLine(to_s(*p1), to_s(*p2))
            
        pen_cr = QPen(QColor(THEME["line_crease"]), 2)
        pen_cr.setStyle(Qt.DashLine)
        painter.setPen(pen_cr)
        for p1, p2 in self.crease_lines: painter.drawLine(to_s(*p1), to_s(*p2))


# --- CLASSE PARAMETRI ---
class ParameterPanel(QWidget):
    params_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background-color: {THEME['bg_ui']}; border: none;")
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {THEME['bg_ui']}; color: {THEME['fg_text']};")
        vbox = QVBoxLayout(container)

        # 1. Dimensioni Base
        gb_dim = QGroupBox("Dimensioni Base")
        gb_dim.setStyleSheet(self._group_style())
        form_dim = QFormLayout()
        
        self.inp_L = self._make_spin(300, 10, 2000)
        self.inp_W = self._make_spin(200, 10, 2000)
        self.inp_T = self._make_spin(5, 1, 20)
        self.inp_F = self._make_spin(85, 10, 200) # Default 85
        
        form_dim.addRow("Lunghezza (L):", self.inp_L)
        form_dim.addRow("Larghezza (W):", self.inp_W)
        form_dim.addRow("Spessore (T):", self.inp_T)
        form_dim.addRow("Lembi Incolla (F):", self.inp_F)
        gb_dim.setLayout(form_dim)
        vbox.addWidget(gb_dim)

        # 2. Fianchi e Testate (Creo i widget ma la logica la gestisco dopo)
        self.fianchi_panel = self._create_side_panel("Fianchi", default_h=100)
        vbox.addWidget(self.fianchi_panel['group'])

        self.testate_panel = self._create_side_panel("Testate", default_h=100)
        vbox.addWidget(self.testate_panel['group'])

        # 3. Piattaforma
        gb_plat = QGroupBox("Piattaforma Interna")
        gb_plat.setStyleSheet(self._group_style())
        form_plat = QFormLayout()
        
        self.chk_plat = QCheckBox("Attiva Piattaforma")
        # Quando cambio la piattaforma, devo aggiornare la UI dei fianchi (per lo scasso)
        self.chk_plat.stateChanged.connect(self.update_ui_state) 
        self.chk_plat.stateChanged.connect(self.emit_change)
        
        self.inp_fascia = self._make_spin(30, 10, 300)
        self.inp_plat_flap = self._make_spin(40, 10, 300)
        
        form_plat.addRow(self.chk_plat)
        form_plat.addRow("Altezza Fascia:", self.inp_fascia)
        form_plat.addRow("Lembo Piattaforma:", self.inp_plat_flap)
        gb_plat.setLayout(form_plat)
        vbox.addWidget(gb_plat)

        vbox.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Inizializza lo stato corretto delle abilitazioni/disabilitazioni
        self.update_ui_state()

    def _group_style(self):
        return f"QGroupBox {{ font-weight: bold; border: 1px solid #555; border-radius: 5px; margin-top: 10px; color: {THEME['highlight']}; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px; }}"

    def _make_spin(self, val, min_v, max_v):
        sb = QDoubleSpinBox()
        sb.setRange(min_v, max_v); sb.setValue(val)
        sb.setStyleSheet(f"background-color: {THEME['bg_draw']}; color: white; border: 1px solid #555;")
        sb.valueChanged.connect(self.emit_change)
        return sb

    def _create_side_panel(self, title, default_h):
        gb = QGroupBox(title)
        gb.setStyleSheet(self._group_style())
        form = QFormLayout()
        
        inp_h = self._make_spin(default_h, 10, 1000)
        combo_shape = QComboBox()
        combo_shape.addItems(["Rettangolare", "Ferro di Cavallo"])
        combo_shape.setStyleSheet(f"background-color: {THEME['bg_draw']}; color: white;")
        
        # Parametri specifici "Ferro" / "Scasso"
        inp_cutout = self._make_spin(150, 10, 1000)
        inp_h_low = self._make_spin(60, 10, 1000)
        
        # Raddoppi
        chk_raddoppi = QCheckBox("Raddoppi (Rinforzi)")
        chk_raddoppi.setStyleSheet("color: white;")
        inp_r_h = self._make_spin(30, 10, 300)

        form.addRow("Altezza:", inp_h)
        form.addRow("Forma:", combo_shape)
        form.addRow("Larghezza Scasso:", inp_cutout)
        form.addRow("Altezza Minima:", inp_h_low)
        form.addRow(chk_raddoppi)
        form.addRow("Altezza Rinforzo:", inp_r_h)
        
        gb.setLayout(form)
        
        # Connessioni
        combo_shape.currentTextChanged.connect(self.update_ui_state)
        combo_shape.currentTextChanged.connect(self.emit_change)
        chk_raddoppi.stateChanged.connect(self.update_ui_state)
        chk_raddoppi.stateChanged.connect(self.emit_change)
        
        return {
            'group': gb, 'h': inp_h, 'shape': combo_shape, 
            'cutout': inp_cutout, 'h_low': inp_h_low,
            'r_active': chk_raddoppi, 'r_h': inp_r_h
        }

    def update_ui_state(self):
        """Gestisce le dipendenze complesse tra i widget"""
        
        # --- LOGICA FIANCHI ---
        is_ferro_f = (self.fianchi_panel['shape'].currentText() == "Ferro di Cavallo")
        is_plat = self.chk_plat.isChecked()
        
        # Lo SCASSO è attivo se è "Ferro di Cavallo" OPPURE se c'è la "Piattaforma"
        # (perché serve lo spazio per i lembi)
        scasso_active_f = is_ferro_f or is_plat
        self.fianchi_panel['cutout'].setEnabled(scasso_active_f)
        self.fianchi_panel['h_low'].setEnabled(scasso_active_f)
        
        # I RADDOPPI sono figli SOLO del "Ferro di Cavallo"
        # Se non è ferro, si disattivano e si toglie la spunta
        if not is_ferro_f:
            self.fianchi_panel['r_active'].setChecked(False)
            self.fianchi_panel['r_active'].setEnabled(False)
        else:
            self.fianchi_panel['r_active'].setEnabled(True)
            
        # L'altezza rinforzo è attiva solo se i raddoppi sono attivi
        self.fianchi_panel['r_h'].setEnabled(self.fianchi_panel['r_active'].isChecked())


        # --- LOGICA TESTATE ---
        is_ferro_t = (self.testate_panel['shape'].currentText() == "Ferro di Cavallo")
        
        # Per le testate, lo scasso è legato solo al ferro (per ora)
        self.testate_panel['cutout'].setEnabled(is_ferro_t)
        self.testate_panel['h_low'].setEnabled(is_ferro_t)
        
        # Raddoppi testate
        if not is_ferro_t:
            self.testate_panel['r_active'].setChecked(False)
            self.testate_panel['r_active'].setEnabled(False)
        else:
            self.testate_panel['r_active'].setEnabled(True)
            
        self.testate_panel['r_h'].setEnabled(self.testate_panel['r_active'].isChecked())


    def emit_change(self):
        p = {
            'L': self.inp_L.value(),
            'W': self.inp_W.value(),
            'thickness': self.inp_T.value(),
            'F': self.inp_F.value(),
            
            # Fianchi
            'h_fianchi': self.fianchi_panel['h'].value(),
            'fianchi_shape': 'ferro' if self.fianchi_panel['shape'].currentText() == "Ferro di Cavallo" else 'rect',
            'fianchi_cutout_w': self.fianchi_panel['cutout'].value(),
            'fianchi_h_low': self.fianchi_panel['h_low'].value(),
            'fianchi_r_active': self.fianchi_panel['r_active'].isChecked(),
            'fianchi_r_h': self.fianchi_panel['r_h'].value(),
            
            # Testate
            'h_testate': self.testate_panel['h'].value(),
            'testate_shape': 'ferro' if self.testate_panel['shape'].currentText() == "Ferro di Cavallo" else 'rect',
            'testate_cutout_w': self.testate_panel['cutout'].value(),
            'testate_h_low': self.testate_panel['h_low'].value(),
            'testate_r_active': self.testate_panel['r_active'].isChecked(),
            'testate_r_h': self.testate_panel['r_h'].value(),
            
            # Piattaforma
            'platform_active': self.chk_plat.isChecked(),
            'fascia_h': self.inp_fascia.value(),
            'plat_flap_w': self.inp_plat_flap.value()
        }
        self.params_changed.emit(p)