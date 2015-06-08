import tank
from tank import Hook
from tank import TankError
import os
import maya.cmds as cmds
import tank
from tank import Hook
from tank import TankError
import configCONST as configCONST
import maya_shd_lib as shd
import maya_asset_lib as asset_lib
import renderGlobals_writeXML as writeXML
import light_writeXML as write_light_xml
from logger import log
reload(configCONST)## leave this alone if you want to update the config using the maya shotgun reload menu


class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """    
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_publish_path, progress_cb, **kwargs):
        """
        Main hook entry point
        :tasks:         List of secondary tasks to be published.  Each task is a 
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

        :primary_publish_path: Path string
                        This is the path of the primary published file as returned
                        by the primary publish hook

        :progress_cb:   Function
                        A progress callback to log progress during pre-publish.  Call:

                            progress_cb(percentage, msg)

                        to report progress to the UI

        :returns:       A list of any tasks that had problems that need to be reported 
                        in the UI.  Each item in the list should be a dictionary containing 
                        the following keys:
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
        """""
        results = []
        shadingDone = False

        for task in tasks:
            log(app = None, method = 'lightingSecPublish.execute', message = 'task: %s' % task, printToLog = False, verbose = configCONST.DEBUGGING)
            item = task["item"]
            log(app = None, method = 'lightingSecPublish.execute', message = 'item: %s' % item, printToLog = False, verbose = configCONST.DEBUGGING)
            output = task["output"]
            errors = []
            # report progress:
            ### SHD XML
            if output["name"] == 'shd_xml':
                progress_cb(0, "Publishing SHD xml now...")
                # type: mesh_grp
                ## Because shading exports from the shaders and not the actual groups we can just run this step ONCE!
                ## If we do this for every item we're wasting serious time outputting the same thing over and over.
                if not shadingDone: 
                    try:
                        log(app = None, method = 'lightingSecPublish.execute', message = 'item: %s' % item, printToLog = False, verbose = configCONST.DEBUGGING)
                        self._publish_shading_xml_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                        ## Now fix the fileNodes back to a work folder structure not the publish folder structure
                        self.repathFileNodesForWork()
                        shadingDone =  True
                        log(app = None, method = 'lightingSecPublish.execute', message = 'shadingDone: %s' % shadingDone, printToLog = False, verbose = configCONST.DEBUGGING)
                    except Exception, e:
                        errors.append("Publish failed - %s" % e)
                else:
                    pass
            ### LIGHTS XML
            elif output["name"] == 'lights_xml':
                progress_cb(0, "Publishing Light xml now...")
                # type: light_grp
                ## Because we have only found in the scan scene just the LIGHTS_hrc group there should only be one light item to process...
                try:
                    self._publish_lighting_xml_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'nukeCam':
                progress_cb(0, "Publishing Nuke Cameras now...")
                ## Because we have only found in the scan scene just the SHOTCAM_hrc group there should only be one camera item to process...
                ## But there may be more cameras under that group so we process these during the _publish_nukeCamera_for_item
                try:
                    self._publish_nukeCamera_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'fx_caches':
                progress_cb(0, "Publishing FX now...")
                ## Export the fx group found to an ma file.
                try:
                    pass ## TO DO FX IF NECESSARY
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'renderglobals_xml':
                progress_cb(0, "Publishing renderglobals_xml now...")
                ## Export the renderglobals_xml
                try:
                    log(app = None, method = 'lightingSecPublish.execute.renderglobals_xml', message = 'item: %s' % item, printToLog = False, verbose = configCONST.DEBUGGING)
                    self._publish_renderglobals_xml_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item!")
        
        progress_cb(50)

        ## if there is anything to report then add to result
        if len(errors) > 0:
            ## add result:
            results.append({"task":task, "errors":errors})
        progress_cb(100)
        return results

    def _publish_renderglobals_xml_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an xml file for the specified item and publish it
        to Shotgun.
        """
        group_name = '%s_LIGHTING_RENDERGLOBALS_XML' % ''.join(item["name"].strip("|").split('_hrc')[0].split('_'))
        log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'group_name: %s' % group_name, printToLog = False, verbose = configCONST.DEBUGGING)
        
        tank_type = output["tank_type"]
        log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'tank_type: %s' % tank_type, printToLog = False, verbose = configCONST.DEBUGGING)

        publish_template = output["publish_template"]
        log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'publish_template: %s' % publish_template, printToLog = False, verbose = configCONST.DEBUGGING)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)
        log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'FINAL publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)

        try:
            self.parent.log_debug("Executing command: SHADING XML EXPORT PREP!")
            print '====================='
            print 'Exporting the renderglobals xml %s' % publish_path
            
            if not os.path.isdir(os.path.dirname(publish_path)):
                log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'PATH NOT FOUND.. MAKING DIRS NOW...', printToLog = False, verbose = configCONST.DEBUGGING)
                os.makedirs(os.path.dirname(publish_path))
                
            ## Now write to xml
            log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'writeXML now...', printToLog = False, verbose = configCONST.DEBUGGING)
            writeXML.writeRenderGlobalData(pathToXML = publish_path)
            
            self._register_publish(publish_path, 
                                  group_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
            print 'Finished xml export...'
            print '====================='
        except Exception, e:
            raise TankError("Failed to export xml")
    
    def _publish_shading_xml_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an xml file for the specified item and publish it
        to Shotgun.
        """
        group_name = '%s_LIGHTING_SHD_XML' % ''.join(item["name"].strip("|").split('_hrc')[0].split('_'))
        log(app = None, method = '_publish_lighting_xml_for_item', message = 'group_name: %s' % group_name, printToLog = False, verbose = configCONST.DEBUGGING)
        
        tank_type = output["tank_type"]
        log(app = None, method = '_publish_shading_xml_for_item', message = 'tank_type: %s' % tank_type, printToLog = False, verbose = configCONST.DEBUGGING)

        publish_template = output["publish_template"]
        log(app = None, method = '_publish_shading_xml_for_item', message = 'publish_template: %s' % publish_template, printToLog = False, verbose = configCONST.DEBUGGING)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)
        log(app = None, method = '_publish_shading_xml_for_item', message = 'FINAL publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)

        try:
            self.parent.log_debug("Executing command: SHADING XML EXPORT PREP!")
            print '====================='
            print 'Exporting the shading xml %s' % publish_path
            
            shd.exportPrep(path = publish_path)
            
            self._register_publish(publish_path, 
                                  group_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
            print 'Finished xml export...'
            print '====================='
        except Exception, e:
            raise TankError("Failed to export xml")

    def _publish_lighting_xml_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an xml file for the specified item and publish it
        to Shotgun.
        """
        group_name = '%s_LIGHTING_LIGHTS_XML' % ''.join(item["name"].strip("|").split('_hrc')[0].split('_'))
        log(app = None, method = '_publish_lighting_xml_for_item', message = 'group_name: %s' % group_name, printToLog = False, verbose = configCONST.DEBUGGING)

        tank_type = output["tank_type"]
        log(app = None, method = '_publish_lighting_xml_for_item', message = 'tank_type: %s' % tank_type, printToLog = False, verbose = configCONST.DEBUGGING)

        publish_template = output["publish_template"]
        log(app = None, method = '_publish_lighting_xml_for_item', message = 'publish_template: %s' % publish_template, printToLog = False, verbose = configCONST.DEBUGGING)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields              = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)
        log(app = None, method = '_publish_lighting_xml_for_item', message = 'FINAL publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)
        try:
            self.parent.log_debug("Executing command: LIGHTING XML EXPORT PREP!")
            print '====================='
            print 'Exporting the lighting xml %s' % publish_path

            if not os.path.isdir(os.path.dirname(publish_path)):
                log(app = None, method = '_publish_renderglobals_xml_for_item', message = 'PATH NOT FOUND.. MAKING DIRS NOW...', printToLog = False, verbose = configCONST.DEBUGGING)
                os.makedirs(os.path.dirname(publish_path))

            write_light_xml.writeLightData(publish_path)

            ## Now register publish with shotgun
            self._register_publish(publish_path, 
                                  group_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
            print 'Finished xml export...'
            print '====================='
        except Exception, e:
            raise TankError("Failed to export xml")

    def _publish_nukeCamera_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an xml file for the specified item and publish it to Shotgun.
        """        
        log(app = None, method = '_publish_nukeCamera_for_item', message = 'item["name"]: %s' % item["name"], printToLog = False, verbose = configCONST.DEBUGGING)
        
        tank_type = output["tank_type"]
        log(app = None, method = '_publish_nukeCamera_for_item', message = 'tank_type: %s' % tank_type, printToLog = False, verbose = configCONST.DEBUGGING)
        
        publish_template = output["publish_template"]
        log(app = None, method = '_publish_nukeCamera_for_item', message = 'publish_template: %s' % publish_template, printToLog = False, verbose = configCONST.DEBUGGING)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        
        ## create the publish path by applying the fields 
        ## with the publish template:            
        try:
            print '====================='
            print 'Exporting the nukeCamera'
            startFrame = cmds.playbackOptions(query =True, animationStartTime = True) 
            log(app = None, method = '_publish_nukeCamera_for_item', message = 'startFrame: %s' % startFrame, printToLog = False, verbose = configCONST.DEBUGGING)

            endFrame = cmds.playbackOptions(query =True, animationEndTime= True)
            log(app = None, method = '_publish_nukeCamera_for_item', message = 'endFrame: %s' % endFrame, printToLog = False, verbose = configCONST.DEBUGGING)          
            
            asset_lib.turnOffModelEditors()
            
            shotCams = []
            for eachCamera in cmds.listRelatives(item["name"], children = True):
                if cmds.getAttr('%s.type' % eachCamera) == 'shotCam':
                    log(app = None, method = '_publish_nukeCamera_for_item', message = 'eachCamera: %s' % eachCamera, printToLog = False, verbose = configCONST.DEBUGGING)
                    shotCams.extend([eachCamera])
            log(app = None, method = '_publish_nukeCamera_for_item', message = 'shotCams: %s' % shotCams, printToLog = False, verbose = configCONST.DEBUGGING)
            
            log(app = None, method = '_publish_nukeCamera_for_item', message = 'len(shotCams): %s' % len(shotCams), printToLog = False, verbose = configCONST.DEBUGGING)
            group_name = ''
            if len(shotCams) == 1:
                # update fields with the group name:
                group_name = '%s_NUKECAM' % shotCams[0]
                fields["grp_name"] = group_name
                log(app = None, method = '_publish_nukeCamera_for_item', message = 'grp_name: %s' % group_name, printToLog = False, verbose = configCONST.DEBUGGING)
                
                fields["cam_name"] = shotCams[0]
                log(app = None, method = '_publish_nukeCamera_for_item', message = 'cam_name: %s' % shotCams[0], printToLog = False, verbose = configCONST.DEBUGGING)
    
                publish_path = publish_template.apply_fields(fields)                 
                log(app = None, method = '_publish_nukeCamera_for_item', message = 'FINAL publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)
                
                ## Make the directory now...
                if not os.path.isdir(os.path.dirname(publish_path)):
                    log(app = None, method = '_publish_nukeCamera_for_item', message = 'Building dir: %s' % os.path.dirname(publish_path), printToLog = False, verbose = configCONST.DEBUGGING)
                    os.mkdir(os.path.dirname(publish_path))

                frame_start = cmds.playbackOptions(query = True, animationStartTime = True)
                frame_end = cmds.playbackOptions(query = True, animationEndTime = True)
    
                cmds.select(shotCams[0], r = True)
                #Switching to alembic output for camera.
                rootList = ''
                for eachRoot in cmds.ls(sl= True):
                    rootList = '-root %s %s' % (str(cmds.ls(eachRoot, l = True)[0]), rootList)
                
                log(app = None, method = '_publish_nukeCamera_for_item', message = 'rootList: %s' % rootList, printToLog = False, verbose = configCONST.DEBUGGING)
                abc_export_cmd = "preRollStartFrame -15 -ro -attr smoothed -attr mcAssArchive -wholeFrameGeo -worldSpace -writeVisibility -uvWrite -fr %d %d %s -file %s" % (frame_start, frame_end, rootList, publish_path)
                cmds.AbcExport(verbose = False, j = abc_export_cmd)
                log(app = None, method = '_publish_nukeCamera_for_item', message = 'Export Complete...', printToLog = False, verbose = configCONST.DEBUGGING)
    
                ## Now register publish with shotgun
                self._register_publish(publish_path,
                                      group_name,
                                      sg_task,
                                      publish_version, 
                                      tank_type,
                                      comment,
                                      thumbnail_path,
                                      [primary_publish_path])
                log(app = None, method = '_publish_nukeCamera_for_item', message = '_register_publish complete for %s...' % shotCams[0], printToLog = False, verbose = configCONST.DEBUGGING)
                print 'Finished camera export for %s...' % shotCams[0]
                print '====================='
                asset_lib.turnOnModelEditors()
            else:
                cmds.warning('Found more than one shotCam, using the first in the list only!!')
                pass
        except Exception, e:
            raise TankError("Failed to export NukeCamera")

    def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths=None):
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

        # register publish;
        sg_data = tank.util.register_publish(**args)
        if dependency_paths:
            print "================DEP===================="
            print '%s dependencies: \n\t%s' % (path, dependency_paths[0])
            print "========================================"
        return sg_data
    
###########################################################################################################
########################## START SHADING XML EXPORT SCRIPTS ##############################################

    def _getMostRecentPublish(self):
        self.workspace = cmds.workspace(query = True, fullName = True)
        # self.publishPath = '%s/publish/maya' % self.workspace.split('work')[0]
        self.publishPath = os.path.join(self.workspace.split('work')[0], 'publish/maya').replace('\\', '/')
        self.getLatestPublish = max(os.listdir(self.publishPath))
        if self.getLatestPublish:
            return self.getLatestPublish, self.publishPath
        else:
            return False, False

    def _getShotCam(self):
        self.cams = cmds.ls(type = 'camera')
        for each in self.cams:
            getParent = cmds.listRelatives(each, parent  = True)
            if getParent:
                if cmds.objExists('%s.type' % getParent[0]):
                    if cmds.getAttr('%s.type' % getParent[0]) == 'shotCam':
                        return each