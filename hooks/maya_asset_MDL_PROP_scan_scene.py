# Copyright (c) 2013 Shotgun Software Inc.
# CONFIDENTIAL AND PROPRIETARY
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import configCONST as configCONST
from maya_SceneScan import mdl_scan_scene
from tank import Hook

class ScanSceneHook(Hook):
    def execute(self, **kwargs):
        items = mdl_scan_scene(configCONST.PROP_SUFFIX, configCONST.SANITY['MDL_GENERIC'])
        return items