#!/usr/bin/python
# Update dependencies based on info.py
# Copyright (C) 2010 Jelmer Vernooij <jelmer@debian.org>
# Licensed under the GNU GPL, version 2 or later.

from debian.deb822 import Deb822, PkgRelation
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from info import bzr_compatible_versions

def update_relation(l, pkg, kind, version):
    found = False
    for pr in l:
        if len(pr) != 1:
            continue
        e = pr[0]
        if e["name"] == pkg and e["version"] and e["version"][0] == kind:
            e["version"] = (kind, version)
            found = True
    if not found:
        l.append([{"version": (kind, version), "name": pkg, "arch": None}])

f = open('debian/control', 'r')

source = Deb822(f)

def update_deps(control, field, package):
    bdi = PkgRelation.parse_relations(control[field])
    update_relation(bdi, package, ">=", "%d.%d~" % bzr_compatible_versions[0][:2])
    update_relation(bdi, package, "<<", "%d.%d.0" % (bzr_compatible_versions[-1][0], bzr_compatible_versions[-1][1]+1))
    control[field] = PkgRelation.str(bdi)

update_deps(source, "Build-Depends-Indep", "bzr")

binary1 = Deb822(f)
binary2 = Deb822(f)

update_deps(binary1, "Depends", "python-breezy")

with open("debian/control", "w+") as f:
    source.dump(f)
    f.write("\n")
    binary1.dump(f)
    f.write("\n")
    binary2.dump(f)
