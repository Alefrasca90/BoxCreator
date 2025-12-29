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
        """Genera geometria fiancata (con Notch e U-Shape)"""
        has_platform = self.p.get('platform_active', False)
        notch_w = 0
        notch_h = 0
        
        if has_platform:
            plat_flap_w = self.p.get('plat_flap_w', 30)
            fascia_h = self.p.get('fascia_h', 30)
            gap = self.p.get('plat_gap', 2)
            notch_h = plat_flap_w + gap
            notch_w = fascia_h + gap
            
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        h_low = self.p.get('fianchi_h_low', H_full * 0.6)
        shoulder = self.p.get('fianchi_shoulder', L_base * 0.2)
        
        if notch_h > H_full: notch_h = H_full - 5
        if h_low > H_full: h_low = H_full
        min_shoulder = notch_w + 10
        if is_ferro and shoulder < min_shoulder: shoulder = min_shoulder
        if shoulder * 2 > L_base: shoulder = L_base / 2 - 1

        pts = []
        pts.append((0, 0)) 
        
        # Lato SX
        if has_platform:
            pts.append((0, -(H_full - notch_h)))
            pts.append((notch_w, -(H_full - notch_h)))
            pts.append((notch_w, -H_full))
        else:
            pts.append((0, -H_full))
            
        # Top
        start_top_x = notch_w if has_platform else 0
        end_top_x = L_base - notch_w if has_platform else L_base
        
        if is_ferro:
            pts.append((shoulder, -H_full))
            pts.append((shoulder, -h_low))
            pts.append((L_base - shoulder, -h_low))
            pts.append((L_base - shoulder, -H_full))
            pts.append((end_top_x, -H_full))
        else:
            pts.append((end_top_x, -H_full))
            
        # Lato DX
        if has_platform:
            pts.append((L_base - notch_w, -(H_full - notch_h)))
            pts.append((L_base, -(H_full - notch_h)))
            pts.append((L_base, 0))
        else:
            pts.append((L_base, 0))

        final_coords = []
        for lx, ly in pts:
            if orientation == 'top': final_coords.append((lx, ly))
            elif orientation == 'bottom': final_coords.append((lx, -ly))

        final_sh_line = []
        if is_ferro:
             # Disegna la linea di spalla per l'highlight
             p1 = (start_top_x, -H_full)
             p2 = (shoulder, -H_full)
             l_pts = [p1, p2]
             for x, y in l_pts:
                if orientation == 'top': final_sh_line.extend([x, y])
                elif orientation == 'bottom': final_sh_line.extend([x, -y])

        return final_coords, final_sh_line

    def _get_platform_assembly(self, corner, h_testata):
        """Genera Fascia e Lembi Esterni"""
        if not self.p.get('platform_active'): return [], [], []

        W = self.p['W']
        H_t = h_testata
        Fascia_H = self.p.get('fascia_h', 30)
        Plat_W = self.p.get('plat_flap_w', 30)
        
        fascia_poly = [(0, H_t), (0, H_t + Fascia_H), (W, H_t + Fascia_H), (W, H_t)]
        plat_l_poly = [(-Plat_W, H_t), (-Plat_W, H_t + Fascia_H), (0, H_t + Fascia_H), (0, H_t)]
        plat_r_poly = [(W, H_t), (W, H_t + Fascia_H), (W + Plat_W, H_t + Fascia_H), (W + Plat_W, H_t)]
        
        polys, creases, cuts = [], [], []
        
        def transform(u, v):
            if corner == 'left': return (-v, u)
            else: return (self.p['L'] + v, u)

        g_fascia = [transform(u, v) for u,v in fascia_poly]
        polys.append({'id': 'poly_platform', 'coords': g_fascia, 'color': '#E3F2FD'})
        creases.append([g_fascia[0], g_fascia[3]]) 
        cuts.append([g_fascia[1], g_fascia[2]])

        for raw_poly in [plat_l_poly, plat_r_poly]:
            g_poly = [transform(u, v) for u,v in raw_poly]
            polys.append({'id': 'poly_platform_flap', 'coords': g_poly, 'color': '#90CAF9'})
            creases.append([g_poly[2], g_poly[3]]) 
            cuts.append([g_poly[0], g_poly[1]])
            cuts.append([g_poly[1], g_poly[2]])
            cuts.append([g_poly[3], g_poly[0]])

        return polys, creases, cuts

    def _get_flap_geo(self, corner, h_testata, f_len):
        """
        Calcola geometria lembo interno con GAP DOPPIO se Platform è attiva.
        """
        T = self.p.get('thickness', 3.0)
        gap = self.base_gap + T 
        
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        shoulder = self.p.get('fianchi_shoulder', 0)
        h_fianco_full = self.p.get('h_fianchi', h_testata)
        h_fianco_low = self.p.get('fianchi_h_low', h_fianco_full)
        has_platform = self.p.get('platform_active', False)
        
        cut_depth = h_fianco_full - h_fianco_low
        if cut_depth < 0: cut_depth = 0
        
        # --- DEFINIZIONE LIMITI ASSE U (Larghezza Lembo) ---
        # u_inner: Lato verso la fiancata (Gap Standard)
        # u_outer: Lato verso la fascia/esterno
        
        u_inner = gap
        
        # NUOVA LOGICA: Se Platform è attiva, dobbiamo lasciare gap anche verso l'esterno
        # per non collidere con la piega della fascia.
        gap_outer = gap if has_platform else 0
        u_outer = h_testata - gap_outer
        
        # Il punto ribassato segue il nuovo u_outer
        u_outer_low = u_outer - cut_depth
        
        # Safety check: se il gap mangia tutto il lembo
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

    def _get_u_shape(self, L, H, orient):
        prefix = "testate"
        h_low = self.p.get(f'{prefix}_h_low', H * 0.6)
        shoulder = self.p.get(f'{prefix}_shoulder', L * 0.2)
        if h_low > H: h_low = H
        if shoulder * 2 > L: shoulder = L / 2 - 1
        
        pts = [(0,0), (0,-H), (shoulder,-H), (shoulder,-h_low), (L-shoulder,-h_low), (L-shoulder,-H), (L,-H), (L,0)]
        sh_line_raw = [(0, -H), (shoulder, -H)]
        
        final, final_sh = [], []
        for x,y in pts:
            if orient=='left': final.append((y,x))
            elif orient=='right': final.append((-y,x))
        for x,y in sh_line_raw:
            if orient=='left': final_sh.extend([y,x])
            elif orient=='right': final_sh.extend([-y,x])
        return final, final_sh

    def get_data(self):
        polygons, cut_lines, crease_lines, dimensions = [], [], [], []
        
        L = self.p['L']
        W = self.p['W']
        H_f = self.p['h_fianchi']
        H_t = self.p['h_testate']
        F = self.p['F']
        
        Fascia_H = self.p.get('fascia_h', 0) if self.p.get('platform_active') else 0
        Plat_W = self.p.get('plat_flap_w', 0) if self.p.get('platform_active') else 0
        
        ox = max(H_t + Fascia_H, H_f) + Plat_W + 50
        oy = max(H_t + Fascia_H, H_f) + F + 30 

        # 1. FONDO
        base_pts = [(ox, oy), (ox+L, oy), (ox+L, oy+W), (ox, oy+W)]
        polygons.append({'id': 'poly_fondo', 'coords': base_pts, 'color': '#EEEEEE'})
        for i in range(4): crease_lines.append([base_pts[i], base_pts[(i+1)%4]])
        dimensions.append({'id': 'dim_L', 'coords': [(ox, oy), (ox+L, oy)]})

        # 2. FIANCATE
        for orient in ['top', 'bottom']:
            pts, sh_line = self._get_fianco_geometry(L, H_f, orient)
            poly_pts = [(x+ox, y+oy) if orient=='top' else (x+ox, y+oy+W) for x,y in pts]
            polygons.append({'id': 'poly_fianchi', 'coords': poly_pts, 'color': 'white'})
            for i in range(len(poly_pts)-1): cut_lines.append([poly_pts[i], poly_pts[i+1]])
            
            sh_line_g = [sh_line[0]+ox, sh_line[1]+oy + (0 if orient=='top' else W), 
                         sh_line[2]+ox, sh_line[3]+oy + (0 if orient=='top' else W)] if sh_line else []
            if sh_line_g: dimensions.append({'id': 'dim_fianchi_shoulder', 'coords': sh_line_g})

        # 3. TESTATE
        for orient in ['left', 'right']:
            if self.p.get('testate_shape') == 'ferro':
                pts, sh_line = self._get_u_shape(W, H_t, orient)
                off_x = ox if orient=='left' else ox+L
                poly_pts = [(x+off_x, y+oy) for x,y in pts]
                sh_line_g = [sh_line[0]+off_x, sh_line[1]+oy, sh_line[2]+off_x, sh_line[3]+oy]
                dimensions.append({'id': 'dim_testate_shoulder', 'coords': sh_line_g})
            else:
                if orient=='left': poly_pts = [(ox, oy), (ox-H_t, oy), (ox-H_t, oy+W), (ox, oy+W)]
                else: poly_pts = [(ox+L, oy), (ox+L+H_t, oy), (ox+L+H_t, oy+W), (ox+L, oy+W)]
            
            polygons.append({'id': 'poly_testate', 'coords': poly_pts, 'color': 'white'})
            
            if self.p.get('platform_active'):
                plat_polys, plat_creases, plat_cuts = self._get_platform_assembly(orient, H_t)
                off_x = ox if orient=='left' else ox+L # Offset manuale per platform non incluso in logic
                # Correction: _get_platform_assembly logic uses transform with self.p['L'].
                # It returns coordinates relative to 0,0 of box? No, relative to Testata logic.
                # Left corner: -v, u. Right: L+v, u.
                # We just add ox, oy.
                
                for pp in plat_polys:
                    pp['coords'] = [(x+ox, y+oy) for x,y in pp['coords']]
                    polygons.append(pp)
                for pc in plat_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in pc])
                for pcut in plat_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in pcut])
                
                crease_lines.append([poly_pts[1], poly_pts[2]]) 
                crease_lines.append([poly_pts[0], poly_pts[1]]) 
                crease_lines.append([poly_pts[2], poly_pts[3]]) 
            else:
                crease_lines.append([poly_pts[0], poly_pts[1]])
                for i in range(1, len(poly_pts)-2): cut_lines.append([poly_pts[i], poly_pts[i+1]])
                crease_lines.append([poly_pts[-2], poly_pts[-1]])

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
        self.title("Packaging CAD - Gap Symmetry")
        self.geometry("1350x900")
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
        
        sec = CollapsibleSection(self.scroll_frame, "1. Fondo", expanded=True)
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Lunghezza (L)", "L", 400, "poly_fondo", "dim_L")
        self.add_entry(sec.content_frame, "Larghezza (W)", "W", 300, "poly_fondo", "")
        self.add_entry(sec.content_frame, "Spessore", "thickness", 5.0, "poly_fondo", "")
        
        sec = CollapsibleSection(self.scroll_frame, "2. Fiancate", expanded=True)
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Altezza", "h_fianchi", 100, "poly_fianchi", "")
        self.params_vars['fianchi_shape'] = tk.StringVar(value="ferro")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['fianchi_shape'], onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w")
        self.f_ferro_frame = ttk.Frame(sec.content_frame)
        self.f_ferro_frame.pack(fill="x", padx=10)
        self.add_entry(self.f_ferro_frame, "Altezza Min", "fianchi_h_low", 60, "poly_fianchi", "")
        self.add_entry(self.f_ferro_frame, "Spalla", "fianchi_shoulder", 80, "poly_fianchi", "dim_fianchi_shoulder")
        
        sec = CollapsibleSection(self.scroll_frame, "3. Testate")
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Altezza", "h_testate", 100, "poly_testate", "")
        
        sec = CollapsibleSection(self.scroll_frame, "4. Platform (Corner)", expanded=True)
        sec.pack(fill="x", pady=2)
        self.params_vars['platform_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(sec.content_frame, text="Attiva Platform", variable=self.params_vars['platform_active'], command=self.refresh).pack(anchor="w", pady=5)
        self.add_entry(sec.content_frame, "Altezza Fascia", "fascia_h", 35, "poly_platform", "")
        self.add_entry(sec.content_frame, "Larghezza Lembo Est.", "plat_flap_w", 40, "poly_platform_flap", "")
        self.add_entry(sec.content_frame, "Gap Platform", "plat_gap", 3, "poly_fianchi", "")
        
        sec = CollapsibleSection(self.scroll_frame, "5. Lembi Interni")
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Lunghezza", "F", 120, "poly_lembi", "")

    def add_entry(self, parent, label, key, val, poly, dim):
        f = ttk.Frame(parent); f.pack(fill="x", pady=2)
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
        if "platform" in poly and not active: fill = "#E3F2FD" if "flap" not in poly else "#90CAF9"
        self.canvas.itemconfigure(poly, fill=fill)

    def refresh(self):
        val = self.params_vars['fianchi_shape'].get()
        if val == 'ferro': self.f_ferro_frame.pack(fill="x", padx=10)
        else: self.f_ferro_frame.pack_forget()

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
        for d in dimensions:
             pts = [c for x, y in d['coords'] for c in (x*scale+dx, y*scale+dy)]
             self.canvas.create_line(pts, fill="blue", width=4, state="hidden", tags=d['id'])

if __name__ == "__main__":
    app = PackagingApp()
    app.mainloop()