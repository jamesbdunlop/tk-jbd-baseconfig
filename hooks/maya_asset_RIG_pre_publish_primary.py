# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
from tank import Hook
from tank import TankError
from apps.app_logger import log

class PrimaryPrePublishHook(Hook):
    def execute(self, task, work_template, progress_cb, **kwargs):
        # get the engine name from the parent object (app/engine/etc.)
        engine_name = self.parent.engine.name
        # depending on engine:
        if engine_name == "tk-maya":
            return self._do_maya_pre_publish(task, work_template, progress_cb)
        elif engine_name == "tk-nuke":
            return self._do_nuke_pre_publish(task, work_template, progress_cb)
        elif engine_name == "tk-3dsmax":
            return self._do_3dsmax_pre_publish(task, work_template, progress_cb)
        elif engine_name == "tk-hiero":
            return self._do_hiero_pre_publish(task, work_template, progress_cb)
        elif engine_name == "tk-houdini":
            return self._do_houdini_pre_publish(task, work_template, progress_cb)
        elif engine_name == "tk-softimage":
            return self._do_softimage_pre_publish(task, work_template, progress_cb)
        elif engine_name == "tk-photoshop":
            return self._do_photoshop_pre_publish(task, work_template, progress_cb)
        else:
            raise TankError("Unable to perform pre-publish for unhandled engine %s" % engine_name)
        
    def _do_maya_pre_publish(self, task, work_template, progress_cb):
        """
        Do Maya primary pre-publish/scene validation
        """
        import maya.cmds as cmds
        log(app = None, method = '_do_maya_pre_publish', message = 'Validating', verbose = True)
        progress_cb(0.0, "Validating current scene", task)
        
        # get the current scene file:
        scene_file = cmds.file(query=True, sn=True)
        if scene_file:
            scene_file = os.path.abspath(scene_file)
            
        # validate it:
        scene_errors = self._validate_work_file(scene_file, work_template, task["output"], progress_cb)
        
        progress_cb(100)
          
        return scene_errors
    
    def _validate_work_file(self, path, work_template, output, progress_cb):
        """
        Validate that the given path is a valid work file and that
        the published version of it doesn't already exist.
        
        Return the new version number that the scene should be
        up'd to after publish
        """
        errors = []
        
        if not work_template.validate(path):
            raise TankError("File '%s' is not a valid work path, unable to publish!" % path)
        
        progress_cb(50, "Validating publish path")
        
        # find the publish path:
        fields = work_template.get_fields(path)
        fields["TankType"] = output["tank_type"]
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields) 
                      
        progress_cb(75, "Validating current version")
        
        # check the version number against existing versions:
        # this check is from the original maya publish - should it check against the existing published files as well?
        # (Note: tk-nuke-publish version is practically the same atm)
        existing_versions = self.parent.tank.paths_from_template(work_template, fields, ["version"])
        version_numbers = [ work_template.get_fields(v).get("version") for v in existing_versions]
        curr_v_no = fields["version"]
        try:
            max_v_no = max(version_numbers)
            if max_v_no > curr_v_no:
                # there is a higher version number - this means that someone is working
                # on an old version of the file. Warn them about upgrading.
                errors.append("Your current work file is v%03d, however a more recent "
                       "version (v%03d) already exists. After publishing, your version "
                       "will become v%03d, thereby shadowing some previous work. " % (curr_v_no, max_v_no, max_v_no + 1))
        except:
            pass
        
        return errors