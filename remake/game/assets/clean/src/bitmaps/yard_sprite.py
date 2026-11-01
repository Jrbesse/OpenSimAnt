"""yard_sprite: a tiny software renderer for the yard's animals (docs/clean_pack/yard_bitmaps.md, passes 4 and 5).

Every animal is a chain of shaded spheres in 3-D (local axes f = forward, r = right, z = up), posed by a `Pose` (heading,
pitch, roll, spin about the view axis), seen by an orthographic camera looking down at `elev` degrees, lit from the top-left of
the screen.  The picture is rendered at S sub-pixels per unit with a z-buffer, then CUT to its bounding box and resampled
(mode of each block) to the exact size of the sprite minus the 1-px black outline, so every sprite is tight by construction
and has the size of its table.  Eyes, collars and noses are single-pixel `marks` stamped after the resample (a mark shows only
where its surface point faces the camera).
"""
import numpy as np

from uilib import Img, T

L_SCREEN = np.array([-0.50, -0.55, 0.66])
L_SCREEN = L_SCREEN / np.linalg.norm(L_SCREEN)


def rot_axis(axis, ang):
    a = np.array(axis, dtype=float)
    a = a / np.linalg.norm(a)
    c, s = np.cos(ang), np.sin(ang)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + s * K + (1 - c) * (K @ K)


class Pose:
    """local (f, r, z) -> world (X right, Y away from the viewer, Z up).  heading in degrees: 0 = right, 90 = away, 180 = left,
    270 = towards the viewer.  pitch (nose up), roll (right side down), spin (turn about the view axis, degrees)."""

    def __init__(self, origin=(0, 0, 0), heading=0.0, pitch=0.0, roll=0.0, spin=0.0, elev=35.0):
        h = np.radians(heading)
        f = np.array([np.cos(h), np.sin(h), 0.0])
        r = np.array([np.sin(h), -np.cos(h), 0.0])
        z = np.array([0.0, 0.0, 1.0])
        B = np.stack([f, r, z], axis=1)
        a, b = np.radians(pitch), np.radians(roll)
        Rp = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])
        Rr = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
        self.M = B @ Rp @ Rr
        if spin:
            e = np.radians(elev)
            self.M = rot_axis((0.0, -np.cos(e), np.sin(e)), np.radians(spin)) @ self.M
        self.o = np.array(origin, dtype=float)

    def w(self, p):
        return self.o + self.M @ np.array(p, dtype=float)

    def local(self, Pw):
        """Pw: (n, 3) world points -> local (n, 3)."""
        return (np.asarray(Pw, dtype=float) - self.o) @ self.M      # M is orthonormal: inverse = transpose


class Scene:
    def __init__(self, ext=34.0, S=6, elev=35.0, thr=(0.12, 0.62)):
        self.ext, self.S, self.elev, self.thr = ext, S, elev, thr
        self.se, self.ce = np.sin(np.radians(elev)), np.cos(np.radians(elev))
        n = int(2 * ext * S)
        self.n = n
        self.col = np.full((n, n), -1, dtype=np.int16)
        self.pid = np.full((n, n), -1, dtype=np.int16)
        self.zb = np.full((n, n), -1e9)
        self.marks = []

    # camera
    def proj(self, P):
        X, Y, Z = P
        return X, -(Z * self.ce + Y * self.se), Z * self.se - Y * self.ce

    def sphere(self, Pw, R, ramp, pid=0, decal=None):
        """Pw = world centre.  ramp = colours dark -> light (1..3 entries).  decal = (pose, fn): fn(local points (n, 3)) -> int array
        of colour overrides (-1 = none)."""
        S, ext = self.S, self.ext
        sx, sy, D = self.proj(Pw)
        ix0 = max(0, int(np.floor((sx - R + ext) * S)))
        ix1 = min(self.n, int(np.ceil((sx + R + ext) * S)) + 1)
        iy0 = max(0, int(np.floor((sy - R + ext) * S)))
        iy1 = min(self.n, int(np.ceil((sy + R + ext) * S)) + 1)
        if ix1 <= ix0 or iy1 <= iy0:
            return
        xs = ((np.arange(ix0, ix1) + 0.5) / S - ext - sx) / R
        ys = ((np.arange(iy0, iy1) + 0.5) / S - ext - sy) / R
        u, v = np.meshgrid(xs, ys)
        rho2 = u * u + v * v
        inside = rho2 <= 1.0
        nz = np.sqrt(np.clip(1.0 - rho2, 0, 1))
        Dp = D + nz * R
        zb = self.zb[iy0:iy1, ix0:ix1]
        upd = inside & (Dp > zb)
        if not upd.any():
            return
        s = u * L_SCREEN[0] + v * L_SCREEN[1] + nz * L_SCREEN[2]
        idx = np.where(s < self.thr[0], 0, np.where(s < self.thr[1], 1, 2))
        idx = np.minimum(idx, len(ramp) - 1)
        if len(ramp) == 2:
            idx = np.where(s < self.thr[1] - 0.1, 0, 1)
        colour = np.array(ramp, dtype=np.int16)[idx]
        if decal is not None:
            pose, fn = decal
            ex = np.array([1.0, 0, 0])
            eup = np.array([0, self.se, self.ce])
            eto = np.array([0, -self.ce, self.se])
            Nw = u[..., None] * ex + (-v)[..., None] * eup + nz[..., None] * eto
            surf = np.asarray(Pw)[None, None, :] + Nw * R
            ov = fn(pose.local(surf.reshape(-1, 3))).reshape(rho2.shape)
            colour = np.where(ov >= 0, ov, colour)
        self.col[iy0:iy1, ix0:ix1] = np.where(upd, colour, self.col[iy0:iy1, ix0:ix1])
        self.pid[iy0:iy1, ix0:ix1] = np.where(upd, pid, self.pid[iy0:iy1, ix0:ix1])
        self.zb[iy0:iy1, ix0:ix1] = np.where(upd, Dp, zb)

    def cap(self, P0, P1, R0, R1, ramp, pid=0, decal=None):
        P0, P1 = np.array(P0, dtype=float), np.array(P1, dtype=float)
        L = np.linalg.norm(P1 - P0)
        n = max(2, int(np.ceil(L / (0.22 * min(R0, R1)))))
        for i in range(n + 1):
            t = i / n
            self.sphere(P0 + (P1 - P0) * t, R0 + (R1 - R0) * t, ramp, pid, decal)

    def mark(self, Pw, colour, tol=1.1):
        self.marks.append((np.array(Pw, dtype=float), colour, tol))

    # ------------------------------------------------------------------------------------------------ output
    def finish(self, w, h, line_pids=None, dthr=0.6, thresh=0.42, outline=15):
        """Cut, resample to (w, h) with a 1-px outline.  line_pids: part ids that get a black separator where a nearer part of
        another id touches them."""
        S, ext = self.S, self.ext
        alpha = self.col >= 0
        ys, xs = np.where(alpha)
        by0, by1, bx0, bx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        iw, ih = w - 2, h - 2
        col = np.full((ih, iw), T, dtype=np.int16)
        pid = np.full((ih, iw), -1, dtype=np.int16)
        dep = np.full((ih, iw), -1e9)
        cov = np.zeros((ih, iw))
        for j in range(ih):
            ya, yb = by0 + (by1 - by0) * j / ih, by0 + (by1 - by0) * (j + 1) / ih
            ya, yb = int(round(ya)), max(int(round(ya)) + 1, int(round(yb)))
            for i in range(iw):
                xa, xb = bx0 + (bx1 - bx0) * i / iw, bx0 + (bx1 - bx0) * (i + 1) / iw
                xa, xb = int(round(xa)), max(int(round(xa)) + 1, int(round(xb)))
                blk = self.col[ya:yb, xa:xb]
                m = blk >= 0
                c = m.mean()
                cov[j, i] = c
                if c > 0:
                    cnt = np.bincount(blk[m], minlength=16)
                    col[j, i] = int(cnt.argmax())
                    bp = self.pid[ya:yb, xa:xb][m]
                    pid[j, i] = int(np.bincount(bp[bp >= 0]).argmax()) if (bp >= 0).any() else 0
                    dep[j, i] = float(self.zb[ya:yb, xa:xb][m].mean())
        sil = cov >= thresh
        # make the four extreme rows / columns exist (thin tails and ears must not be cut by the threshold)
        for axis, edge in ((0, 0), (0, ih - 1), (1, 0), (1, iw - 1)):
            line = sil[edge, :] if axis == 0 else sil[:, edge]
            if not line.any():
                cv = cov[edge, :] if axis == 0 else cov[:, edge]
                k = int(cv.argmax())
                assert cv[k] > 0, 'empty edge'
                if axis == 0:
                    sil[edge, k] = True
                else:
                    sil[k, edge] = True
        img = Img(w, h, T)
        pids = np.full((h, w), -1, dtype=np.int16)
        deps = np.full((h, w), -1e9)
        for j in range(ih):
            for i in range(iw):
                if sil[j, i]:
                    img.a[j + 1, i + 1] = col[j, i] if col[j, i] != T else 15
                    pids[j + 1, i + 1] = pid[j, i]
                    deps[j + 1, i + 1] = dep[j, i]
        # separators
        if line_pids:
            base = img.a.copy()
            for y in range(h):
                for x in range(w):
                    if base[y, x] == T or pids[y, x] not in line_pids:
                        continue
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w and 0 <= yy < h and base[yy, xx] != T and pids[yy, xx] != pids[y, x] \
                                and deps[yy, xx] > deps[y, x] + dthr:
                            img.a[y, x] = outline
                            break
        # marks
        for (Pw, c, tol) in self.marks:
            sx, sy, D = self.proj(Pw)
            cx, cy = (sx + ext) * S, (sy + ext) * S
            ci, cj = int(cx), int(cy)
            if not (0 <= ci < self.n and 0 <= cj < self.n):
                continue
            if abs(self.zb[cj, ci] - D) > tol * 1.0 or self.col[cj, ci] < 0:
                continue
            i = int(np.floor((cx - bx0) * iw / (bx1 - bx0)))
            j = int(np.floor((cy - by0) * ih / (by1 - by0)))
            if 0 <= i < iw and 0 <= j < ih and sil[j, i]:
                img.a[j + 1, i + 1] = c
        # the outline
        sm = img.a != T
        out = np.zeros_like(sm)
        out[1:, :] |= sm[:-1, :]
        out[:-1, :] |= sm[1:, :]
        out[:, 1:] |= sm[:, :-1]
        out[:, :-1] |= sm[:, 1:]
        img.a[out & ~sm] = outline
        return img


def tight(img):
    a = img.a != T
    return bool(a[0].any() and a[-1].any() and a[:, 0].any() and a[:, -1].any())


def centroid(img):
    ys, xs = np.where(img.a != T)
    return float(xs.mean()), float(ys.mean())
