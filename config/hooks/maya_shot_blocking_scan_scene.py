# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os, sys, tank
import maya.cmds as cmds
import maya.mel as mel
from tank import Hook
from tank import TankError
## Custom stuff
if 'T:/software/bubblebathbay_sandbox/custom' not in sys.path:
    sys.path.append('T:/software/bubblebathbay_sandbox/custom')
import maya_asset_MASTERCLEANUPCODE as cleanup
reload(cleanup)

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
      
        ## Make sure all definitions are at FULL RES for alembic exporting.
        for each in cmds.ls(transforms = True):
            myType = ''
            if cmds.nodeType(each) == 'assemblyReference':         
                ## FIRST Check to see what the active state is of the assembly reference node
                ## If it is still on GPU add this for gpu rendering
                ## Else look for what type of building it is for the alembic caching
                
                ## GPU CACHES
                if cmds.assembly(each, query = True, active = True) == 'gpuCache':
                    items.append({"type":"gpu_caches", "name":each})
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
                            if myType == 'animBLD':
                                ## Now put the Assembly References into items, remember the type is set to match the shot_step.yml secondary output type!
                                items.append({"type":"anim_caches", "name":each})
                            ## STATIC BLD -- Now get the static buildings
                            elif myType == 'staticBLD':
                                 ## Now put the Assembly References into items, remember the type is set to match the shot_step.yml secondary output type!
                                items.append({"type":"static_caches", "name":each})
                            elif myType == 'staticLND':
                                 ## Now put the Assembly References into items, remember the type is set to match the shot_step.yml secondary output type!
                                items.append({"type":"static_caches", "name":each})
                            else:
                                pass
                    except:
                        pass
            else:
                try:
                    myType = cmds.getAttr('%s.type' % each)
                    ## FLUIDS -- Now get the fluid containers
#                     if myType == 'oceanWakeFoamTexture' or myType == 'oceanWakeTexture':
#                         items.append({"type":"fx_caches", "name":'%sShape' % each})
                    if myType == 'fx':
                        items.append({"type":"fx_caches", "name":each})
                    ## CAMERA -- Now get the camera
                    elif myType == 'shotCam' or myType == 'shotcam':
                        items.append({"type":"camera", "name":each})
                    ## REFERENCES -- Now process the references to get their types
                    elif myType == 'animCHAR' or myType == 'char':
                        items.append({"type":"anim_caches", "name":each})
                    elif myType == 'animPROP':
                        items.append({"type":"anim_caches", "name":each})
                    elif myType == 'staticPROP':
                        items.append({"type":"static_caches", "name":each})
                    elif myType == 'staticCHAR':
                        items.append({"type":"static_caches", "name":each})
                    else:
                        pass
                except:
                    pass

        ## NPARTICLES
        for eachNpart in cmds.ls(type = 'nParticle'):
            ## Now put the fx nodes to be cached into items, remember the type is set to match the shot_step.yml secondary output type!
            items.append({"type":"nparticle_caches", "name":eachNpart})
        
        ## Now turn off all the modelEditors to speed up exporting
        ## cleanup.turnOffModelEditors()

        ## Check if the ocean exists..if it does do some work...
        if cmds.objExists('OCEAN_hrc'):
            ## Hide the preview planes
            cmds.setAttr('oceanPreviewPlane_prv.visibility', 0)
            cmds.setAttr('animPreviewPlane_prv.visibility', 0)       
            ## Now make sure the wakes are calculating
            #cmds.setAttr('OCEAN_hrc.oceanCalcOnOff', 0)
            ## Now set the ocean preview plane res to something very low and fast to calc
            cmds.setAttr('OCEAN_hrc.oceanRes', 1)
        else:
            raise TankError("MAYA OCEAN IS MISSING FROM YOUR SHOT!!! YOU SHOULD FIX THIS BEFORE PUBLISHING TO LIGHTING!!!!!!")
            cleanup.turnOnModelEditors()

        ## Cleanup panels so nParticles don't keep crashing on export.
#         for each in cmds.lsUI(panels = True):
#             if 'outlinerPanel' in each or 'nodeEditorPanel' in each:
#                 cmds.deleteUI(each, panel = True)
        
        cleanup.cleanupUnknown()
        ## NOW MOVE ON TO PUBLISHING STEPS
        return items