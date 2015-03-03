import os
import sys

import maya.cmds as cmds
import maya.mel as mel

import sgtk
import tank
from tank import Hook
from tank import TankError
import configCONST as configCONST
import maya_secondarypublishmessage as secpubmsg
import maya_adef_lib as adef_lib
from logger import log
import maya_cam_lib as cam_lib
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
        """
        ## Make sure the scene assembly plugins are loaded
        adef_lib.loadSceneAssemblyPlugins(TankError)

        ## Instantiate the API
        tk = sgtk.sgtk_from_path(configCONST.SHOTGUN_CONFIG_PATH)

        results         = []
        gpuCaches       = []
        staticCaches    = []
        animCaches      = []

        ## Clean the animation alembic bat now for a fresh publish
        pathToBatFile   = configCONST.PATH_TO_ANIM_BAT
        if os.path.isfile(pathToBatFile):
            os.remove(pathToBatFile)

        ## PROCESS THE ITEMS into lists so we can compress down the alembic export into selected items.
        ## This saves a bunch of time because we won't be running the animated stuff over the full range
        ## of the time line for EACH item, we can do it on a larger selection.
        for task in tasks:
            item    = task["item"]
            output  = task["output"]
            errors  = []
            geoGrp  = ''

            ######################
            ## STATIC CACHES LIST
            ######################
            progress_cb(0, "Processing Scene Secondaries now...", task)
            if item["type"] == "static_caches":
                try:
                    assetName = item['name'].split('_hrc')[0]
                    ## Do a ns check on assetName and strip it
                    if ':' in assetName:
                        assetName = assetName.split(':')[-1]
                    log(app = None, method = 'execute', message = "assetName: %s" % assetName, printToLog = False, verbose = configCONST.DEBUGGING)

                    assetType = tk.shotgun.find_one('Asset', filters = [["code", "is", assetName]], fields = ['sg_asset_type'])
                    log(app = None, method = 'execute', message = "assetType: %s" % assetType, printToLog = False, verbose = configCONST.DEBUGGING)
                    if assetType:
                        if assetType['sg_asset_type'] == configCONST.SG_PROP_TYPE_NAME:
                            if item['name'] not in staticCaches:
                                staticCaches.append(item['name'])
                        elif assetType['sg_asset_type'] == configCONST.SG_ENV_TYPE_NAME:
                            ## Now process the assembly definition files as these have a difference hrc
                            ## to normal references as they exist without a top level ns in the scene.
                            geoGrp = [geoGrp for geoGrp in cmds.listRelatives(item['name'], children = True) if '_hrc' in geoGrp][0]
                            if geoGrp not in staticCaches:
                                staticCaches.append(geoGrp)
                        else:
                            pass
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            ######################
            ## ANIM CACHES LIST
            ######################
            elif item["type"] == "anim_caches":
                try:
                    assetName = item['name'].split('_hrc')[0]
                    ## Do a ns check on assetName and strip it
                    if ':' in assetName:
                        assetName = assetName.split(':')[-1]
                    log(app = None, method = 'execute', message = "assetName: %s" % assetName, printToLog = False, verbose = configCONST.DEBUGGING)

                    assetType = tk.shotgun.find_one('Asset', filters = [["code", "is", assetName]], fields = ['sg_asset_type'])
                    log(app = None, method = 'execute', message = "assetType: %s" % assetType, printToLog = False, verbose = configCONST.DEBUGGING)

                    if assetType:
                        if assetType['sg_asset_type'] == configCONST.SG_PROP_TYPE_NAME:
                            if item['name'] not in animCaches:
                                animCaches.append(item['name'])
                        elif assetType['sg_asset_type'] == configCONST.SG_CHAR_TYPE_NAME:
                            if item['name'] not in animCaches:
                                animCaches.append(item['name'])
                        elif assetType['sg_asset_type'] == configCONST.SG_ENV_TYPE_NAME:
                            ## Now process the assembly definition files as these have a difference hrc
                            ## to normal references as they exist without a top level ns in the scene.
                            geoGrp = [geoGrp for geoGrp in cmds.listRelatives(item['name'], children = True) if '_hrc' in geoGrp][0]
                            if geoGrp not in animCaches:
                                animCaches.append(geoGrp)
                        else:
                            pass
                except Exception, e:
                    errors.append("Publish failed - %s" % e)
            ######################
            ## GPU CACHES
            ######################
            elif item["type"] == "gpu_caches":
                if item['name'] not in gpuCaches:
                    gpuCaches.append(item['name'])
            ######################
            ## CAMERA
            ######################
            elif item["type"] == "camera":
                self._publish_camera_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
            ######################
            ## ANIMATION CURVES
            ######################
            elif item["type"] == "anim_atom":
                log(app = None, method = '_publish_animation_curves_for_item', message = "Processing Animation Curves now...", printToLog = False, verbose = configCONST.DEBUGGING)
                self._publish_animation_curves_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! Contact your supervisor to build a hook for this type.")

            ## if there is anything to report then add to result
            if len(errors) > 0:
                ## add result:
                results.append({"task":task, "errors":errors})

            progress_cb(100, "Done Processing INITIAL Secondaries, moving to final caching....", task)

        ## Because we don't want to continually iter through the tasks and do the same shit over and over
        ## we're setting a quick Done true or false here because I'm tired and can't think of a better way at the moment....
        staticDone      = False
        animDone        = False
        gpuDone         = False
        cachesToExport  = False
        progress_cb(0, "Processing Static, Anim, GPU and Fluid caches now...")

        log(app = None, method = '_publish_fx_caches_for_item', message = "Processing DONE. Performing Cache exports now...", printToLog = False, verbose = configCONST.DEBUGGING)
        log(app = None, method = '_publish_fx_caches_for_item', message = "gpuCaches: %s" % gpuCaches, printToLog = False, verbose = configCONST.DEBUGGING)
        log(app = None, method = '_publish_fx_caches_for_item', message = "animCaches: %s" % animCaches, printToLog = False, verbose = configCONST.DEBUGGING)
        log(app = None, method = '_publish_fx_caches_for_item', message = "staticCaches: %s" % staticCaches, printToLog = False, verbose = configCONST.DEBUGGING)

        if gpuCaches or animCaches or staticCaches:
            for task in tasks:
                item    = task["item"]
                output  = task["output"]
                errors  = []

                ## DEBUGG
                ## report progress:
                geoGrp  = ''
                ## STATIC CACHES
                if item["type"] == "static_caches":
                    if not staticDone:
                        ## Now process the publishing of the lists so we can bulk export the appropriate assets to avoid hundreds of alembic files.
                        ## STATIC CACHES
                        static      = True
                        groupName   = 'staticCaches'
                        if len(staticCaches) <= 0:
                            print 'Static cache list empty, skipping...'
                        else:
                            progress_cb(25, "Processing Static Caches now...")
                            log(app = None, method = '_publish_fx_caches_for_item', message = "Processing Static Caches now...", printToLog = False, verbose = configCONST.DEBUGGING)
                            ## Select the cache objects for static export now
                            ## and replace the current selection with this list.
                            cmds.select(staticCaches, r = True)

                            ## Do a quick check that every assembly reference marked for export as alembic is at full res
                            for each in cmds.ls(sl= True):
                                self._upResAssemblyRefs(each)

                            ## Now publish
                            self._publish_alembic_cache_for_item(groupName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, static)
                            staticDone      = True
                            cachesToExport  = True
                            progress_cb(35, "Done processing Static Caches!")

                ## ANIMATED CACHES
                elif item["type"] == "anim_caches":
                    if not animDone:
                        static      = False
                        groupName   = 'animCaches'
                        if len(animCaches) <= 0:
                            print 'Animated cache list empty, skipping...'
                        else:
                            progress_cb(45, "Processing Anim Caches now...")
                            log(app = None, method = '_publish_fx_caches_for_item', message = "Processing Anim Caches now...", printToLog = False, verbose = configCONST.DEBUGGING)
                            cmds.select(animCaches, r = True) # Select the cache objects for static export now and replace the current selection with this list.

                            ## Do a quick check that every assembly reference marked for export as alembic is at full res
                            for each in cmds.ls(sl= True):
                                self._upResAssemblyRefs(each)

                            ## Now publish
                            self._publish_alembic_cache_for_item(groupName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, static)
                            animDone        = True
                            cachesToExport  = True
                            progress_cb(50, "Done processing Anim Caches!")

                ## GPU CACHES
                elif item["type"] == "gpu_caches":
                    if not gpuDone:
                        if len(gpuCaches) <= 0:
                            print 'GPU caches list empty, skipping...'
                        else:
                            progress_cb(55, "Processing GPU Caches now...")
                            allItems        = gpuCaches
                            log(app = None, method = '_publish_fx_caches_for_item', message = "Processing GPU Caches now...", printToLog = False, verbose = configCONST.DEBUGGING)
                            ## Select the cache objects for static export now
                            ## and replace the current selection with this list.
                            cmds.select(gpuCaches, r = True)

                            ## Now publish
                            self._publish_gpu_cache_for_item(allItems, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                            gpuDone         = True
                            cachesToExport  = True
                else:
                    pass

        progress_cb(100)
        log(app = None, method = '_publish_fx_caches_for_item', message = "Cache exports finished... moving cache files now if appropriate", printToLog = False, verbose = configCONST.DEBUGGING)

        ### COPY THE CACHE FILES TO THE SERVER NOW
        ### Subprocess to copy files from the temp folder to the server
        progress_cb(0, "Copying caches to server now...")
        if cachesToExport:
            import subprocess
            CTEMP           = configCONST.TEMP_FOLDER
            BATCHNAME       = configCONST.ALEMBIC_BATCH_NAME
            progress_cb(50, "Copying caches to server now...")
            p               = subprocess.Popen(BATCHNAME, cwd=CTEMP, shell=True, bufsize=4096, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout, stderr  = p.communicate()
            # if p.returncode == 0:
            #     return results
            # else:
            #     results.append({"task":'File Copy', "errors":['Publish failed - could not copy files to the server!']})
            #     return results
            return results
        else:
            return results
        progress_cb(100, "Done...")

    def _upResAssemblyRefs(self, aRef):
        """
        Used to upres the assemblyRefs, need to double check this is even necessary
        as they wont even report as static or anim caches if they are in anything other
        than full res?!
        """
        if cmds.nodeType(aRef) == 'assemblyReference':
            ## Check to see what isn't loaded to full res for exporting.
            ## Those that are not turn them to full res now for cache exporting.
            if not cmds.assembly(aRef, query = True, active = True) == 'full':
                cmds.assembly(aRef, edit = True, active = 'full')

    def _publish_alembic_cache_for_item(self, groupName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, static):
        """
        Export an Alembic cache for the specified item and publish it to Shotgun.
        NOTE:
        Because we are not processing tasks which would give us 500 bazillion caches we have to hardset some of the naming and pathing here for the exporting.
        This way we can select the entire list of static or animated groups / meshes in the scene and use ONE alembic export for selected command instead of massive data
        through put for ALL the individual parts.
        NOTE 2:
        GroupName is handled differently than normal here because we are processing the item[] as a list after the initial task iter see the execution for this
        """
        group_name          = groupName
        tank_type           = 'Alembic Cache'
        publish_template    = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields              = work_template.get_fields(scene_path)
        publish_version     = fields["version"]

        # update fields with the group name:
        fields["grp_name"]  = group_name

        ## create the publish path by applying the fields with the publish template:
        publish_path        = publish_template.apply_fields(fields)
        log(app = None, method = 'PublishHook', message = 'publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)

        tempFolder          = configCONST.TEMP_FOLDER
        log(app = None, method = 'PublishHook', message = 'tempFolder: %s' % tempFolder, printToLog = False, verbose = configCONST.DEBUGGING)
        tempFilePath = '%s\\%s' % ( tempFolder, publish_path.replace(':', ''))

        pathToVersionDir    = '\\'.join(publish_path.split('\\')[0:-1])
        ## build and execute the Alembic export command for this item:
        if static:
            frame_start     = 1
            frame_end       = 1
        else:
            frame_start     = cmds.playbackOptions(query = True, animationStartTime = True)
            frame_end       = cmds.playbackOptions(query = True, animationEndTime = True)

        ## Exporting on selection requires the entire selection to be added with their full paths as -root flags for the export command
        ## Do this now by setting up a string and processing the selection into that string.
        rootList            = ''
        for eachRoot in cmds.ls(sl= True):
            rootList = '-root %s %s' % (str(cmds.ls(eachRoot, l = True)[0]), rootList)

        ## If the publish dir doesn't exist make one now.
        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        ## If the temp folder doesn't exist make one now
        if ':' in publish_path:
            tempFolder = '%s\\%s\\' % (tempFolder, pathToVersionDir.replace(":", ""))
        else:
            tempFolder = '%s/%s/' % (tempFolder, pathToVersionDir)

        log(app = None, method = 'PublishHook', message = 'tempFolder: %s' % tempFolder, printToLog = False, verbose = configCONST.DEBUGGING)
        if not os.path.isdir(os.path.dirname(tempFolder)):
            os.makedirs(os.path.dirname(tempFolder))


        ## Now build the final export command to use with the python AbcExport
        abc_export_cmd = "-attr smoothed -attr dupAsset -attr mcAssArchive -attr version -ro -uvWrite -wholeFrameGeo -worldSpace -writeVisibility -fr %d %d %s -file %s" % (frame_start, frame_end, rootList, tempFilePath.replace("\\", "/"))
        log(app = None, method = 'PublishHook', message = 'abc_export_cmd: %s' % abc_export_cmd, printToLog = False, verbose = configCONST.DEBUGGING)

        ## add to bat file
        ## Now write the bat file out for the file copy
        pathToBatFile = configCONST.PATH_TO_ANIM_BAT
        log(app = None, method = 'PublishHook', message = 'pathToBatFile: %s' % pathToBatFile, printToLog = False, verbose = configCONST.DEBUGGING)
        if not os.path.isfile(pathToBatFile):
            outfile = open(pathToBatFile, "w")
        else:
            outfile = open(pathToBatFile, "a")
        log(app = None, method = 'PublishHook', message = 'copy %s %s\n' % (tempFolder, publish_path), printToLog = False, verbose = configCONST.DEBUGGING)
        outfile.write('copy %s %s\n' % (tempFilePath, publish_path))
        outfile.close()

        try:
            self.parent.log_debug("Executing command: %s" % abc_export_cmd)
            secpubmsg.publishmessage('Exporting %s to alembic cache now to %s' % (group_name, publish_path), True)

            cmds.AbcExport(verbose = False, j = abc_export_cmd)
        except Exception, e:
            raise TankError("Failed to export Alembic Cache!!")

        ## Finally, register this publish with Shotgun
        self._register_publish(publish_path,
                               '%s_ABC' % group_name,
                               sg_task,
                               publish_version,
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])
        secpubmsg.publishmessage('Exporting %s to alembic cache now to %s' % (group_name, publish_path), False)

    def _publish_gpu_cache_for_item(self, items, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        """
        group_name          = 'gpuCaches'
        items               = items
        tank_type           = 'Alembic Cache'
        publish_template    = output["publish_template"]

        ## Get the current scene path and extract fields from it using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields              = work_template.get_fields(scene_path)
        publish_version     = fields["version"]
        ## Update fields with the group name:
        fields["grp_name"]  = group_name
        ## Create the publish path by applying the fields with the publish template:
        publish_path        = publish_template.apply_fields(fields)
        fileName            = os.path.splitext(publish_path)[0].split('\\')[-1]
        fileDir             = '/'.join(publish_path.split('\\')[0:-1])
        pathToVersionDir    = '\\'.join(publish_path.split('\\')[0:-1])

        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        try:
            self.parent.log_debug("Executing GPU Cache export now to: \n\t\t%s" % publish_path)
            secpubmsg.publishmessage('Exporting gpu now to %s\%s' % (fileDir, fileName), True)

            for each in items:
                ## Now do the gpu cache export for each of the items
                try:
                    mel.eval("gpuCache -startTime 1 -endTime 1 -optimize -optimizationThreshold 40000 -directory \"%s\" \"%s\";" % (fileDir, each))
                except:
                    cmds.warning('FAILED TO PUBLISH GPU CACHE: %s' %  each)

        except Exception, e:
            raise TankError("Failed to export gpu cache file.. check for corrupt assembly references!")

        ## Finally, register this publish with Shotgun
        self._register_publish(publish_path,
                               '%s_GPU' % group_name,
                               sg_task,
                               publish_version,
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])

        secpubmsg.publishmessage('Exporting gpu now to %s\%s' % (fileDir, fileName), False)

    def _publish_camera_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export the camera
        """
        ## Do the regular Shotgun processing now
        cam_name            = item['name']
        tank_type           = 'Maya Scene'
        publish_template    = output["publish_template"]

        ## Get the current scene path and extract fields from it using the work template:
        scene_path          = os.path.abspath(cmds.file(query=True, sn= True))
        fields              = work_template.get_fields(scene_path)
        publish_version     = fields["version"]
        ## Update fields with the group name:
        fields["cam_name"]  = cam_name
        ## Create the publish path by applying the fields with the publish template:
        publish_path        = publish_template.apply_fields(fields)
        pathToVersionDir    = '\\'.join(publish_path.split('\\')[0:-1])

        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        if cmds.objExists('BAKE_CAM_hrc'):
            cmds.delete('BAKE_CAM_hrc')

        log(app = None, method = '_publish_camera_for_item', message = "Baking %s now..." % cam_name, printToLog = False, verbose = configCONST.DEBUGGING)

        secpubmsg.publishmessage('Exporting camera now..', True)
        cam_lib._bakeCamera(cam_name)

        cmds.select('BAKE_CAM_hrc', r = True)
        cmds.file(publish_path, options = "v=0;", typ = "mayaAscii", es = True, force= True)
        ## Finally, register this publish with Shotgun
        self._register_publish(publish_path,
                               '%s_CAM' % cam_name,
                               sg_task,
                               publish_version,
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])

        secpubmsg.publishmessage('Exporting camera now..', False)
        if cmds.objExists('BAKE_CAM_hrc'):
            cmds.delete('BAKE_CAM_hrc')

    def _publish_animation_curves_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Method for publishing animation curves...
        """
        # Get the current scene path and extract fields from it
        # Using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn = True)) # I:\bubblebathbay\episodes\ep106\ep106_sh030\FX\work\maya\ep106sh030.v025.ma
        log(app = None, method = '_publish_animation_curves_for_item', message =  'scene_path: %s' % scene_path, printToLog = False, verbose = configCONST.DEBUGGING)

        fields = work_template.get_fields(scene_path) # {'Shot': u'ep106_sh030', 'name': u'ep106sh030', 'Sequence': u'ep106', 'Step': u'FX', 'version': 25, 'group_name': u'spriteSpray_nParticle_T_RShape'}

        ############################################################

        ## Do the regular Shotgun processing now
        group_name = '%s_ATOM' % fields['name'] # ep106sh030_animCurves_XML
        log(app = None, method = '_publish_animation_curves_for_item', message =  'group_name: %s' % group_name, printToLog = False, verbose = configCONST.DEBUGGING)

        tank_type = 'Maya Scene' # Maya Scene
        log(app = None, method = '_publish_animation_curves_for_item', message =  'tank_type: %s' % tank_type, printToLog = False, verbose = configCONST.DEBUGGING)

        publish_template = output["publish_template"] # <Sgtk TemplatePath maya_shot_fxRenderFinal: episodes/{Sequence}/{Shot}//FxLayers/R{version}>
        log(app = None, method = '_publish_animation_curves_for_item', message =  'publish_template: %s' % publish_template, printToLog = False, verbose = configCONST.DEBUGGING)

        ############################################################

        publish_version         = fields["version"]

        ## Update fields with the group_name
        fields["group_name"]    = group_name

        ## Get sequence and shot name from field directly
        epShotName              = fields["name"]

        ## create the publish path by applying the fields
        ## with the publish template:
        publish_path            = publish_template.apply_fields(fields)
        pathToVersionDir        = '\\'.join(publish_path.split('\\')[0:-1])
        log(app = None, method = '_publish_animation_curves_for_item', message = 'publish_path: %s' % publish_path, printToLog = False, verbose = configCONST.DEBUGGING)
        log(app = None, method = '_publish_animation_curves_for_item', message = 'pathToVersionDir: %s' % pathToVersionDir, printToLog = False, verbose = configCONST.DEBUGGING)

        if not os.path.isdir(pathToVersionDir):
            os.makedirs(pathToVersionDir)
        ################################################################################################################
        ## ATOM EXPORT
        ## Get min/max time
        secpubmsg.publishmessage('Exporting ATOM now..', True)
        min = cmds.playbackOptions(min = True, q = True)
        max = cmds.playbackOptions(max = True, q = True)

        ## Force ATOM UI to pop out
        mel.eval('ExportAnimOptions;')

        ## Get scene stuffs except for default cameras, and constraints...
        assemblies = [x for x in cmds.ls(assemblies = True) if x not in ['persp', 'top', 'front', 'side']]
        allDescendents = []
        for root in assemblies:
            descendents = cmds.listRelatives(root, allDescendents = True, fullPath = True)
            if descendents:
                for each in descendents:
                    if not cmds.nodeType(each) in ['parentConstraint', 'pointConstraint', 'orientConstraint', 'aimConstraint', 'scaleConstraint', 'pointOnPolyConstraint']:
                        allDescendents.append(each)
        assemblies.extend(allDescendents)
        cmds.select(assemblies, replace = True)

        ## Perform ATOM Export
        cmds.file(  publish_path,
                    force = True,
                    type = 'atomExport',
                    exportSelected = True,
                    options = 'precision=8;statics=1;baked=1;sdk=0;constraint=0;animLayers=1;selected=selectedOnly;whichRange=2;range=%s:%s;hierarchy=none;controlPoints=0;useChannelBox=1;options=keys;copyKeyCmd=-animation objects -time >%s:%s> -float >%s:%s> -option keys -hierarchy none -controlPoints 0 ' % (min, max, min, max, min, max),
                    )

        ## Delete ATOM UI after export
        if cmds.window('OptionBoxWindow', exists = True):
            cmds.deleteUI('OptionBoxWindow', window = True)
        ################################################################################################################

        ## Finally, register publish to shotgun...
        self._register_publish(publish_path,
                               group_name,
                               sg_task,
                               publish_version,
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])
        secpubmsg.publishmessage('Exporting ATOM now..', False)

    def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths = None):
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