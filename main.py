import tkinter as tk
from tkinter import ttk
import traceback

# ==========================================
# 1. WIDGET UTILS
# ==========================================
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

# ==========================================
# 2. MOTORE GEOMETRICO (FIXED)
# ==========================================
class BoxModel:
    def __init__(self, params):
        self.p = params
        self.base_gap = 2.0 

    def _transform_point(self, pt, orientation):
        """
        Trasforma un punto (u, v) locale nel sistema globale (x, y).
        u: Lunghezza lungo il lato di attacco.
        v: Estensione verso l'esterno (v negativo = fuori).
        """
        x, y = pt
        L = self.p['L']
        W = self.p['W']

        if orientation == 'top':
            # Attaccato a y=0. v negativo va in alto.
            return (x, y)
        elif orientation == 'bottom':
            # Attaccato a y=W. v negativo va in basso (y aumenta).
            return (x, W - y)
        elif orientation == 'left':
            # Attaccato a x=0. Lunghezza (u) su Y. Estensione (v) su -X.
            return (y, x)
        elif orientation == 'right':
            # Attaccato a x=L. Lunghezza (u) su Y. Estensione (v) su +X.
            # v è negativo, quindi L - v diventa L + estensione.
            return (L - y, x)
        
        # --- ANGOLI (Lembi interni) ---
        # tl: Top-Left (Testata SX, lato alto).
        elif orientation == 'tl': return (-x, -y) # va a sinistra e in alto
        elif orientation == 'tr': return (L + x, -y) # va a destra e in alto
        elif orientation == 'bl': return (-x, W + y) # va a sinistra e in basso
        elif orientation == 'br': return (L + x, W + y) # va a destra e in basso
        
        return (x, y)

    def _transform_list(self, pts_list, orientation):
        return [self._transform_point(p, orientation) for p in pts_list]

    def _get_fianco_geometry(self, L_base, H_full, orientation):
        # Parametri
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

        # --- PUNTI LOCALI (u, v) ---
        # u va da 0 a L. v va da 0 a -H.
        pts_poly = []
        cuts = []
        creases = []
        
        curr = (0, 0)
        pts_poly.append(curr)
        
        # 1. Lato Sinistro
        if has_platform:
            path = [(0, -(H_full - notch_h)), (notch_w, -(H_full - notch_h)), (notch_w, -H_full)]
        else:
            path = [(0, -H_full)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        # 2. Profilo Superiore
        p_sh_sx = (shoulder, -H_full)
        p_u_sx = (shoulder, -h_low)
        p_u_dx = (L_base - shoulder, -h_low)
        p_sh_dx = (L_base - shoulder, -H_full)
        target_dx = (L_base - notch_w, -H_full) if has_platform else (L_base, -H_full)
        
        if is_ferro:
            cuts.append([curr, p_sh_sx]); curr = p_sh_sx; pts_poly.append(curr)
            cuts.append([curr, p_u_sx]); curr = p_u_sx; pts_poly.append(curr)
            
            if has_reinf:
                # Rinforzo Raddoppio
                p_r_tl = (shoulder + r_gap, -h_low)
                p_r_bl = (shoulder + r_gap, -(h_low + r_h))
                p_r_br = (L_base - shoulder - r_gap, -(h_low + r_h))
                p_r_tr = (L_base - shoulder - r_gap, -h_low)
                
                cuts.append([curr, p_r_tl]); curr = p_r_tl; pts_poly.append(curr)
                cuts.append([curr, p_r_bl]); curr = p_r_bl; pts_poly.append(curr)
                cuts.append([curr, p_r_br]); curr = p_r_br; pts_poly.append(curr)
                cuts.append([curr, p_r_tr]); curr = p_r_tr; pts_poly.append(curr)
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
                creases.append([p_r_tl, p_r_tr])
            else:
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
            
            cuts.append([curr, p_sh_dx]); curr = p_sh_dx; pts_poly.append(curr)
            cuts.append([curr, target_dx]); curr = target_dx; pts_poly.append(curr)
        else:
            cuts.append([curr, target_dx]); curr = target_dx; pts_poly.append(curr)
            
        # 3. Lato Destro
        if has_platform:
            path = [(L_base - notch_w, -(H_full - notch_h)), (L_base, -(H_full - notch_h)), (L_base, 0)]
        else:
            path = [(L_base, 0)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        # Trasformazione Globale
        g_poly = self._transform_list(pts_poly, orientation)
        g_cuts = [self._transform_list(seg, orientation) for seg in cuts]
        g_creases = [self._transform_list(seg, orientation) for seg in creases]

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

        # Punti Locali (u=0..W, v=0..-H)
        curr = (0, 0)
        pts_poly = [curr]
        cuts, creases = [], []
        
        # Lato SX (Attacco Lembo 1)
        target = (0, -H_full)
        creases.append([curr, target]); curr = target; pts_poly.append(curr)
        
        # Profilo Superiore
        if is_ferro:
            p_sh_sx = (shoulder, -H_full)
            p_u_sx = (shoulder, -h_low)
            p_u_dx = (W - shoulder, -h_low)
            p_sh_dx = (W - shoulder, -H_full)
            
            # Spalla SX
            if has_platform: creases.append([curr, p_sh_sx])
            else: cuts.append([curr, p_sh_sx])
            curr = p_sh_sx; pts_poly.append(curr)
            
            # Discesa
            cuts.append([curr, p_u_sx]); curr = p_u_sx; pts_poly.append(curr)
            
            # Centro (Rinforzo o Piatto)
            if has_reinf:
                p_r_tl = (shoulder + r_gap, -h_low)
                p_r_bl = (shoulder + r_gap, -(h_low + r_h))
                p_r_br = (W - shoulder - r_gap, -(h_low + r_h))
                p_r_tr = (W - shoulder - r_gap, -h_low)
                
                cuts.append([curr, p_r_tl]); curr = p_r_tl; pts_poly.append(curr)
                cuts.append([curr, p_r_bl]); curr = p_r_bl; pts_poly.append(curr)
                cuts.append([curr, p_r_br]); curr = p_r_br; pts_poly.append(curr)
                cuts.append([curr, p_r_tr]); curr = p_r_tr; pts_poly.append(curr)
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
                creases.append([p_r_tl, p_r_tr])
            else:
                cuts.append([curr, p_u_dx]); curr = p_u_dx; pts_poly.append(curr)
            
            # Risalita
            cuts.append([curr, p_sh_dx]); curr = p_sh_dx; pts_poly.append(curr)
            
            # Spalla DX
            target = (W, -H_full)
            if has_platform: creases.append([curr, target])
            else: cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
        else:
            # Rect
            target = (W, -H_full)
            if has_platform: creases.append([curr, target])
            else: cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
            
        # Lato Destro
        creases.append([curr, (W, 0)]); curr = (W, 0); pts_poly.append(curr)
        
        # Trasformazione Testata Base
        g_poly = self._transform_list(pts_poly, orientation)
        g_cuts = [self._transform_list(seg, orientation) for seg in cuts]
        g_creases = [self._transform_list(seg, orientation) for seg in creases]
        
        # Assembly Platform
        if has_platform:
            plat_polys, plat_cr, plat_ct = self._get_platform_assembly(orientation, H_full)
            # Uniamo tutto in liste uniche
            # plat_polys è una lista di dict: {'coords': ...}
            # Restituiamo una struttura coerente
            return [{'coords': g_poly, 'color': 'white'}] + plat_polys, g_cuts + plat_ct, g_creases + plat_cr
        else:
            return [{'coords': g_poly, 'color': 'white'}], g_cuts, g_creases

    def _get_platform_assembly(self, orientation, H_t):
        """
        Genera Fascia e Lembi Esterni.
        Restituisce direttamente oggetti ruotati nel sistema globale.
        """
        W = self.p['W']
        Fascia_H = self.p.get('fascia_h', 30)
        Plat_W = self.p.get('plat_flap_w', 30)
        is_ferro = (self.p.get('testate_shape') == 'ferro')
        shoulder = self.p.get('testate_shoulder', W * 0.2)
        if shoulder * 2 > W: shoulder = W / 2 - 1

        # Coordinate LOCALI relative alla testata (u, v)
        # u=0..W, v=-H..-(H+Fascia)
        # Nota: nel sistema locale del metodo _transform_point, v negativo è estensione.
        # Qui Fascia_H estende oltre H_t. Quindi v va da -H_t a -(H_t + Fascia_H).
        
        parts_local = [] # (PolyPts, Creases, Cuts, Color)
        
        def create_unit(u_s, u_e, left_flap, right_flap):
            # Fascia
            # Punti: BL, TL, TR, BR (Bottom=attacco testata, Top=esterno)
            # v_base = -H_t, v_top = -(H_t + Fascia_H)
            v_b, v_t = -H_t, -(H_t + Fascia_H)
            
            f_poly = [(u_s, v_b), (u_s, v_t), (u_e, v_t), (u_e, v_b)]
            f_cr = [[(u_s, v_b), (u_e, v_b)]] # Attacco basso
            f_ct = [[(u_s, v_t), (u_e, v_t)]] # Lato alto
            
            # Lembo SX
            if left_flap:
                f_cr.append([(u_s, v_b), (u_s, v_t)]) # Piega verticale
                l_poly = [(u_s-Plat_W, v_b), (u_s-Plat_W, v_t), (u_s, v_t), (u_s, v_b)]
                l_ct = [
                    [(u_s-Plat_W, v_b), (u_s-Plat_W, v_t)], # Lato esterno
                    [(u_s-Plat_W, v_t), (u_s, v_t)],       # Top
                    [(u_s, v_b), (u_s-Plat_W, v_b)]        # Bot
                ]
                parts_local.append((l_poly, [], l_ct, '#90CAF9'))
            else:
                f_ct.append([(u_s, v_b), (u_s, v_t)]) # Taglio verticale fascia
            
            # Lembo DX
            if right_flap:
                f_cr.append([(u_e, v_b), (u_e, v_t)])
                r_poly = [(u_e, v_b), (u_e, v_t), (u_e+Plat_W, v_t), (u_e+Plat_W, v_b)]
                r_ct = [
                    [(u_e, v_t), (u_e+Plat_W, v_t)],
                    [(u_e+Plat_W, v_t), (u_e+Plat_W, v_b)],
                    [(u_e+Plat_W, v_b), (u_e, v_b)]
                ]
                parts_local.append((r_poly, [], r_ct, '#90CAF9'))
            else:
                f_ct.append([(u_e, v_b), (u_e, v_t)])
            
            parts_local.append((f_poly, f_cr, f_ct, '#E3F2FD'))

        if is_ferro:
            create_unit(0, shoulder, True, False)
            create_unit(W-shoulder, W, False, True)
        else:
            create_unit(0, W, True, True)

        # Trasformazione Globale
        g_polys, g_cr, g_ct = [], [], []
        
        for poly, cr, ct, col in parts_local:
            g_p = self._transform_list(poly, orientation)
            g_polys.append({'coords': g_p, 'color': col})
            g_cr.extend([self._transform_list(s, orientation) for s in cr])
            g_ct.extend([self._transform_list(s, orientation) for s in ct])
            
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
        
        # Punti Locali (u=larghezza, v=estensione)
        pts_local = []
        if is_ferro and f_len > shoulder:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer_low, f_len),
                         (u_outer_low, shoulder), (u_outer, shoulder), (u_outer, 0)]
        else:
            pts_local = [(u_inner, 0), (u_inner, f_len), (u_outer, f_len), (u_outer, 0)]

        # Trasformazione Corner
        final_pts = self._transform_list(pts_local, corner)
        
        cuts = []
        for i in range(len(final_pts)-1): cuts.append([final_pts[i], final_pts[i+1]])
        crease = [final_pts[0], final_pts[-1]]
        return final_pts, cuts, crease

    def get_data(self):
        """Assembla tutto e applica Offset"""
        polygons, cut_lines, crease_lines = [], [], []
        L = self.p['L']; W = self.p['W']
        H_f = self.p['h_fianchi']; H_t = self.p['h_testate']; F = self.p['F']
        
        Fascia_H = self.p.get('fascia_h', 0) if self.p.get('platform_active') else 0
        Plat_W = self.p.get('plat_flap_w', 0) if self.p.get('platform_active') else 0
        
        # Offset centratura
        ox = max(H_t + Fascia_H, H_f) + Plat_W + 50
        oy = max(H_t + Fascia_H, H_f) + F + 30 

        # 1. FONDO
        base_pts = [(0, 0), (L, 0), (L, W), (0, W)]
        base_off = [(x+ox, y+oy) for x,y in base_pts]
        polygons.append({'id': 'poly_fondo', 'coords': base_off, 'color': '#EEEEEE'})
        for i in range(4): crease_lines.append([base_off[i], base_off[(i+1)%4]])

        # 2. FIANCATE
        for orient in ['top', 'bottom']:
            g_poly, g_cuts, g_creases = self._get_fianco_geometry(L, H_f, orient)
            poly_off = [(x+ox, y+oy) for x,y in g_poly]
            polygons.append({'id': 'poly_fianchi', 'coords': poly_off, 'color': 'white'})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])

        # 3. TESTATE
        for orient in ['left', 'right']:
            # poly_items è lista di dict [{'coords':..., 'color':...}]
            poly_items, g_cuts, g_creases = self._get_testata_geometry(W, H_t, orient)
            
            for item in poly_items:
                coords_off = [(x+ox, y+oy) for x,y in item['coords']]
                item_copy = item.copy(); item_copy['coords'] = coords_off
                if 'id' not in item_copy: item_copy['id'] = 'poly_testate' # Default ID
                polygons.append(item_copy)
                
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])

        # 4. LEMBI
        for c in ['tl', 'tr', 'bl', 'br']:
            g_pts, g_cuts, g_crease = self._get_flap_geo(c, H_t, F)
            pts_off = [(x+ox, y+oy) for x,y in g_pts]
            cuts_off = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in g_cuts]
            crease_off = [(p[0]+ox, p[1]+oy) for p in g_crease]
            
            polygons.append({'id': 'poly_lembi', 'coords': pts_off, 'color': 'white'})
            cut_lines.extend(cuts_off)
            crease_lines.append(crease_off)

        return polygons, cut_lines, crease_lines

# ==========================================
# 3. APP PRINCIPALE
# ==========================================
class PackagingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Packaging CAD - Final Fixed")
        self.geometry("1400x950")
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
        self.add_entry(sec.content_frame, "Lunghezza", "L", 400); self.add_entry(sec.content_frame, "Larghezza", "W", 300)
        self.add_entry(sec.content_frame, "Spessore", "thickness", 5.0)
        
        sec = CollapsibleSection(self.scroll_frame, "2. Fiancate", expanded=True)
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Altezza", "h_fianchi", 100)
        self.params_vars['fianchi_shape'] = tk.StringVar(value="ferro")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['fianchi_shape'], onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w")
        self.f_ferro_frame = ttk.Frame(sec.content_frame); self.f_ferro_frame.pack(fill="x", padx=10)
        self.add_entry(self.f_ferro_frame, "Altezza Min", "fianchi_h_low", 60)
        self.add_entry(self.f_ferro_frame, "Spalla", "fianchi_shoulder", 80)
        self.params_vars['fianchi_r_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.f_ferro_frame, text="Raddoppio (Rinforzo)", variable=self.params_vars['fianchi_r_active'], command=self.refresh).pack(anchor="w", pady=5)
        self.add_entry(self.f_ferro_frame, "Alt. Rinforzo", "fianchi_r_h", 40)
        self.add_entry(self.f_ferro_frame, "Gap Lat. Rinf.", "fianchi_r_gap", 2)
        
        sec = CollapsibleSection(self.scroll_frame, "3. Testate", expanded=True)
        sec.pack(fill="x", pady=2)
        self.add_entry(sec.content_frame, "Altezza", "h_testate", 100)
        self.params_vars['testate_shape'] = tk.StringVar(value="ferro")
        ttk.Checkbutton(sec.content_frame, text="Ferro di Cavallo", variable=self.params_vars['testate_shape'], onvalue="ferro", offvalue="rect", command=self.refresh).pack(anchor="w")
        self.t_ferro_frame = ttk.Frame(sec.content_frame); self.t_ferro_frame.pack(fill="x", padx=10)
        self.add_entry(self.t_ferro_frame, "Altezza Min", "testate_h_low", 60)
        self.add_entry(self.t_ferro_frame, "Spalla", "testate_shoulder", 50)
        self.params_vars['testate_r_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.t_ferro_frame, text="Raddoppio (Rinforzo)", variable=self.params_vars['testate_r_active'], command=self.refresh).pack(anchor="w", pady=5)
        self.add_entry(self.t_ferro_frame, "Alt. Rinforzo", "testate_r_h", 30)
        self.add_entry(self.t_ferro_frame, "Gap Rinforzo", "testate_r_gap", 2)
        
        sec = CollapsibleSection(self.scroll_frame, "4. Platform")
        sec.pack(fill="x", pady=2)
        self.params_vars['platform_active'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(sec.content_frame, text="Attiva Platform", variable=self.params_vars['platform_active'], command=self.refresh).pack(anchor="w")
        self.add_entry(sec.content_frame, "Altezza Fascia", "fascia_h", 35)
        self.add_entry(sec.content_frame, "Larg. Lembo Ext", "plat_flap_w", 40)
        self.add_entry(sec.content_frame, "Gap Platform", "plat_gap", 3)
        
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

        try:
            self.canvas.delete("all")
            params = {k: v.get() for k, v in self.params_vars.items()}
            model = BoxModel(params)
            polygons, cut_lines, crease_lines = model.get_data()
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
                col = p.get('color', 'white')
                self.canvas.create_polygon(pts, fill=col, outline="", tags=p.get('id', ''))
            for line in crease_lines:
                pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
                self.canvas.create_line(pts, fill="#2E7D32", width=2, dash=(5, 3))
            for line in cut_lines:
                pts = [c for pt in line for c in (pt[0]*scale+dx, pt[1]*scale+dy)]
                self.canvas.create_line(pts, fill="black", width=2)
        except Exception as e:
            traceback.print_exc()
            self.canvas.create_text(10, 10, anchor="nw", text=f"ERRORE: {e}", fill="red")

if __name__ == "__main__":
    app = PackagingApp()
    app.mainloop()