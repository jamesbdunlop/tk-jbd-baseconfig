# Copyright (c) 2013 Shotgun Software Inc.
# CONFIDENTIAL AND PROPRIETARY
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
from hooks.maya_SceneScan import mdl_scan_scene
from tank import Hook
import config_constants as configCONST

class ScanSceneHook(Hook):
    def execute(self, **kwargs):
        items = mdl_scan_scene(configCONST.LND_SUFFIX, configCONST.SANITY['MDL_LND'])
        return items
