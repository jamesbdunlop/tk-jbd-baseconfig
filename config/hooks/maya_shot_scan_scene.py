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
import maya_asset_lib as asset_lib
import configCONST as configCONST
reload(configCONST)## leave this alone if you want to update the config using the maya shotgun reload menu
from tank import Hook
from tank import TankError


class ScanSceneHook(Hook):
    """
    Hook to scan scene for items to publish
    """
    
    def execute(self, **kwargs):
        """
        Main hook entry point
        :returns:       A list of any items that were found to be published.  
                        Each item in the list should be a dictionary containing 
                        the following keys:
                        {
                            type:   String
                                    This should match a scene_item_type defined in
                                    one of the outputs in the configuration and is 
                                    used to determine the outputs that should be 
                                    published for the item
                                    
                            name:   String
                                    Name to use for the item in the UI
                            
                            description:    String
                                            Description of the item to use in the UI
                                            
                            selected:       Bool
                                            Initial selected state of item in the UI.  
                                            Items are selected by default.
                                            
                            required:       Bool
                                            Required state of item in the UI.  If True then
                                            item will not be deselectable.  Items are not
                                            required by default.
                                            
                            other_params:   Dictionary
                                            Optional dictionary that will be passed to the
                                            pre-publish and publish hooks
                        }
        """   
                
        items = []
        
        # get the main scene:
        scene_name = cmds.file(query=True, sn= True)
        if not scene_name:
            raise TankError("Please Save your file before Publishing")
      
        scene_path = os.path.abspath(scene_name)
        name = os.path.basename(scene_path)

        # create the primary item - this will match the primary output 'scene_item_type':            
        items.append({"type": "work_file", "name": name})

        ## ANIM CURVES
        items.append({"type":"anim_atom", "name":"Animation Curves"})

        
        ## Make sure all definitions necessary are at FULL RES for alembic exporting!
        for each in cmds.ls(transforms = True):
            myType = ''
            if cmds.nodeType(each) == 'assemblyReference':         
                ## FIRST Check to see what the active state is of the assembly reference node
                ## If it is still on GPU add this for gpu rendering
                ## Else look for what type of building it is for the alembic caching

                ## GPU CACHES
                if cmds.assembly(each, query = True, active = True) == 'gpuCache':
                    if configCONST.ANIM_SHORTNAME in scene_name.split('/'):
                        cmds.assembly(each, edit = True, active = 'full')
                        items.append({"type":"static_caches", "name":each})
                else:
                    ## FULL GEO RIGGED OR STATIC
                    ## Check what type is its. Static or Animated
                    try:
                        for eachChild in cmds.listRelatives(each, children = True):
                            try:
                                myType = cmds.getAttr('%s.type' % eachChild)
                            except ValueError:
                                print '%s is not set to a valid assemblyReference type to query for export...' % eachChild
                                pass
                            ## RIGGED BLD -- Now get the rigged buildings
                            if myType == 'anim%s' % configCONST.BUILDING_SUFFIX:
                                ## Now put the Assembly References into items, remember the type is set to match the shot_step.yml secondary output type!
                                items.append({"type":"anim_caches", "name":each})

                            ## STATIC BLD -- Now get the static buildings
                            elif myType == 'static%s' % configCONST.BUILDING_SUFFIX:
                                 ## Now put the Assembly References into items, remember the type is set to match the shot_step.yml secondary output type!
                                items.append({"type":"static_caches", "name":each})

                            elif myType == 'static%s' % configCONST.LND_SUFFIX:
                                 ## Now put the Assembly References into items, remember the type is set to match the shot_step.yml secondary output type!
                                items.append({"type":"static_caches", "name":each})

                            else:
                                pass
                    except:
                        pass
            else:
                try:
                    myType = cmds.getAttr('%s.type' % each)
                    if myType == 'fx':
                        items.append({"type":"fx_caches", "name":each})
                    ## CAMERA -- Now get the camera
                    elif myType == 'shotCam' or myType == 'shotcam':
                        items.append({"type":"camera", "name":each})
                    ## REFERENCES -- Now process the references to get their types
                    ## Anim Char and Prop
                    elif myType == 'anim%s' % configCONST.CHAR_SUFFIX or myType == configCONST.CHAR_SUFFIX:
                        items.append({"type":"anim_caches", "name":each})
                    elif myType == 'anim%s' % configCONST.PROP_SUFFIX:
                        items.append({"type":"anim_caches", "name":each})
                    ## Static Char and Prop
                    elif myType == 'static%s' % configCONST.PROP_SUFFIX:
                        items.append({"type":"static_caches", "name":each})
                    elif myType == 'static%s' % configCONST.CHAR_SUFFIX:
                        items.append({"type":"static_caches", "name":each})
                    else:
                        pass
                except:
                    pass


        ## NOW ADD THE TAGS FOR CREASES TO BE EXPORTED CORRECTLY
        ## NEED TO DO THIS LONG WAY IN CASE THE ATTR ALREADY EXISTS AND FAILS>.
        for each in cmds.ls(type = 'mesh', l = True):
            if not cmds.objExists('%s.SubDivisionMesh' % each):
                try:
                    cmds.addAttr('%s' % each, ln = 'SubDivisionMesh', at = 'bool')
                    cmds.setAttr("%s.SubDivisionMesh" % each, 1)
                except:
                    pass

        ## remove unknown nodes from scene
        asset_lib.cleanupUnknown()

        ## NOW MOVE ON TO PUBLISHING STEPS
        return items