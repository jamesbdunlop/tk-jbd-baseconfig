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
from tank import Hook
from tank import TankError
reload(configCONST)## leave this alone if you want to update the config using the maya shotgun reload menu
reload(asset_lib)

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
        items       = []
        # get the main scene:
        scene_name  = cmds.file(query=True, sn= True)
        if not scene_name:
            raise TankError("Please Save your file before Publishing")
        scene_path  = os.path.abspath(scene_name)
        name        = os.path.basename(scene_path)
        # create the primary item - this will match the primary output 'scene_item_type':            
        items.append({"type": "work_file", "name": name})

        ### CLEANUP ################################################################################
        ### NOW DO SCENE CRITICAL CHECKS LIKE DUPLICATE OBJECT NAMES ETC AND FAIL HARD IF THESE FAIL!
        ############################################################################################
        #############################
        ## INITIAL HARD FAILS
        ## Do a quick check for geo_hrc and rig_hrc
        ## geo_hrc
        if not cmds.objExists('%s_%s' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX)):
            raise TankError("Please Group all your geo under a %s_%s group UNDER the root _%s node." % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX, configCONST.GROUP_SUFFIX))
        ## rig_hrc
        ## UNCOMMENT FOR MDL STEP
        if asset_lib.rigGroupCheck():
            raise TankError('Rig group found!! Please use the RIG menus to publish rigs...')
        ## UNCOMMENT FOR RIG STEP
        #  if not asset_lib.rigGroupCheck():
        #      raise TankError('No rig group found!! Please make sure your animation controls are under rig_%s.' % configCONST.GROUP_PREFIX)
        ## Now check it's the right KIND of asset eg CHAR or PROP                
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.BUILDING_SUFFIX, customTag = 'static%s' % configCONST.BUILDING_SUFFIX)
        
        #############################
        ## SECONDARIES FOR PUBLISHING
        ## WE NEED TO FIND THE MAIN GROUP THAT HAS MESHES IN IT NOW AND PUSH THIS INTO THE ITEMS LIST FOR SECONDARY PUBLISHING
        ## Look for root level groups that have meshes as children:
        for grp in cmds.ls(assemblies=True, long= True):
            if cmds.ls(grp, dag=True, type="mesh"):
            # include this group as a 'mesh_group' type
        ### UNCOMMENT FOR PROP CHAR LND ASSETS
        #          items.append({"type":"mesh_group", "name":grp})
        ### UNCOMMENT FOR BLD MLD STEP IF YOU ARE NOT USING A LAYOUT STEP TO POSITION YOUR BUILDINGS INTO AN ENVIRONMENT
                if configCONST.FORCE_TRANSFORM_CHECK:
                    if asset_lib.BLDTransformCheck(grp): ## Check for BLD step only to make sure the transforms are not frozen on the BLD grps
                            items.append({"type": "mesh_group", "name": grp})
                else:
                    items.append({"type": "mesh_group", "name": grp})
        
        #############################
        ## HARD FAILS
        ## Duplicate name check
        if not asset_lib.duplicateNameCheck():
            raise TankError("Duplicate names found please fix before publishing.\nCheck the outliner for the duplicate name set.")
        ## Incorrect Suffix check
        checkSceneGeo = asset_lib._geoSuffixCheck(items)
        if not checkSceneGeo:
            raise TankError("Incorrect Suffixes found! Fix suffixes before publishing.\nCheck the outliner for the duplicate name set.")
        ## Incorrect root name
        if not asset_lib.checkRoot_hrc_Naming(items):
            raise TankError("YOUR ASSET IS NAMED INCORRECTLY! Remember it is CASE SENSITIVE!")
        #############################
        ## NOW PREP THE GEO FOR EXPORT!!!
        ## THESE CLEANUPS SHOULD NOT FAIL THEY SHOULD JUST BE PERFORMED
        ## UNCOMMENT FOR MDL STEP
        ## PERFORM MDL CLEANUP
        asset_lib.cleanUp(items = items, checkShapes = True, history = True, pivots = True, freezeXFRM = True, smoothLvl = True, tagSmoothed = True, checkVerts = True,
                        renderflags = True, deleteIntermediate = True, turnOffOpposite = True, instanceCheck = True, shaders = True)
        ## UNCOMMENT FOR RIG STEP
        ## PERFORM RIG CLEANUP
        # asset_lib.cleanUp(items = items, checkShapes = False, history = False, pivots = False, freezeXFRM = False, smoothLvl = True, tagSmoothed = True, checkVerts = False,
        #                 renderflags = True, deleteIntermediate = False, turnOffOpposite = True, instanceCheck = False, shaders = True)

        ##Now set the auxNodes to something that won't clash during a shot build!!
        bad = ['hyperLayout', 'hyperGraphInfo', 'hyperView']
        for each in bad:
            print "CHECKING FOR ASSEMBLY DEFINITION HYPERLAYOUTS NOW"
            for eachNaughty in cmds.ls(type = each):
                try:
                    getAdef = cmds.listConnections(eachNaughty)
                    if getAdef:
                        if '_ADEF' in getAdef[0]:
                            print 'Renamed %s to %s' % (eachNaughty, '%s_%s' % (getAdef[0], each))
                            cmds.rename(eachNaughty, '%s_%s' % (getAdef[0], each))
                except TypeError:
                    pass
        #############################################################################
        ## NOW MOVE ON TO PUBLISHING
        return items