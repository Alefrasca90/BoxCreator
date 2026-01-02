from PySide6.QtGui import QColor

THEME = {
    "bg_ui": "#2E2E2E",
    "bg_panel": "#3C3F41",
    "fg_text": "#F0F0F0",
    "bg_draw": "#404040",
    
    # 2D Colors
    "cardboard": "#E0C0A0",
    "line_cut": "#000000",
    "line_crease": "#00C853",
    
    # 3D Colors - Stile CAD
    # Alpha 255 = Completamente opaco (niente effetto vetro)
    "white_opaque": QColor(230, 230, 230, 255),
    "brown_opaque": QColor(210, 180, 140, 255), # Cartone più chiaro e realistico
    "brown_dark":   QColor(139, 100, 60, 255),  # Per i bordi/spessore
    "highlight": "#81D4FA",
    
    # Colori per modalità trasparenza
    "white_alpha":  QColor(240, 240, 240, 150),
    "brown_alpha":  QColor(139, 100, 60, 150)
}