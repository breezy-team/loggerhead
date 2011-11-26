#!/usr/bin/env python
# API Info for loggerhead

bzr_plugin_name = "loggerhead"

bzr_plugin_version = (1, 18, 1)  # Keep in sync with loggerhead/__init__.py

bzr_compatible_versions = [
    (1, 17, 0), (1, 18, 0), (2, 0, 0), (2, 1, 0), (2, 2, 0), (2, 3, 0),
    (2, 4, 0), (2, 5, 0),
    ]

bzr_minimum_version = bzr_compatible_versions[0]

bzr_maximum_version = bzr_compatible_versions[-1]
