import tkinter as tk
from tkinter import ttk
import traceback

# --- CONFIGURAZIONE COLORI (LOOK & FEEL) ---
THEME = {
    # UI Scura (Pannello laterale)
    "bg_ui": "#2E2E2E",         # Grigio Scuro (Sfondo UI)
    "bg_panel": "#3C3F41",      # Grigio Medio (Pannelli Input)
    "fg_text": "#F0F0F0",       # Testo Chiaro
    
    # Canvas Chiaro (Area Disegno)
    "canvas_bg": "#F5F5F5",     # Grigio Chiarissimo (Quasi bianco)
    
    # Colori Scatola
    "cardboard": "#E0C0A0",     # Marroncino Kraft Naturale
    "platform": "#A1887F",      # Marrone più scuro (Platform/Rinforzi)
    "highlight": "#81D4FA",     # Azzurro Pastello (Evidenziazione)
    
    # Linee Tecniche
    "line_cut": "#000000",      # Nero (Taglio)
    "line_crease": "#00C853"    # Verde Tecnico (Piega)
}

# ==========================================
# 1. WIDGET UTILS (Interfaccia)
# ==========================================
class CollapsibleSection(ttk.Frame):
    def __init__(self, parent, title, expanded=False):
        super().__init__(parent, style="Card.TFrame")
        self.expanded = expanded
        
        # Header Button senza bordi fastidiosi
        self.btn_toggle = tk.Button(self, text=f"▼ {title}" if expanded else f"▶ {title}", 
                                    command=self.toggle, 
                                    bg=THEME["bg_panel"], fg=THEME["fg_text"],
                                    activebackground=THEME["bg_ui"], activeforeground=THEME["fg_text"],
                                    relief="flat", bd=0, highlightthickness=0, # RIMUOVE BORDI BIANCHI
                                    anchor="w", padx=10, font=("Segoe UI", 10, "bold"))
        self.btn_toggle.pack(fill="x", anchor="n", pady=1)
        
        self.content_frame = ttk.Frame(self, style="Card.TFrame")
        if expanded:
            self.content_frame.pack(fill="x", expand=True, padx=5, pady=5)

    def toggle(self):
        self.expanded = not self.expanded
        title = self.btn_toggle.cget("text")[2:]
        if self.expanded:
            self.btn_toggle.config(text=f"▼ {title}")
            self.content_frame.pack(fill="x", expand=True, padx=5, pady=5)
        else:
            self.btn_toggle.config(text=f"▶ {title}")
            self.content_frame.pack_forget()

# ==========================================
# 2. MOTORE GEOMETRICO
# ==========================================
class BoxModel:
    def __init__(self, params):
        self.p = params
        self.base_gap = 2.0 

    def _rotate_points(self, pts, orientation):
        L = self.p['L']; W = self.p['W']
        final = []
        for x, y in pts:
            if orientation == 'top': final.append((x, y))
            elif orientation == 'bottom': final.append((x, W - y))
            elif orientation == 'left': final.append((y, x))
            elif orientation == 'right': final.append((L - y, x))
            elif orientation == 'tl': final.append((-x, -y))
            elif orientation == 'tr': final.append((L + x, -y))
            elif orientation == 'bl': final.append((-x, W + y))
            elif orientation == 'br': final.append((L + x, W + y))
        return final

    def _get_fianco_geometry(self, L_base, H_full, orientation):
        has_platform = self.p.get('platform_active', False)
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        has_reinf = is_ferro and self.p.get('fianchi_r_active', False)
        
        notch_w, notch_h = 0, 0
        if has_platform:
            notch_h = self.p.get('plat_flap_w', 30) + self.p.get('plat_gap', 2)
            notch_w = self.p.get('fascia_h', 30) + self.p.get('plat_gap', 2)
            if notch_h > H_full: notch_h = H_full - 5

        h_low = self.p.get('fianchi_h_low', H_full * 0.6)
        if h_low > H_full: h_low = H_full
        shoulder = self.p.get('fianchi_shoulder', L_base * 0.2)
        min_shoulder = notch_w + 5
        if is_ferro and shoulder < min_shoulder: shoulder = min_shoulder
        if shoulder * 2 > L_base: shoulder = L_base / 2 - 1

        r_h = self.p.get('fianchi_r_h', 30)
        r_gap = self.p.get('fianchi_r_gap', 2)
        if r_h > h_low: r_h = h_low - 1
        avail_w = L_base - 2*shoulder
        if r_gap * 2 >= avail_w: r_gap = (avail_w / 2) - 5

        p_base_L = (0, 0); p_base_R = (L_base, 0)
        pts_poly, cuts, creases = [], [], []
        
        pts_poly.append(p_base_L); curr = p_base_L
        
        # SX
        path = [(0, -(H_full - notch_h)), (notch_w, -(H_full - notch_h)), (notch_w, -H_full)] if has_platform else [(0, -H_full)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        # TOP
        p_sh_sx = (shoulder, -H_full); p_u_sx = (shoulder, -h_low)
        p_u_dx = (L_base - shoulder, -h_low); p_sh_dx = (L_base - shoulder, -H_full)
        target_dx = (L_base - notch_w, -H_full) if has_platform else (L_base, -H_full)
        
        if is_ferro:
            cuts.append([curr, p_sh_sx]); curr = p_sh_sx; pts_poly.append(curr)
            cuts.append([curr, p_u_sx]); curr = p_u_sx; pts_poly.append(curr)
            
            if has_reinf:
                p_r_tl = (shoulder + r_gap, -h_low); p_r_bl = (shoulder + r_gap, -(h_low + r_h))
                p_r_br = (L_base - shoulder - r_gap, -(h_low + r_h)); p_r_tr = (L_base - shoulder - r_gap, -h_low)
                cuts.extend([[curr, p_r_tl], [p_r_tl, p_r_bl], [p_r_bl, p_r_br], [p_r_br, p_r_tr], [p_r_tr, p_u_dx]])
                creases.append([p_r_tl, p_r_tr])
                curr = p_u_dx; pts_poly.extend([p_r_tl, p_r_bl, p_r_br, p_r_tr, p_u_dx])
            else:
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
            
            cuts.append([curr, p_sh_dx]); curr = p_sh_dx; pts_poly.append(curr)
            cuts.append([curr, target_dx]); curr = target_dx; pts_poly.append(curr)
        else:
            cuts.append([curr, target_dx]); curr = target_dx; pts_poly.append(curr)
            
        # DX
        path = [(L_base - notch_w, -(H_full - notch_h)), (L_base, -(H_full - notch_h)), (L_base, 0)] if has_platform else [(L_base, 0)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        g_poly = self._rotate_points(pts_poly, orientation)
        g_cuts = [self._rotate_points(seg, orientation) for seg in cuts]
        g_creases = [self._rotate_points(seg, orientation) for seg in creases]
        return g_poly, g_cuts, g_creases

    def _get_testata_geometry(self, L_base, H_full, orientation):
        W = self.p['W']
        is_ferro = (self.p.get('testate_shape') == 'ferro')
        has_platform = self.p.get('platform_active', False)
        h_low = self.p.get('testate_h_low', H_full * 0.6)
        if h_low > H_full: h_low = H_full
        shoulder = self.p.get('testate_shoulder', W * 0.2)
        if shoulder * 2 > W: shoulder = W / 2 - 1
        
        has_reinf = is_ferro and self.p.get('testate_r_active', False)
        r_h = self.p.get('testate_r_h', 30)
        r_gap = self.p.get('testate_r_gap', 2)
        if r_h > h_low: r_h = h_low - 1
        avail_w = W - 2*shoulder
        if r_gap * 2 >= avail_w: r_gap = (avail_w / 2) - 5

        curr = (0, 0); pts_poly = [curr]
        cuts, creases = [], []
        
        target = (0, -H_full); creases.append([curr, target]); curr = target; pts_poly.append(curr)
        
        if is_ferro:
            p_sh_sx = (shoulder, -H_full); p_u_sx = (shoulder, -h_low)
            p_u_dx = (W - shoulder, -h_low); p_sh_dx = (W - shoulder, -H_full)
            
            if has_platform: creases.append([curr, p_sh_sx])
            else: cuts.append([curr, p_sh_sx])
            curr = p_sh_sx; pts_poly.append(curr)
            
            cuts.append([curr, p_u_sx]); curr = p_u_sx; pts_poly.append(curr)
            
            if has_reinf:
                p_r_tl = (shoulder + r_gap, -h_low); p_r_bl = (shoulder + r_gap, -(h_low + r_h))
                p_r_br = (W - shoulder - r_gap, -(h_low + r_h)); p_r_tr = (W - shoulder - r_gap, -h_low)
                cuts.extend([[curr, p_r_tl], [p_r_tl, p_r_bl], [p_r_bl, p_r_br], [p_r_br, p_r_tr], [p_r_tr, p_u_dx]])
                creases.append([p_r_tl, p_r_tr])
                curr = p_u_dx; pts_poly.extend([p_r_tl, p_r_bl, p_r_br, p_r_tr, p_u_dx])
            else:
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
            
            cuts.append([curr, p_sh_dx]); curr = p_sh_dx; pts_poly.append(curr)
            
            target = (W, -H_full)
            if has_platform: creases.append([curr, target])
            else: cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
        else:
            target = (W, -H_full)
            if has_platform: creases.append([curr, target])
            else: cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
            
        creases.append([curr, (W, 0)]); curr = (W, 0); pts_poly.append(curr)
        
        g_poly = self._rotate_points(pts_poly, orientation)
        g_cuts = [self._rotate_points(seg, orientation) for seg in cuts]
        g_creases = [self._rotate_points(seg, orientation) for seg in creases]
        
        if has_platform:
            plat_polys, plat_creases, plat_cuts = self._get_platform_assembly(orientation, H_full)
            return [{'coords': g_poly, 'type': 'testate'}] + plat_polys, g_cuts + plat_cuts, g_creases + plat_creases
        else:
            return [{'coords': g_poly, 'type': 'testata'}], g_cuts, g_creases

    def _get_platform_assembly(self, corner, H_t):
        W = self.p['W']
        Fascia_H = self.p.get('fascia_h', 30)
        Plat_W = self.p.get('plat_flap_w', 30)
        is_ferro = (self.p.get('testate_shape') == 'ferro')
        shoulder = self.p.get('testate_shoulder', W * 0.2)
        if shoulder * 2 > W: shoulder = W / 2 - 1

        parts = [] 
        
        def create_unit(u_s, u_e, left, right):
            v_b, v_t = -H_t, -(H_t + Fascia_H)
            f_poly = [(u_s, v_b), (u_s, v_t), (u_e, v_t), (u_e, v_b)]
            f_cr = [[(u_s, v_b), (u_e, v_b)]]
            f_ct = [[(u_s, v_t), (u_e, v_t)]]
            
            if left:
                f_cr.append([(u_s, v_b), (u_s, v_t)])
                l_poly = [(u_s-Plat_W, v_b), (u_s-Plat_W, v_t), (u_s, v_t), (u_s, v_b)]
                l_ct = [[(u_s-Plat_W, v_b), (u_s-Plat_W, v_t)], [(u_s-Plat_W, v_t), (u_s, v_t)], [(u_s, v_b), (u_s-Plat_W, v_b)]]
                parts.append((l_poly, [], l_ct, 'platform_flap'))
            else:
                f_ct.append([(u_s, v_b), (u_s, v_t)])
                
            if right:
                f_cr.append([(u_e, v_b), (u_e, v_t)])
                r_poly = [(u_e, v_b), (u_e, v_t), (u_e+Plat_W, v_t), (u_e+Plat_W, v_b)]
                r_ct = [[(u_e, v_t), (u_e+Plat_W, v_t)], [(u_e+Plat_W, v_t), (u_e+Plat_W, v_b)], [(u_e+Plat_W, v_b), (u_e, v_b)]]
                parts.append((r_poly, [], r_ct, 'platform_flap'))
            else:
                f_ct.append([(u_e, v_b), (u_e, v_t)])
            
            parts.append((f_poly, f_cr, f_ct, 'platform'))

        if is_ferro:
            create_unit(0, shoulder, True, False)
            create_unit(W-shoulder, W, False, True)
        else:
            create_unit(0, W, True, True)

        g_polys, g_cr, g_ct = [], [], []
        for poly, cr, ct, typ in parts:
            g_polys.append({'coords': self._rotate_points(poly, corner), 'type': typ})
            g_cr.extend([self._rotate_points(s, corner) for s in cr])
            g_ct.extend([self._rotate_points(s, corner) for s in ct])
        return g_polys, g_cr, g_ct

    def _get_flap_geo(self, corner, h_testata, f_len):
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

        final_pts = self._rotate_points(pts_local, corner)
        cuts = []
        for i in range(len(final_pts)-1): cuts.append([final_pts[i], final_pts[i+1]])
        crease = [final_pts[0], final_pts[-1]]
        return final_pts, cuts, crease

    def get_data(self):
        polygons, cut_lines, crease_lines = [], [], []
        L = self.p['L']; W = self.p['W']
        H_f = self.p['h_fianchi']; H_t = self.p['h_testate']; F = self.p['F']
        Fascia_H = self.p.get('fascia_h', 0) if self.p.get('platform_active') else 0
        Plat_W = self.p.get('plat_flap_w', 0) if self.p.get('platform_active') else 0
        
        ox = max(H_t + Fascia_H, H_f) + Plat_W + 50
        oy = max(H_t + Fascia_H, H_f) + F + 30 

        # FONDO
        base_pts = [(0, 0), (L, 0), (L, W), (0, W)]
        base_off = [(x+ox, y+oy) for x,y in base_pts]
        polygons.append({'id': 'poly_fondo', 'type': 'fondo', 'coords': base_off})
        for i in range(4): crease_lines.append([base_off[i], base_off[(i+1)%4]])

        # FIANCATE
        for orient in ['top', 'bottom']:
            g_poly, g_cuts, g_creases = self._get_fianco_geometry(L, H_f, orient)
            poly_off = [(x+ox, y+oy) for x,y in g_poly]
            polygons.append({'id': 'poly_fianchi', 'type': 'fianchi', 'coords': poly_off})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])

        # TESTATE
        for orient in ['left', 'right']:
            poly_items, g_cuts, g_creases = self._get_testata_geometry(W, H_t, orient)
            for item in poly_items:
                coords_off = [(x+ox, y+oy) for x,y in item['coords']]
                t_type = item.get('type', 'testate')
                polygons.append({'id': f'poly_{t_type}', 'type': t_type, 'coords': coords_off})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])

        # LEMBI
        for c in ['tl', 'tr', 'bl', 'br']:
            g_pts, g_cuts, g_crease = self._get_flap_geo(c, H_t, F)
            pts_off = [(x+ox, y+oy) for x,y in g_pts]
            cuts_off = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in g_cuts]
            crease_off = [(p[0]+ox, p[1]+oy) for p in g_crease]
            polygons.append({'id': 'poly_lembi', 'type': 'lembi', 'coords': pts_off})
            cut_lines.extend(cuts_off)
            crease_lines.append(crease_off)

        return polygons, cut_lines, crease_lines

# ==========================================
# 3. APP PRINCIPALE
# ==========================================
class PackagingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Packaging CAD Pro")
        self.geometry("1400x950")
        
        self.configure(bg=THEME["bg_ui"])
        style = ttk.Style()
        style.theme_use('clam')
        
        # Styles
        style.configure(".", background=THEME["bg_ui"], foreground=THEME["fg_text"], borderwidth=0)
        style.configure("TLabel", background=THEME["bg_panel"], foreground=THEME["fg_text"])
        style.configure("TEntry", fieldbackground="#555555", foreground="white", insertcolor="white", borderwidth=0)
        style.configure("TButton", background=THEME["bg_panel"], foreground=THEME["fg_text"], borderwidth=0)
        style.map("TButton", background=[("active", THEME["bg_ui"])])
        style.configure("TCheckbutton", background=THEME["bg_panel"], foreground=THEME["fg_text"])
        style.map("TCheckbutton", background=[("active", THEME["bg_panel"])])
        style.configure("Card.TFrame", background=THEME["bg_panel"], relief="flat")

        self.params_vars = {}
        
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME["bg_ui"], sashwidth=4, sashrelief="flat", bd=0)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        self.input_container = tk.Frame(self.paned, bg=THEME["bg_ui"], bd=0, highlightthickness=0)
        self.canvas_scroll = tk.Canvas(self.input_container, width=380, bg=THEME["bg_ui"], bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.input_container, orient="vertical", command=self.canvas_scroll.yview)
        self.scroll_frame = ttk.Frame(self.canvas_scroll, style="Card.TFrame")
        
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        self.canvas_window = self.canvas_scroll.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas_scroll.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.paned.add(self.input_container)
        
        self.draw_frame = tk.Frame(self.paned, bg=THEME["canvas_bg"], bd=0, highlightthickness=0)
        self.paned.add(self.draw_frame)
        self.canvas = tk.Canvas(self.draw_frame, bg=THEME["canvas_bg"], bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.build_ui()
        
        self.canvas_scroll.bind("<Configure>", lambda e: self.canvas_scroll.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind("<Configure>", lambda e: self.refresh())
        self.after(200, self.refresh)

    def build_ui(self):
        header = tk.Label(self.scroll_frame, text="PARAMETRI PROGETTO", 
                         font=("Segoe UI", 12, "bold", "italic"), 
                         bg=THEME["bg_panel"], fg=THEME["highlight"], pady=20)
        header.pack(fill="x")
        
        # FONDO
        sec = CollapsibleSection(self.scroll_frame, "1. Fondo", expanded=True)
        sec.pack(fill="x", pady=2, padx=5)
        self.add_entry(sec.content_frame, "Lunghezza (L)", "L", 400, ["fondo", "fianchi", "testate"])
        self.add_entry(sec.content_frame, "Larghezza (W)", "W", 300, ["fondo", "testate", "fianchi"])
        self.add_entry(sec.content_frame, "Spessore", "thickness", 5.0, ["fondo", "lembi"])
        
        # FIANCATE
        sec = CollapsibleSection(self.scroll_frame, "2. Fiancate", expanded=True)
        sec.pack(fill="x", pady=2, padx=5)
        self.add_entry(sec.content_frame, "Altezza", "h_fianchi", 100, ["fianchi"])
        self.params_vars['fianchi_shape'] = tk.StringVar(value="ferro")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['fianchi_shape'], 
                        onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w", padx=5)
        self.f_ferro_frame = ttk.Frame(sec.content_frame, style="Card.TFrame")
        self.f_ferro_frame.pack(fill="x", padx=15)
        self.add_entry(self.f_ferro_frame, "Altezza Min", "fianchi_h_low", 60, ["fianchi"])
        self.add_entry(self.f_ferro_frame, "Spalla", "fianchi_shoulder", 80, ["fianchi"])
        self.params_vars['fianchi_r_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.f_ferro_frame, text="Raddoppio (Rinforzo)", variable=self.params_vars['fianchi_r_active'], command=self.refresh).pack(anchor="w")
        self.add_entry(self.f_ferro_frame, "Alt. Rinforzo", "fianchi_r_h", 40, ["fianchi"])
        self.add_entry(self.f_ferro_frame, "Gap Lat. Rinf.", "fianchi_r_gap", 2, ["fianchi"])
        
        # TESTATE
        sec = CollapsibleSection(self.scroll_frame, "3. Testate", expanded=True)
        sec.pack(fill="x", pady=2, padx=5)
        self.add_entry(sec.content_frame, "Altezza", "h_testate", 100, ["testate", "lembi", "platform"])
        self.params_vars['testate_shape'] = tk.StringVar(value="ferro")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['testate_shape'], 
                        onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w", padx=5)
        self.t_ferro_frame = ttk.Frame(sec.content_frame, style="Card.TFrame")
        self.t_ferro_frame.pack(fill="x", padx=15)
        self.add_entry(self.t_ferro_frame, "Altezza Min", "testate_h_low", 60, ["testate"])
        self.add_entry(self.t_ferro_frame, "Spalla", "testate_shoulder", 50, ["testate", "platform"])
        self.params_vars['testate_r_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.t_ferro_frame, text="Raddoppio (Rinforzo)", variable=self.params_vars['testate_r_active'], command=self.refresh).pack(anchor="w")
        self.add_entry(self.t_ferro_frame, "Alt. Rinforzo", "testate_r_h", 30, ["testate"])
        self.add_entry(self.t_ferro_frame, "Gap Rinforzo", "testate_r_gap", 2, ["testate"])
        
        # PLATFORM
        sec = CollapsibleSection(self.scroll_frame, "4. Platform")
        sec.pack(fill="x", pady=2, padx=5)
        self.params_vars['platform_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(sec.content_frame, text="Attiva Platform", variable=self.params_vars['platform_active'], command=self.refresh).pack(anchor="w", padx=5)
        self.add_entry(sec.content_frame, "Altezza Fascia", "fascia_h", 35, ["platform", "fianchi"])
        self.add_entry(sec.content_frame, "Larg. Lembo Ext", "plat_flap_w", 40, ["platform", "fianchi"])
        self.add_entry(sec.content_frame, "Gap Platform", "plat_gap", 3, ["platform", "fianchi"])
        
        # LEMBI
        sec = CollapsibleSection(self.scroll_frame, "5. Lembi Interni")
        sec.pack(fill="x", pady=2, padx=5)
        self.add_entry(sec.content_frame, "Lunghezza", "F", 120, ["lembi"])

    def add_entry(self, parent, label, key, val, tags):
        f = tk.Frame(parent, bg=THEME["bg_panel"])
        f.pack(fill="x", pady=2)
        tk.Label(f, text=label, bg=THEME["bg_panel"], fg=THEME["fg_text"], width=20, anchor="w").pack(side="left")
        if key not in self.params_vars: self.params_vars[key] = tk.DoubleVar(value=val)
        e = ttk.Entry(f, textvariable=self.params_vars[key], width=8)
        e.pack(side="right", padx=5)
        
        e.bind("<Enter>", lambda e: self.highlight(tags, True))
        e.bind("<Leave>", lambda e: self.highlight(tags, False))
        e.bind("<KeyRelease>", lambda e: self.refresh())

    def highlight(self, tags, active):
        if not active:
            self.refresh()
            return
        for type_tag in tags:
            self.canvas.itemconfigure(type_tag, fill=THEME["highlight"])

    def refresh(self):
        if self.params_vars['fianchi_shape'].get() == 'ferro': self.f_ferro_frame.pack(fill="x", padx=15)
        else: self.f_ferro_frame.pack_forget()
        if self.params_vars['testate_shape'].get() == 'ferro': self.t_ferro_frame.pack(fill="x", padx=15)
        else: self.t_ferro_frame.pack_forget()

        try:
            self.canvas.delete("all")
            params = {k: v.get() for k, v in self.params_vars.items()}
            model = BoxModel(params)
            polygons, cut_lines, crease_lines = model.get_data()
            
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw < 50: return
            
            tot_w = params['L'] + params['h_testate']*2 + 300
            tot_h = params['W'] + params['h_fianchi']*2 + params['F']*2 + 200
            scale = min(cw/tot_w, ch/tot_h) * 0.8
            ox_model = max(params['h_testate'], params['h_fianchi']) + 100
            oy_model = max(params['h_testate'], params['h_fianchi']) + params['F'] + 50
            dx = (cw/2) - (ox_model + params['L']/2)*scale
            dy = (ch/2) - (oy_model + params['W']/2)*scale
            
            # Draw Polygons
            for p in polygons:
                pts = [c for x, y in p['coords'] for c in (x*scale+dx, y*scale+dy)]
                # Determine Color
                base_col = THEME["cardboard"]
                if 'platform' in p.get('type', ''): base_col = THEME["platform"]
                
                self.canvas.create_polygon(pts, fill=base_col, outline="", tags=p.get('type', ''))

            # Draw Creases
            for line in crease_lines:
                pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
                self.canvas.create_line(pts, fill=THEME["line_crease"], width=1.5, dash=(4, 2))

            # Draw Cuts
            for line in cut_lines:
                pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
                self.canvas.create_line(pts, fill=THEME["line_cut"], width=2, capstyle=tk.ROUND)

        except Exception as e:
            traceback.print_exc()
            self.canvas.create_text(20, 20, anchor="nw", text=f"ERROR: {e}", fill="red")

if __name__ == "__main__":
    app = PackagingApp()
    app.mainloop()