from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from config import THEME

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
                padding: 8px;
                border: none;
                font-weight: bold;
                border-bottom: 1px solid #555;
            }}
            QPushButton:hover {{ background-color: {THEME['bg_ui']}; }}
        """)
        self.btn_toggle.clicked.connect(self.toggle)
        self.layout.addWidget(self.btn_toggle)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(5, 5, 5, 10)
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