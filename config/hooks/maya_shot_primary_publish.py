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
import uuid
import tempfile
import tank
from tank import Hook
from tank import TankError
import maya_asset_lib as asset_lib

class PrimaryPublishHook(Hook):
    """
    Single hook that implements publish of the primary task
    """    
    def execute(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb, **kwargs):
        """
        Main hook entry point
        :task:          Primary task to be published.  This is a
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
               
        :comment:       String
                        The comment provided for the publish
                        
        :thumbnail:     Path string
                        The default thumbnail provided for the publish
                        
        :sg_task:       Dictionary (shotgun entity description)
                        The shotgun task to use for the publish    
                        
        :progress_cb:   Function
                        A progress callback to log progress during pre-publish.  Call:
                        
                            progress_cb(percentage, msg)
                             
                        to report progress to the UI
        
        :returns:       Path String
                        Hook should return the path of the primary publish so that it
                        can be passed as a dependency to all secondary publishes
        
                        Hook should raise a TankError if publish of the 
                        primary task fails
        """
        # get the engine name from the parent object (app/engine/etc.)
        engine_name = self.parent.engine.name
       
        # depending on engine:
        if engine_name == "tk-maya":
            return self._do_maya_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        else:
            raise TankError("Unable to perform publish for unhandled engine %s \n Check with your TD that the config is loading the right primary publish hook." % engine_name)
       
    def _do_maya_publish(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb):
        """
        Publish the main Maya scene
        """
        import maya.cmds as cmds

        ## Turn off the model editors for the new bake
        asset_lib.turnOffModelEditors()

        progress_cb(0.0, "Finding scene dependencies", task)
        dependencies = self._maya_find_additional_scene_dependencies()
        ## Get scene path
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        ## Test if it's a valid scene path
        if not work_template.validate(scene_path):
            raise TankError("File '%s' is not a valid work path, unable to publish!" % scene_path)
        
        ## Use templates to convert to publish path:
        output = task["output"]
        fields = work_template.get_fields(scene_path)
        fields["TankType"] = output["tank_type"]
        
        ## Now update the name to be the actual assetName from shotgun and remove the _ for saving
        fields['name'] = fields['Shot'].replace('_', '')
               
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        
        if os.path.exists(publish_path):
           ## If it already exists version up one. 
           ## We should never fail a publish just because a published asset already exists
           cmds.warning('Found existing publish_path: %s' % publish_path)
           cmds.warning('Adjusting publish_path now...')
           path     = '\\'.join(publish_path.split('\\')[0:-1])
           getfiles = os.listdir(path)
           if 'Keyboard' in getfiles:
               getfiles.remove('Keyboard')
           
           ## legacy check remove any ma files from the list as we're now publishing only to mb!
           for each in getfiles:
               if not each.endswith('mb'):
                   getfiles.remove(each)
           
           ## Now process the rest of the list..
           ## Get the max of the list
           highestVersFile = max(getfiles).split('.')[1].split('v')[-1]
           ## Update the fields with a new version number
           fields["version"]  = int(highestVersFile) + 1
           ## Apply the fields to the templates paths..
           publish_path = publish_template.apply_fields(fields)
           ## Output the new publish path to the scripteditor
           cmds.warning('NewPublishPath: %s' % publish_path)
        
        ## PROCESS FOR SAVE
        progress_cb(10.0, "Saving the current working scene")
        self.parent.log_debug("Saving the current working scene...")
        publish_name = self._get_publish_name(publish_path, publish_template, fields)
        if fields['version'] < 10:
            padding = '00'
        elif fields['version'] < 100:
            padding = '0'
        else:
            padding = ''
        
        ## Save the current working file just in case
        cmds.file(save=True, force= True)
        
        ## Now rename and save the working file with the new version number for the publish
        ## Change the file type to mb for publish
        progress_cb(50.0, "Publishing the file to publish area")
        try:
            ## Now rename the file to the correct name and version number...
            cmds.file(rename = '%s.v%s%s.mb' % (publish_name, padding, fields['version']))

            ## Now save the file
            cmds.file(save=True, force = True, type = 'mayaBinary')       
            
            ## Now put the published file into the publish folder
            publish_folder = os.path.dirname(publish_path)
            ## Make sure the folder exists
            self.parent.ensure_folder_exists(publish_folder)
            
            ## Find current scene path and rename the saved file using os.rename to move it into the publish folder
            getCurrentScenePath = os.path.abspath(cmds.file(query=True, sn= True))
            os.rename(getCurrentScenePath, publish_path)
            
            self.parent.log_debug("Publishing %s --> %s..." % (getCurrentScenePath, publish_path))
            progress_cb(65.0, "Moved the publish")
        except Exception, e:
            raise TankError("Failed to working file to publish folder.... please contact a TD about this: " %  e)
        
        progress_cb(100)
        
        ## Now put it back to Ascii
        cmds.file(rename = '%s.v%s%s.ma' % (publish_name, padding, fields['version']))
        cmds.file(save=True, force=True, type = 'mayaAscii')
        
        # finally, register the publish:
        progress_cb(75.0, "Registering the publish")
        
        publish_name = '%s_ANIM' % publish_name
            
        self._register_publish(publish_path, 
                               publish_name, 
                               sg_task, 
                               fields["version"], 
                               output["tank_type"],
                               comment,
                               thumbnail_path, 
                               dependencies)
        
        return publish_path
        
    def _maya_find_additional_scene_dependencies(self):
        """
        Find additional dependencies from the scene
        """
        import maya.cmds as cmds

        # default implementation looks for references and 
        # textures (file nodes) and returns any paths that
        # match a template defined in the configuration
        ref_paths = set()
        
        # first let's look at maya references
           
        ref_nodes = cmds.ls(references= True)
        for ref_node in ref_nodes:
            print 'Checking ref node %s' % ref_node
            try:
                ref_path = cmds.referenceQuery(ref_node, filename= True)
                # make it platform dependent
                # (maya uses C:/style/paths)
                ref_path = ref_path.replace("/", os.path.sep)
                if ref_path:
                    ref_paths.add(ref_path)
            except RuntimeError:
                cmds.warning('This file is broken removing: %s' % ref_node)
                cmds.lockNode(ref_node, lock = False)
                cmds.delete(ref_node)
            
        # now look at file texture nodes    
        for file_node in cmds.ls(l=True, type="file"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(file_node, isNodeReferenced= True):
                # this is embedded in another reference, so don't include it in the
                # breakdown
                continue

            # get path and make it platform dependent
            # (maya uses C:/style/paths)
            texture_path = cmds.getAttr("%s.fileTextureName" % file_node).replace("/", os.path.sep)
            if texture_path:
                ref_paths.add(texture_path)
            
        # now, for each reference found, build a list of the ones
        # that resolve against a template:
        dependency_paths = []
        for ref_path in ref_paths:
            # see if there is a template that is valid for this path:
            for template in self.parent.tank.templates.values():
                if template.validate(ref_path):
                    dependency_paths.append(ref_path)
                    break

        return dependency_paths

    def _get_publish_name(self, path, template, fields=None):
        """
        Return the 'name' to be used for the file - if possible
        this will return a 'versionless' name
        """
        # first, extract the fields from the path using the template:
        fields = fields.copy() if fields else template.get_fields(path)
        if "name" in fields and fields["name"]:
            # well, that was easy!
            name = fields["name"]
        else:
            # find out if version is used in the file name:
            template_name, _ = os.path.splitext(os.path.basename(template.definition))
            version_in_name = "{version}" in template_name
        
            # extract the file name from the path:
            name, _ = os.path.splitext(os.path.basename(path))
            delims_str = "_-. "
            if version_in_name:
                # looks like version is part of the file name so we        
                # need to isolate it so that we can remove it safely.  
                # First, find a dummy version whose string representation
                # doesn't exist in the name string
                version_key = template.keys["version"]
                dummy_version = 9876
                while True:
                    test_str = version_key.str_from_value(dummy_version)
                    if test_str not in name:
                        break
                    dummy_version += 1
                
                # now use this dummy version and rebuild the path
                fields["version"] = dummy_version
                path = template.apply_fields(fields)
                name, _ = os.path.splitext(os.path.basename(path))
                
                # we can now locate the version in the name and remove it
                dummy_version_str = version_key.str_from_value(dummy_version)
                
                v_pos = name.find(dummy_version_str)
                # remove any preceeding 'v'
                pre_v_str = name[:v_pos].rstrip("v")
                post_v_str = name[v_pos + len(dummy_version_str):]
                
                if (pre_v_str and post_v_str 
                    and pre_v_str[-1] in delims_str 
                    and post_v_str[0] in delims_str):
                    # only want one delimiter - strip the second one:
                    post_v_str = post_v_str.lstrip(delims_str)

                versionless_name = pre_v_str + post_v_str
                versionless_name = versionless_name.strip(delims_str)
                
                if versionless_name:
                    # great - lets use this!
                    name = versionless_name
                else: 
                    # likely that version is only thing in the name so 
                    # instead, replace the dummy version with #'s:
                    zero_version_str = version_key.str_from_value(0)        
                    new_version_str = "#" * len(zero_version_str)
                    name = name.replace(dummy_version_str, new_version_str)
        
        return name  

    def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths):
        """
        Helper method to register publish using the 
        specified publish info.
        """
        # construct args:
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": path,
            "name": name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": dependency_paths,
            "published_file_type":tank_type,
        }
        
        self.parent.log_debug("Register publish in shotgun: %s" % str(args))
        
        # register publish;
        sg_data = tank.util.register_publish(**args)
        
        return sg_data
