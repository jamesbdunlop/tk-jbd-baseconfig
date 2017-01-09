import os, shutil
import maya.cmds as cmds
import maya.mel as mel
import tank
from tank import Hook
from tank import TankError
from logger import log
import shotgun.sg_adef_lib as adef_lib
import tk_findhumanuserid as fhu
import shotgun.sg_secondarypublishmessage as secpubmsg
import configCONST as configCONST
reload(adef_lib)

# TODO register these as deps
# TODO add ztl publishing
# TODO ADD 2nd for ZBRUSH main ztl file, built from the os.listdir for the Zbrush folder in the modelling context

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
        """
        results = []
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            # report progress:
            progress_cb(0, "Publishing", task)

            if output["name"] == "GoZ_ma":
                try:
                    secpubmsg.publishmessage('GOZ EXPORT -ma %s' % item["name"], True)
                    self._publish_goZMaya_for_item(item, output, work_template, sg_task, comment, thumbnail_path, progress_cb)
                    secpubmsg.publishmessage('GOZ EXPORT -ma %s' % item["name"], False)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == "GoZ_ztn":
                try:
                    secpubmsg.publishmessage('GOZ EXPORT -ztn %s' % item["name"], True)
                    self._publish_goZ_archive_for_item(item, output, work_template, sg_task, comment, thumbnail_path, progress_cb)
                    secpubmsg.publishmessage('GOZ EXPORT -ztn %s' % item["name"], False)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            elif output["name"] == "zbrush_ztl":
                try:
                    secpubmsg.publishmessage('GOZ EXPORT zbrush ztl %s' % item["name"], True)
                    self._publish_zbrushZTL_for_item(item, output, work_template, sg_task, comment, thumbnail_path, progress_cb)
                    secpubmsg.publishmessage('GOZ EXPORT zbrush ztl %s' % item["name"], False)
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! Check your asset_step.yml??")

            ## if there is anything to report then add to result
            if len(errors) > 0:
                ## add result:
                results.append({"task":task, "errors":errors})
            progress_cb(100)

        return results

    def _publish_goZMaya_for_item(self, item, output, work_template, sg_task, comment, thumbnail_path, progress_cb):
        """
        """
        tank_type = output["tank_type"]
        publish_template = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        goZName = item["name"].strip("|")
        fields["grp_name"] = goZName

        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path        = publish_template.apply_fields(fields)

        ## The default path for Zbrush caches...
        goZPath = configCONST.GOZ_PUBLIC_CACHEPATH

        ## If the publish dir doesn't exist make one now.
        if not os.path.isdir(publish_path):
            os.mkdir(publish_path)

        try:
            fileSrcPath = os.path.join(goZPath, '%s.ma' % goZName)
            fileDestPath = os.path.join(publish_path, '%s.ma' % goZName)
            ## Now copy the file from the cache to the publish
            shutil.copyfile(fileSrcPath, fileDestPath)
        except Exception, e:
            raise TankError("Failed to export GoZ ma file %s" % goZName)

    def _publish_goZ_archive_for_item(self, item, output, work_template, sg_task, comment, thumbnail_path, progress_cb):
        """
        """
        tank_type = output["tank_type"]
        publish_template = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        goZName = item["name"].strip("|")
        fields["grp_name"] = goZName

        ## create the publish path by applying the fields
        ## with the publish template:
        publish_path        = publish_template.apply_fields(fields)

        ## The default path for Zbrush caches...
        goZPath = configCONST.GOZ_PUBLIC_CACHEPATH

        ## If the publish dir doesn't exist make one now.
        if not os.path.isdir(publish_path):
            os.mkdir(publish_path)

        try:
            ## Do the ztn files first
            fileSrcPath = os.path.join(goZPath, '%s.ztn' % goZName)
            fileDestPath = os.path.join(publish_path, '%s.ztn' % goZName)
            ## Now copy the file from the cache to the publish
            shutil.copyfile(fileSrcPath, fileDestPath)
        except Exception, e:
            cmds.warning('ZTN fileSrcPath: %s' % fileSrcPath)
            cmds.warning('No ZTN for %s check script editor for details.' % goZName)


        try:
            ## Now do the ZTL files
            fileSrcPath = os.path.join(goZPath, '%s.ZTL' % goZName)
            if os.path.isfile(fileSrcPath):
                fileDestPath = os.path.join(publish_path, '%s.ZTL' % goZName)
                ## Now copy the file from the cache to the publish
                shutil.copyfile(fileSrcPath, fileDestPath)
            else:
                cmds.warning('ZTL fileSrcPath: %s' % fileSrcPath)
                cmds.warning('No ZTL for %s check script editor for details.' % goZName)
        except Exception, e:
            raise TankError("Failed to export GoZ ztl file %s" % goZName)

    def _publish_zbrushZTL_for_item(self, item, output, work_template, sg_task, comment, thumbnail_path, progress_cb):
        """
        This takes items from the zbrush subfolder for publishing
        """
        tank_type = output["tank_type"]
        publish_template = output["publish_template"]
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        # update fields with the group name:
        zbrushName = item["name"].strip("|")
        fields["grp_name"] = zbrushName
        ## create the publish path by applying the fields
        ## with the publish template:
        publish_path        = publish_template.apply_fields(fields)
        ## If the publish dir doesn't exist make one now.
        if not os.path.isdir(publish_path):
            os.mkdir(publish_path)
        ## Scan the zbrush folder if it exists
        zbrushdir       = os.path.join((scene_path.split("maya%s" % os.path.sep)[0]), 'zbrush')
        fileSrcPath     = os.path.join(zbrushdir, zbrushName)
        fileDestPath    = os.path.join(publish_path, zbrushName)
        try:
            ## Now copy the file from the cache to the publish
            shutil.copyfile(fileSrcPath, fileDestPath)
        except Exception, e:
            cmds.warning('ZTL source path %s' % fileSrcPath)
            cmds.warning('ZTL dest path %s' % fileDestPath)
            cmds.warning('No ZTL for %s check script editor for details' % zbrushName)

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
            "published_file_type": tank_type
        }

        getHumanUser = fhu._returnUserID()
        if getHumanUser:
            args['created_by'] = {'type': 'HumanUser', 'id': getHumanUser}
            args['updated_by'] = {'type': 'HumanUser', 'id': getHumanUser}

        # register publish;
        sg_data = tank.util.register_publish(**args)
        if dependency_paths:
            print "================DEP===================="
            print '%s dependencies: \n\t%s' % (path, dependency_paths[0])
            print "========================================"
        return sg_data