import os, tank, time, logging
import maya.cmds as cmds
from tank import Hook
from tank import TankError
from apps.app_logger import log
import config_constants as configCONST
import shotgun.sg_shd_lib as shd_lib
import xml_export.shd_writeXML as shd_writexml
import xml_export.uv_writeXML as uvwrite
import xml_export.uv_getUVs as getUvs
import shotgun.sg_secondarypublishmessage as secpubmsg
logger = logging.getLogger(__name__)


class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_publish_path, progress_cb, **kwargs):
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

                except Exception as e:
                    errors.append("Publish failed - {}".format(e))

            ### COPY HIRES IMAGES TO PUBLISH FOLDERS
            elif output["name"] == 'copyHiRes':
                """
                Copies the high res files over to the publish sourceimages folder
                """
                try:
                    self._publish_copyHiRes_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)

                except Exception as e:
                    errors.append("Copy failed - {}".format(e))

            ### IGNORE DG DOWNGRADED SHADERS
            elif output["name"] == 'dg_texture':
                pass

            ### UV XML
            elif output["name"] == 'uvxml':
                self._publish_uvXML_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)

            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! {}".format(output["name"]))
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
                except Exception as e:
                    errors.append("Publish failed - {}".format(e))
            elif output["name"] == 'shd_xml':
                pass
            elif output["name"] == 'copyHiRes':
                pass
            elif output["name"] == 'uvxml':
                pass
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item!{}".format(output["name"]))
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
        tank_type = output["tank_type"]
        publish_template  = output["publish_template"]
        assetName = item["name"].split('|')[-1]
        log(None, method = '_publish_xml_for_item', message = 'assetName: {}'.format(assetName, outputToLogFile = False, verbose = configCONST.DEBUGGING))
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        if not 'SRFVar_' in scene_path:
            group_name = '{}_UV_XML'.format(''.join(item["name"].strip("|").split('_hrc')[0].split('_')))
        else:
            group_name = '{}_UV_XML_SurfVar{}'.format((''.join(item["name"].strip("|").split('_hrc')[0].split('_')), scene_path.split('SRFVar_')[-1].split('\\')[0]))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)

        try:
            self.parent.log_debug("Executing command: XML EXPORT PREP!")
            log(None, method = '_publish_xml_for_item', message = 'Export prep...', outputToLogFile = False, verbose = configCONST.DEBUGGING)
            
            start = time.time()
            secpubmsg.publishmessage('UV XML', True)
            getGeohrc = [eachChild for eachChild in cmds.listRelatives(assetName, children = True) if eachChild == '{}_{}'.format((configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX))]
            try:
                geoList = [eachChild for eachChild in cmds.listRelatives(getGeohrc, children = True, ad = True) if 'Shape' not in eachChild and cmds.listRelatives(eachChild, shapes = True)]
            except:
                geoList = []

            allGeoUVData = []
            log(None, method = '_publish_xml_for_item', message = 'Fetching UV information for xml now...', outputToLogFile = False, verbose = configCONST.DEBUGGING)
            if geoList:
                for eachGeo in geoList:
                    uvData = getUvs.getUVs(eachGeo)
                    if uvData:
                        allGeoUVData.extend([uvData])

                log(None, method = '_publish_xml_for_item', message = 'Writing UV xml information to disk now...', outputToLogFile = False, verbose = configCONST.DEBUGGING)
                uvwrite.writeUVData(assetName, allGeoUVData, publish_path)
                print('TIME: {}'.format((time.time()-start)))
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
            else:
                secpubmsg.publishmessage('UV XML FAILED no geoList found! Is your heirachy setup correctly? And your grps are named correctly???', False)
        except Exception as e:
            raise TankError("Failed to export uv_xml")

    def _publish_shd_xml_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export an Alembic cache for the specified item and publish it
        to Shotgun.
        """
        logger.info('Doing _publish_shd_xml_for_item')

        tank_type = output["tank_type"]
        publish_template  = output["publish_template"]

        logger.info('tank_type: {}'.format(tank_type))
        logger.info('publish_template: {}'.format(publish_template))

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        logger.info('scene_path: {}'.format(scene_path))

        if not 'SRFVar_' in scene_path:
            group_name = '{}_{}_XML'.format((item["name"].strip("|").replace('_{}'.format(configCONST.GROUP_SUFFIX, '').replace('_', '')), configCONST.SURFACE_SHORTNAME))
        else:
            group_name = '{}_SHD_XML_SurfVar{}'.format((item["name"].strip("|").replace('_{}'.format(configCONST.GROUP_SUFFIX, '')).replace('_', ''), configCONST.SURFACE_SHORTNAME, scene_path.split('SRFVar_')[-1].split('\\')[0]))
        logger.info('group_name: {}'.format(group_name))

        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)
        logger.info('publish_path: {}'.format(publish_path))

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
        except Exception as e:
            raise TankError("Failed to export xml")

    def _publish_copyHiRes_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export the highres textures from work/maya/sourceimages to publish/sourceimages.
        """
        group_name = item["name"].strip("|")
        tank_type = output["tank_type"]
        publish_template  = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path  = publish_template.apply_fields(fields)

        try:
            self.parent.log_debug("Executing command: XML EXPORT PREP!")
            secpubmsg.publishmessage('Copying hi res textures to publish path...', True)
            shd_lib.copyHiRes(destFolder = publish_path)
            secpubmsg.publishmessage('Copying hi res textures to publish path...', False)
        except Exception as e:
            raise TankError("Failed to copy textures")

    def _publish_dg_texture_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export downgraded textures for the texture files for models and rig use
        """

        group_name = item["name"].strip("|")
        tank_type = output["tank_type"]
        publish_template  = output["publish_template"]


        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path  = publish_template.apply_fields(fields)
        try:
            self.parent.log_debug("Executing command: XML EXPORT PREP!")
            secpubmsg.publishmessage('Making Downgraded Textures now...', True)
            if not shd_lib.doThumbs(path = publish_path):
                raise TankError("Failed to down grade shaders")
            secpubmsg.publishmessage('Making Downgraded Textures now...', False)
        except Exception as e:
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
            print("================DEP====================")
            print('{} dependencies: \n\t{}'.format((path, dependency_paths[0])))
            print("========================================")
        return sg_data