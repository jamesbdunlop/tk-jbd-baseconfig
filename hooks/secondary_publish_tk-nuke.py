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
import shutil
import nuke

import tank
from tank import Hook
from tank import TankError

class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """
            
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_task, primary_publish_path, progress_cb, **kwargs):
        """
        Main hook entry point
        :param tasks:                   List of secondary tasks to be published.  Each task is a 
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
                        
        :param work_template:           template
                                        This is the template defined in the config that
                                        represents the current work file
               
        :param comment:                 String
                                        The comment provided for the publish
                        
        :param thumbnail:               Path string
                                        The default thumbnail provided for the publish
                        
        :param sg_task:                 Dictionary (shotgun entity description)
                                        The shotgun task to use for the publish    
                        
        :param primary_publish_path:    Path string
                                        This is the path of the primary published file as returned
                                        by the primary publish hook
                        
        :param progress_cb:             Function
                                        A progress callback to log progress during pre-publish.  Call:
                                        
                                            progress_cb(percentage, msg)
                                             
                                        to report progress to the UI
                        
        :param primary_task:            The primary task that was published by the primary publish hook.  Passed
                                        in here for reference.  This is a dictionary in the same format as the
                                        secondary tasks above.
        
        :returns:                       A list of any tasks that had problems that need to be reported 
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

        # it's important that tasks for render output are processed
        # before tasks for quicktime output, so let's group the
        # task list by output.  This can be controlled through the
        # configuration but we shouldn't rely on that being set up 
        # correctly!
        output_order = ["render", "quicktime", 'AvidQuicktime']
        tasks_by_output = {}
        for task in tasks:
            output_name = task["output"]["name"]
            tasks_by_output.setdefault(output_name, list()).append(task)
            if output_name not in output_order:
                output_order.append(output_name)

        # make sure we have any apps required by the publish process:
        write_node_app = None
        if tasks_by_output.get("render") or tasks_by_output.get("quicktime") or tasks_by_output.get("AvidQuicktime"):
            # we will need the write node app if we have any render outputs to validate
            write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
            if not write_node_app:
                raise TankError("Unable to publish Shotgun Write Nodes without the tk-nuke-writenode app!")

        review_submission_app = None
        if tasks_by_output.get("quicktime"):
            # If we have the tk-multi-reviewsubmission app we can create versions
            review_submission_app = self.parent.engine.apps.get("tk-multi-reviewsubmission")
            if not review_submission_app:
                raise TankError("Unable to publish Review Versions without the tk-multi-reviewsubmission app!")

        # Keep of track of what has been published in shotgun
        # this is needed as input into the review creation code...
        render_publishes = {}

        # process outputs in order:
        for output_name in output_order:
            
            # process each task for this output:
            for task in tasks_by_output.get(output_name, []):
            
                # keep track of our errors for this task
                errors = []
    
                # report progress:
                progress_cb(0.0, "Publishing", task)
            
                if output_name == "render":
                    # Publish the rendered output for a Shotgun Write Node

                    # each publish task is connected to a nuke write node
                    # this value was populated via the scan scene hook
                    write_node = task["item"].get("other_params", dict()).get("node")
                    if not write_node:
                        raise TankError("Could not determine nuke write node for item '%s'!" % str(task))
        
                    # publish write-node rendered sequence                
                    try:
                        (sg_publish, thumbnail_path) = self._publish_write_node_render(task, 
                                                                                       write_node, 
                                                                                       write_node_app, 
                                                                                       primary_publish_path, 
                                                                                       sg_task, 
                                                                                       comment, 
                                                                                       progress_cb)
                        
                        # keep track of our publish data so that we can pick it up later in review
                        render_publishes[ write_node.name() ] = (sg_publish, thumbnail_path)
                    except Exception, e:
                        errors.append("Publish failed - %s" % e)
    
                elif output_name == "quicktime":
                    # Publish the reviewable quicktime movie for a Shotgun Write Node
    
                    # each publish task is connected to a nuke write node
                    # this value was populated via the scan scene hook
                    write_node = task["item"].get("other_params", dict()).get("node")
                    if not write_node:
                        raise TankError("Could not determine nuke write node for item '%s'!" % str(task))
                    
                    # Submit published sequence to Screening Room
                    try:
                        # pick up sg data from the render dict we are maintianing
                        # note: we assume that the rendering tasks always happen
                        # before the review tasks inside the publish... 
                        (sg_publish, thumbnail_path) = render_publishes[ write_node.name() ]
                        
                        self._send_to_screening_room (
                            write_node,
                            write_node_app,
                            review_submission_app,
                            sg_publish,
                            sg_task,
                            comment,
                            thumbnail_path,
                            progress_cb
                        )

                    except Exception, e:
                        errors.append("Submit to Screening Room failed - %s" % e)
                
                elif output_name == "AvidQuicktime":
                    # Publish the reviewable quicktime movie for a Shotgun Write Node

                    # each publish task is connected to a nuke write node
                    # this value was populated via the scan scene hook
                    write_node = task["item"].get("other_params", dict()).get("node")
                    if not write_node:
                        raise TankError("Could not determine nuke write node for item '%s'!" % str(task))
        
                    # Submit published sequence to Screening Room
                    try:
                        # pick up sg data from the render dict we are maintianing
                        # note: we assume that the rendering tasks always happen
                        # before the review tasks inside the publish... 
                        (sg_publish, thumbnail_path) = render_publishes[ write_node.name() ]

                        self._createAvidMov(
                            task["output"],
                            primary_publish_path,
                            write_node,
                            write_node_app,
                            review_submission_app,
                            sg_publish,
                            sg_task,
                            comment,
                            thumbnail_path,
                            progress_cb,
                            
                        )

                    except Exception, e:
                        errors.append("Avid QT Creation Failed - %s" % e)
                else:
                    # unhandled output type!
                    errors.append("Don't know how to publish this item! SecondaryPublishFail")
    
                # if there is anything to report then add to result
                if len(errors) > 0:
                    # add result:
                    results.append({"task":task, "errors":errors})
    
                # task is finished
                progress_cb(100)            
        
        return results

    def _createAvidMov(self, output, primary_publish_path, write_node, write_node_app, review_submission_app, sg_publish, sg_task, comment, thumbnail_path, progress_cb):
        pathToFFMpeg = r'\\192.168.5.253\BBB_main\bbb\t\dev_installers\ffmpeg\bin\ffmpeg.exe'
        options = '-r 25'
        inbetweenOptions = '-vf scale=1280:720 -vcodec dnxhd -b:v 90M'
        inputSeq = '%s' % sg_publish['path']['local_path']
        outputPath = output['publish_template']
        sequence = nuke.root()['name'].value().split('/')[3]
       
        fields =  {}
        fields['Sequence'] = sequence
        fields['Shot'] = sg_publish['entity']['name']
        fields['name'] = sg_publish['name']
        fields['version'] = sg_publish['version_number']
        finalOutputPath = r'%s' % outputPath.apply_fields(fields)
        #K:\bubblebathbay\episodes\eptst\eptst_sh001\Avid\R028\eptst_sh001_test_v028.mov
        outputFolder = os.path.dirname(finalOutputPath.replace('/', '\\'))
        #print outputFolder
        
        ## put it all together for ffmpeg
        cmd = '%s %s -i \"%s\" %s \"%s\"' % (pathToFFMpeg, options, inputSeq, inbetweenOptions, finalOutputPath)
        #print cmd
        ## Check for folder ...
        if not os.path.isdir(outputFolder):
            os.mkdir(outputFolder)
        
        os.system(cmd)
        
        ### NOW REGISTER THE PUBLISH
        publish_name = '%s_v%s_AvidMov' %( sg_publish['entity']['name'], sg_publish['version_number'])
        publish_version = sg_publish['version_number']
        tank_type = 'Quicktime'

        # register the publish:
        self._register_publish(finalOutputPath, 
                                publish_name, 
                                sg_task, 
                                publish_version, 
                                tank_type,
                                comment,
                                thumbnail_path, 
                                [primary_publish_path])

    def _send_to_screening_room(self, write_node, write_node_app, review_submission_app, sg_publish, sg_task, comment, thumbnail_path, progress_cb):
        """
        Take a write node's published files and run them through the
        review_submission app to get a movie and Shotgun Version.
        """
        render_path = write_node_app.get_node_render_path(write_node)
        render_template = write_node_app.get_node_render_template(write_node)
        publish_template = write_node_app.get_node_publish_template(write_node)                        
        render_path_fields = render_template.get_fields(render_path)

        review_submission_app.render_and_submit(
            publish_template,
            render_path_fields,
            int(nuke.root()["first_frame"].value()),
            int(nuke.root()["last_frame"].value()),
            [sg_publish],
            sg_task,
            comment,
            thumbnail_path,
            progress_cb,
        )

    def _publish_write_node_render(self, task, write_node, write_node_app, published_script_path, sg_task, comment, progress_cb):
        """
        Publish render output for write node
        """
 
        if write_node_app.is_node_render_path_locked(write_node):
            # this is a fatal error as publishing would result in inconsistent paths for the rendered files!
            raise TankError("The render path is currently locked and does not match match the current Work Area.")
 
        progress_cb(10, "Finding renders")
 
        # get info we need in order to do the publish:
        render_path = write_node_app.get_node_render_path(write_node)
        render_files = write_node_app.get_node_render_files(write_node)
        render_template = write_node_app.get_node_render_template(write_node)
        publish_template = write_node_app.get_node_publish_template(write_node)                        
        tank_type = write_node_app.get_node_tank_type(write_node)
        
        # publish (copy files):
        
        progress_cb(25, "Copying files")
        
        for fi, rf in enumerate(render_files):
            
            progress_cb(25 + (50*(len(render_files)/(fi+1))))
            
            # construct the publish path:
            fields = render_template.get_fields(rf)
            fields["TankType"] = tank_type
            target_path = publish_template.apply_fields(fields)

            # copy the file
            try:
                target_folder = os.path.dirname(target_path)
                self.parent.ensure_folder_exists(target_folder)
                self.parent.copy_file(rf, target_path, task)
            except Exception, e:
                raise TankError("Failed to copy file from %s to %s - %s" % (rf, target_path, e))
            
        progress_cb(40, "Publishing to Shotgun")
            
        # use the render path to work out the publish 'file' and name:
        render_path_fields = render_template.get_fields(render_path)
        render_path_fields["TankType"] = tank_type
        publish_path = publish_template.apply_fields(render_path_fields)
            
        # construct publish name:
        publish_name = ""
        rp_name = render_path_fields.get("name")
        rp_channel = render_path_fields.get("channel")
        if not rp_name and not rp_channel:
            publish_name = "Publish"
        elif not rp_name:
            publish_name = "Channel %s" % rp_channel
        elif not rp_channel:
            publish_name = rp_name
        else:
            publish_name = "%s, Channel %s" % (rp_name, rp_channel)
        
        publish_version = render_path_fields["version"]
            
        # get/generate thumbnail:
        thumbnail_path = write_node_app.generate_node_thumbnail(write_node)
            
        # register the publish:
        sg_publish = self._register_publish(publish_path, 
                                            publish_name, 
                                            sg_task, 
                                            publish_version, 
                                            tank_type,
                                            comment,
                                            thumbnail_path, 
                                            [published_script_path])
        
        return sg_publish, thumbnail_path

    def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths):
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
        
        return sg_data
        






