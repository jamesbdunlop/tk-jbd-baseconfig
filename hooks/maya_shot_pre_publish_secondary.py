# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
import config_constants as configCONST
import maya.cmds as cmds
from tank import Hook

class PrePublishHook(Hook):
    def execute(self, tasks, work_template, progress_cb, **kwargs):
        results = []
        
        # validate tasks:
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            # report progress:
            progress_cb(0, "Validating", task)
            if item["type"] == configCONST.STATIC_CACHE:
                errors.extend(self._validate_item_for_publish(item))
            elif item["type"] == configCONST.ANIM_CACHE:
                errors.extend(self._validate_item_for_publish(item))
            elif item["type"] == configCONST.FX_CACHE:
                errors.extend(self._validate_item_for_publish(item))
            elif item["type"] == configCONST.CAMERA_CACHE:
                errors.extend(self._validate_item_for_publish(item))
            elif item["type"] == configCONST.GPU_CACHE:
                errors.extend(self._validate_item_for_publish(item))
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! \nPlease contact your supervisor...{}".format(output["name"]))

            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                results.append({"task": task, "errors": errors})
                
            progress_cb(100)
            
        return results

    def _validate_item_for_publish(self, item):
        """
        Validate that the item is valid to be exported 
        to an alembic cache
        """
        errors = []
        ## FINAL CHECKS PRE PUBLISH JUST TO MAKE SURE NOTHING ODD HAS HAPPENED IN THE SCENE BEFORE CLICKING THE PUBLISH BUTTON
        # check that the group still exists:
        if not cmds.objExists(item["name"]):
            errors.append("{} couldn't be found in the scene!".format(item["name"]))
        # finally return any errors
        return errors