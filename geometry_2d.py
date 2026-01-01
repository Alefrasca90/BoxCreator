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
        T = self.p.get('thickness', 5.0)
        has_platform = self.p.get('platform_active', False)
        is_ferro = (self.p.get('fianchi_shape') == 'ferro')
        has_reinf = is_ferro and self.p.get('fianchi_r_active', False)
        
        notch_h = self.p.get('plat_flap_w', 30) + self.p.get('plat_gap', 2) + T
        notch_w = self.p.get('fascia_h', 30) + self.p.get('plat_gap', 2) + T
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
        
        x_start = T
        x_end = L_base - T
        
        p_base_L = (x_start, 0)
        curr = p_base_L
        pts_poly = [curr]
        cuts, creases = [], []
        
        if has_platform:
            path = [(x_start, -(H_full - notch_h)), (x_start+notch_w, -(H_full - notch_h)), (x_start+notch_w, -H_full)]
        else:
            path = [(x_start, -H_full)]
        for pt in path: cuts.append([curr, pt]); curr = pt; pts_poly.append(curr)

        p_sh_sx = (shoulder, -H_full); p_u_sx = (shoulder, -h_low)
        p_u_dx = (L_base - shoulder, -h_low); p_sh_dx = (L_base - shoulder, -H_full)
        target_dx = (x_end - notch_w, -H_full) if has_platform else (x_end, -H_full)
        
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
            
        path = [(x_end, -(H_full - notch_h)), (x_end, 0)] if has_platform else [(x_end, 0)]
        if has_platform:
            cuts.append([curr, (x_end - notch_w, -(H_full - notch_h))]); curr = (x_end - notch_w, -(H_full - notch_h)); pts_poly.append(curr)
            cuts.append([curr, (x_end, -(H_full - notch_h))]); curr = (x_end, -(H_full - notch_h)); pts_poly.append(curr)
            cuts.append([curr, (x_end, 0)]); curr = (x_end, 0); pts_poly.append(curr)
        else:
            cuts.append([curr, (x_end, 0)]); curr = (x_end, 0); pts_poly.append(curr)

        g_poly = self._rotate_points(pts_poly, orientation)
        g_cuts = [self._rotate_points(seg, orientation) for seg in cuts]
        g_creases = [self._rotate_points(seg, orientation) for seg in creases]
        return g_poly, g_cuts, g_creases

    def _get_testata_geometry(self, L_base, H_full, orientation):
        W = self.p['W']
        T = self.p.get('thickness', 5.0)
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
        
        x_start = T
        x_end = W - T
        
        curr = (x_start, 0); pts_poly = [curr]
        cuts, creases = [], []
        target = (x_start, -H_full); creases.append([curr, target]); curr = target; pts_poly.append(curr)
        
        if is_ferro:
            p_sh_sx = (shoulder, -H_full); p_u_sx = (shoulder, -h_low)
            p_u_dx = (W - shoulder, -h_low); p_sh_dx = (W - shoulder, -H_full)
            if not has_platform: cuts.append([curr, p_sh_sx])
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
            target = (x_end, -H_full)
            if not has_platform: cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
        else:
            target = (x_end, -H_full)
            if not has_platform: cuts.append([curr, target])
            curr = target; pts_poly.append(curr)
            
        creases.append([curr, (x_end, 0)]); curr = (x_end, 0); pts_poly.append(curr)
        
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
        T = self.p.get('thickness', 5.0)
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
            pts_local = [(u_inner, 0-T), (u_inner, f_len-T), (u_outer_low, f_len-T),
                         (u_outer_low, shoulder-T), (u_outer, shoulder-T), (u_outer, 0-T)]
        else:
            pts_local = [(u_inner, 0-T), (u_inner, f_len-T), (u_outer, f_len-T), (u_outer, 0-T)]
            
        final_pts = self._rotate_points(pts_local, corner)
        cuts = []
        for i in range(len(final_pts)-1): cuts.append([final_pts[i], final_pts[i+1]])
        return final_pts, cuts, []

    def get_data(self):
        polygons, cut_lines, crease_lines = [], [], []
        L = self.p['L']; W = self.p['W']
        H_f = self.p['h_fianchi']; H_t = self.p['h_testate']; F = self.p['F']
        Fascia_H = self.p.get('fascia_h', 0) if self.p.get('platform_active') else 0
        Plat_W = self.p.get('plat_flap_w', 0) if self.p.get('platform_active') else 0
        ox = max(H_t + Fascia_H, H_f) + Plat_W + 50
        oy = max(H_t + Fascia_H, H_f) + F + 30 
        base_pts = [(0, 0), (L, 0), (L, W), (0, W)]
        base_off = [(x+ox, y+oy) for x,y in base_pts]
        polygons.append({'id': 'poly_fondo', 'type': 'fondo', 'coords': base_off})
        for i in range(4): crease_lines.append([base_off[i], base_off[(i+1)%4]])
        for orient in ['top', 'bottom']:
            g_poly, g_cuts, g_creases = self._get_fianco_geometry(L, H_f, orient)
            poly_off = [(x+ox, y+oy) for x,y in g_poly]
            polygons.append({'id': 'poly_fianchi', 'type': 'fianchi', 'coords': poly_off})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])
        for orient in ['left', 'right']:
            poly_items, g_cuts, g_creases = self._get_testata_geometry(W, H_t, orient)
            for item in poly_items:
                coords_off = [(x+ox, y+oy) for x,y in item['coords']]
                t_type = item.get('type', 'testate')
                polygons.append({'id': f'poly_{t_type}', 'type': t_type, 'coords': coords_off})
            for c in g_cuts: cut_lines.append([(p[0]+ox, p[1]+oy) for p in c])
            for c in g_creases: crease_lines.append([(p[0]+ox, p[1]+oy) for p in c])
        for c in ['tl', 'tr', 'bl', 'br']:
            g_pts, g_cuts, g_crease = self._get_flap_geo(c, H_t, F)
            pts_off = [(x+ox, y+oy) for x,y in g_pts]
            cuts_off = [[(p1[0]+ox, p1[1]+oy), (p2[0]+ox, p2[1]+oy)] for p1,p2 in g_cuts]
            if g_crease: crease_lines.append([(p[0]+ox, p[1]+oy) for p in g_crease])
            polygons.append({'id': 'poly_lembi', 'type': 'lembi', 'coords': pts_off})
            cut_lines.extend(cuts_off)
        return polygons, cut_lines, crease_lines