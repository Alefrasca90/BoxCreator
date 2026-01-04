import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QLabel)
from PySide6.QtCore import Qt
from config import THEME

class GlueTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # Etichetta descrittiva
        lbl_info = QLabel("Tabella Encoder Colla - Pistola Superiore (mm Interi)")
        lbl_info.setStyleSheet(f"color: {THEME['fg_text']}; font-weight: bold; margin-bottom: 5px; font-size: 14px;")
        lbl_info.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(lbl_info)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
        # Configurazione Colonne: 4 Ugelli x 2 stati (ON/OFF) = 8 colonne
        self.table.setColumnCount(8)
        
        # Creazione Intestazioni
        headers = []
        for i in range(1, 5):
            headers.extend([f"Ugello {i}\nON", f"Ugello {i}\nOFF"])
        self.table.setHorizontalHeaderLabels(headers)
        
        # Stile Tabella (Tema Scuro + Header Blu)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['bg_ui']};
                gridline-color: #555;
                color: {THEME['fg_text']};
                font-size: 14px;
                border: 1px solid #444;
            }}
            QHeaderView::section {{
                background-color: #4A90E2; 
                color: white;
                font-weight: bold;
                border: 1px solid #333;
                padding: 6px;
                height: 40px;
            }}
            QTableCornerButton::section {{ background-color: #4A90E2; }}
            QTableWidget::item {{ padding: 5px; }}
            QTableWidget::item:selected {{ background-color: {THEME['highlight']}; color: black; }}
        """)
        
        # Adatta le colonne alla larghezza disponibile
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Imposta SEMPRE 6 righe fisse per i tratti
        self.table.setRowCount(6)
        
        # Header Verticale (Tratto 1...6)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setStyleSheet(f"background-color: {THEME['bg_panel']}; color: {THEME['fg_text']};")
        
        # Imposta le etichette delle righe una volta sola
        for row in range(6):
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(f"Tratto {row + 1}"))
        
        # Colori righe alternati
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet() + f"QTableWidget {{ alternate-background-color: {THEME['bg_panel']}; }}")

    def update_data(self, glue_lines, all_polys):
        """
        Popola la tabella per UNA SOLA PISTOLA (Lato Superiore/Y<0).
        - 6 righe fisse.
        - Valori interi in mm.
        - 0 = Estremità sinistra assoluta del fustellato.
        """
        
        # 1. Pulisce la tabella (riempie tutto con "0" per default)
        self.clear_table_values()
        
        # 2. Trova il punto zero (X Minima globale tra tutti i poligoni)
        if not all_polys: return
        
        all_x = []
        for poly in all_polys:
            for x, y in poly['coords']:
                all_x.append(x)
        
        if not all_x: return
        min_x_global = min(all_x) # Punto "0" dell'encoder
        
        # 3. Organizza i dati per Ugello (0-3) filtrando per la Pistola Superiore
        # nozzle_data[ugello_idx] = [ (start_mm, end_mm), ... ]
        nozzle_data = {0: [], 1: [], 2: [], 3: []}
        
        for lines, idx, pid in glue_lines:
            if idx not in nozzle_data: continue
            
            p1, p2 = lines[0], lines[1]
            
            # --- FILTRO PISTOLA ---
            # Consideriamo solo i tratti con Y < 0 (Parte Alta del disegno 2D)
            # Se volessi la pistola inferiore, useresti p1[1] > 0
            if p1[1] > 0: 
                continue 

            # Calcolo coordinate assolute (Left-to-Right)
            x1_abs = p1[0] - min_x_global
            x2_abs = p2[0] - min_x_global
            
            # Ordina (Start < End) e CONVERTE IN INTERI ARROTONDATI
            start_val = min(x1_abs, x2_abs)
            end_val = max(x1_abs, x2_abs)
            
            start_int = int(round(start_val))
            end_int = int(round(end_val))
            
            nozzle_data[idx].append((start_int, end_int))
            
        # 4. Popola le celle
        # Per ogni ugello, ordiniamo i tratti e riempiamo le prime N righe
        for ugello_idx in range(4):
            # Ordina per posizione Start (da sinistra a destra)
            tratti = sorted(nozzle_data[ugello_idx], key=lambda x: x[0])
            
            # Prendiamo solo i primi 6 tratti (se ce ne sono di più, li ignoriamo come da specifica "max 6")
            tratti = tratti[:6]
            
            col_on = ugello_idx * 2
            col_off = col_on + 1
            
            for row in range(6):
                val_on = "0"
                val_off = "0"
                
                # Se esiste un tratto per questa riga, usiamo i valori
                if row < len(tratti):
                    s, e = tratti[row]
                    val_on = str(s)
                    val_off = str(e)
                
                # Scriviamo in tabella
                item_on = QTableWidgetItem(val_on)
                item_off = QTableWidgetItem(val_off)
                
                item_on.setTextAlignment(Qt.AlignCenter)
                item_off.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(row, col_on, item_on)
                self.table.setItem(row, col_off, item_off)

    def clear_table_values(self):
        """Riempie tutte le celle con '0' prima di aggiornare"""
        for row in range(6):
            for col in range(8):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)