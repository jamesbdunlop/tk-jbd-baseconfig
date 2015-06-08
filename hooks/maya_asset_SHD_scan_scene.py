# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
import os, time
import maya.cmds as cmds
from tank import Hook
from tank import TankError
import configCONST as configCONST
import maya_asset_lib as asset_lib
import maya_shd_lib as shd_lib

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

        ## Do a quick check for geo_hrc
        if not cmds.objExists('%s_%s' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX)):
            raise TankError("Please Group all your geo under a %s_%s group UNDER the root _%s node." % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX, configCONST.GROUP_SUFFIX))
        ## rig_hrc
        ## UNCOMMENT FOR MDL STEP
        if asset_lib.rigGroupCheck():
            raise TankError('Rig group found!! Please use the RIG menus to publish rigs...')
        # look for root level groups that have meshes as children:
        for grp in cmds.ls(assemblies=True, long= True):
            if cmds.ls(grp, dag=True, type="mesh"):
                # include this group as a 'mesh_group' type
                if '_importDELME' in grp:
                    raise TankError('Import group found!! Please remove this group and parent your assets root group to world accordingly...')
                elif '_%s' % configCONST.GROUP_SUFFIX in grp:
                    items.append({"type": "mesh_group", "name": grp})
                else:
                    pass
        ## DO MAIN CHECKING NOW
        #############################
        ## HARD FAILS
        ## Duplicate name check
        if not asset_lib.duplicateNameCheck():
            raise TankError("Duplicate names found please fix before publishing.\nCheck the outliner for the duplicate name set.")
        ## Incorrect Suffix check
        checkSceneGeo = asset_lib._geoSuffixCheck(items)
        if not checkSceneGeo:
            raise TankError("Incorrect Suffixes found! Fix suffixes before publishing.\nCheck the outliner for the duplicate name set.")
        #############################
        if shd_lib.sceneCheck():## note this returns TRUE if there ARE errors
            raise TankError("You have errors in your scene, please fix.. check the script editor for details.")

        asset_lib.cleanUp(items = items, checkShapes = True, history = False, pivots = False, freezeXFRM = False, smoothLvl = False, tagSmoothed = False, checkVerts = False, 
        renderflags = False, deleteIntermediate = False, turnOffOpposite = False, instanceCheck = False, shaders = False, removeNS = False, defaultRG = False, lightingCleanup = True)

        ## Now do the smartConn
        start = time.time()
        shd_lib.smartConn()
        print 'Total time to %s: %s' % ('shd_lib.smartConn()', time.time()-start)
        
        ## Fix remap and ramps color entry plugs and any incorrect ordering
        ## Leads to bad plugs being inserted when the XML recreates all the values. Querying also creates which makes black colour entry plugs.
        start = time.time()
        shd_lib.fixRamps(cmds.ls(type = 'remapValue'))
        shd_lib.fixRamps(cmds.ls(type = 'ramp'))
        print 'Total time to %s: %s' % ('shd_lib.fixRamps()', time.time()-start)

        ## Removed duplicate dgSHD nodes...
        shd_lib.deleteDGSHD()

        ## Delete empty UV Sets
        start = time.time()
        asset_lib.deleteEmptyUVSets()
        print 'Total time to %s: %s' % ('asset_lib.deleteEmptyUVSets()', time.time() - start)
        ## NOW MOVE ON TO PUBLISHING
        return items    