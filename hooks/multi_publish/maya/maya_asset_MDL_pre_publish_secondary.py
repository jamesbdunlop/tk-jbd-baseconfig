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
import maya.cmds as cmds
from tank import Hook
import config_constants as configCONST


class PrePublishHook(Hook):
    """
    Single hook that implements pre-publish functionality
    """
    def execute(self, tasks, work_template, progress_cb, **kwargs):
        """
        Main hook entry point
        :tasks:         List of tasks to be pre-published.  Each task is be a 
                        dictionary containing the following keys:
                        {   
                            item:   Dictionary
                                    This is the item returned by the scan hook 
                                    {   
                                        name:           String
                                        description:    String
                                        type:           String
                                        other_params:   Dictionary
                                    }
                                   
                            output: Dictionary
                                    This is the output as defined in the configuration - the 
                                    primary output will always be named 'primary' 
                                    {
                                        name:             String
                                        publish_template: template
                                        tank_type:        String
                                    }
                        }
                        
        :work_template: template
                        This is the template defined in the config that
                        represents the current work file
               
        :progress_cb:   Function
                        A progress callback to log progress during pre-publish.  Call:
                        
                            progress_cb(percentage, msg)
                             
                        to report progress to the UI
                        
        :returns:       A list of any tasks that were found which have problems that
                        need to be reported in the UI.  Each item in the list should
                        be a dictionary containing the following keys:
                        {
                            task:   Dictionary
                                    This is the task that was passed into the hook and
                                    should not be modified
                                    {
                                        item:...
                                        output:...
                                    }
                                    
                            errors: List
                                    A list of error messages (strings) to report    
                        }
        """       
        results = []      
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []
        
            # report progress:
            progress_cb(0, "Validating", task)
        
            if output["name"] == "alembic_cache":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "bounding_box":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "gpu_cache":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "assembly_definition":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "shader_export":
                errors.extend(self._validate_item_for_publish(item))               
            elif output["name"] == "shd_yaml":
                errors.extend(self._validate_item_for_publish(item))    
            elif output["name"] == "dg_texture":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "copyHiRes":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "coreArchive":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "uvxml":
                errors.extend(self._validate_item_for_publish(item))
            elif output["name"] == "GoZ_ma":
                errors.extend(self._validate_goZ_ma_item_for_publish(item))
            elif output["name"] == "GoZ_ztn":
                errors.extend(self._validate_goZ_ztl_item_for_publish(item))
            elif output["name"] == "zbrush_ztl":
                ## passing here cause we just want to scan the zbrush folder in the model context
                ## for outputs for the operator to select so  nothing to fail on here.
                pass
            else:
                # don't know how to publish this output types!
                errors.append("We're good but we just don't know how to publish this item! \nWhat the heck is {} anyway?".format(output["name"])   )

            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                results.append({"task":task, "errors":errors})

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

        ## Now check the group ends in hrc
        if not item["name"].endswith(configCONST.GROUP_SUFFIX):
            errors.append("{} does not end in correct _hrc suffix!".format(item["name"]))

        # finally return any errors
        return errors

    def _validate_goZ_ma_item_for_publish(self, item):
        goZFolder = configCONST.GOZ_PUBLIC_CACHEPATH
        getFolderContents = os.listdir(goZFolder)
        errors = []
        ## make sure the cache file exists in the default goZ folder !
        if '{}.ma'.format(item["name"]) not in getFolderContents:
            errors.append('Can not find a goZ ma cache file in {}'.format(goZFolder))
        return errors

    def _validate_goZ_ztl_item_for_publish(self, item):
        goZFolder = configCONST.GOZ_PUBLIC_CACHEPATH
        getFolderContents = os.listdir(goZFolder)
        errors = []
        ## make sure the cache file exists in the default goZ folder !
        if '{}.ztn'.format(item["name"]) not in getFolderContents:
            errors.append('Can not find a goZ ztn cache file in {}'.format(goZFolder))
        return errors