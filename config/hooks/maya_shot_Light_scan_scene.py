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

        ## Turn off feature displacements for all meshes just incase artists forgot to!
        allMeshNodes = cmds.ls(type='mesh', l=True)
        for each in allMeshNodes:
            cmds.setAttr(each+".featureDisplacement", 0)
            
        # create the primary item - this will match the primary output 'scene_item_type':            
        items.append({"type": "work_file", "name": name})
      
        ## Make sure all definitions are at FULL RES for alembic exporting.
        for grp in cmds.ls(assemblies = True, long = True):
            if 'BAKE_CAM_%s' % configCONST.GROUP_SUFFIX in grp:
                ## Finds the shotCam group
                items.append({"type": "cam_grp", "name": grp.split('|')[-1]})
                ## returns the grp
            if '%s_%s' % (configCONST.ANIM_CACHE.upper(), configCONST.GROUP_SUFFIX) in grp:
                for eachChild in cmds.listRelatives(grp, children = True):
                     if cmds.ls(eachChild, dag=True, type="mesh"):
                         items.append({"type": "mesh_grp", "name" :eachChild})
                 ## returns each child in the grp                
            if '%s_%s' % (configCONST.STATIC_CACHE.upper(), configCONST.GROUP_SUFFIX) in grp:
                for eachChild in cmds.listRelatives(grp, children = True):
                     if cmds.ls(eachChild, dag=True, type="mesh"):
                         items.append({"type": "mesh_grp", "name": eachChild})
                 ## returns each child in the grp
            if '%s_%s' % (configCONST.FX_CACHE.upper(), configCONST.GROUP_SUFFIX) in grp:
                items.append({"type": "fx_grp", "name": grp.split('|')[-1]})
                ## returns the grp
        
        # Finding the Cameras in the scene and Making sure that 'shotCam_bake' is renderable.
        for eachCam in cmds.ls(type = 'camera'):
            if '%s_bake' % configCONST.SHOTCAM_SUFFIX in eachCam:
                cmds.setAttr('%s.renderable' % eachCam,1)
            else:
                cmds.setAttr('%s.renderable' % eachCam,0)
        
        #Making Sure the it make layers for each layers
        cmds.setAttr('defaultRenderGlobals.imageFilePrefix','<RenderLayer>/<Scene>',type='string') 
        
        ## Now force an item for render submissions to always show up in the secondaries
        items.append({"type":"renderPreview", "name":'renderPreview'})
        items.append({"type":"renderFinal", "name":'renderFinal'})
        items.append({"type":"xml_grp", "name":'renderglobals_xml'})
        items.append({"type":"light_grp", "name":'light_xml'})
        
        ## NOW MOVE ON TO PUBLISHING STEPS
        return items