import math

# --- Utility per Arrotondare gli Angoli ---
def round_poly(points, radius=2.0, steps=3):
    """Arrotonda gli angoli di un poligono usando curve di Bezier."""
    if len(points) < 3: return points
    new_points = []
    n = len(points)
    
    def dist(p1, p2): return math.hypot(p1[0]-p2[0], p1[1]-p2[1])

    for i in range(n):
        p_prev = points[i-1]
        p_curr = points[i]
        p_next = points[(i+1)%n]
        
        l1 = dist(p_curr, p_prev)
        l2 = dist(p_curr, p_next)
        
        r = min(radius, l1/2, l2/2)
        
        if r < 0.1:
            new_points.append(p_curr)
            continue
            
        v1_x, v1_y = p_prev[0]-p_curr[0], p_prev[1]-p_curr[1]
        v2_x, v2_y = p_next[0]-p_curr[0], p_next[1]-p_curr[1]
        d1 = math.hypot(v1_x, v1_y)
        d2 = math.hypot(v2_x, v2_y)
        
        if d1 == 0 or d2 == 0:
            new_points.append(p_curr); continue

        n1 = (v1_x/d1, v1_y/d1)
        n2 = (v2_x/d2, v2_y/d2)
        
        p_start = (p_curr[0] + n1[0]*r, p_curr[1] + n1[1]*r)
        p_end   = (p_curr[0] + n2[0]*r, p_curr[1] + n2[1]*r)
        
        new_points.append(p_start)
        for s in range(1, steps + 1):
            t = s / steps
            inv = 1.0 - t
            bx = (inv**2 * p_start[0]) + (2 * inv * t * p_curr[0]) + (t**2 * p_end[0])
            by = (inv**2 * p_start[1]) + (2 * inv * t * p_curr[1]) + (t**2 * p_end[1])
            new_points.append((bx, by))
            
    return new_points

class BoxComponent:
    def __init__(self, name, width, height, thickness, parent=None, attachment='top', label='', custom_offset=0):
        self.name = name
        self.width = width
        self.height = height
        self.thickness = thickness
        self.parent = parent
        self.children = []
        self.label = label 
        self.polygon = [] 
        
        self.fold_angle = 0.0
        self.fold_axis = 'x'
        self.fold_multiplier = 1 
        self.pivot_3d = (0,0,0)
        self.pre_rot_z = 0.0 
        self.layout_pos = (0,0)
        self.layout_rot = 0
        self.custom_offset = custom_offset 
        
        if parent: parent.add_child(self, attachment)
        else: self.generate_shape()

    def add_child(self, child, edge):
        self.children.append(child)
        gw, gh = self.width, self.height
        
        if self.name == "Fondo":
            if edge == 'top':
                child.pivot_3d = (0, -gh/2, 0); child.pre_rot_z = 0 
                child.fold_axis = 'x'; child.fold_multiplier = -1 
                child.layout_pos = (0, -gh/2); child.layout_rot = 0
            elif edge == 'bottom':
                child.pivot_3d = (0, gh/2, 0); child.pre_rot_z = 180 
                child.fold_axis = 'x'; child.fold_multiplier = 1 
                child.layout_pos = (0, gh/2); child.layout_rot = 180
            elif edge == 'left':
                child.pivot_3d = (-gw/2, 0, 0); child.pre_rot_z = -90 
                child.fold_axis = 'y'; child.fold_multiplier = 1 
                child.layout_pos = (-gw/2, 0); child.layout_rot = -90 
            elif edge == 'right':
                child.pivot_3d = (gw/2, 0, 0); child.pre_rot_z = 90 
                child.fold_axis = 'y'; child.fold_multiplier = -1 
                child.layout_pos = (gw/2, 0); child.layout_rot = 90 
        else:
            if edge == 'bottom': 
                child.pivot_3d = (0, -gh, 0)
                child.pre_rot_z = 0; child.fold_axis = 'x'; child.fold_multiplier = -1
                child.layout_pos = (0, -gh); child.layout_rot = 0
            elif edge == 'left': 
                child.pivot_3d = (-gw/2, -gh/2, 0); child.pre_rot_z = -90; child.fold_axis = 'y'; child.fold_multiplier = 1
                child.layout_pos = (-gw/2, -gh/2); child.layout_rot = -90
            elif edge == 'right': 
                child.pivot_3d = (gw/2, -gh/2, 0); child.pre_rot_z = 90; child.fold_axis = 'y'; child.fold_multiplier = -1
                child.layout_pos = (gw/2, -gh/2); child.layout_rot = 90
            elif edge == 'leg_left':
                sh = getattr(self, 'shoulder_val', 20)
                cx_parent = -gw/2 + sh/2
                cx = cx_parent - child.custom_offset
                child.pivot_3d = (cx, -gh, 0); child.pre_rot_z = 0; child.fold_axis = 'x'; child.fold_multiplier = -1
                child.layout_pos = (cx, -gh); child.layout_rot = 0
            elif edge == 'leg_right':
                sh = getattr(self, 'shoulder_val', 20)
                cx_parent = gw/2 - sh/2
                cx = cx_parent + child.custom_offset
                child.pivot_3d = (cx, -gh, 0); child.pre_rot_z = 0; child.fold_axis = 'x'; child.fold_multiplier = -1
                child.layout_pos = (cx, -gh); child.layout_rot = 0
            elif edge == 'reinf_attach':
                hl = getattr(self, 'h_low_val', self.height*0.6)
                child.pivot_3d = (0, -hl, 0); child.pre_rot_z = 0; child.fold_axis = 'x'; child.fold_multiplier = -1
                child.layout_pos = (0, -hl); child.layout_rot = 0
        
        child.generate_shape()

    def generate_shape(self):
        w, h = self.width, self.height
        pts = [(w/2, 0), (w/2, -h), (-w/2, -h), (-w/2, 0)]
        self.polygon = round_poly(pts, 2.0)

    def _make_transform(self, parent_tm, angle_override=None):
        angle = self.fold_angle if angle_override is None else angle_override
        rf = math.radians(angle * self.fold_multiplier)
        cf, sf = math.cos(rf), math.sin(rf)
        rp = math.radians(self.pre_rot_z)
        cp, sp = math.cos(rp), math.sin(rp)
        
        def local_tm(v):
            x, y, z = v
            rx, ry = x*cp - y*sp, x*sp + y*cp
            rz = z
            if self.fold_axis == 'x': yf, zf, xf = ry*cf - rz*sf, ry*sf + rz*cf, rx
            else: xf, zf, yf = rx*cf + rz*sf, -rx*sf + rz*cf, ry
            return (xf + self.pivot_3d[0], yf + self.pivot_3d[1], zf + self.pivot_3d[2])
            
        if parent_tm is None: return lambda v: local_tm(v)
        return lambda v: parent_tm(local_tm(v))

    def get_world_transform_3d(self, parent_tm=None):
        return self._make_transform(parent_tm, angle_override=None)

    def get_mesh_3d(self, parent_tm=None):
        tm = self.get_world_transform_3d(parent_tm)
        faces = []
        vt = [tm((x,y,0)) for x,y in self.polygon]
        vb = [tm((x,y,-self.thickness)) for x,y in self.polygon]
        faces.append({'verts': vt, 'type': 'front', 'name': self.name, 'col': 'cardboard'})     
        faces.append({'verts': vb, 'type': 'back', 'name': self.name, 'col': 'white'}) 
        n = len(self.polygon)
        for i in range(n):
            faces.append({'verts': [vt[i], vt[(i+1)%n], vb[(i+1)%n], vb[i]], 'type': 'side', 'name': self.name})
        if self.parent:
            faces.extend(self._get_hinge_mesh(parent_tm))
        for c in self.children:
            faces.extend(c.get_mesh_3d(tm))
        return faces

    def _get_hinge_mesh(self, parent_tm):
        faces = []
        w_child = self.width
        p_left_child = (w_child/2, 0, -self.thickness)
        p_right_child = (-w_child/2, 0, -self.thickness)
        steps = 6 
        current_angle = self.fold_angle
        prev_v_left = None
        prev_v_right = None
        for i in range(steps + 1):
            t = i / steps
            interp_angle = current_angle * t
            tm_step = self._make_transform(parent_tm, angle_override=interp_angle)
            curr_v_left = tm_step(p_left_child)
            curr_v_right = tm_step(p_right_child)
            if prev_v_left is not None:
                faces.append({
                    'verts': [prev_v_left, curr_v_left, curr_v_right, prev_v_right],
                    'type': 'hinge', 'name': f"{self.name}_hinge", 'col': 'white'
                })
            prev_v_left = curr_v_left
            prev_v_right = curr_v_right
        return faces

    def get_layout_transform_2d(self, parent_pos=(0,0), parent_rot=0):
        rad = math.radians(parent_rot)
        rc, rs = math.cos(rad), math.sin(rad)
        lox, loy = self.layout_pos
        go_x = lox * rc - loy * rs
        go_y = lox * rs + loy * rc
        return (parent_pos[0] + go_x, parent_pos[1] + go_y), parent_rot + self.layout_rot

    def get_layout_2d(self, parent_pos=(0,0), parent_rot=0):
        my_pos, my_rot = self.get_layout_transform_2d(parent_pos, parent_rot)
        rad = math.radians(my_rot)
        c, s = math.cos(rad), math.sin(rad)
        gp = []
        for x, y in self.polygon: gp.append((x*c - y*s + my_pos[0], x*s + y*c + my_pos[1]))
        data = [{'coords': gp, 'type': self.label, 'id': self.name}]
        creases = []
        w = self.width; p1, p2 = (w/2, 0), (-w/2, 0)
        def to_g(pt): return (pt[0]*c - pt[1]*s + my_pos[0], pt[0]*s + pt[1]*c + my_pos[1])
        if self.parent: creases.append([to_g(p1), to_g(p2)])
        for ch in self.children:
            d, cr = ch.get_layout_2d(my_pos, my_rot)
            data.extend(d); creases.extend(cr)
        return data, creases

class Fondo(BoxComponent):
    def generate_shape(self):
        w, h = self.width, self.height
        pts = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
        self.polygon = round_poly(pts, 2.0)

class Fianco(BoxComponent):
    def __init__(self, name, w, h, t, p, edge, shape='rect', pars={}):
        self.shape = shape; self.pars = pars
        cutout_w = pars.get('cutout_w', w/2)
        self.shoulder_val = max(0, (w - cutout_w) / 2)
        self.h_low_val = pars.get('h_low', h*0.6)
        super().__init__(name, w, h, t, p, edge, 'fianchi')
        # I RADDOPPI (Reinf) si creano solo se l'utente li ha attivati esplicitamente
        if self.pars.get('r_active'):
            r_h = self.pars.get('r_h', 30); rw = w - 2*self.shoulder_val
            BoxComponent(f"{name}_Reinf", rw, r_h, t, self, 'reinf_attach', 'lembi')

    def generate_shape(self):
        w, h = self.width, self.height
        pts = []
        # MODIFICA CRUCIALE: Genera la forma "scassata" se è FERRO DI CAVALLO *OPPURE* se c'è la PIATTAFORMA
        if self.shape == 'ferro' or self.pars.get('plat_active'):
            sh, hl = self.shoulder_val, self.h_low_val
            pts = [(w/2, 0)]
            if self.pars.get('plat_active'):
                fh, ext_w, T = self.pars.get('fascia_h', 30), self.pars.get('plat_flap_w', 40), self.thickness
                cx, cy = fh + T/2, ext_w + T/2
                pts += [(w/2, -h + cy), (w/2 - cx, -h + cy), (w/2 - cx, -h)]
            else:
                pts.append((w/2, -h))
            pts += [(w/2 - sh, -h), (w/2 - sh, -hl), (-w/2 + sh, -hl), (-w/2 + sh, -h)]
            if self.pars.get('plat_active'):
                fh, ext_w, T = self.pars.get('fascia_h', 30), self.pars.get('plat_flap_w', 40), self.thickness
                cx, cy = fh + T/2, ext_w + T/2
                pts += [(-w/2 + cx, -h), (-w/2 + cx, -h + cy), (-w/2, -h + cy)]
            else:
                pts.append((-w/2, -h))
            pts.append((-w/2, 0))
        else: 
            pts = [(w/2, 0), (w/2, -h), (-w/2, -h), (-w/2, 0)]
        
        self.polygon = round_poly(pts, 2.0)

class Testata(BoxComponent):
    def __init__(self, name, w, h, t, p, edge, shape='rect', pars={}):
        self.shape = shape; self.pars = pars
        cutout_w = pars.get('cutout_w', w/2)
        self.shoulder_val = max(0, (w - cutout_w) / 2)
        self.h_low_val = pars.get('h_low', h*0.6)
        super().__init__(name, w, h, t, p, edge, 'testate')
        if self.pars.get('r_active'):
            r_h = self.pars.get('r_h', 30); rw = w - 2*self.shoulder_val
            BoxComponent(f"{name}_Reinf", rw, r_h, t, self, 'reinf_attach', 'lembi')

    def generate_shape(self):
        w, h = self.width, self.height
        pts = []
        if self.shape == 'ferro':
            sh, hl = self.shoulder_val, self.h_low_val
            pts = [
                (w/2, 0), (w/2, -h), (w/2 - sh, -h), (w/2 - sh, -hl),
                (-w/2 + sh, -hl), (-w/2 + sh, -h), (-w/2, -h), (-w/2, 0)
            ]
        else: 
            pts = [(w/2, 0), (w/2, -h), (-w/2, -h), (-w/2, 0)]
            
        self.polygon = round_poly(pts, 2.0)

class BoxManager:
    def __init__(self): self.root = None
    
    def build(self, p):
        L, W = p['L'], p['W']
        T = p.get('thickness', 5.0)
        HF, HT, F = p['h_fianchi'], p['h_testate'], p['F']
        
        WT = W - (2 * T)
        WF = W 
        LF = L
        HL = HT - T 

        self.root = Fondo("Fondo", L, W, T, None, None, 'fondo')
        
        # FIANCHI
        pf = {'cutout_w': p.get('fianchi_cutout_w', L/2), 'h_low': p.get('fianchi_h_low', 0),
              'r_active': p.get('fianchi_r_active', False), 'r_h': p.get('fianchi_r_h', 30),
              'plat_active': p.get('platform_active', False), 'fascia_h': p.get('fascia_h', 30), 'plat_flap_w': p.get('plat_flap_w', 40)}
        sf = p['fianchi_shape']
        Fianco("Fianco_T", LF, HF, T, self.root, 'top', sf, pf)
        Fianco("Fianco_B", LF, HF, T, self.root, 'bottom', sf, pf)
        
        # TESTATE
        pt = {'cutout_w': p.get('testate_cutout_w', W/2), 'h_low': p.get('testate_h_low', 0),
              'r_active': p.get('testate_r_active', False), 'r_h': p.get('testate_r_h', 30)}
        st = p['testate_shape']
        tl = Testata("Testata_L", WT, HT, T, self.root, 'left', st, pt)
        tr = Testata("Testata_R", WT, HT, T, self.root, 'right', st, pt)
        
        # LEMBI E PIATTAFORMA
        for t in [tl, tr]:
            l1 = BoxComponent(f"{t.name}_L1", HL, F, T, t, 'left', 'lembi'); l1.fold_axis = 'y'
            l2 = BoxComponent(f"{t.name}_L2", HL, F, T, t, 'right', 'lembi'); l2.fold_axis = 'y'
            
            if p.get('platform_active'):
                fh, ext_w = p.get('fascia_h', 30), p.get('plat_flap_w', 30)
                # Verifica se usare la logica a ferro anche per generare la piattaforma
                # La piattaforma si attacca ai lati (shoulder) della testata
                if pt['r_active'] and st == 'ferro':
                    cutout = t.pars['cutout_w']
                    sh_fascia = (WF - cutout) / 2
                    offset_val = (sh_fascia - t.shoulder_val) / 2
                    fl = BoxComponent(f"{t.name}_Fascia_L", sh_fascia, fh, T, t, 'leg_left', 'fasce', custom_offset=offset_val)
                    BoxComponent("ExtL", fh, ext_w, T, fl, 'left', 'ext') 
                    fr = BoxComponent(f"{t.name}_Fascia_R", sh_fascia, fh, T, t, 'leg_right', 'fasce', custom_offset=offset_val)
                    BoxComponent("ExtR", fh, ext_w, T, fr, 'right', 'ext')
                else:
                    fascia = BoxComponent(f"{t.name}_Fascia", WF, fh, T, t, 'bottom', 'fasce')
                    BoxComponent("Ext1", fh, ext_w, T, fascia, 'left', 'ext')
                    BoxComponent("Ext2", fh, ext_w, T, fascia, 'right', 'ext')

    def get_3d_faces(self): return self.root.get_mesh_3d() if self.root else []
    
    def get_2d_diagram(self):
        if not self.root: return [], [], []
        polys, creases = self.root.get_layout_2d()
        cut_lines = []
        for p in polys:
            pts = p['coords']
            for i in range(len(pts)): cut_lines.append([pts[i], pts[(i+1)%len(pts)]])
        return polys, cut_lines, creases

    def set_angles(self, angles):
        def visit(n):
            if "Reinf" in n.name: n.fold_angle = angles.get('reinf', 0)
            elif n.label == 'fasce': n.fold_angle = angles.get('fasce', 0)
            elif n.label == 'ext': n.fold_angle = angles.get('ext', 0)
            elif n.label == 'lembi': n.fold_angle = angles.get('lembi', 0)
            elif n.label == 'testate': n.fold_angle = angles.get('testate', 0)
            elif n.label == 'fianchi': n.fold_angle = angles.get('fianchi', 0)
            for c in n.children: visit(c)
        if self.root: visit(self.root)