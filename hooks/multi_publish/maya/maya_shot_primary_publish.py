# Copyright (c) 2013 Shotgun Software Inc.
# CONFIDENTIAL AND PROPRIETARY
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
from tank import TankError
from tank import Hook
import tank
import hooks.multi_publish.maya.maya_ScenePublish as scnPub


class PrimaryPublishHook(Hook):
    def execute(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb, **kwargs):
        # get the engine name from the parent object (app/engine/etc.)
        engine_name = self.parent.engine.name
        # depending on engine:
        if engine_name == "tk-maya":
            return scnPub._do_maya_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb, tank, self.parent)
        else:
            raise TankError("Unable to perform publish for unhandled engine {} \n \
                Check with your TD that the config is loading the right primary publish hook.".format(engine_name))
