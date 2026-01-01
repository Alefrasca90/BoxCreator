import math

class Part3D:
    def __init__(self, name, vertices, parent=None, pivot=(0,0,0), axis='x', fold_sign=1):
        self.name = name
        self.local_vertices = vertices 
        self.parent = parent
        self.pivot = pivot 
        self.axis = axis 
        self.fold_sign = fold_sign 
        self.angle = 0.0
        self.children = []
        if parent: parent.children.append(self)

    def compute_world_transform(self, parent_tr=None):
        rad = math.radians(self.angle)
        c, s = math.cos(rad), math.sin(rad)
        
        def transform(v):
            x, y, z = v
            # Rotazione Locale
            if self.axis == 'x': rx, ry, rz = (x, y*c - z*s, y*s + z*c)
            elif self.axis == 'y': rx, ry, rz = (x*c + z*s, y, -x*s + z*c)
            else: rx, ry, rz = (x*c - y*s, x*s + y*c, z)
            
            # Traslazione al Pivot
            px, py, pz = (rx + self.pivot[0], ry + self.pivot[1], rz + self.pivot[2])
            
            if parent_tr:
                return parent_tr((px, py, pz))
            else:
                return (px, py, pz)
        
        return transform

class Scene3D:
    def __init__(self):
        self.parts = []
    
    def build_box(self, p):
        self.parts = []
        L, W = p['L'], p['W']
        H_f, H_t = p['h_fianchi'], p['h_testate']
        F = p['F']
        T = p.get('thickness', 5.0)
        
        # Offset fisico per le parti interne (Z = -T)
        def off(v_list):
            return [(x, y, -T) for x, y, z in v_list]
        
        # 1. FONDO (Z=0).
        v_fondo = [(-L/2, -W/2, 0), (-L/2, W/2, 0), (L/2, W/2, 0), (L/2, -W/2, 0)]
        fondo = Part3D("Fondo", v_fondo, None, (0,0,0), 'x', 0)
        self.parts.append(fondo)
        
        # 2. FIANCATE (ESTERNE -> Z=0, Ristrette di T per lato)
        v_f_top = [(-L/2 + T, -H_f, 0), (-L/2 + T, 0, 0), (L/2 - T, 0, 0), (L/2 - T, -H_f, 0)]
        fianco_top = Part3D("Fianco_Top", v_f_top, fondo, (0, -W/2, 0), 'x', 1) 
        self.parts.append(fianco_top)
        
        v_f_btm = [(-L/2 + T, 0, 0), (-L/2 + T, H_f, 0), (L/2 - T, H_f, 0), (L/2 - T, 0, 0)]
        fianco_btm = Part3D("Fianco_Btm", v_f_btm, fondo, (0, W/2, 0), 'x', -1) 
        self.parts.append(fianco_btm)
        
        # 3. TESTATE (ESTERNE -> Z=0, Ristrette di T per lato)
        v_t_left = [(-H_t, -W/2 + T, 0), (-H_t, W/2 - T, 0), (0, W/2 - T, 0), (0, -W/2 + T, 0)]
        testata_sx = Part3D("Testata_L", v_t_left, fondo, (-L/2, 0, 0), 'y', -1) 
        self.parts.append(testata_sx)
        
        v_t_right = [(0, -W/2 + T, 0), (0, W/2 - T, 0), (H_t, W/2 - T, 0), (H_t, -W/2 + T, 0)]
        testata_dx = Part3D("Testata_R", v_t_right, fondo, (L/2, 0, 0), 'y', 1) 
        self.parts.append(testata_dx)
        
        # 4. LEMBI (INTERNI -> off(-T))
        v_l_tl = [(-H_t, -F, 0), (-H_t, 0, 0), (0, 0, 0), (0, -F, 0)]
        lembo_tl = Part3D("Lembo_TL", off(v_l_tl), testata_sx, (0, -W/2 + T, 0), 'x', 1)
        self.parts.append(lembo_tl)
        
        v_l_bl = [(-H_t, 0, 0), (-H_t, F, 0), (0, F, 0), (0, 0, 0)]
        lembo_bl = Part3D("Lembo_BL", off(v_l_bl), testata_sx, (0, W/2 - T, 0), 'x', -1)
        self.parts.append(lembo_bl)
        
        v_l_tr = [(0, -F, 0), (0, 0, 0), (H_t, 0, 0), (H_t, -F, 0)]
        lembo_tr = Part3D("Lembo_TR", off(v_l_tr), testata_dx, (0, -W/2 + T, 0), 'x', 1)
        self.parts.append(lembo_tr)

        v_l_br = [(0, 0, 0), (0, F, 0), (H_t, F, 0), (H_t, 0, 0)]
        lembo_br = Part3D("Lembo_BR", off(v_l_br), testata_dx, (0, W/2 - T, 0), 'x', -1)
        self.parts.append(lembo_br)
        
        # 5. PLATFORM (INTERNI -> off(-T))
        if p.get('platform_active'):
            fh = p.get('fascia_h', 30)
            pl_w = p.get('plat_flap_w', 30)
            
            v_fascia_l = [(-fh, -W/2, 0), (-fh, W/2, 0), (0, W/2, 0), (0, -W/2, 0)]
            fascia_l = Part3D("Fascia_L", off(v_fascia_l), testata_sx, (-H_t, 0, 0), 'y', -1)
            self.parts.append(fascia_l)
            
            v_pfl_top = [(-fh, -pl_w, 0), (-fh, 0, 0), (0, 0, 0), (0, -pl_w, 0)]
            pfl_top = Part3D("PFlap_L_Top", off(v_pfl_top), fascia_l, (0, -W/2, 0), 'x', 1)
            self.parts.append(pfl_top)
            
            v_pfl_btm = [(-fh, 0, 0), (-fh, pl_w, 0), (0, pl_w, 0), (0, 0, 0)]
            pfl_btm = Part3D("PFlap_L_Btm", off(v_pfl_btm), fascia_l, (0, W/2, 0), 'x', -1)
            self.parts.append(pfl_btm)
            
            v_fascia_r = [(0, -W/2, 0), (0, W/2, 0), (fh, W/2, 0), (fh, -W/2, 0)]
            fascia_r = Part3D("Fascia_R", off(v_fascia_r), testata_dx, (H_t, 0, 0), 'y', 1)
            self.parts.append(fascia_r)
            
            v_pfr_top = [(0, -pl_w, 0), (0, 0, 0), (fh, 0, 0), (fh, -pl_w, 0)]
            pfr_top = Part3D("PFlap_R_Top", off(v_pfr_top), fascia_r, (0, -W/2, 0), 'x', 1)
            self.parts.append(pfr_top)
            
            v_pfr_btm = [(0, 0, 0), (0, pl_w, 0), (fh, pl_w, 0), (fh, 0, 0)]
            pfr_btm = Part3D("PFlap_R_Btm", off(v_pfr_btm), fascia_r, (0, W/2, 0), 'x', -1)
            self.parts.append(pfr_btm)

    def get_world_polygons(self):
        transforms = {} 
        def get_tr(part):
            if part in transforms: return transforms[part]
            parent_tr = get_tr(part.parent) if part.parent else None
            tr = part.compute_world_transform(parent_tr)
            transforms[part] = tr
            return tr
        polys = []
        for p in self.parts:
            tr = get_tr(p)
            w_verts = [tr(v) for v in p.local_vertices]
            polys.append((w_verts, p.name))
        return polys