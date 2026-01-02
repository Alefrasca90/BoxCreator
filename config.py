from PySide6.QtGui import QColor

THEME = {
    "bg_ui": "#2E2E2E",
    "bg_panel": "#3C3F41",
    "fg_text": "#F0F0F0",
    "bg_draw": "#404040", # <--- Correzione crash
    
    # 2D Colors
    "cardboard": "#E0C0A0",
    "line_cut": "#000000",
    "line_crease": "#00C853",
    
    # 3D Colors
    "white_opaque": QColor(240, 240, 240, 255),
    "brown_opaque": QColor(139, 100, 60, 255),
    "highlight": "#81D4FA"
}