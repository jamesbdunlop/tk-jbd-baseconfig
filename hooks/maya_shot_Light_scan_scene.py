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
import config_constants as configCONST
from tank import Hook
from tank import TankError

class ScanSceneHook(Hook):
    def execute(self, **kwargs):
        items = []
        
        # get the main scene:
        scene_name = cmds.file(query=True, sn=True)
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
        for grp in cmds.ls(assemblies=True, long=True):
            if 'BAKE_CAM_{}'.format(configCONST.GROUP_SUFFIX) in grp:
                ## Finds the shotCam group
                items.append({"type": "cam_grp", "name": grp.split('|')[-1]})
                ## returns the grp
            if '{}_{}'.format((configCONST.ANIM_CACHE.upper(), configCONST.GROUP_SUFFIX)) in grp:
                for eachChild in cmds.listRelatives(grp, children=True):
                     if cmds.ls(eachChild, dag=True, type="mesh"):
                         items.append({"type": "mesh_grp", "name" :eachChild})
                 ## returns each child in the grp                
            if '{}_{}'.format((configCONST.STATIC_CACHE.upper(), configCONST.GROUP_SUFFIX)) in grp:
                for eachChild in cmds.listRelatives(grp, children=True):
                     if cmds.ls(eachChild, dag=True, type="mesh"):
                         items.append({"type": "mesh_grp", "name": eachChild})
                 ## returns each child in the grp
            if '{}_{}'.format((configCONST.FX_CACHE.upper(), configCONST.GROUP_SUFFIX)) in grp:
                items.append({"type": "fx_grp", "name": grp.split('|')[-1]})
                ## returns the grp
        
        # Finding the Cameras in the scene and Making sure that 'shotCam_bake' is renderable.
        for eachCam in cmds.ls(type='camera'):
            if '{}_bake'.format(configCONST.SHOTCAM_SUFFIX) in eachCam:
                cmds.setAttr('{}.renderable'.format(eachCam,1))
            else:
                cmds.setAttr('{}.renderable'.format(eachCam,0))
        
        #Making Sure the it make layers for each layers
        cmds.setAttr('defaultRenderGlobals.imageFilePrefix','<RenderLayer>/<Scene>',type='string') 
        
        ## Now force an item for render submissions to always show up in the secondaries
        items.append({"type": "xml_grp", "name": 'renderglobals_xml'})
        items.append({"type": "light_grp", "name": 'light_xml'})
        
        ## NOW MOVE ON TO PUBLISHING STEPS
        return items