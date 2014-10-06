import os, sys
import shutil
import maya.cmds as cmds
import maya.mel as mel
import xml.etree.ElementTree as xml
import maya.OpenMaya as om
import tank
from tank import Hook
from tank import TankError
from getpass import getuser
import subprocess, tempfile, socket
if 'T:/software/bubblebathbay_sandbox/custom' not in sys.path:
    sys.path.append('T:/software/bubblebathbay_sandbox/custom')
import maya_asset_MASTERCLEANUPCODE as cleanup
from debug import debug
import FromMaya2Nuke as fm2n
import shader_lib as shd
import renderGlobals_writeXML as writeXML
import light_WriteXML as write_light_xml
reload(writeXML)
reload(fm2n)
reload(cleanup)
reload(shd)
reload(write_light_xml)


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
        ## PROCESS STUFF BEFORE DOWNGRADING
        shadingDone = False
        for task in tasks:
            debug(app = None, method = 'lightingSecPublish.execute', message = 'task: %s' % task, verbose = True)
            item = task["item"]
            debug(app = None, method = 'lightingSecPublish.execute', message = 'item: %s' % item, verbose = True)
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
                        debug(app = None, method = 'lightingSecPublish.execute', message = 'item: %s' % item, verbose = True)
                        self._publish_shading_xml_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                        ## Now fix the fileNodes back to a work folder structure not the publish folder structure
                        self.repathFileNodesForWork()
                        shadingDone =  True
                        debug(app = None, method = 'lightingSecPublish.execute', message = 'shadingDone: %s' % shadingDone, verbose = True)
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
                progress_cb(0, "Publishing Ocean and Fluids now...")
                ## Export the fx group found to an ma file.
                try:
                    self._publish_ocean_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'renderPreview':
                progress_cb(0, "Publishing Render Preview to Deadline now...")
                ## Export the renderPreview  found to submit to deadline
                try:
                    debug(app = None, method = 'lightingSecPublish.execute.renderPreview', message = 'item: %s' % item, verbose = True)
                    self.submitPreviewToDeadline(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'renderFinal':
                progress_cb(0, "Publishing Render Final to Deadline now...")
                ## Export the renderPreview  found to submit to deadline
                try:
                    debug(app = None, method = 'lightingSecPublish.execute.renderPreview', message = 'item: %s' % item, verbose = True)
                    self.submitFinalToDeadline(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'renderglobals_xml':
                progress_cb(0, "Publishing renderglobals_xml now...")
                ## Export the renderglobals_xml
                try:
                    debug(app = None, method = 'lightingSecPublish.execute.renderglobals_xml', message = 'item: %s' % item, verbose = True)
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
        debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'group_name: %s' % group_name, verbose = True)
        
        tank_type = output["tank_type"]
        debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'tank_type: %s' % tank_type, verbose = True)

        publish_template = output["publish_template"]
        debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'publish_template: %s' % publish_template, verbose = True)

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
        debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'FINAL publish_path: %s' % publish_path, verbose = True)

        try:
            self.parent.log_debug("Executing command: SHADING XML EXPORT PREP!")
            print '====================='
            print 'Exporting the renderglobals xml %s' % publish_path
            
            if not os.path.isdir(os.path.dirname(publish_path)):
                debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'PATH NOT FOUND.. MAKING DIRS NOW...', verbose = True)
                os.makedirs(os.path.dirname(publish_path))
                
            ## Now write to xml
            debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'writeXML now...', verbose = True)
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
        debug(app = None, method = '_publish_lighting_xml_for_item', message = 'group_name: %s' % group_name, verbose = True)
        
        tank_type = output["tank_type"]
        debug(app = None, method = '_publish_shading_xml_for_item', message = 'tank_type: %s' % tank_type, verbose = True)

        publish_template = output["publish_template"]
        debug(app = None, method = '_publish_shading_xml_for_item', message = 'publish_template: %s' % publish_template, verbose = True)

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
        debug(app = None, method = '_publish_shading_xml_for_item', message = 'FINAL publish_path: %s' % publish_path, verbose = True)

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
        debug(app = None, method = '_publish_lighting_xml_for_item', message = 'group_name: %s' % group_name, verbose = True)

        tank_type = output["tank_type"]
        debug(app = None, method = '_publish_lighting_xml_for_item', message = 'tank_type: %s' % tank_type, verbose = True)

        publish_template = output["publish_template"]
        debug(app = None, method = '_publish_lighting_xml_for_item', message = 'publish_template: %s' % publish_template, verbose = True)

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
        debug(app = None, method = '_publish_lighting_xml_for_item', message = 'FINAL publish_path: %s' % publish_path, verbose = True)
        try:
            self.parent.log_debug("Executing command: LIGHTING XML EXPORT PREP!")
            print '====================='
            print 'Exporting the lighting xml %s' % publish_path

            if not os.path.isdir(os.path.dirname(publish_path)):
                debug(app = None, method = '_publish_renderglobals_xml_for_item', message = 'PATH NOT FOUND.. MAKING DIRS NOW...', verbose = True)
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
        debug(app = None, method = '_publish_nukeCamera_for_item', message = 'item["name"]: %s' % item["name"], verbose = True)
        
        tank_type = output["tank_type"]
        debug(app = None, method = '_publish_nukeCamera_for_item', message = 'tank_type: %s' % tank_type, verbose = True)
        
        publish_template = output["publish_template"]
        debug(app = None, method = '_publish_nukeCamera_for_item', message = 'publish_template: %s' % publish_template, verbose = True)

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
            debug(app = None, method = '_publish_nukeCamera_for_item', message = 'startFrame: %s' % startFrame, verbose = True)

            endFrame = cmds.playbackOptions(query =True, animationEndTime= True)
            debug(app = None, method = '_publish_nukeCamera_for_item', message = 'endFrame: %s' % endFrame, verbose = True)          
            
            cleanup.turnOffModelEditors()
            
            shotCams = []
            for eachCamera in cmds.listRelatives(item["name"], children = True):
                if cmds.getAttr('%s.type' % eachCamera) == 'shotCam':
                    debug(app = None, method = '_publish_nukeCamera_for_item', message = 'eachCamera: %s' % eachCamera, verbose = True)
                    shotCams.extend([eachCamera])
            debug(app = None, method = '_publish_nukeCamera_for_item', message = 'shotCams: %s' % shotCams, verbose = True)
            
            debug(app = None, method = '_publish_nukeCamera_for_item', message = 'len(shotCams): %s' % len(shotCams), verbose = True)
            group_name = ''
            if len(shotCams) == 1:
                # update fields with the group name:
                group_name = '%s_NUKECAM' % shotCams[0]
                fields["grp_name"] = group_name
                debug(app = None, method = '_publish_nukeCamera_for_item', message = 'grp_name: %s' % group_name, verbose = True)
                
                fields["cam_name"] = shotCams[0]
                debug(app = None, method = '_publish_nukeCamera_for_item', message = 'cam_name: %s' % shotCams[0], verbose = True)
    
                publish_path = publish_template.apply_fields(fields)                 
                debug(app = None, method = '_publish_nukeCamera_for_item', message = 'FINAL publish_path: %s' % publish_path, verbose = True)
                
                ## Make the directory now...
                if not os.path.isdir(os.path.dirname(publish_path)):
                    debug(app = None, method = '_publish_nukeCamera_for_item', message = 'Building dir: %s' % os.path.dirname(publish_path), verbose = True)
                    os.mkdir(os.path.dirname(publish_path))

                frame_start = cmds.playbackOptions(query = True, animationStartTime = True)
                frame_end = cmds.playbackOptions(query = True, animationEndTime = True)
    
                cmds.select(shotCams[0], r = True)
                #Switching to alembic output for camera.
                rootList = ''
                for eachRoot in cmds.ls(sl= True):
                    rootList = '-root %s %s' % (str(cmds.ls(eachRoot, l = True)[0]), rootList)
                
                debug(app = None, method = '_publish_nukeCamera_for_item', message = 'rootList: %s' % rootList, verbose = True)
                abc_export_cmd = "preRollStartFrame -15 -ro -attr smoothed -attr mcAssArchive -wholeFrameGeo -worldSpace -writeVisibility -uvWrite -fr %d %d %s -file %s" % (frame_start, frame_end, rootList, publish_path)
                cmds.AbcExport(verbose = False, j = abc_export_cmd)
                ##fm2n.FromMaya2Nuke(exportPath = os.path.dirname(publish_path), nukePath = 'C:\\"Program Files\"\Nuke7.0v6\\', nukeExec = 'Nuke7.0.exe', scriptName = '%s' % shotCams[0], startFrame = startFrame, endFrame = endFrame, camera = shotCams[0])
                #fm2n.FromMaya2Nuke(exportPath = os.path.dirname(publish_path), nukePath = '', nukeExec = '', scriptName = '%s' % shotCams[0], startFrame = startFrame, endFrame = endFrame)
                debug(app = None, method = '_publish_nukeCamera_for_item', message = 'Export Complete...', verbose = True)
    
                ## Now register publish with shotgun
                self._register_publish(publish_path,
                                      group_name,
                                      sg_task,
                                      publish_version, 
                                      tank_type,
                                      comment,
                                      thumbnail_path,
                                      [primary_publish_path])
                debug(app = None, method = '_publish_nukeCamera_for_item', message = '_register_publish complete for %s...' % shotCams[0], verbose = True)
                print 'Finished camera export for %s...' % shotCams[0]
                print '====================='
                cleanup.turnOnModelEditors()
            else:
                cmds.warning('Found more than one shotCam, using the first in the list only!!')
                pass
        except Exception, e:
            raise TankError("Failed to export NukeCamera")

    def _publish_ocean_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an xml file for the specified item and publish it
        to Shotgun.
        """
        debug(app = None, method = '_publish_ocean_for_item', message = 'Processing item: %s' % item['name'], verbose = True)
        
        group_name = '%s' % ''.join(item["name"].strip("|").split('_hrc')[0].split('_'))
        debug(app = None, method = '_publish_ocean_for_item', message = 'group_name: %s' % group_name, verbose = True)

        tank_type = output["tank_type"]
        debug(app = None, method = '_publish_ocean_for_item', message = 'tank_type: %s' % tank_type, verbose = True)
        
        publish_template = output["publish_template"]
        debug(app = None, method = '_publish_ocean_for_item', message = 'publish_template: %s' % publish_template, verbose = True)

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
        debug(app = None, method = '_publish_ocean_for_item', message = 'FINAL publish_path: %s' % publish_path, verbose = True)

        ## Make the directory now...
        if not os.path.isdir(os.path.dirname(publish_path)):
            debug(app = None, method = '_publish_ocean_for_item', message = 'Building dir: %s' % os.path.dirname(publish_path), verbose = True)
            os.mkdir(os.path.dirname(publish_path))

        try:
            self.parent.log_debug("Executing command: OCEAN EXPORT!")
            print '====================='
            print 'Exporting the ocean and fluids %s' % publish_path
            
            ## Now export
            cmds.select(item['name'], r = True)
            cmds.file(publish_path, force = True, options =  "v=0;", typ = "mayaAscii", es = True)
            
            ## Now register publish with shotgun
            self._register_publish(publish_path, 
                                  group_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
            print 'Finished ocean and fluids export...'
            print '====================='
        except Exception, e:
            raise TankError("Failed to export %s" % group_name)

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

    def submitPreviewToDeadline(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        debug(app = None, method = 'submitPreviewToDeadline', message = 'Entered submitPreviewToDeadline' , verbose = True)
        render_name = item["name"]
        debug(app = None, method = 'submitPreviewToDeadline', message = 'render_name: %s' % render_name, verbose = True)

        tank_type = output["tank_type"]
        debug(app = None, method = 'submitPreviewToDeadline', message = 'tank_type: %s' % tank_type, verbose = True)
        
        publish_template = output["publish_template"]
        debug(app = None, method = 'submitPreviewToDeadline', message = 'publish_template: %s' % publish_template, verbose = True)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields                      = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = render_name

        ## BUILD THE Job Info File for deadline
        ##deadlinecommand.exe [Job Info File] [Plug-in Info File]
        publish_path = publish_template.apply_fields(fields)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'FINAL publish_path: %s' % publish_path, verbose = True)
        
        ## define log paths etc
        logTo = r'%s/deadlinebg_output' % tempfile.gettempdir().replace('\\', '/')
        jobInfoPath = r'%s/maya_job_info.job' % tempfile.gettempdir().replace('\\', '/')
        pluginInfoPath = r'%s/maya_plugin_info.job' % tempfile.gettempdir().replace('\\', '/')
        debug(app = None, method = 'submitPreviewToDeadline', message = 'logTo: %s' % logTo, verbose = True)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'jobInfoPath: %s' % jobInfoPath, verbose = True)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'pluginInfoPath: %s' % pluginInfoPath, verbose = True)
        
        ## Job Info stuff
        jobname = '%s_%s' % ( '_'.join((self._getMostRecentPublish()[0].split('.'))), render_name)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'jobname: %s' % jobname, verbose = True)
        username = render_name
        debug(app = None, method = 'submitPreviewToDeadline', message = 'username: %s' % username, verbose = True)
        projectPath  = r'%s' % cmds.workspace(query = True, fullName = True).replace('/', '\\')
        debug(app = None, method = 'submitPreviewToDeadline', message = 'projectPath: %s' % projectPath, verbose = True)
        outputFilePath  = publish_path
        debug(app = None, method = 'submitPreviewToDeadline', message = 'outputFilePath: %s' % outputFilePath, verbose = True)
        ## check and build output path if it doesn't exist
        if not os.path.isdir(outputFilePath):
            os.mkdir(outputFilePath)
        sceneFilePath = os.path.join(self._getMostRecentPublish()[1], self._getMostRecentPublish()[0]).replace('\\', '/')
        debug(app = None, method = 'submitPreviewToDeadline', message = 'sceneFilePath: %s' % sceneFilePath, verbose = True)
        ouputFileName = '_'.join((self._getMostRecentPublish()[0].split('.')))
        debug(app = None, method = 'submitPreviewToDeadline', message = 'ouputFileName: %s' % ouputFileName, verbose = True)
        comment  = comment
        debug(app = None, method = 'submitPreviewToDeadline', message = 'comment: %s' % comment, verbose = True)
        version = '2013.5'
        debug(app = None, method = 'submitPreviewToDeadline', message = 'version: %s' % version, verbose = True)
        pool = 'None'
        debug(app = None, method = 'submitPreviewToDeadline', message = 'pool: %s' % pool, verbose = True)
        machineLimit = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'machineLimit: %s' % machineLimit, verbose = True)
        priority = 99
        debug(app = None, method = 'submitPreviewToDeadline', message = 'priority: %s' % priority, verbose = True)
        taskTimeoutMinutes = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'taskTimeoutMinutes: %s' % taskTimeoutMinutes, verbose = True)
        minRenderTimeMinutes = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'minRenderTimeMinutes: %s' % minRenderTimeMinutes, verbose = True)
        concurrentTasks = 1
        debug(app = None, method = 'submitPreviewToDeadline', message = 'concurrentTasks: %s' % concurrentTasks, verbose = True)
        department = getuser()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'department: %s' % department, verbose = True)
        renderer = 'MentalRay'
        debug(app = None, method = 'submitPreviewToDeadline', message = 'renderer: %s' % renderer, verbose = True)
        autoMemoryLimit = 1
        debug(app = None, method = 'submitPreviewToDeadline', message = 'autoMemoryLimit: %s' % autoMemoryLimit, verbose = True)
        memoryLimit = 1
        debug(app = None, method = 'submitPreviewToDeadline', message = 'memoryLimit: %s' % memoryLimit, verbose = True)
        camera = self._getShotCam()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'camera: %s' % camera, verbose = True)
        startFrame = cmds.playbackOptions(query = True, animationStartTime = True)
        endFrame = cmds.playbackOptions(query = True, animationEndTime = True)

        ## Process the data into the right formats
        submitString = [
                        'Plugin=MayaBatch',
                        'Name=%s' % jobname,
                        'Comment=%s' % comment,
                        'Department=%s' % department,
                        'Pool=%s' % pool,
                        'Group=bbbrender_16',
                        'Priority=%s' % priority,
                        'TaskTimeoutMinutes=%s' % taskTimeoutMinutes,
                        'EnableAutoTimeout=False',
                        'ConcurrentTasks=%s' % concurrentTasks,
                        'LimitConcurrentTasksToNumberOfCpus=True',
                        'MachineLimit=%s' % machineLimit,
                        'Whitelist=',
                        'LimitGroups=',
                        'JobDependencies=',
                        'OnJobComplete=Nothing',
                        'Frames=%s-%s' % (int(startFrame), int(endFrame)),
                        'ChunkSize=1',
                        'OutputDirectory0=%s/' % outputFilePath,
                        ]
        ## write to file
        jobInfoFile = open(jobInfoPath, "w")
        for eachLine in submitString:
            jobInfoFile.write('%s\n' % eachLine)
        jobInfoFile.close()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'Wrote jobInfoFile successfully...', verbose = True)
        
        ### Plugin Info File
        _MAYA_PLUGIN_INFO_ATTRS = [
                                    'SceneFile=%s' %(str(cmds.file(q = 1, sceneName = 1)).replace('\\', '/')),
                                    'Version=%s' % version,
                                    'Build=64bit',
                                    'ProjectPath=\\\\192.168.5.252/BBB_main/bbb',
                                    'StrictErrorChecking=True',
                                    'LocalRendering=True',
                                    'MaxProcessors=0',
                                    'OutputFilePath=%s/' % outputFilePath,
                                    'Renderer=%s' % renderer,
                                    'MentalRayVerbose=Progress Messages',
                                    'AutoMemoryLimit=True',
                                    'MemoryLimit=0',
                                    'CommandLineOptions=',
                                    'UseOnlyCommandLineOptions=0',
                                    'IgnoreError211=False',
                                    'Camera=%s' % [cam for cam in cmds.ls(type = 'camera')  if 'shotCam_bake' in cam][0].replace('Shape', ''),
                                    ]
        ## write to file
        pluginInfoFile = open(pluginInfoPath, "w")
        for eachLine in _MAYA_PLUGIN_INFO_ATTRS:
            pluginInfoFile.write('%s\n' % eachLine)
        pluginInfoFile.close()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'Wrote pluginInfoFile successfully...', verbose = True)
        
        try:
            self.parent.log_debug("Executing command: RENDER PREVIEW!")
            print '====================='
            print 'Submitting to deadlines %s' % publish_path

            subprocess.call( 'Deadlinecommand.exe %s %s %s' % (jobInfoPath, pluginInfoPath, sceneFilePath) )
            
            ## Now register publish with shotgun
            self._register_publish(publish_path, 
                                  'render_name', 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
            print 'Finished submitting render preview to deadline.....'
            print '====================='
        except Exception, e:
            raise TankError("Failed to export %s" % render_name)

    def submitFinalToDeadline(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        debug(app = None, method = 'submitPreviewToDeadline', message = 'Entered submitPreviewToDeadline' , verbose = True)
        render_name = item["name"]
        debug(app = None, method = 'submitPreviewToDeadline', message = 'render_name: %s' % render_name, verbose = True)

        tank_type = output["tank_type"]
        debug(app = None, method = 'submitPreviewToDeadline', message = 'tank_type: %s' % tank_type, verbose = True)
        
        publish_template = output["publish_template"]
        debug(app = None, method = 'submitPreviewToDeadline', message = 'publish_template: %s' % publish_template, verbose = True)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields                      = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = render_name

        ## BUILD THE Job Info File for deadline
        ##deadlinecommand.exe [Job Info File] [Plug-in Info File]
        publish_path = publish_template.apply_fields(fields)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'FINAL publish_path: %s' % publish_path, verbose = True)
        
        ## define log paths etc
        logTo = r'%s/deadlinebg_output' % tempfile.gettempdir().replace('\\', '/')
        jobInfoPath = r'%s/maya_job_info.job' % tempfile.gettempdir().replace('\\', '/')
        pluginInfoPath = r'%s/maya_plugin_info.job' % tempfile.gettempdir().replace('\\', '/')
        debug(app = None, method = 'submitPreviewToDeadline', message = 'logTo: %s' % logTo, verbose = True)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'jobInfoPath: %s' % jobInfoPath, verbose = True)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'pluginInfoPath: %s' % pluginInfoPath, verbose = True)
        
        ## Job Info stuff
        jobname = '%s_%s' % ( '_'.join((self._getMostRecentPublish()[0].split('.'))), render_name)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'jobname: %s' % jobname, verbose = True)
        username = render_name
        debug(app = None, method = 'submitPreviewToDeadline', message = 'username: %s' % username, verbose = True)
        projectPath  = cmds.workspace(query = True, fullName = True)
        debug(app = None, method = 'submitPreviewToDeadline', message = 'projectPath: %s' % projectPath, verbose = True)
        outputFilePath  = publish_path
        debug(app = None, method = 'submitPreviewToDeadline', message = 'outputFilePath: %s' % outputFilePath, verbose = True)
        ## check and build output path if it doesn't exist
        if not os.path.isdir(outputFilePath):
            os.mkdir(outputFilePath)
        sceneFilePath = os.path.join(self._getMostRecentPublish()[1], self._getMostRecentPublish()[0]).replace('\\', '/')
        debug(app = None, method = 'submitPreviewToDeadline', message = 'sceneFilePath: %s' % sceneFilePath, verbose = True)
        ouputFileName = '_'.join((self._getMostRecentPublish()[0].split('.')))
        debug(app = None, method = 'submitPreviewToDeadline', message = 'ouputFileName: %s' % ouputFileName, verbose = True)
        comment  = comment
        debug(app = None, method = 'submitPreviewToDeadline', message = 'comment: %s' % comment, verbose = True)
        version = '2013.5'
        debug(app = None, method = 'submitPreviewToDeadline', message = 'version: %s' % version, verbose = True)
        pool = 'None'
        debug(app = None, method = 'submitPreviewToDeadline', message = 'pool: %s' % pool, verbose = True)
        machineLimit = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'machineLimit: %s' % machineLimit, verbose = True)
        priority = 99
        debug(app = None, method = 'submitPreviewToDeadline', message = 'priority: %s' % priority, verbose = True)
        taskTimeoutMinutes = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'taskTimeoutMinutes: %s' % taskTimeoutMinutes, verbose = True)
        minRenderTimeMinutes = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'minRenderTimeMinutes: %s' % minRenderTimeMinutes, verbose = True)
        concurrentTasks = 1
        debug(app = None, method = 'submitPreviewToDeadline', message = 'concurrentTasks: %s' % concurrentTasks, verbose = True)
        department = getuser()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'department: %s' % department, verbose = True)
        limitGroups = 0
        debug(app = None, method = 'submitPreviewToDeadline', message = 'limitGroups: %s' % limitGroups, verbose = True)
        renderer = 'MentalRay'
        debug(app = None, method = 'submitPreviewToDeadline', message = 'renderer: %s' % renderer, verbose = True)
        autoMemoryLimit = 1
        debug(app = None, method = 'submitPreviewToDeadline', message = 'autoMemoryLimit: %s' % autoMemoryLimit, verbose = True)
        memoryLimit = 1
        debug(app = None, method = 'submitPreviewToDeadline', message = 'memoryLimit: %s' % memoryLimit, verbose = True)
        camera = self._getShotCam()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'camera: %s' % camera, verbose = True)
        startFrame = cmds.playbackOptions(query = True, animationStartTime = True)
        endFrame = cmds.playbackOptions(query = True, animationEndTime = True)

        ## Process the data into the right formats
        submitString = [
                        'Plugin=MayaBatch',
                        'Name=%s' % jobname,
                        'Comment=%s' % comment,
                        'Department=%s' % department,
                        'Pool=%s' % pool,
                        'Group=bbbrender_16',
                        'Priority=%s' % priority,
                        'TaskTimeoutMinutes=%s' % taskTimeoutMinutes,
                        'EnableAutoTimeout=False',
                        'ConcurrentTasks=%s' % concurrentTasks,
                        'LimitConcurrentTasksToNumberOfCpus=True',
                        'MachineLimit=%s' % machineLimit,
                        'Whitelist=',
                        'LimitGroups=',
                        'JobDependencies=',
                        'OnJobComplete=Nothing',
                        'Frames=%s-%s' % (int(startFrame), int(endFrame)),
                        'ChunkSize=1',
                        'OutputDirectory0=%s/' % outputFilePath,
                        ]
                        
        ## write to file
        jobInfoFile = open(jobInfoPath, "w")
        for eachLine in submitString:
            jobInfoFile.write('%s\n' % eachLine)
        jobInfoFile.close()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'Wrote jobInfoFile successfully...', verbose = True)
        
        ### Plugin Info File
        _MAYA_PLUGIN_INFO_ATTRS =   [
                                    'SceneFile=%s' %(str(cmds.file(q = 1, sceneName = 1)).replace('\\', '/')),
                                    'Version=%s' % version,
                                    'Build=64bit',
                                    'ProjectPath=\\\\192.168.5.252/BBB_main/bbb',
                                    'StrictErrorChecking=True',
                                    'LocalRendering=True',
                                    'MaxProcessors=0',
                                    'OutputFilePath=%s/' % outputFilePath,
                                    'Renderer=%s' % renderer,
                                    'MentalRayVerbose=Progress Messages',
                                    'AutoMemoryLimit=True',
                                    'MemoryLimit=0',
                                    'CommandLineOptions=',
                                    'UseOnlyCommandLineOptions=0',
                                    'IgnoreError211=False',
                                    'Camera=%s' % [cam for cam in cmds.ls(type = 'camera')  if 'shotCam_bake' in cam][0].replace('Shape', ''),
                                    ]

                                    
        ## write to file
        pluginInfoFile = open(pluginInfoPath, "w")
        for eachLine in _MAYA_PLUGIN_INFO_ATTRS:
            pluginInfoFile.write('%s\n' % eachLine)
        pluginInfoFile.close()
        debug(app = None, method = 'submitPreviewToDeadline', message = 'Wrote pluginInfoFile successfully...', verbose = True)
        
        try:
            self.parent.log_debug("Executing command: RENDER FINAL!")
            print '====================='
            print 'Submitting to deadlines %s' % publish_path

            subprocess.call( 'Deadlinecommand.exe %s %s %s' % (jobInfoPath, pluginInfoPath, sceneFilePath) )
            
            ## Now register publish with shotgun
            self._register_publish(publish_path, 
                                  render_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
            print 'Finished submitting render preview to deadline.....'
            print '====================='
        except Exception, e:
            raise TankError("Failed to export %s" % render_name)