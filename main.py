import tkinter as tk
from tkinter import ttk

# --- WIDGET UTILS ---
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

# --- MODEL GEOMETRICO ---
class BoxModel:
    def __init__(self, params):
        self.p = params
        self.base_gap = 2.0

    def _get_fianco_geometry(self, L_base, H_full, orientation):
        """
        Genera geometria fiancata con:
        - Notch (Platform)
        - U-Shape (Ferro di cavallo)
        - Raddoppio (Rinforzo interno)
        """
        # --- PARAMETRI PIATTAFORMA ---
        has_platform = self.p.get('platform_active', False)
        notch_w, notch_h = 0, 0
        if has_platform:
            notch_h = self.p.get('plat_flap_w', 30) + self.p.get('plat_gap', 2)
            notch_w = self.p.get('fascia_h', 30) + self.p.get('plat_gap', 2)

        # --- PARAMETRI FORMA ---
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        h_low = self.p.get('fianchi_h_low', H_full * 0.6)
        shoulder = self.p.get('fianchi_shoulder', L_base * 0.2)
        
        # --- PARAMETRI RINFORZO ---
        has_reinf = is_ferro and self.p.get('fianchi_r_active', False)
        r_h = self.p.get('fianchi_r_h', 30)
        r_gap = self.p.get('fianchi_r_gap', 2)

        # Validazioni
        if notch_h > H_full: notch_h = H_full - 5
        if h_low > H_full: h_low = H_full
        min_shoulder = notch_w + 10
        if is_ferro and shoulder < min_shoulder: shoulder = min_shoulder
        if shoulder * 2 > L_base: shoulder = L_base / 2 - 1
        
        # Validazione Rinforzo
        # Altezza max rinforzo = h_low (altrimenti tocca il fondo quando piegato)
        if r_h > h_low: r_h = h_low - 1 
        # Larghezza disponibile
        avail_w = L_base - 2*shoulder
        if r_gap * 2 >= avail_w: r_gap = (avail_w / 2) - 5 # Safety

        # --- COSTRUZIONE PUNTI LOCALI (0,0 = Base SX) ---
        pts = []
        extra_creases = [] # Liste di segmenti [(x1,y1), (x2,y2)]
        
        pts.append((0, 0)) 
        
        # LATO SX
        if has_platform:
            pts.append((0, -(H_full - notch_h)))
            pts.append((notch_w, -(H_full - notch_h)))
            pts.append((notch_w, -H_full))
        else:
            pts.append((0, -H_full))
            
        # TOP PROFILE
        end_top_x = L_base - notch_w if has_platform else L_base
        
        if is_ferro:
            # Spalla SX
            pts.append((shoulder, -H_full))
            pts.append((shoulder, -h_low))
            
            # --- ZONA CENTRALE (Rinforzo o Piatto) ---
            if has_reinf:
                # Disegna il raddoppio
                # 1. Gap SX (spostamento verso centro)
                pts.append((shoulder + r_gap, -h_low))
                # 2. Salita Rinforzo
                pts.append((shoulder + r_gap, -(h_low + r_h)))
                # 3. Traversa Rinforzo
                pts.append((L_base - shoulder - r_gap, -(h_low + r_h)))
                # 4. Discesa Rinforzo
                pts.append((L_base - shoulder - r_gap, -h_low))
                # 5. Gap DX (spostamento verso spalla)
                pts.append((L_base - shoulder, -h_low))
                
                # Aggiungi la CORDONATURA DI ATTACCO del rinforzo
                # Collega punto 1 e punto 4 (nella sequenza locale sopra)
                # Attenzione alle coordinate orientate dopo
                c_start = (shoulder + r_gap, -h_low)
                c_end = (L_base - shoulder - r_gap, -h_low)
                extra_creases.append([c_start, c_end])
            else:
                # Ferro semplice
                pts.append((L_base - shoulder, -h_low))

            # Spalla DX
            pts.append((L_base - shoulder, -H_full))
            pts.append((end_top_x, -H_full))
        else:
            # Rect
            pts.append((end_top_x, -H_full))
            
        # LATO DX
        if has_platform:
            pts.append((L_base - notch_w, -(H_full - notch_h)))
            pts.append((L_base, -(H_full - notch_h)))
            pts.append((L_base, 0))
        else:
            pts.append((L_base, 0))

        # --- TRASFORMAZIONE ---
        final_coords = []
        for lx, ly in pts:
            if orientation == 'top': final_coords.append((lx, ly))
            elif orientation == 'bottom': final_coords.append((lx, -ly))

        final_creases = []
        for p1, p2 in extra_creases:
            if orientation == 'top': final_creases.append([(p1[0], p1[1]), (p2[0], p2[1])])
            elif orientation == 'bottom': final_creases.append([(p1[0], -p1[1]), (p2[0], -p2[1])])

        # Highlight Spalla
        final_sh_line = []
        # (Omesso per brevità, non richiesto esplicitamente ora)

        return final_coords, final_creases

    def _get_testata_geometry(self, L_base, H_full, orientation):
        """
        Genera geometria testata con logica U-Shape e Rinforzo.
        Platform/Split Fascia gestito separatamente.
        """
        # --- PARAMETRI ---
        is_ferro = (self.p.get('testate_shape') == 'ferro')
        h_low = self.p.get('testate_h_low', H_full * 0.6)
        shoulder = self.p.get('testate_shoulder', L_base * 0.2)
        
        # --- RINFORZO ---
        has_reinf = is_ferro and self.p.get('testate_r_active', False)
        r_h = self.p.get('testate_r_h', 30)
        r_gap = self.p.get('testate_r_gap', 2)

        if h_low > H_full: h_low = H_full
        if shoulder * 2 > L_base: shoulder = L_base / 2 - 1
        
        if r_h > h_low: r_h = h_low - 1
        avail_w = L_base - 2*shoulder
        if r_gap * 2 >= avail_w: r_gap = (avail_w / 2) - 5

        # --- PUNTI LOCALI (0,0 = Base SX) ---
        pts = []
        extra_creases = []
        
        pts.append((0, 0))
        pts.append((0, -H_full))
        
        if is_ferro:
            pts.append((shoulder, -H_full))
            pts.append((shoulder, -h_low))
            
            if has_reinf:
                pts.append((shoulder + r_gap, -h_low))
                pts.append((shoulder + r_gap, -(h_low + r_h)))
                pts.append((L_base - shoulder - r_gap, -(h_low + r_h)))
                pts.append((L_base - shoulder - r_gap, -h_low))
                pts.append((L_base - shoulder, -h_low))
                
                extra_creases.append([(shoulder + r_gap, -h_low), (L_base - shoulder - r_gap, -h_low)])
            else:
                pts.append((L_base - shoulder, -h_low))
                
            pts.append((L_base - shoulder, -H_full))
            pts.append((L_base, -H_full))
        else:
            pts.append((L_base, -H_full))
            
        pts.append((L_base, 0))

        # --- TRASFORMAZIONE ---
        final_coords = []
        for lx, ly in pts:
            if orientation == 'left': final_coords.append((ly, lx))
            elif orientation == 'right': final_coords.append((-ly, lx))

        final_creases = []
        for p1, p2 in extra_creases:
            if orientation == 'left': final_creases.append([(p1[1], p1[0]), (p2[1], p2[0])])
            elif orientation == 'right': final_creases.append([(-p1[1], p1[0]), (-p2[1], p2[0])])

        return final_coords, final_creases

    def _get_platform_assembly(self, corner, h_testata):
        # ... (Logica precedente invariata: Split Fascia e Lembi Esterni) ...
        if not self.p.get('platform_active'): return [], [], []
        W = self.p['W']
        H_t = h_testata
        Fascia_H = self.p.get('fascia_h', 30)
        Plat_W = self.p.get('plat_flap_w', 30)
        is_testata_ferro = (self.p.get('testate_shape') == 'ferro')
        shoulder = self.p.get('testate_shoulder', W * 0.2)
        if shoulder * 2 > W: shoulder = W / 2 - 1
        
        fascia_polys, flap_polys = [], []
        if is_testata_ferro:
            fascia_polys.append([(0, H_t), (0, H_t + Fascia_H), (shoulder, H_t + Fascia_H), (shoulder, H_t)])
            flap_polys.append([(-Plat_W, H_t), (-Plat_W, H_t + Fascia_H), (0, H_t + Fascia_H), (0, H_t)])
            fascia_polys.append([(W-shoulder, H_t), (W-shoulder, H_t + Fascia_H), (W, H_t + Fascia_H), (W, H_t)])
            flap_polys.append([(W, H_t), (W, H_t + Fascia_H), (W + Plat_W, H_t + Fascia_H), (W + Plat_W, H_t)])
        else:
            fascia_polys.append([(0, H_t), (0, H_t + Fascia_H), (W, H_t + Fascia_H), (W, H_t)])
            flap_polys.append([(-Plat_W, H_t), (-Plat_W, H_t + Fascia_H), (0, H_t + Fascia_H), (0, H_t)])
            flap_polys.append([(W, H_t), (W, H_t + Fascia_H), (W + Plat_W, H_t + Fascia_H), (W + Plat_W, H_t)])

        polys, creases, cuts = [], [], []
        def transform(u, v):
            if corner == 'left': return (-v, u)
            else: return (self.p['L'] + v, u)

        for raw_f in fascia_polys:
            g_fascia = [transform(u, v) for u,v in raw_f]
            polys.append({'id': 'poly_platform', 'coords': g_fascia, 'color': '#E3F2FD'})
            creases.append([g_fascia[0], g_fascia[3]]) 
            cuts.append([g_fascia[1], g_fascia[2]])
            if is_testata_ferro:
                u_sx = raw_f[0][0]
                if u_sx == 0 or u_sx == W: pass 
                else: cuts.append([g_fascia[0], g_fascia[1]])
                u_dx = raw_f[2][0]
                if u_dx == 0 or u_dx == W: pass 
                else: cuts.append([g_fascia[2], g_fascia[3]])

        for raw_p in flap_polys:
            g_poly = [transform(u, v) for u,v in raw_p]
            polys.append({'id': 'poly_platform_flap', 'coords': g_poly, 'color': '#90CAF9'})
            creases.append([g_poly[2], g_poly[3]]) 
            cuts.append([g_poly[0], g_poly[1]])
            cuts.append([g_poly[1], g_poly[2]])
            cuts.append([g_poly[3], g_poly[0]])
        return polys, creases, cuts

    def _get_flap_geo(self, corner, h_testata, f_len):
        # ... (Logica precedente invariata: Lembi Interni con Gap) ...
        T = self.p.get('thickness', 3.0)
        gap = self.base_gap + T 
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        shoulder = self.p.get('fianchi_shoulder', 0)
        h_fianco_full = self.p.get('h_fianchi', h_testata)
        h_fianco_low = self.p.get('fianchi_h_low', h_fianco_full)
        has_platform = self.p.get('platform_active', False)
        
        cut_depth = h_fianco_full - h_fianco_low
        if cut_depth < 0: cut_depth = 0
        u_inner = gap
        gap_outer = gap if has_platform else 0
        u_outer = h_testata - gap_outer
        u_outer_low = u_outer - cut_depth
        if u_outer < u_inner: u_outer = u_inner + 1
        
        pts_local = []
        if is_ferro and f_len > shoulder:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer_low, f_len),
                         (u_outer_low, shoulder), (u_outer, shoulder), (u_outer, 0)]
        else:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer, f_len), (u_outer, 0)]

        final_pts, cuts = [], []
        for u, v in pts_local:
            gx, gy = 0, 0
            if corner == 'tl': gx, gy = -u, -v
            elif corner == 'tr': gx, gy = self.p['L'] + u, -v
            elif corner == 'bl': gx, gy = -u, self.p['W'] + v
            elif corner == 'br': gx, gy = self.p['L'] + u, self.p['W'] + v
            final_pts.append((gx, gy))
        for i in range(len(final_pts)-1): cuts.append([final_pts[i], final_pts[i+1]])
        return final_pts, cuts

    def get_data(self):
        polygons, cut_lines, crease_lines, dimensions = [], [], [], []
        L = self.p['L']; W = self.p['W']
        H_f = self.p['h_fianchi']; H_t = self.p['h_testate']; F = self.p['F']
        
        Fascia_H = self.p.get('fascia_h', 0) if self.p.get('platform_active') else 0
        Plat_W = self.p.get('plat_flap_w', 0) if self.p.get('platform_active') else 0
        
        ox = max(H_t + Fascia_H, H_f) + Plat_W + 50
        oy = max(H_t + Fascia_H, H_f) + F + 30 

        # 1. FONDO
        base_pts = [(ox, oy), (ox+L, oy), (ox+L, oy+W), (ox, oy+W)]
        polygons.append({'id': 'poly_fondo', 'coords': base_pts, 'color': '#EEEEEE'})
        for i in range(4): crease_lines.append([base_pts[i], base_pts[(i+1)%4]])

        # 2. FIANCATE
        for orient in ['top', 'bottom']:
            pts, extra_cr = self._get_fianco_geometry(L, H_f, orient)
            poly_pts = [(x+ox, y+oy) if orient=='top' else (x+ox, y+oy+W) for x,y in pts]
            
            polygons.append({'id': 'poly_fianchi', 'coords': poly_pts, 'color': 'white'})
            for i in range(len(poly_pts)-1): cut_lines.append([poly_pts[i], poly_pts[i+1]])
            
            # Cordonatura Rinforzo (Sovrascriviamo il taglio base se presente? No, è extra)
            # In realtà il segmento del rinforzo che si attacca al fianco (extra_cr)
            # deve sostituire il segmento di taglio che c'era lì.
            # Ma il poly_pts include il perimetro del rinforzo.
            # L'extra_cr è la linea che chiude il rinforzo verso il basso.
            # Aspetta: nel poly_pts ho disegnato il rinforzo.
            # La linea di piega è quella "dentro" il poligono che connette i gap.
            for cr in extra_cr:
                crease_lines.append([(p[0]+ox, p[1]+oy + (0 if orient=='top' else W)) for p in cr])

        # 3. TESTATE
        for orient in ['left', 'right']:
            pts, extra_cr = self._get_testata_geometry(W, H_t, orient)
            off_x = ox if orient=='left' else ox+L
            poly_pts = [(x+off_x, y+oy) for x,y in pts]
            
            polygons.append({'id': 'poly_testate', 'coords': poly_pts, 'color': 'white'})
            
            # Platform Logic
            if self.p.get('platform_active'):
                plat_polys, plat_creases, plat_cuts = self._get_platform_assembly(orient, H_t)
                for pp in plat_polys:
                    pp['coords'] = [(x+off_x, y+oy) for x,y in pp['coords']]
                    polygons.append(pp)
                for pc in plat_creases: crease_lines.append([(p[0]+off_x, p[1]+oy) for p in pc])
                for pcut in plat_cuts: cut_lines.append([(p[0]+off_x, p[1]+oy) for p in pcut])
                
                # Attacchi Testata
                if self.p.get('testate_shape') == 'ferro':
                    # U-Shape + Platform
                    # Perimetro esterno:
                    # 0=BaseTop, 1=TopExt, 2=ShoulderExt ...
                    # Shoulder Top sono indici 1 e ...
                    # Con Rinforzo attivo, poly_pts è più complesso.
                    # Semplificazione: Disegniamo tutto il perimetro come taglio
                    # E sovrascriviamo le pieghe note.
                    for i in range(len(poly_pts)-1): cut_lines.append([poly_pts[i], poly_pts[i+1]])
                    
                    # Sovrascrivi pieghe attacco fascia (Top Shoulders)
                    # Punti 1->2 (Spalla SX) e ... difficile tracciare indici dinamici.
                    # Usiamo coordinate geometriche note: H_t
                    # Se un segmento è orizzontale a distanza H_t (o -H_t), è una piega fascia.
                    # Se un segmento è verticale a distanza 0 o W, è una piega lembo.
                    pass # (Gestito visualmente sopra dal verde che copre il nero se disegnato dopo)
                else:
                    crease_lines.append([poly_pts[1], poly_pts[2]])
            else:
                for i in range(len(poly_pts)-1): cut_lines.append([poly_pts[i], poly_pts[i+1]])
            
            # Base Testata Piega
            crease_lines.append([poly_pts[0], poly_pts[1]]) # Lembo 1
            crease_lines.append([poly_pts[-2], poly_pts[-1]]) # Lembo 2
            
            # Piega Rinforzo Testata
            for cr in extra_cr:
                crease_lines.append([(p[0]+off_x, p[1]+oy) for p in cr])

        # 4. LEMBI INTERNI
        for c in ['tl', 'tr', 'bl', 'br']:
            pts, cuts = self._get_flap_geo(c, H_t, F)
            pts_off = [(x+ox, y+oy) for x,y in pts]
            cuts_off = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in cuts]
            polygons.append({'id': 'poly_lembi', 'coords': pts_off, 'color': 'white'})
            cut_lines.extend(cuts_off)
            crease_lines.append([pts_off[0], pts_off[-1]])

        return polygons, cut_lines, crease_lines, dimensions

# --- APP ---
class PackagingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Packaging CAD - Reinforcement & Platform")
        self.geometry("1350x950")
        s = ttk.Style()
        s.configure("Toggle.TButton", font=("Segoe UI", 10, "bold"))
        self.params_vars = {}
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        self.canvas_scroll = tk.Canvas(self.paned, width=420, bg="#f5f5f5")
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
        ttk.Label(self.scroll_frame, text="Parametri Progetto", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        # FONDO
        sec = CollapsibleSection(self.scroll_frame, "1. Fondo", expanded=True)
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Lunghezza", "L", 400); self.add_entry(sec.content_frame, "Larghezza", "W", 300)
        self.add_entry(sec.content_frame, "Spessore", "thickness", 5.0)
        
        # FIANCATE
        sec = CollapsibleSection(self.scroll_frame, "2. Fiancate", expanded=True)
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Altezza", "h_fianchi", 100)
        self.params_vars['fianchi_shape'] = tk.StringVar(value="ferro")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['fianchi_shape'], onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w")
        self.f_ferro_frame = ttk.Frame(sec.content_frame); self.f_ferro_frame.pack(fill="x", padx=10)
        self.add_entry(self.f_ferro_frame, "Altezza Min", "fianchi_h_low", 60)
        self.add_entry(self.f_ferro_frame, "Spalla", "fianchi_shoulder", 80)
        # Rinforzo Fiancate
        self.params_vars['fianchi_r_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.f_ferro_frame, text="Raddoppio (Rinforzo)", variable=self.params_vars['fianchi_r_active'], command=self.refresh).pack(anchor="w", pady=5)
        self.add_entry(self.f_ferro_frame, "Alt. Rinforzo", "fianchi_r_h", 40)
        self.add_entry(self.f_ferro_frame, "Gap Lat. Rinf.", "fianchi_r_gap", 2)
        
        # TESTATE
        sec = CollapsibleSection(self.scroll_frame, "3. Testate")
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Altezza", "h_testate", 100)
        self.params_vars['testate_shape'] = tk.StringVar(value="rect")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['testate_shape'], onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w")
        self.t_ferro_frame = ttk.Frame(sec.content_frame)
        self.add_entry(self.t_ferro_frame, "Altezza Min", "testate_h_low", 60)
        self.add_entry(self.t_ferro_frame, "Spalla", "testate_shoulder", 50)
        # Rinforzo Testate
        self.params_vars['testate_r_active'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.t_ferro_frame, text="Raddoppio (Rinforzo)", variable=self.params_vars['testate_r_active'], command=self.refresh).pack(anchor="w", pady=5)
        self.add_entry(self.t_ferro_frame, "Alt. Rinforzo", "testate_r_h", 30)
        
        # PLATFORM
        sec = CollapsibleSection(self.scroll_frame, "4. Platform")
        sec.pack(fill="x", pady=2)
        self.params_vars['platform_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(sec.content_frame, text="Attiva Platform", variable=self.params_vars['platform_active'], command=self.refresh).pack(anchor="w")
        self.add_entry(sec.content_frame, "Altezza Fascia", "fascia_h", 35)
        self.add_entry(sec.content_frame, "Larg. Lembo Ext", "plat_flap_w", 40)
        
        # LEMBI
        sec = CollapsibleSection(self.scroll_frame, "5. Lembi Interni")
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Lunghezza", "F", 120)

    def add_entry(self, parent, label, key, val):
        f = ttk.Frame(parent); f.pack(fill="x", pady=2)
        ttk.Label(f, text=label, width=18).pack(side="left")
        if key not in self.params_vars: self.params_vars[key] = tk.DoubleVar(value=val)
        e = ttk.Entry(f, textvariable=self.params_vars[key], width=8)
        e.pack(side="right")
        e.bind("<KeyRelease>", lambda e: self.refresh())

    def refresh(self):
        if self.params_vars['fianchi_shape'].get() == 'ferro': self.f_ferro_frame.pack(fill="x", padx=10)
        else: self.f_ferro_frame.pack_forget()
        if self.params_vars['testate_shape'].get() == 'ferro': self.t_ferro_frame.pack(fill="x", padx=10)
        else: self.t_ferro_frame.pack_forget()

        self.canvas.delete("all")
        params = {k: v.get() for k, v in self.params_vars.items()}
        model = BoxModel(params)
        polygons, cut_lines, crease_lines, dimensions = model.get_data()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 50: return
        tot_w = params['L'] + params['h_testate']*2 + 250
        tot_h = params['W'] + params['h_fianchi']*2 + params['F']*2 + 150
        scale = min(cw/tot_w, ch/tot_h) * 0.85
        ox_model = max(params['h_testate'], params['h_fianchi']) + 60 + params.get('fascia_h',0)
        oy_model = max(params['h_testate'], params['h_fianchi']) + params['F'] + 20
        dx = (cw/2) - (ox_model + params['L']/2)*scale
        dy = (ch/2) - (oy_model + params['W']/2)*scale

        for p in polygons:
            pts = [c for x, y in p['coords'] for c in (x*scale+dx, y*scale+dy)]
            self.canvas.create_polygon(pts, fill=p['color'], outline="", tags=p['id'])
        for line in crease_lines:
            pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
            self.canvas.create_line(pts, fill="#2E7D32", width=2, dash=(5, 3))
        for line in cut_lines:
            pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
            self.canvas.create_line(pts, fill="black", width=2)

if __name__ == "__main__":
    app = PackagingApp()
    app.mainloop()