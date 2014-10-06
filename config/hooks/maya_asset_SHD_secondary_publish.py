import os
import maya.cmds as cmds
import tank
import time
from tank import Hook
from tank import TankError
from logger import log
import configCONST as configCONST
import maya_shd_lib as shd_lib
import shd_writeXML as shd_writexml
import uv_writeXML as uvwrite
import uv_getUVs as getUvs
import maya_secondarypublishmessage as secpubmsg
reload(shd_lib)
reload(shd_writexml)
reload(getUvs)


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

        ##################################################################
        ## PROCESS STUFF BEFORE DOWNGRADING
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []
            
            # report progress:
            progress_cb(0, "Publishing", task)

            ### SHD XML
            if output["name"] == 'shd_xml':
                """
                Main xml exporter for lighting tools for reconnecting shaders to the alembics etc
                """
                try:
                    self._publish_shd_xml_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                    shd_lib.repathFileNodesForWork()

                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            ### COPY HIRES IMAGES TO PUBLISH FOLDERS
            elif output["name"] == 'copyHiRes':
                """
                Copies the high res files over to the publish sourceimages folder
                """
                try:
                    self._publish_copyHiRes_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)

                except Exception, e:
                    errors.append("Copy failed - %s" % e)

            ### IGNORE DG DOWNGRADED SHADERS
            elif output["name"] == 'dg_texture':
                pass

            ### UV XML
            elif output["name"] == 'uvxml':
                self._publish_uvXML_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)

            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! %s" % output["name"])
        progress_cb(50)
        
        ##################################################################
        ## Now iter again to force the thumbs to be done after the shaders
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            # report progress:
            progress_cb(0, "Publishing", task)
            
            if output["name"] == 'dg_texture':
                """
                Main dg_texture exporter
                """
                try:
                    self._publish_dg_texture_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == 'shd_xml':
                pass
            elif output["name"] == 'copyHiRes':
                pass
            elif output["name"] == 'uvxml':
                pass
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item!%s" % output["name"])
        progress_cb(50)

        ##################################################################
        ## if there is anything to report then add to result
        if len(errors) > 0:
            ## add result:
            results.append({"task": task, "errors": errors})
        progress_cb(100)
        return results

    def _publish_uvXML_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an Alembic cache for the specified item and publish it
        to Shotgun.
        """
        tank_type           = output["tank_type"]
        publish_template    = output["publish_template"]
        assetName           = item["name"].split('|')[-1]
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        if not 'SRFVar_' in scene_path:
            group_name      = '%s_UV_XML' % ''.join(item["name"].strip("|").split('_hrc')[0].split('_'))
        else:
            group_name      = '%s_UV_XML_SurfVar%s' % (''.join(item["name"].strip("|").split('_hrc')[0].split('_')), scene_path.split('SRFVar_')[-1].split('\\')[0])
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)

        try:
            self.parent.log_debug("Executing command: XML EXPORT PREP!")
            log(None, method = '_publish_xml_for_item', message = 'Export prep...', printToLog = False, verbose = configCONST.DEBUGGING)
            
            start = time.time()
            secpubmsg.publishmessage('UV XML', True)
            getGeohrc = [eachChild for eachChild in cmds.listRelatives(assetName, children = True) if eachChild == '%s_%s' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX)]
            geoList = [eachChild for eachChild in cmds.listRelatives(getGeohrc, children = True, ad = True) if 'Shape' not in eachChild and cmds.listRelatives(eachChild, shapes = True)]
            allGeoUVData = []
            log(None, method = '_publish_xml_for_item', message = 'Fetching UV information for xml now...', printToLog = False, verbose = configCONST.DEBUGGING)

            for eachGeo in geoList:
                #log(None, method = '_publish_xml_for_item', message = 'Processing uvs for %s...' % eachGeo, printToLog = False, verbose = configCONST.DEBUGGING)
                uvData = getUvs.getUVs(eachGeo)
                if uvData:
                    allGeoUVData.extend([uvData])

            log(None, method = '_publish_xml_for_item', message = 'Writing UV xml information to disk now...', printToLog = False, verbose = configCONST.DEBUGGING)
            uvwrite.writeUVData(assetName, allGeoUVData, publish_path)
            print 'TIME: %s' % (time.time()-start)         
            secpubmsg.publishmessage('UV XML', False)
            ## Now register with shotgun
            self._register_publish(publish_path, 
                                  group_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
        except Exception, e:
            raise TankError("Failed to export uv_xml")

    def _publish_shd_xml_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an Alembic cache for the specified item and publish it
        to Shotgun.
        """
        log(None, method = '_publish_shd_xml_for_item', message = 'Doing shd_xml', printToLog = False, verbose = configCONST.DEBUGGING)

        tank_type           = output["tank_type"]
        publish_template    = output["publish_template"]

        log(None, method = '_publish_shd_xml_for_item', message = 'tank_type: %s' % tank_type, printToLog = False, verbose = configCONST.DEBUGGING)
        log(None, method = '_publish_shd_xml_for_item', message = 'publish_template: %s' % publish_template, printToLog = False, verbose = configCONST.DEBUGGING)

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        log(None, method = '_publish_shd_xml_for_item', message = 'scene_path: %s' % scene_path, printToLog = False, verbose = configCONST.DEBUGGING)

        if not 'SRFVar_' in scene_path:
            group_name      = '%s_%s_XML' % (item["name"].strip("|").replace('_%s' % configCONST.GROUP_SUFFIX, '').replace('_', ''), configCONST.SURFACE_SHORTNAME)
        else:
            group_name      = '%s_SHD_XML_SurfVar%s' % (item["name"].strip("|").replace('_%s' % configCONST.GROUP_SUFFIX, '').replace('_', ''), configCONST.SURFACE_SHORTNAME, scene_path.split('SRFVar_')[-1].split('\\')[0])
        log(None, method = '_publish_shd_xml_for_item', message = 'group_name: %s' % group_name, printToLog = False, verbose = configCONST.DEBUGGING)

        fields              = work_template.get_fields(scene_path)
        publish_version     = fields["version"]
        # update fields with the group name:
        fields["grp_name"]  = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path        = publish_template.apply_fields(fields)
        log(None, method = '_publish_shd_xml_for_item', message = 'publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)

        try:
            secpubmsg.publishmessage('Writing Shading XML', True)
            shd_writexml.exportPrep(path = publish_path)

            secpubmsg.publishmessage('Writing Shading XML', False)
            ## Now register with shotgun
            self._register_publish(publish_path, 
                                  group_name, 
                                  sg_task, 
                                  publish_version, 
                                  tank_type,
                                  comment,
                                  thumbnail_path, 
                                  [primary_publish_path])
        except Exception, e:
            raise TankError("Failed to export xml")

    def _publish_copyHiRes_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export the highres textures from work/maya/sourceimages to publish/sourceimages.
        """
        group_name          = item["name"].strip("|")
        tank_type           = output["tank_type"]
        publish_template    = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields              = work_template.get_fields(scene_path)
        publish_version     = fields["version"]

        # update fields with the group name:
        fields["grp_name"]  = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path        = publish_template.apply_fields(fields)

        try:
            self.parent.log_debug("Executing command: XML EXPORT PREP!")
            secpubmsg.publishmessage('Copying hi res textures to publish path...', True)
            shd_lib.copyHiRes(destFolder = publish_path)
            secpubmsg.publishmessage('Copying hi res textures to publish path...', False)
        except Exception, e:
            raise TankError("Failed to copy textures")

    def _publish_dg_texture_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export downgraded textures for the texture files for models and rig use
        """

        group_name          = item["name"].strip("|")
        tank_type           = output["tank_type"]
        publish_template    = output["publish_template"]


        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields              = work_template.get_fields(scene_path)
        publish_version     = fields["version"]

        # update fields with the group name:
        fields["grp_name"]  = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path        = publish_template.apply_fields(fields)
        try:
            self.parent.log_debug("Executing command: XML EXPORT PREP!")
            secpubmsg.publishmessage('Making Downgraded Textures now...', True)
            if not shd_lib.doThumbs(path = publish_path):
                raise TankError("Failed to down grade shaders")
            secpubmsg.publishmessage('Making Downgraded Textures now...', False)
        except Exception, e:
            raise TankError("Failed to downgrade shaders")

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