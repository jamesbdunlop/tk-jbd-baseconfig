import os, sgtk, logging
import maya.cmds as cmds
import maya.mel as mel
from tank import Hook
from tank import TankError
import config_constants as configCONST
import shotgun.sg_adef_lib as adef_lib
import shotgun.sg_cam_lib as cam_lib
import hooks.multi_publish.maya.maya_RegisterPublish as regPub
logger = logging.getLogger(__name__)


class PublishHook(Hook):
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_publish_path, progress_cb, **kwargs):
        results  = []
        ## Make sure the scene assembly plugins are loaded
        adef_lib.loadSceneAssemblyPlugins(TankError)
        logger.info("Alembic Plugins loaded successfully")

        ## Instantiate the API
        tk = sgtk.sgtk_from_path(configCONST.SHOTGUN_CONFIG_PATH)

        ## Clean the animation alembic bat now for a fresh publish
        pathToBatFile = configCONST.PATH_TO_ANIM_BAT
        if os.path.isfile(pathToBatFile):
            os.remove(pathToBatFile)

        ## Build the asset lists for a nice quick clean selection for exporting in one hit as opposed to individual items
        staticCaches, animCaches, gpuCaches = self._sortAlembicCaches(tk=tk, tasks=tasks)
        logger.info("gpuCaches: {}".format(gpuCaches))
        logger.info("staticCaches: {}".format(staticCaches))
        logger.info("animCaches: {}".format(animCaches))

        progress_cb(0, "Processing Static, Animation, GPU Alembic now...")
        cacheTasks = {
                     'staticCaches': [],
                     'animCaches': [],
                     'gpuCaches': [],
                     }
        ## Do the publishing tasks now.
        for task in tasks:
            item = task["item"]
            output = task["output"]
            ## Publish the camera now if it is ready to go
            if item["type"] == configCONST.CAMERA_CACHE:
                self._publish_camera_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb),
            ## Sort the cache tasks to a single item for processing so we don't repeat. We will process this dictionary next.
            if item["type"] == configCONST.STATIC_CACHE:
                if not cacheTasks['staticCaches']:
                    cacheTasks['staticCaches'].append(item)
            elif item["type"] == configCONST.ANIM_CACHE:
                if not cacheTasks['animCaches']:
                    cacheTasks['animCaches'].append(item)
            elif item["type"] == configCONST.GPU_CACHE:
                if not cacheTasks['gpuCaches']:
                    cacheTasks['gpuCaches'].append(item)
        ## ABC
        ## Do the cache tasks just once now as we are selecting a full group of objects for export instead of each item/task found
        for cacheTask, cacheData in cacheTasks.items():
            if cacheData:
                if cacheData[0]["type"] == configCONST.STATIC_CACHE:
                    isStatic = True
                    cacheGroup = staticCaches
                    cacheName = 'staticCaches'
                    cmds.select(cacheGroup, r=True)
                    ## Do a quick check that every assembly reference marked for export as alembic is at full res
                    for each in cmds.ls(sl= True):
                        self._upResAssemblyRefs(each)
                    self._publish_alembic_cache_for_item(cacheName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, isStatic)
                    cachesToTransfer = True
                elif cacheData[0]["type"] == configCONST.ANIM_CACHE:
                    isStatic = False
                    cacheGroup = animCaches
                    cacheName = 'animCaches'
                    cmds.select(cacheGroup, r=True)
                    ## Do a quick check that every assembly reference marked for export as alembic is at full res
                    for each in cmds.ls(sl= True):
                        self._upResAssemblyRefs(each)
                    self._publish_alembic_cache_for_item(cacheName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, isStatic)
                    cachesToTransfer = True
                elif cacheData[0]["type"] == configCONST.GPU_CACHE:
                    isStatic = False
                    cacheGroup = gpuCaches
                    cacheName = 'gpuCaches'
                    cmds.select(cacheGroup, r=True)
                    self._publish_gpu_cache_for_item(cacheGroup, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                    cachesToTransfer = True

        progress_cb(100)
        results = self._transferCachesToServer(cachesToTransfer, progress_cb, results)
        return results

    def _transferCachesToServer(self, cachesToTransfer, progress_cb, results):
        ### COPY THE CACHE FILES TO THE SERVER NOW # Subprocess to copy files from the temp folder to the server
        logger.info('Cache exports finished... moving cache files now if appropriate')
        progress_cb(0, "Copying caches to server now...")
        if cachesToTransfer:
            import subprocess
            CTEMP = configCONST.TEMP_FOLDER
            BATCHNAME = configCONST.ALEMBIC_BATCH_NAME
            progress_cb(50, "Copying caches to server now...")
            p = subprocess.Popen(BATCHNAME, cwd=CTEMP, shell=True, bufsize=4096, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout, stderr = p.communicate()
            return results
        else:
            return results
        progress_cb(100, "Caches moved. AllDone...")
        logger.info(" ")

    def _scanForAssetType(self, type=None, item=None, tk=None):
        assetList = []
        errors = []
        assetName = item['name'].split('_hrc')[0]
        if ':' in assetName:
            assetName = assetName.split(':')[-1]
        logger.info("assetName: {}".format(assetName))

        ## Work out which type we're processing now..
        if type == configCONST.STATIC_CACHE:
            sgTypes = (configCONST.SG_PROP_TYPE_NAME, configCONST.SG_ENV_TYPE_NAME)
        elif type == configCONST.ANIM_CACHE:
             sgTypes = (configCONST.SG_PROP_TYPE_NAME, configCONST.SG_ENV_TYPE_NAME, configCONST.SG_CHAR_TYPE_NAME)

        ## Now process the assets and return the info
        try:
            assetType = tk.shotgun.find_one('Asset', filters=[["code", "is", assetName]], fields=['sg_asset_type'])
            logger.info("assetType: {}".format(assetType))

            if assetType:
                getSGAssetType = assetType['sg_asset_type']

                if getSGAssetType == configCONST.SG_PROP_TYPE_NAME:
                    if configCONST.SG_PROP_TYPE_NAME in sgTypes:
                        if item['name'] not in assetList:
                            assetList.append(item['name'])
                elif getSGAssetType == configCONST.SG_CHAR_TYPE_NAME:
                    if configCONST.SG_CHAR_TYPE_NAME in sgTypes:
                        if item['name'] not in assetList:
                            assetList.append(item['name'])
                elif getSGAssetType == configCONST.SG_ENV_TYPE_NAME:
                    if configCONST.SG_ENV_TYPE_NAME in sgTypes:
                        geoGrp = [geoGrp for geoGrp in cmds.listRelatives(item['name'], children=True) if '_{0}'.format(configCONST.GROUP_SUFFIX) in geoGrp][0]
                        if geoGrp not in assetList:
                            assetList.append(geoGrp)
                else:
                    pass
        except Exception as e:
            errors.append("Publish failed - {}".format(e))

        return assetList

    def _sortAlembicCaches(self, tk, tasks):
        ## PROCESS THE ITEMS into lists so we can compress down the alembic export into selected items.
        ## This saves a bunch of time because we won't be running the animated stuff over the full range
        ## of the time line for EACH item, we can do it on a larger selection.
        staticCaches = []
        animCaches = []
        gpuCaches = []

        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []
            ######################
            ## STATIC CACHES LIST
            ######################
            if item["type"] == configCONST.STATIC_CACHE:
                 cache = self._scanForAssetType(type=configCONST.STATIC_CACHE, item=item, tk=tk)
                 logger.info('cache: {}'.format(cache))
                 if cache:
                     staticCaches = staticCaches + cache
            ######################
            ## ANIM CACHES LIST
            ######################
            elif item["type"] == configCONST.ANIM_CACHE:
                 cache = self._scanForAssetType(type=configCONST.ANIM_CACHE, item=item, tk=tk)
                 logger.info('cache: {}'.format(cache))
                 if cache:
                     animCaches = animCaches + cache
            ######################
            ## GPU CACHES
            ######################
            elif item["type"] == configCONST.GPU_CACHE:
                if item['name'] not in gpuCaches:
                    gpuCaches.append(item['name'])
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! Contact your supervisor to build a hook for this type.")

        return staticCaches, animCaches, gpuCaches

    def _upResAssemblyRefs(self, aRef):
        """
        Used to upres the assemblyRefs, need to double check this is even necessary
        as they wont even report as static or anim caches if they are in anything other
        than full res?!
        """
        if cmds.nodeType(aRef) == 'assemblyReference':
            ## Check to see what isn't loaded to full res for exporting.
            ## Those that are not turn them to full res now for cache exporting.
            if not cmds.assembly(aRef, query=True, active=True) == 'full':
                cmds.assembly(aRef, edit=True, active='full')

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
        group_name = groupName
        tank_type = 'Alembic Cache'
        publish_template = output["publish_template"]

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        # update fields with the group name:
        fields["grp_name"] = group_name

        ## create the publish path by applying the fields with the publish template:
        publish_path = publish_template.apply_fields(fields)
        logger.info('publish_path: {}'.format(publish_path))

        tempFolder = configCONST.TEMP_FOLDER
        logger.info('tempFolder: {}'.format(tempFolder))
        tempFilePath = '{}\\{}'.format(tempFolder, publish_path.replace(':', ''))

        pathToVersionDir = '\\'.join(publish_path.split('\\')[0:-1])
        ## build and execute the Alembic export command for this item:
        if static:
            frame_start = 1
            frame_end = 1
        else:
            frame_start = cmds.playbackOptions(query=True, animationStartTime=True)
            frame_end = cmds.playbackOptions(query=True, animationEndTime=True)

        ## Exporting on selection requires the entire selection to be added with their full paths as -root flags for the export command
        ## Do this now by setting up a string and processing the selection into that string.
        rootList = ''
        for eachRoot in cmds.ls(sl=True):
            rootList = '-root {} {}'.format(str(cmds.ls(eachRoot, l=True)[0]), rootList)

        ## If the publish dir doesn't exist make one now.
        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        ## If the temp folder doesn't exist make one now
        if ':' in publish_path:
            tempFolder = '{}\\{}\\'.format(tempFolder, pathToVersionDir.replace(":", ""))
        else:
            tempFolder = '{}/{}/'.format(tempFolder, pathToVersionDir)

        logger.info('tempFolder: {}'.format(tempFolder))
        if not os.path.isdir(os.path.dirname(tempFolder)):
            os.makedirs(os.path.dirname(tempFolder))

        ## Now build the final export command to use with the python AbcExport
        abc_export_cmd = "-attr smoothed -attr dupAsset -attr mcAssArchive -attr version -ro -uvWrite -wholeFrameGeo \
                         -worldSpace -writeVisibility -fr {} {} {} -file {}".format(frame_start, frame_end, rootList, tempFilePath.replace("\\", "/"))
        logger.info('abc_export_cmd: {}'.format(abc_export_cmd))

        ## add to bat file
        ## Now write the bat file out for the file copy
        pathToBatFile = configCONST.PATH_TO_ANIM_BAT
        logger.info('pathToBatFile: {}'.format(pathToBatFile))
        if not os.path.isfile(pathToBatFile):
            outfile = open(pathToBatFile, "w")
        else:
            outfile = open(pathToBatFile, "a")
        logger.info('copy {} {}'.format(tempFolder, publish_path))
        outfile.write('copy {} {}\n'.format(tempFilePath, publish_path))
        outfile.close()

        try:
            logger.info('Exporting {} to alembic cache now to {}'.format(group_name, publish_path))
            cmds.AbcExport(verbose=False, j=abc_export_cmd)
        except Exception as e:
            raise TankError("Failed to export Alembic Cache {}!!".format(group_name))

        ## Finally, register this publish with Shotgun
        regPub._register_publish(path=publish_path,
                               name='{}_{}'.format(group_name, configCONST.GPU_SUFFIX),
                               sg_task=sg_task,
                               publish_version=publish_version,
                               tank_type=tank_type,
                               comment=comment,
                               thumbnail_path=thumbnail_path,
                               dependency_paths=[primary_publish_path],
                               parent=self.parent)
        logger.info('Alembic publish successfully registered.')

    def _publish_gpu_cache_for_item(self, items, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        """
        group_name = 'gpuCaches'
        items = items
        tank_type = 'Alembic Cache'
        publish_template = output["publish_template"]

        ## Get the current scene path and extract fields from it using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        ## Update fields with the group name:
        fields["grp_name"] = group_name
        ## Create the publish path by applying the fields with the publish template:
        publish_path = publish_template.apply_fields(fields)
        fileName = os.path.splitext(publish_path)[0].split('\\')[-1]
        fileDir = '/'.join(publish_path.split('\\')[0:-1])
        pathToVersionDir = '\\'.join(publish_path.split('\\')[0:-1])

        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        try:
            logger.info('Exporting gpu now to {}\{}'.format(fileDir, fileName))
            for each in items:
                ## Now do the gpu cache export for each of the items
                try:
                    mel.eval("gpuCache -startTime 1 -endTime 1 -optimize -optimizationThreshold 40000 -directory \"{}\" \"{}\";".format(fileDir, each))
                except:
                    logger.warning('FAILED TO PUBLISH GPU CACHE: {}'.format(each))

        except Exception as e:
            raise TankError("Failed to export gpu cache file.. check for corrupt assembly references!")

        ## Finally, register this publish with Shotgun
        regPub._register_publish(path=publish_path,
                               name='{}_{}'.format(group_name, configCONST.GPU_SUFFIX),
                               sg_task=sg_task,
                               publish_version=publish_version,
                               tank_type=tank_type,
                               comment=comment,
                               thumbnail_path=thumbnail_path,
                               dependency_paths=[primary_publish_path],
                               parent=self.parent)
        logger.info('Camera publish successfully registered.')
        logger.info('')

    def _publish_camera_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export the camera
        """

        ## Do the regular Shotgun processing now
        cam_name = item['name']
        tank_type = 'Maya Scene'
        publish_template = output["publish_template"]

        ## Get the current scene path and extract fields from it using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]

        ## Update fields with the group name:
        fields["cam_name"] = cam_name

        ## Create the publish path by applying the fields with the publish template:
        publish_path = publish_template.apply_fields(fields)
        pathToVersionDir = '\\'.join(publish_path.split('\\')[0:-1])
        if not os.path.isdir(pathToVersionDir):
            logger.info('Creating new publish folder.')

            os.mkdir(pathToVersionDir)
        ## Delete existing bake if it isn't already (It should be done by the scan scene.)
        if cmds.objExists('BAKE_CAM_hrc'):
            logger.info('BAKE_CAM_hrc removed sucessfully.')
            cmds.delete('BAKE_CAM_hrc')

        ## Now bake the camera
        cam_lib._bakeCamera(cam_name)
        logger.info('cam_lib._bakeCamera success!')

        ## Export the baked cam to it's publish path now.
        cmds.select('BAKE_CAM_hrc', r=True)
        cmds.file(publish_path, options="v=0;", typ="mayaAscii", es=True, force=True)
        logger.info('Exported camera successfully. Registering publish now.')

        ## Finally, register this publish with Shotgun
        regPub._register_publish(path=publish_path,
                               name='{}_{}'.format(cam_name, configCONST.CAMERA_SUFFIX),
                               sg_task=sg_task,
                               publish_version=publish_version,
                               tank_type=tank_type,
                               comment=comment,
                               thumbnail_path=thumbnail_path,
                               dependency_paths=[primary_publish_path],
                               parent=self.parent)
        logger.info('Camera publish successfully registered.')
        logger.info('')