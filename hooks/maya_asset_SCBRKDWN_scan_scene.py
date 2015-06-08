# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that scans the scene for referenced maya files. Used by the breakdown to 
establish a list of things in the scene.

This implementation supports the following types of references:

* maya references
* texture file input nodes

"""

import os
import maya_adef_lib as adef_lib
from tank import Hook
from tank import TankError
from logger import log
import configCONST as configCONST
import datetime


class ScanScene(Hook):
    
    def execute(self, **kwargs):
        # scan scene for references.
        # for each reference found, return
        # a dict with keys node, type and path
        import pymel.core as pm
        import maya.cmds as cmds
        ## Make sure the scene assembly plugins are loaded
        adef_lib.loadSceneAssemblyPlugins(TankError)
            
        refs = []
        
        # first let's look at maya references        
        for x in pm.listReferences():
            node_name = x.refNode.longName()
            # get the path and make it platform dependent
            # (maya uses C:/style/paths)
            maya_path = x.path.replace("/", os.path.sep)
            
            refs.append({"node": node_name, "type": "reference", "path": maya_path})

        ## Now look for assembly References
        ref_nodes = cmds.ls(type = 'assemblyReference')
        log(app = None, method = 'ScanScene.execute', message = 'ref_nodes: %s' % ref_nodes, printToLog = False, verbose = configCONST.DEBUGGING)
        for eachRef in ref_nodes:
            # get the path:
            ref_path = cmds.getAttr('%s.definition' % eachRef)
            log(app = None, method = 'ScanScene.execute', message = 'ref_path: %s' % ref_path, printToLog = False, verbose = configCONST.DEBUGGING)

            ## Do a quick check here for RIG in the path. If RIG is in the path then ignore it because the RIG is dominant
            ## Over the Model step. How ever if it is MDL here we want do to a quick scan for creation dates of the latest RIG publish and the latest MDL publish
            ## If the RIG is more recent, use that path instead and send it through to the scene breakdown tool instead.
            if not '%s' % configCONST.RIG_SHORTNAME in ref_path:
                ## check the rig folder exists
                rigDir                      = os.path.dirname(ref_path.replace('%s' % configCONST.MODEL_SHORTNAME, '%s' % configCONST.RIG_SHORTNAME))
                if os.path.isdir(rigDir):
                    getFiles                = os.listdir(rigDir)

                    if getFiles:
                        getLatestRigFile    = max(getFiles)
                        latestgetmt         = os.path.getmtime('%s/%s' % (rigDir, getLatestRigFile))
                        lastRigModified     = datetime.datetime.fromtimestamp(latestgetmt)
                        log(app = None, method = 'ScanScene.execute', message = 'lastRigModified: %s' % lastRigModified, printToLog = False, verbose = configCONST.DEBUGGING)

                        latestmodelgetmt    = os.path.getmtime(ref_path)
                        reflastmodified     = datetime.datetime.fromtimestamp(latestmodelgetmt)
                        log(app = None, method = 'ScanScene.execute', message = 'reflastmodified: %s' % reflastmodified, printToLog = False, verbose = configCONST.DEBUGGING)

                        ## Now if the rig is more recent than the model file...
                        if lastRigModified > reflastmodified:
                            cmds.warning('%s HAS A MORE RECENT RIG PUBLISH! PLEASE UPDATE TO THE RIG PATH IMMEDIATELY!' % eachRef)

                            ## Now make an out of date group
                            outDatedGroup   = 'UPDATE_TO_RIG_ADEF_NOW_%s' % configCONST.GROUP_SUFFIX
                            if not cmds.objExists(outDatedGroup):
                                cmds.group(n = outDatedGroup, em = True)

                            ## Parent it to the group
                            try:
                                cmds.parent(eachRef, outDatedGroup)
                            except RuntimeError:
                                pass

                            ##Now rename it as old
                            try:
                                cmds.rename(eachRef, '%s_UPDATEMENOW' % eachRef)
                            except RuntimeError:
                                pass

                            ## Now null out the ref path so this asset doesn't show up in the scenebreakdown
                            ## TODO see if this can be added as a red item to the scene breakdown list???
                            ref_path = ''

            # make it platform dependent
            # (maya uses C:/style/paths)
            maya_path = ref_path.replace("/", os.path.sep)
            refs.append({"node": eachRef, "type": "assemblyReference", "path": maya_path})

        # now look at file texture nodes
        for file_node in cmds.ls(l=True, type="file"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(file_node, isNodeReferenced = True):
                # this is embedded in another reference, so don't include it in the
                # breakdown
                continue

            # get path and make it platform dependent
            # (maya uses C:/style/paths)
            path = cmds.getAttr("%s.fileTextureName" % file_node).replace("/", os.path.sep)
            
            refs.append({"node": file_node, "type": "file", "path": path})
        return refs