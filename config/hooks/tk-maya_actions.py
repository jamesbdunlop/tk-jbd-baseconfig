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
Hook that loads defines all the available actions, broken down by publish type. 
"""
import sgtk, os
import maya.cmds as cmds
import maya.mel as mel
from logger import log
import configCONST as configCONST
import maya_shd_lib as shd_lib
import maya_asset_lib as asset_lib
import maya_adef_lib as adef_lib
import shd_readXML as shd_readxml
from PySide.QtGui import *
from tank import TankError
HookBaseClass = sgtk.get_hook_baseclass()
reload(shd_readxml)

class MayaActions(HookBaseClass):
    
    ##############################################################################################################
    # public interface - to be overridden by deriving classes 
    
    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.
    
        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.
        
        The hook should return at least one action for each item passed in via the 
        actions parameter.
        
        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.
        
        Because you are operating on a particular publish, you may tailor the output 
        (caption, tooltip etc) to contain custom information suitable for this publish.
        
        The ui_area parameter is a string and indicates where the publish is to be shown. 
        - If it will be shown in the main browsing area, "main" is passed. 
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed. 
        
        Please note that it is perfectly possible to create more than one action "instance" for 
        an action! You can for example do scene introspection - if the action passed in 
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than 
        one object is returned for an action, use the params key to pass additional 
        data into the run_action hook.
        
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data))
        
        action_instances = []

        if "open" in actions:
            action_instances.append( {"name": "open", 
                                      "params": None,
                                      "caption": "Open maya scene file", 
                                      "description": "This will open the maya publish file."} )

        if "audio" in actions:
            action_instances.append( {"name": "audio", 
                                      "params": None,
                                      "caption": "Create audioNode...", 
                                      "description": "This will add the item to the scene as an audioNode."} )

        if "assemblyReference" in actions:
            action_instances.append( {"name": "assemblyReference", 
                                      "params": None,
                                      "caption": "Create assemblyReference", 
                                      "description": "This will add the item to the scene as an assembly reference."} )

        if "reference" in actions:
            action_instances.append( {"name": "reference", 
                                      "params": None,
                                      "caption": "Create Reference...", 
                                      "description": "This will add the item to the scene as a standard reference."} )

        if "import" in actions:
            action_instances.append( {"name": "import", 
                                      "params": None,
                                      "caption": "Import into Scene...", 
                                      "description": "This will import the item into the current scene."} )

        if "texture_node" in actions:        
            action_instances.append( {"name": "texture_node",
                                      "params": None, 
                                      "caption": "Create Texture Node...", 
                                      "description": "Creates a file texture node for the selected item.."} )        

        if "importDGSHD" in actions:
            action_instances.append( {"name": "importDGSHD", 
                                      "params": None,
                                      "caption": "Import downgraded shaders...", 
                                      "description": "This will import the published down graded shaders onto the current asset geo.."} )

        if "loadSurfVar" in actions:
            action_instances.append( {"name": "loadSurfVar", 
                                      "params": None,
                                      "caption": "Load published SRFVar XML...", 
                                      "description": "This will load published SRF XML for a surface variation onto geo in lighting scene."} )

        if "loadANIMForFX" in actions:
            action_instances.append( {"name": "loadANIMForFX", 
                                      "params": None,
                                      "caption": "Load published animation scene...", 
                                      "description": "This will load a published animation scene for FX."} )
            
        if "openLayout" in actions:
            action_instances.append( {"name": "openLayout", 
                                      "params": None,
                                      "caption": "Load published layout scene...", 
                                      "description": "This will load a published layout scene for Animation."} )

        if "assetXML" in actions:        
            action_instances.append( {"name": "assetXML",
                                      "params": None, 
                                      "caption": "Load published SHD xml...", 
                                      "description": "Create shaders for lighting asset from published xml.."} )        

        return action_instances
                
    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.
        
        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """
        app = self.parent
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data))
        
        # resolve path
        path = self.get_publish_path(sg_publish_data)

        if name == "assemblyReference":
            self._create_assemblyReference(path, sg_publish_data)

        if name == "reference":
            self._create_reference(path, sg_publish_data)

        if name == "import":
            self._importAssetToMaya(path, sg_publish_data)
        
        if name == "texture_node":
            self._create_texture_node(path, sg_publish_data)
                        
        if name == "audio":
            self._create_audio_node(path, sg_publish_data)

        if name == "open":
            self._openScene(path, sg_publish_data)

        if name == "coreArchive":
            self._add_coreArchive(path, sg_publish_data)

        if name == "importDGSHD":
            self._importDGSHD(path, sg_publish_data)

        if name == "loadSurfVar":
            self._loadSurfVar(path, sg_publish_data)
        
        if name == "loadANIMForFX":
            self._loadANIMScene_ForFX(path, sg_publish_data)
            
        if name == "openLayout":
            self._loadLayoutScene_ForANIM(path, sg_publish_data)

        if name == "assetXML":
            self._fetchAssetXML(path, sg_publish_data)

    def _fetchLIBWORLD(self, path, sg_publish_data):
        print 'STILL GOT SOME STUFF TO ADD IN HERE!!...such as;'
        print 'Waterfall handling into render layers setup'
        print 'BG Hills render layers setup'
        
        ## Do the import
        self._do_import(path, sg_publish_data)
        
        ## Check for the clouds import and setup those correctly
        if 'cloud' in path:
            self.setCloudsToCloudLayer()
        ## Check for the waterfall import and setup those correctly
        elif 'waterfall' in path:
            pass
        elif 'bghills' in path:
            pass
        else:
            pass
        
        ## Now try to clean the duplicate cores that may exist
        #self._cleanFnCores()

    def _fetchAssetXML(self, path, sg_publish_data):
        #print path, sg_publish_data
        ## I:\bubblebathbay\assets\Environment\BBB_JBDDUMMY_LND\SRF\publish\uvxml\BBBJBDDUMMYLND.xml 
        ## {'version.Version.sg_status_list': None, 'task.Task.due_date': None, 'version_number': 53, 'code': 'BBBJBDDUMMYLND.xml', 'description': None, 'task.Task.sg_status_list': 'wtg', 'image': 'https://sg-media-usor-01.s3.amazonaws.com/ea241984334a6d66408726328553b1baecf5f5f9/49d59fec2908edc8a73bfe3eb0fc776de1058770/no_preview_t.jpg?AWSAccessKeyId=AKIAIFHY52V77FIVWKLQ&Expires=1401237658&Signature=lkCn8kdlHILUj16W%2FTqnagQWBQ4%3D', 'published_file_type': {'type': 'PublishedFileType', 'id': 1, 'name': 'Maya Scene'}, 'entity': {'type': 'Asset', 'id': 1768, 'name': 'BBB_JBDDUMMY_LND'}, 'task.Task.content': 'Surface', 'task': {'type': 'Task', 'id': 24841, 'name': 'Surface'}, 'version': None, 'path': {'local_path_windows': 'I:\\bubblebathbay\\assets\\Environment\\BBB_JBDDUMMY_LND\\SRF\\publish\\uvxml\\BBBJBDDUMMYLND.xml', 'name': 'BBBJBDDUMMYLND.xml', 'local_path_linux': None, 'url': 'file://I:\\bubblebathbay\\assets\\Environment\\BBB_JBDDUMMY_LND\\SRF\\publish\\uvxml\\BBBJBDDUMMYLND.xml', 'local_storage': {'type': 'LocalStorage', 'id': 1, 'name': 'primary'}, 'local_path': 'I:\\bubblebathbay\\assets\\Environment\\BBB_JBDDUMMY_LND\\SRF\\publish\\uvxml\\BBBJBDDUMMYLND.xml', 'content_type': None, 'local_path_mac': '/Volumes/bubblebathbay3D/bubblebathbay/assets/Environment/BBB_JBDDUMMY_LND/SRF/publish/uvxml/BBBJBDDUMMYLND.xml', 'type': 'Attachment', 'id': 46475, 'link_type': 'local'}, 'type': 'PublishedFile', 'id': 24964, 'name': 'BBBJBDDUMMYLNDXML'}
        ## Find the assets parent group in the scene now..
        parentGrp = cmds.listRelatives('%s_%s' % (sg_publish_data['entity']["name"], configCONST.GROUP_SUFFIX), p = True) or ''
            
        if 'uvxml' in path:
            cmds.warning('This is not a valid SHD XML try again....')
        else:
            shd_lib.createAll(XMLPath = path, parentGrp = parentGrp, Namespace = '', Root = 'MaterialNodes', selected = False, selectedOrigHrcName = '')
            shd_lib.connectAll(XMLPath = path, parentGrp= parentGrp, Namespace = '', Root = 'MaterialNodes', selected = False, selectedOrigHrcName = '')             

    def _openScene(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
                
        cmds.file(path, o = True, f = True)

    def _create_audio_node(self, path, sg_publish_data):
        """
        Load file into Maya.
        This implementation creates a standard maya audio node.
        """
        # get the slashes right
        path = path.replace(os.path.sep, "/")
        
        (path, ext) = os.path.splitext(path)
        if os.path.isfile(path):      
            if ext in [".ma", ".mb"]:
                # maya file - load it as a reference
                getEntity = sg_publish_data.get('entity')
                namespace = getEntity.get('name')
                print 'Namespace: %s' % namespace
                print 'Path: %s' % path
                
                if not cmds.objExists(namespace):
                    cmds.file('%s.ma' % path, i = True, f = True)
                    ## Clean out any imported namespaces
                    for eachNode in cmds.ls(ap= True):
                        if ':' in eachNode:
                            try:
                                cmds.rename(eachNode, '%s' % eachNode.split(':')[-1])
                            except RuntimeError:
                                pass
                else:
                    cmds.warning('Audio already exists in the scene. Use the scene breakdown to update your audio.')
                
            else:
                self.parent.log_error("Unsupported file extension for %s! Nothing will be loaded." % file_path)
        else:
            cmds.warning('File not found! Please contact a co-ord to fix this for you now.')

    def _create_assemblyReference(self, path, sg_publish_data):
        """
        Create an assembly reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        print 'path: %s' % path
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
        
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody                
        #namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = "%s_ADef_ARef" % sg_publish_data.get("entity").get("name").replace('_', '')

        ## Check for the Assembly References group
        assemblyRefGrp = 'ASSEMBLYREFS_%s' % configCONST.GROUP_SUFFIX
        if not cmds.objExists(assemblyRefGrp):
            cmds.group(n = assemblyRefGrp, em = True)

        ## Make sure the scene assembly plugins are loaded
        adef_lib.loadSceneAssemblyPlugins(TankError)
        
        # maya file - load it as an assembly reference
        assemblyDefPath = 'assemblyDef'.join(path.split('maya'))

        if not cmds.objExists(namespace):
            cmds.container(type = 'assemblyReference', name = namespace)
            cmds.setAttr('%s.definition' % namespace, assemblyDefPath, type = 'string')
        else:
            cmds.warning('Asset %s already exists in scene, try using the sceneBreakdown tool to update instead....' % namespace)     

        ## Now parent to the assembyRefs group
        try:
            cmds.parent(namespace, assemblyRefGrp)
        except RuntimeError:
            pass

    def _create_reference(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        import pymel.core as pm

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
        
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody                
        namespace = "%s" % (sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")
        if '_primaryPublish' in namespace:
            namespace = namespace.replace('_primaryPublish', '')

        pm.system.createReference(path, 
                                  loadReferenceDepth= "all", 
                                  mergeNamespacesOnClash=False, 
                                  namespace=namespace)
    
    def _doSTATIC_import(self, path, sg_publish_data):
        """       
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
                
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody                
        namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")
        
        # perform a more or less standard maya import, putting all nodes brought in into a specific namespace
        cmds.file(path, i=True)
        
        ## Clean any bad build grps just incase the person in cahrge of the static env rebuilt the cores but didn't clean the geo_hrc core groups out..
        ## This helps stop a full scene rebuild from failing if the lighter needs to do this..
        self._removeCoreGrps()
        
        ## Clean general namespaces from the import ignoring the core archive names...
        getAllNameSpaces = cmds.namespaceInfo(listOnlyNamespaces = True)
        for eachNS in getAllNameSpaces:
            if namespace in eachNS and 'CORE' not in eachNS:
                try:
                    cmds.namespace(removeNamespace = eachNS, mergeNamespaceWithRoot = True)
                except RuntimeError:
                    pass
                    

        ## Now try to clean the duplicate cores that may exist
        self._cleanFnCores()
        self._removeCoreGrps()
    
    def _do_import(self, path, sg_publish_data):
        """       
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
                
        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody                
        namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")
        
        # perform a more or less standard maya import, putting all nodes brought in into a specific namespace
        cmds.file(path, i=True, renameAll=True, namespace=namespace, loadReferenceDepth="all", preserveReferences=True)
        self._stripNamespaces(namespace)

    def _create_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a texture

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        x = cmds.shadingNode('file', asTexture=True)
        cmds.setAttr("%s.fileTextureName" % x, path, type="string" )
                    
    def _importAssetToMaya(self, path, sg_publish_data, group = True, env = False):
        """
        Import asset file into Maya
        """
        # get the slashes right
        myConfirmBox = cmds.confirmDialog(title='Import Group:', message='Create an import group?', button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )

        file_path = path.replace(os.path.sep, "/")
        (path, ext) = os.path.splitext(file_path)
        namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")
        if ext in [".ma", ".mb"]:
            assetName = '%s_%s' % (file_path.split('.')[0].split('/')[-1], configCONST.GROUP_SUFFIX)
            if myConfirmBox == 'Yes':
                groupName = '%s_%s' % (assetName, configCONST.IMPORT_SUFFIX)
                ## Now do the import
                cmds.file(file_path, i =True, gr = group, gn = groupName, loadReferenceDepth="all", preserveReferences=True)
            else:
                ## Now do the import
                cmds.file(file_path, i =True, loadReferenceDepth="all", preserveReferences=True)

            self._stripNamespaces(namespace)
        else:
            raise Exception("Unsupported file extension for %s! Nothing will be loaded." % file_path)

    def _importDGSHD(self, path, sg_publish_data):
        """
        Load dg shader xml file
        """
        # get the slashes right
        file_path = path.replace(os.path.sep, "/")

        (path, ext) = os.path.splitext(file_path)

        if ext in [".xml"]:
            if not cmds.objExists('dgSHD'):
                cmds.scriptNode(n ='dgSHD')
            log(None, method = 'add_file_to_maya', message = 'Cleaning shaders...', printToLog = False, verbose = configCONST.DEBUGGING)
            asset_lib.cleanUpShaders()

            log(None, method = 'add_file_to_maya', message = 'Creating shaders...', printToLog = False, verbose = configCONST.DEBUGGING)
            shd_readxml.createAll(XMLPath = file_path, Namespace = '', Root = 'MaterialNodes')

            log(None, method = 'add_file_to_maya', message = 'Connect all shaders...', printToLog = False, verbose = configCONST.DEBUGGING)
            shd_readxml.connectAll(XMLPath = file_path, Namespace = '', Root = 'MaterialNodes')

            log(None, method = 'add_file_to_maya', message = 'Downgrading shaders now...', printToLog = False, verbose = configCONST.DEBUGGING)
            shd_lib.downgradeShaders()

            log(None, method = 'add_file_to_maya', message = 'Downgrade complete!', printToLog = False, verbose = configCONST.DEBUGGING)

            ####TAG geo_hrc with DGSHD XML VERSION NUMBER
            ##################
            versionNumber = file_path.split('.')[-2]
            if not cmds.objExists('%s_%s.version' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX)):
                cmds.addAttr('%s_%s' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX), ln = 'version', dt = 'string')
                cmds.setAttr('%s_%s.version' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX), versionNumber, type = 'string')

    def _loadSurfVar(self, path, sg_publish_data):
        """
        Load file into Maya as an assembly reference
        """
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))

        # get the slashes right
        file_path = path.replace(os.path.sep, "/")

        (path, ext) = os.path.splitext(file_path)
        log(None, method = 'add_surfVarfile_to_maya', message = 'Creating shaders for surface variation...', printToLog = False, verbose = configCONST.DEBUGGING)

        curSel = cmds.ls(sl = True)
        if curSel:
            ## Cleanup shaders on selected
            for each in cmds.ls(sl = True):
                cmds.sets(each, e = True, forceElement = 'initialShadingGroup')
            mel.eval("MLdeleteUnused();")

            ## Now process the xml
            if ext in [".xml"]:
                if 'Light' in scene_path:
                    """
                    Example of shotgun_data:
                    {
                    'version_number': 7,
                    'description': 'Updating for lighting testing',
                    'created_at': datetime.datetime(2014, 3, 3, 12, 46, 31, tzinfo=<tank_vendor.shotgun_api3.lib.sgtimezone.LocalTimezone object at 0x000000002A29BE48>),
                    'published_file_type': {'type': 'PublishedFileType', 'id': 1, 'name': 'Maya Scene'},
                    'created_by': {'type': 'HumanUser', 'id': 42, 'name': 'James Dunlop'},
                    'entity': {'type': 'Asset', 'id': 1427, 'name': 'jbd_dummybld_BLD'},
                    'image': 'https://sg-media-usor-01.s3.amazonaws.com/ea241984334a6d66408726328553b1baecf5f5f9/1dd2116047d57cf945dca0222a43e2ab02a682dc/tanktmpfk17lm_t.jpg?AWSAccessKeyId=AKIAJ2N7QGDWF5H5DGZQ&Expires=1393812258&Signature=Ah5c866A8LJkMQQzaGkjK3E%2F9ag%3D',
                    'path': {'local_path_windows': 'I:\\bubblebathbay\\assets\\Building\\jbd_dummybld_BLD\\SRFVar_01\\publish\\xml\\jbddummybldBLD.v007.xml',
                    'name': 'jbddummybldBLD.v007.xml',
                    'local_path_linux': None,
                    'url': 'file://I:\\bubblebathbay\\assets\\Building\\jbd_dummybld_BLD\\SRFVar_01\\publish\\xml\\jbddummybldBLD.v007.xml',
                    'local_storage': {'type': 'LocalStorage', 'id': 1, 'name': 'primary'},
                    'local_path': 'I:\\bubblebathbay\\assets\\Building\\jbd_dummybld_BLD\\SRFVar_01\\publish\\xml\\jbddummybldBLD.v007.xml',
                    'content_type': None,
                    'local_path_mac': '/Volumes/bubblebathbay3D/bubblebathbay/assets/Building/jbd_dummybld_BLD/SRFVar_01/publish/xml/jbddummybldBLD.v007.xml',
                    'type': 'Attachment', 'id': 6202, 'link_type': 'local'},
                    'type': 'PublishedFile',
                    'id': 4752,
                    'name': 'jbddummyBLDXML_SurfVar01'
                    }
                    """
                    log(None, method = 'add_surfVarfile_to_maya', message = 'Create all shaders for surface variation for lighting step...', printToLog = False, verbose = configCONST.DEBUGGING)

                    for each in curSel:
                        shd_lib.createAll(XMLPath = file_path, Namespace = '', Root = 'MaterialNodes', selected = True, selectedOrigHrcName = each)

                        ## Find the parent group
                        #sg_publish_data.get("entity").get("name")
                        entity      = sg_publish_data.get("entity")
                        assetName   = '%s_%s' % (entity.get("name"), configCONST.GROUP_SUFFIX)
                        getParent   = '|%s' % cmds.listRelatives(assetName, parent  = True)[0]
                        log(None, method = 'add_surfVarfile_to_maya', message = 'getParent: %s' % getParent, printToLog = False, verbose = configCONST.DEBUGGING)

                        shd_lib.connectAll(XMLPath = file_path, parentGrp = getParent, Namespace = '', Root = 'MaterialNodes', selected = True, selectedOrigHrcName = each)
                else:
                    for each in curSel:
                        log(None, method = 'add_surfVarfile_to_maya', message = 'Create all shaders for surface variation outside lighting step...', printToLog = False, verbose = configCONST.DEBUGGING)
                        shd_lib.createAll(XMLPath = file_path, Namespace = '', Root = 'MaterialNodes', selected = True, selectedOrigHrcName = each)

                        log(None, method = 'add_surfVarfile_to_maya', message = 'Connect all shaders for surface variation outside lighting step...', printToLog = False, verbose = configCONST.DEBUGGING)
                        shd_lib.connectAll(XMLPath = file_path, parentGrp = '', Namespace = '', Root = 'MaterialNodes', selected = True, selectedOrigHrcName = each)
            else:
                self.parent.log_error("Unsupported file extension for %s! Nothing will be loaded." % file_path)
        else:
            cmds.warning('You must have a valid selection to assign the surfVar to!!!')

    def _loadANIMScene_ForFX(self, path, sg_publish_data):
        """
        Load file into Maya.

        This implementation opens a maya animation scene for FX and saves this newly opened scene in the right workspace with
        a new version number appropriate to the FX files.
        """
        # get the slashes right
        file_path = path.replace(os.path.sep, "/")
        log(app = None, method = 'add_file_to_maya', message = 'file_path: %s' % file_path, printToLog = False, verbose = configCONST.DEBUGGING)
        #file_path: I:/bubblebathbay/episodes/eptst/eptst_sh2000/Anm/publish/maya/eptstsh2000.v002.mb


        file_version = int(file_path.split('.')[1].split('v')[-1])
        log(app = None, method = 'add_file_to_maya', message = 'file_version: %s' % file_version, printToLog = False, verbose = configCONST.DEBUGGING)

        (path, ext) = os.path.splitext(file_path)

        if ext in [".ma", ".mb"]:
            ## Open the blocking file
            cmds.file(file_path, o = True, f = True)

            ## Cleanup unknown nodes to make sure we can save from mb back to ma
            for each in cmds.ls():
                if cmds.nodeType(each) == 'unknown':
                    cmds.delete(each)

            ## Build the script node for the FX app.py to use as the current version number of the oceanPreset
            if not cmds.objExists('fxNugget'):
                cmds.scriptNode(n ='fxNugget')
                cmds.addAttr('fxNugget', ln = 'animVersion', at = 'long')
                cmds.setAttr('fxNugget.animVersion', file_version)
            ## Save the animation file as the next working file in the FX folder
            tk              = sgtk.sgtk_from_path("T:/software/bubblebathbay")
            getEntity       = sg_publish_data.get("entity")
            shotName        = getEntity.get("name")
            work_template   = tk.templates['shot_work_area_maya']
            pathToWorking   = r'%s' % tk.paths_from_template(work_template, {"Shot" : shotName, "Step":'FX'})[0]
            pathToWorking.replace('\\\\', '\\')
            log(app = None, method = 'add_file_to_maya', message = 'pathToWorking: %s' % pathToWorking, printToLog = False, verbose = configCONST.DEBUGGING)
            ## Scan the folder and find the highest version number
            fileShotName = "".join(shotName.split('_'))
            padding = ''
            versionNumber = ''

            if os.path.exists(pathToWorking):
               getfiles = os.listdir(pathToWorking)

               ## Remove the stupid Keyboard folder if it exists.. thx autodesk.. not
               if 'Keyboard' in getfiles:
                   getfiles.remove('Keyboard')

               ## Process a clean list now.. trying to remove from the current list is giving me grief and I'm too fn tired to care...
               finalFiles = []
               for each in getfiles:
                   if each.split('.')[0] == fileShotName:
                       finalFiles.append(each)
                   else:
                       pass

               if finalFiles:
                   highestVersFile = max(finalFiles)
                   versionNumber  = int(highestVersFile.split('.')[1].split('v')[1]) + 1
               else:
                   versionNumber  = 1

               ## Now pad the version number
               if versionNumber < 10:
                   padding = '00'
               elif versionNumber < 100:
                   padding = '0'
               else:
                   padding = ''

            ## Rename the file
            #print 'FinalFilePath: %s\%s.v%s%s' % (pathToWorking, fileShotName, padding, versionNumber)
            renameTo = '%s\%s.v%s%s' % (pathToWorking, fileShotName, padding, versionNumber)
            ## Now rename the file
            cmds.file(rename = renameTo)
            ## Now save this as a working version in the animation working folder
            cmds.file(save = True, force = True, type = 'mayaAscii')
            cmds.workspace(pathToWorking, openWorkspace = True)
            asset_lib.turnOnModelEditors()

        else:
            self.parent.log_error("Unsupported file extension for %s! Nothing will be loaded." % file_path)
    
    def _loadLayoutScene_ForANIM(self, path, sg_publish_data):
        """
        Load file into Maya.

        This implementation opens a maya animation scene for Animation and saves this newly opened scene in the right workspace with
        a new version number appropriate to the Animation files.
        """
        # get the slashes right
        file_path = path.replace(os.path.sep, "/")
        log(app = None, method = 'add_file_to_maya', message = 'file_path: %s' % file_path, printToLog = False, verbose = configCONST.DEBUGGING)
        #file_path: I:/bubblebathbay/episodes/eptst/eptst_sh2000/Anm/publish/maya/eptstsh2000.v002.mb

        file_version = int(file_path.split('.')[1].split('v')[-1])
        log(app = None, method = 'add_file_to_maya', message = 'file_version: %s' % file_version, printToLog = False, verbose = configCONST.DEBUGGING)

        (path, ext) = os.path.splitext(file_path)

        if ext in [".ma", ".mb"]:
            ## Open the blocking file
            cmds.file(file_path, o = True, f = True)

            ## Cleanup unknown nodes to make sure we can save from mb back to ma
            for each in cmds.ls():
                if cmds.nodeType(each) == 'unknown':
                    cmds.delete(each)

            ## Save the animation file as the next working file in the FX folder
            tk = sgtk.sgtk_from_path(configCONST.SHOTGUN_CONFIG_PATH)
            getEntity = sg_publish_data.get("entity")
            shotName = getEntity.get("name")
            work_template = tk.templates['shot_work_area_maya']
            pathToWorking = r'%s' % tk.paths_from_template(work_template, {"Shot" : shotName, "Step":'Anm'})[0]
            pathToWorking.replace('\\\\', '\\')
            log(app = None, method = 'add_file_to_maya', message = 'pathToWorking: %s' % pathToWorking, printToLog = False, verbose = configCONST.DEBUGGING)
            ## Scan the folder and find the highest version number
            fileShotName = "".join(shotName.split('_'))
            padding = ''
            versionNumber = ''

            if os.path.exists(pathToWorking):
               getfiles = os.listdir(pathToWorking)

               ## Remove the stupid Keyboard folder if it exists.. thx autodesk.. not
               if 'Keyboard' in getfiles:
                   getfiles.remove('Keyboard')

               ## Process a clean list now.. trying to remove from the current list is giving me grief and I'm too fn tired to care...
               finalFiles = []
               for each in getfiles:
                   if each.split('.')[0] == fileShotName:
                       finalFiles.append(each)
                   else:
                       pass

               if finalFiles:
                   highestVersFile = max(finalFiles)
                   versionNumber  = int(highestVersFile.split('.')[1].split('v')[1]) + 1
               else:
                   versionNumber  = 1

               ## Now pad the version number
               if versionNumber < 10:
                   padding = '00'
               elif versionNumber < 100:
                   padding = '0'
               else:
                   padding = ''

            ## Rename the file
            #print 'FinalFilePath: %s\%s.v%s%s' % (pathToWorking, fileShotName, padding, versionNumber)
            renameTo = '%s\%s.v%s%s' % (pathToWorking, fileShotName, padding, versionNumber)
            ## Now rename the file
            cmds.file(rename = renameTo)
            ## Now save this as a working version in the animation working folder
            cmds.file(save = True, force = True, type = 'mayaAscii')
            cmds.workspace(pathToWorking, openWorkspace = True)
            asset_lib.turnOnModelEditors()

        else:
            self.parent.log_error("Unsupported file extension for %s! Nothing will be loaded." % file_path)



#######################################################################
## HELPERS
#######################################################################

    def _stripNamespaces(self, namespace):
        getAllNameSpaces = cmds.namespaceInfo(listOnlyNamespaces = True)
        for eachNS in getAllNameSpaces:
            if namespace in eachNS:
                try:
                    cmds.namespace(removeNamespace = eachNS, mergeNamespaceWithRoot = True)
                except RuntimeError:
                    pass