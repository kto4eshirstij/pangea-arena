# Arrow: reed shaft, flint leaf head, three feathers. proj_arrow_fire adds a pitch-soaked tow
# wad behind the head + "flame" surface. Origin at the balance point, flies +X.
from types import SimpleNamespace

from lib import geo
from lib import materials as M


def variant(mid):
    fire = mid.endswith("fire")

    def build():
        reed = M.make("wood_ash", mid + "_reed", axis='X', grain=3.0)
        flint = M.make("flint", mid + "_head", chip=2.5)
        feather = M.make("feather", mid + "_fl", color=1, axis='X', bars=1.6)
        sinew = M.make("sinew", mid + "_bind")
        o = [geo.tube("shaft", [(-14.5, 0, 0), (11.6, 0, 0)], 0.17, sides=4, mat=reed),
             geo.blob("head", (13.5, 0, 0), (2.0, 0.62, 0.14), segs=4, rings=4, mat=flint,
                      sharpen=0.4, sharp=25),
             geo.tube("bind", [(11.0, 0, 0), (12.0, 0, 0)], 0.25, sides=4, mat=sinew,
                      caps=(False, False))]
        for k in range(3):
            r = geo.rot(120 * k, 0, 0)
            o.append(geo.blob("vane%d" % k, r @ geo.Vector((-11.6, 0, 0.42)), (2.4, 0.04, 0.42),
                              segs=4, rings=3, mat=feather, sharp=80, r=r))
        if fire:
            tow = M.make("tow", mid + "_tow", glow=True)
            o.append(geo.blob("tow", (10.2, 0, 0), (1.5, 0.75, 0.75), segs=5, rings=3, mat=tow,
                              jitter=0.08))
            o.append(geo.cross_planes("flame", (9.4, 0, -0.6), 3.2, 4.5, n=2, surface="flame"))
        o.append(geo.tag("tag_flash", (13.0 if not fire else 10.2, 0, 0)))
        return o
    return SimpleNamespace(ID=mid, KIND="projectile", TEX=256, TRI_MAX=120, PAINT=False,
                           build=build)
