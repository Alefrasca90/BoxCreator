import tkinter as tk
from tkinter import ttk

# --- WIDGET PERSONALIZZATI ---
class CollapsibleSection(ttk.Frame):
    def __init__(self, parent, title, expanded=False):
        super().__init__(parent)
        self.expanded = expanded
        self.btn_toggle = ttk.Button(self, text=title, command=self.toggle, style="Toggle.TButton")
        self.btn_toggle.pack(fill="x", anchor="n")
        self.content_frame = ttk.Frame(self)
        if expanded:
            self.content_frame.pack(fill="x", expand=True, padx=5, pady=5)

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.content_frame.pack(fill="x", expand=True, padx=5, pady=5)
        else:
            self.content_frame.pack_forget()

# --- GEOMETRIA ---
class BoxModel:
    def __init__(self, params):
        self.p = params
        self.gap_base = 1.5 

    def _get_u_shape(self, L_base, H_full, orientation):
        """Genera punti per profilo a U"""
        prefix = "fianchi" if orientation in ['top', 'bottom'] else "testate"
        h_low = self.p.get(f'{prefix}_h_low', H_full * 0.6)
        shoulder = self.p.get(f'{prefix}_shoulder', L_base * 0.2)
        
        if h_low > H_full: h_low = H_full
        if shoulder * 2 > L_base: shoulder = L_base / 2 - 1
        if shoulder < 0: shoulder = 0

        # Coordinate base (Sistema locale TOP)
        pts = [
            (0, 0), (0, -H_full), 
            (shoulder, -H_full), (shoulder, -h_low), 
            (L_base - shoulder, -h_low), (L_base - shoulder, -H_full),
            (L_base, -H_full), (L_base, 0)
        ]
        sh_line_raw = [(0, -H_full), (shoulder, -H_full)]

        final_coords = []
        final_sh_line = []

        for x, y in pts:
            if orientation == 'top': final_coords.append((x, y))
            elif orientation == 'bottom': final_coords.append((x, -y))
            elif orientation == 'left': final_coords.append((y, x))
            elif orientation == 'right': final_coords.append((-y, x))
        
        for x, y in sh_line_raw:
             if orientation == 'top': final_sh_line.extend([x, y])
             elif orientation == 'bottom': final_sh_line.extend([x, -y])
             elif orientation == 'left': final_sh_line.extend([y, x])
             elif orientation == 'right': final_sh_line.extend([-y, x])

        return final_coords, final_sh_line

    def _get_flap_geo(self, corner, h_testata, f_len):
        """Calcola geometria lembo"""
        T = self.p.get('thickness', 3.0)
        gap = self.gap_base + T 
        
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        shoulder = self.p.get('fianchi_shoulder', 0)
        h_fianco_full = self.p.get('h_fianchi', h_testata)
        h_fianco_low = self.p.get('fianchi_h_low', h_fianco_full)
        
        cut_depth = h_fianco_full - h_fianco_low
        if cut_depth < 0: cut_depth = 0
        
        u_inner = gap 
        u_outer = h_testata 
        u_outer_low = h_testata - cut_depth

        pts_local = []
        
        if is_ferro and f_len > shoulder:
            pts_local = [
                (u_inner, 0), (u_inner, f_len), (u_outer_low, f_len),
                (u_outer_low, shoulder), (u_outer, shoulder), (u_outer, 0)
            ]
        else:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer, f_len), (u_outer, 0)]

        final_pts = []
        for u, v in pts_local:
            gx, gy = 0, 0
            if corner == 'tl': gx, gy = -u, -v
            elif corner == 'tr': gx, gy = self.p['L'] + u, -v
            elif corner == 'bl': gx, gy = -u, self.p['W'] + v
            elif corner == 'br': gx, gy = self.p['L'] + u, self.p['W'] + v
            final_pts.append((gx, gy))

        # Nota: La linea di piega (chiusura su testata) non la aggiungiamo qui
        # perché la gestiremo disegnando il bordo della testata come verde.
        # Qui ritorniamo solo il perimetro di taglio del lembo.
        
        # Tutto il perimetro del lembo tranne l'ultimo segmento (che è quello aperto sulla testata)
        # In pts_local partiamo da u_inner,0 e finiamo a u_outer,0.
        # Quindi il taglio è tutto tranne il segmento che unisce Last->First (virtuale) o l'attacco?
        # I punti sono una "U". Il taglio è la sequenza dei punti.
        # La chiusura (Last Point -> First Point) è la linea di piega, ma è "aperta" geometricamente qui.
        
        cut_segments = []
        for i in range(len(final_pts)-1):
            cut_segments.append([final_pts[i], final_pts[i+1]])
            
        return final_pts, cut_segments

    def get_data(self):
        polygons = []
        cut_lines = []
        crease_lines = []
        dimensions = []
        
        L = self.p['L']
        W = self.p['W']
        H_f = self.p['h_fianchi']
        H_t = self.p['h_testate']
        F = self.p['F']

        ox = max(H_t, H_f) + 60
        oy = max(H_t, H_f) + F + 20 

        # --- 1. FONDO ---
        base_pts = [(ox, oy), (ox+L, oy), (ox+L, oy+W), (ox, oy+W)]
        polygons.append({'id': 'poly_fondo', 'coords': base_pts, 'color': '#EEEEEE'})
        
        # Pieghe Fondo
        crease_lines.append([(ox, oy), (ox+L, oy)])
        crease_lines.append([(ox+L, oy), (ox+L, oy+W)])
        crease_lines.append([(ox+L, oy+W), (ox, oy+W)])
        crease_lines.append([(ox, oy+W), (ox, oy)])

        dimensions.append({'id': 'dim_L', 'coords': [(ox, oy), (ox+L, oy)]})
        dimensions.append({'id': 'dim_W', 'coords': [(ox, oy), (ox, oy+W)]})

        # --- 2. FIANCATE ---
        for orient in ['top', 'bottom']:
            if self.p.get('fianchi_shape') == 'ferro':
                pts, sh_line = self._get_u_shape(L, H_f, orient)
                poly_pts = [(x+ox, y+oy) if orient=='top' else (x+ox, y+oy+W) for x,y in pts]
                
                sh_line = [sh_line[0]+ox, sh_line[1]+oy + (0 if orient=='top' else W), 
                           sh_line[2]+ox, sh_line[3]+oy + (0 if orient=='top' else W)]
                dimensions.append({'id': 'dim_fianchi_shoulder', 'coords': sh_line})
                
                h_low = self.p.get('fianchi_h_low', H_f*0.6)
                s_val = self.p.get('fianchi_shoulder', L*0.2)
                y_pos = oy-h_low if orient=='top' else oy+W+h_low
                dimensions.append({'id': 'dim_fianchi_h_low', 'coords': [(ox+s_val, y_pos), (ox+L-s_val, y_pos)]})
            else:
                poly_pts = [(ox, oy), (ox, oy-H_f), (ox+L, oy-H_f), (ox+L, oy)] if orient=='top' else \
                           [(ox, oy+W), (ox, oy+W+H_f), (ox+L, oy+W+H_f), (ox+L, oy+W)]
            
            polygons.append({'id': 'poly_fianchi', 'coords': poly_pts, 'color': 'white'})
            
            # Tagli Fiancate: Tutto tranne la base (che è già disegnata come piega del fondo)
            for i in range(len(poly_pts)-1):
                cut_lines.append([poly_pts[i], poly_pts[i+1]])

        dimensions.append({'id': 'dim_h_fianchi', 'coords': [(ox, oy), (ox, oy-H_f)]})

        # --- 3. TESTATE (CORRETTO PER PIEGE LEMBI) ---
        for orient in ['left', 'right']:
            if self.p.get('testate_shape') == 'ferro':
                pts, sh_line = self._get_u_shape(W, H_t, orient)
                off_x = ox if orient=='left' else ox+L
                poly_pts = [(x+off_x, y+oy) for x,y in pts]
                
                sh_line = [sh_line[0]+off_x, sh_line[1]+oy, sh_line[2]+off_x, sh_line[3]+oy]
                dimensions.append({'id': 'dim_testate_shoulder', 'coords': sh_line})
                
                h_low_t = self.p.get('testate_h_low', H_t*0.6)
                sh_val_t = self.p.get('testate_shoulder', W*0.2)
                x_pos = ox-h_low_t if orient=='left' else ox+L+h_low_t
                dimensions.append({'id': 'dim_testate_h_low', 'coords': [(x_pos, oy+sh_val_t), (x_pos, oy+W-sh_val_t)]})
            else:
                if orient == 'left': poly_pts = [(ox, oy), (ox-H_t, oy), (ox-H_t, oy+W), (ox, oy+W)]
                else: poly_pts = [(ox+L, oy), (ox+L+H_t, oy), (ox+L+H_t, oy+W), (ox+L, oy+W)]
            
            polygons.append({'id': 'poly_testate', 'coords': poly_pts, 'color': 'white'})
            
            # GESTIONE LINEE TESTATA (Pieghe vs Tagli)
            # poly_pts è una sequenza di punti.
            # Seg 0: Lato Alto (Attacco Lembo) -> PIEGA
            # Seg 1..N-1: Profilo Esterno -> TAGLIO
            # Seg N: Lato Basso (Attacco Lembo) -> PIEGA
            # Chiusura (Last->First): Base (Fondo) -> PIEGA (già fatta)
            
            # Lato Alto (Segmento 0) -> Piega Lembo 1
            crease_lines.append([poly_pts[0], poly_pts[1]])
            
            # Profilo Esterno (Segmenti intermedi) -> Taglio
            # Dal punto 1 al penultimo
            for i in range(1, len(poly_pts)-2):
                 cut_lines.append([poly_pts[i], poly_pts[i+1]])
                 
            # Lato Basso (Ultimo segmento della lista aperta) -> Piega Lembo 2
            crease_lines.append([poly_pts[-2], poly_pts[-1]])

        dimensions.append({'id': 'dim_h_testate', 'coords': [(ox, oy), (ox-H_t, oy)]})

        # --- 4. LEMBI ---
        corners = ['tl', 'tr', 'bl', 'br']
        for c in corners:
            pts, cuts = self._get_flap_geo(c, H_t, F)
            
            pts_off = [(x+ox, y+oy) for x,y in pts]
            cuts_off = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in cuts]
            
            polygons.append({'id': 'poly_lembi', 'coords': pts_off, 'color': 'white'})
            cut_lines.extend(cuts_off)

        # Dimensione F
        if len(polygons) > 0:
            l_pts = next((p['coords'] for p in polygons if p['id'] == 'poly_lembi'), None)
            if l_pts:
                 dimensions.append({'id': 'dim_F', 'coords': [l_pts[1], l_pts[2]]}) 

        return polygons, cut_lines, crease_lines, dimensions

# --- APP SETUP ---
class PackagingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Packaging CAD - Linee Corrette")
        self.geometry("1300x900")
        s = ttk.Style()
        s.configure("Toggle.TButton", font=("Segoe UI", 10, "bold"))
        self.params_vars = {}

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.canvas_scroll = tk.Canvas(self.paned, width=400, bg="#f5f5f5")
        self.scrollbar = ttk.Scrollbar(self.paned, orient="vertical", command=self.canvas_scroll.yview)
        self.scroll_frame = ttk.Frame(self.canvas_scroll)
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        self.canvas_scroll.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)
        
        self.paned.add(self.canvas_scroll, weight=0)
        self.paned.add(self.scrollbar, weight=0)

        self.draw_frame = ttk.Frame(self.paned)
        self.paned.add(self.draw_frame, weight=3)
        self.canvas = tk.Canvas(self.draw_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.build_ui()
        self.canvas.bind("<Configure>", lambda e: self.refresh())
        self.after(200, self.refresh)

    def build_ui(self):
        ttk.Label(self.scroll_frame, text="Parametri Fustella", font=("Segoe UI", 16, "bold")).pack(pady=15)

        sec_fondo = CollapsibleSection(self.scroll_frame, "1. Fondo & Materiale", expanded=True)
        sec_fondo.pack(fill="x", pady=2)
        self.add_entry(sec_fondo.content_frame, "Lunghezza (L)", "L", 400, "poly_fondo", "dim_L")
        self.add_entry(sec_fondo.content_frame, "Larghezza (W)", "W", 300, "poly_fondo", "dim_W")
        self.add_entry(sec_fondo.content_frame, "Spessore Cartone", "thickness", 5.0, "poly_fondo", "")

        sec_fianchi = CollapsibleSection(self.scroll_frame, "2. Fiancate", expanded=True)
        sec_fianchi.pack(fill="x", pady=2)
        self.add_entry(sec_fianchi.content_frame, "Altezza Fianco", "h_fianchi", 100, "poly_fianchi", "dim_h_fianchi")
        self.params_vars['fianchi_shape'] = tk.StringVar(value="ferro")
        cb_f = ttk.Checkbutton(sec_fianchi.content_frame, text="Ferro di Cavallo", variable=self.params_vars['fianchi_shape'], 
                               onvalue="ferro", offvalue="rect", command=lambda: self.toggle_shape_opts('fianchi'))
        cb_f.pack(anchor="w", pady=5)
        self.f_ferro_frame = ttk.Frame(sec_fianchi.content_frame)
        self.f_ferro_frame.pack(fill="x", padx=10)
        self.add_entry(self.f_ferro_frame, "Altezza Minima", "fianchi_h_low", 60, "poly_fianchi", "dim_fianchi_h_low")
        self.add_entry(self.f_ferro_frame, "Spalla Laterale", "fianchi_shoulder", 80, "poly_fianchi", "dim_fianchi_shoulder")

        sec_testate = CollapsibleSection(self.scroll_frame, "3. Testate", expanded=True)
        sec_testate.pack(fill="x", pady=2)
        self.add_entry(sec_testate.content_frame, "Altezza Testata", "h_testate", 100, "poly_testate", "dim_h_testate")
        self.params_vars['testate_shape'] = tk.StringVar(value="rect")
        cb_t = ttk.Checkbutton(sec_testate.content_frame, text="Ferro di Cavallo", variable=self.params_vars['testate_shape'], 
                               onvalue="ferro", offvalue="rect", command=lambda: self.toggle_shape_opts('testate'))
        cb_t.pack(anchor="w", pady=5)
        self.t_ferro_frame = ttk.Frame(sec_testate.content_frame)
        self.add_entry(self.t_ferro_frame, "Altezza Minima", "testate_h_low", 60, "poly_testate", "dim_testate_h_low")
        self.add_entry(self.t_ferro_frame, "Spalla Testata", "testate_shoulder", 50, "poly_testate", "dim_testate_shoulder")

        sec_lembi = CollapsibleSection(self.scroll_frame, "4. Incollaggio")
        sec_lembi.pack(fill="x", pady=2)
        self.add_entry(sec_lembi.content_frame, "Lembo Incollaggio", "F", 120, "poly_lembi", "dim_F")
        ttk.Label(sec_lembi.content_frame, text="Attacco lembo è ora tratteggiato (Piega)", font=("Arial", 9), foreground="#2E7D32").pack(pady=5)

    def toggle_shape_opts(self, section):
        val = self.params_vars[f'{section}_shape'].get()
        frame = self.f_ferro_frame if section == 'fianchi' else self.t_ferro_frame
        if val == 'ferro': frame.pack(fill="x", padx=10)
        else: frame.pack_forget()
        self.refresh()

    def add_entry(self, parent, label, key, val, poly, dim):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=2)
        ttk.Label(f, text=label, width=18).pack(side="left")
        if key not in self.params_vars: self.params_vars[key] = tk.DoubleVar(value=val)
        e = ttk.Entry(f, textvariable=self.params_vars[key], width=8)
        e.pack(side="right")
        e.bind("<Enter>", lambda e: self.highlight(poly, dim, True))
        e.bind("<Leave>", lambda e: self.highlight(poly, dim, False))
        e.bind("<KeyRelease>", lambda e: self.refresh())

    def highlight(self, poly, dim, active):
        fill = "#FFF176" if active else "white"
        if poly == 'poly_fondo' and not active: fill = "#EEEEEE"
        self.canvas.itemconfigure(poly, fill=fill)
        if dim:
            st = "normal" if active else "hidden"
            self.canvas.itemconfigure(dim, state=st)

    def refresh(self):
        self.canvas.delete("all")
        params = {}
        try:
            for k, v in self.params_vars.items(): params[k] = v.get()
        except: return

        model = BoxModel(params)
        polygons, cut_lines, crease_lines, dimensions = model.get_data()

        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 50: return
        
        tot_w = params['L'] + params['h_testate']*2 + 100
        tot_h = params['W'] + params['h_fianchi']*2 + params['F']*2 + 100
        scale = min(cw/tot_w, ch/tot_h) * 0.85
        
        ox_model = max(params['h_testate'], params['h_fianchi']) + 60
        oy_model = max(params['h_testate'], params['h_fianchi']) + params['F'] + 20
        
        dx = (cw/2) - (ox_model + params['L']/2)*scale
        dy = (ch/2) - (oy_model + params['W']/2)*scale

        for p in polygons:
            pts = [c for x, y in p['coords'] for c in (x*scale+dx, y*scale+dy)]
            self.canvas.create_polygon(pts, fill=p['color'], outline="", tags=p['id'])

        # Cordonature (Pieghe)
        for line in crease_lines:
            pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
            self.canvas.create_line(pts, fill="#2E7D32", width=2, dash=(5, 3))

        # Tagli
        for line in cut_lines:
            pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
            self.canvas.create_line(pts, fill="black", width=2, capstyle=tk.ROUND)

        for d in dimensions:
            pts = [c for x, y in d['coords'] for c in (x*scale+dx, y*scale+dy)]
            self.canvas.create_line(pts, fill="blue", width=4, state="hidden", tags=d['id'])

if __name__ == "__main__":
    app = PackagingApp()
    app.mainloop()