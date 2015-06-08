# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os, sys
import maya.cmds as cmds
import tank
from tank import Hook
from tank import TankError


class PostPublishHook(Hook):
    """
    Single hook that implements post-publish functionality
    """    
    def execute(self, work_template, progress_cb, **kwargs):
        """
        Main hook entry point
        
        :work_template: template
                        This is the template defined in the config that
                        represents the current work file
                        
        :progress_cb:   Function
                        A progress callback to log progress during pre-publish.  Call:
                        
                            progress_cb(percentage, msg)
                             
                        to report progress to the UI

        :returns:       None - raise a TankError to notify the user of a problem
        """
        # get the engine name from the parent object (app/engine/etc.)
        engine_name = self.parent.engine.name
        
        # depending on engine:
        if engine_name == "tk-maya":
            self._do_maya_post_publish(work_template, progress_cb)
        elif engine_name == "tk-nuke":
            self._do_nuke_post_publish(work_template, progress_cb)
        elif engine_name == "tk-3dsmax":
            self._do_3dsmax_post_publish(work_template, progress_cb)
        elif engine_name == "tk-hiero":
            self._do_hiero_post_publish(work_template, progress_cb)
        elif engine_name == "tk-houdini":
            self._do_houdini_post_publish(work_template, progress_cb)
        elif engine_name == "tk-softimage":
            self._do_softimage_post_publish(work_template, progress_cb)
        elif engine_name == "tk-photoshop":
            self._do_photoshop_post_publish(work_template, progress_cb)
        else:
            raise TankError("Unable to perform post publish for unhandled engine %s" % engine_name)
        
    def _do_maya_post_publish(self, work_template, progress_cb):
        """
        Do any Maya post-publish work
        """        
        import maya.cmds as cmds
        progress_cb(0, "Post Checking scene now...")

        ## Set model panel to show back to ALL after publish
        modelPanels = cmds.getPanel(type = 'modelPanel')
        if modelPanels:
            [cmds.modelEditor(mp, edit = True, allObjects = True) for mp in modelPanels]

        cmds.file(save = True, force = True)
        progress_cb(100,"Post complete...")

    def _get_next_work_file_version(self, work_template, fields):
        """
        Find the next available version for the specified work_file
        """
        existing_versions = self.parent.tank.paths_from_template(work_template, fields, ["version"])
        version_numbers = [work_template.get_fields(v).get("version") for v in existing_versions]
        curr_v_no = fields["version"]
        max_v_no = max(version_numbers)
        return max(curr_v_no, max_v_no) + 1
