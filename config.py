from PySide6.QtGui import QColor

THEME = {
    "bg_ui": "#121212",
    "bg_panel": "#3C3F41",
    "fg_text": "#F0F0F0",
    "bg_draw": "#404040",
    "highlight": "#81D4FA",
    "cardboard": "#E0C0A0",
    "line_cut": "#000000",
    "line_crease": "#00C853",
    
    # Colori 3D OpenGL (RGBA float)
    # Bianco reso ancora più grigio (0.75) per evitare che "bruci" con le luci forti
    "gl_white": (0.75, 0.75, 0.75, 1.0),
    "gl_brown": (0.63, 0.51, 0.39, 1.0),
    "gl_brown_dark": (0.35, 0.25, 0.18, 1.0),
    "gl_edge": (0.0, 0.0, 0.0, 1.0),
}