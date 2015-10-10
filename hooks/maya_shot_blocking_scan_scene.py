# Copyright (c) 2013 Shotgun Software Inc.
# CONFIDENTIAL AND PROPRIETARY
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import configCONST as configCONST
from hooks.maya_SceneScan import anim_scan_Scene
from tank import Hook

class ScanSceneHook(Hook):
    def execute(self, **kwargs):
        items = anim_scan_Scene(env = configCONST.LAYOUT_SHORTNAME, cleanup = None)
        return items