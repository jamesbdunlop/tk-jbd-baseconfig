import os
import sys

import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
from tank import TankError


## Now get the custom tools
from config.const import configCONST as CONST

if 'T:/software/bubblebathbay_sandbox/custom' not in sys.path:
    sys.path.append('T:/software/bubblebathbay_sandbox/custom')
import utils as utils
from debug import debug
reload(CONST)

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
        utils.loadSceneAssemblyPlugins(TankError)
            
        results = []
        gpuCaches = []
        staticCaches = []
        animCaches = []
        fxCaches = []
        npartCaches = []
        
        ## Clean the animation alembic bat now for a fresh publish
        pathToBatFile = CONST.PATHTOANIMBAT
        if os.path.isfile(pathToBatFile):
            os.remove(pathToBatFile)
        
        ## PROCESS THE ITEMS into lists so we can compress down the alembic export into selected items.
        ## This saves a bunch of time because we won't be running the animated stuff over the full range of the time line for EACH item, we can do it on
        ## a larger selection.    
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []
            
            ##DEBUGG
            # report progress:
            geoGrp = ''
            progress_cb(0, "Processing Scene Secondaries now...", task)           
            
            ## STATIC CACHES LIST
            if item["type"] == "static_caches":
                try:
                    ## Now process the assembly definition files as these have a difference hrc to normal references as they exist without a top level ns in the scene.
                    if '_ADef_' in item['name']:
                        geoGrp = [geoGrp for geoGrp in cmds.listRelatives(item['name'], children = True) if '_hrc' in geoGrp][0]
                        if geoGrp not in staticCaches:
                            staticCaches.append(geoGrp)
                    elif 'PROP' in item['name']:
                        if item['name'] not in staticCaches:
                            staticCaches.append(item['name'])
                    else:
                        pass
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            ## ANIM CACHES LIST
            elif item["type"] == "anim_caches":
                try:
                    ## Now process the assembly definition files as these have a difference hrc to normal references as they exist without a top level ns in the scene.
                    if '_ADef_' in item['name']:
                        geoGrp = [geoGrp for geoGrp in cmds.listRelatives(item['name'], children = True) if '_hrc' in geoGrp][0]
                        if geoGrp not in animCaches:
                            animCaches.append(geoGrp)

                    elif 'CHAR' in item['name']:
                        if item['name'] not in animCaches:
                            animCaches.append(item['name'])

                    elif 'PROP' in item['name']:
                        if item['name'] not in animCaches:
                            animCaches.append(item['name'])
                    else:
                        pass
                except Exception, e:
                    errors.append("Publish failed - %s" % e)

            ## GPU CACHES
            elif item["type"] == "gpu_caches":
                if item['name'] not in gpuCaches:
                    gpuCaches.append(item['name'])

            ## CAMERA
            elif item["type"] == "camera":
                self._publish_camera_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)

            ## FX CACHES
            elif item["type"] == "fx_caches":
                progress_cb(25, "Processing Fluid Cache %s now..." % item['name'], task)
                self._publish_oceanPreset(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                progress_cb(50, "DONE Processing Fluid Cache %s" % item['name'], task)                
            
            ## NPARTICLE CACHES
#             elif item["type"] == "nparticle_caches":
#                 self._publish_nparticle_caches_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
            
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item! Contact your supervisor to build a hook for this type.")
                            
            ## if there is anything to report then add to result
            if len(errors) > 0:
                ## add result:
                results.append({"task":task, "errors":errors})

            progress_cb(100, "Done Processing INITIAL Secondaries, moving to final caching....", task)
            
        staticDone = False
        animDone = False
        gpuDone = False
        npartDone = False
        ## Because we don't want to continually iter through the tasks and do the same shit over and over we're setting a quick Done true or false here because I'm tired and can't 
        ## think of a better way at the moment....
        progress_cb(0, "Processing Static, Anim, GPU and Nparticle caches now...") 
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []
            
            ##DEBUGG
            # report progress:
            geoGrp = ''
            ## STATIC CACHES            
            if item["type"] == "static_caches":
                if not staticDone:
                    ## Now process the publishing of the lists so we can bulk export the appropriate assets to avoid hundreds of alembic files.
                    ## STATIC CACHES
                    static = True
                    groupName = 'staticCaches'
                    if len(staticCaches) <= 0:
                        print 'Static cache list empty, skipping...'
                    else:
                        progress_cb(25, "Processing Static Caches %s now..." % groupName)
                        cmds.select(staticCaches, r = True) # Select the cache objects for static export now and replace the current selection with this list.

                        ## Do a quick check that every assembly reference marked for export as alembic is at full res
                        for each in cmds.ls(sl= True):
                            self._upResAssemblyRefs(each)
 
                        self._publish_alembic_cache_for_item(groupName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, static)
                        staticDone = True
                        progress_cb(35, "Done processing Static Caches!")
            
            ## ANIMATED CACHES
            elif item["type"] == "anim_caches":
                if not animDone:
                    static = False
                    groupName = 'animCaches'
                    if len(animCaches) <= 0:
                        print 'Animated cache list empty, skipping...'
                    else:
                        progress_cb(45, "Processing Anim Caches %s now..." % groupName)
                        cmds.select(animCaches, r = True) # Select the cache objects for static export now and replace the current selection with this list.
                        
                        ## Do a quick check that every assembly reference marked for export as alembic is at full res
                        for each in cmds.ls(sl= True):
                            self._upResAssemblyRefs(each)
                            
                        self._publish_alembic_cache_for_item(groupName, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb, static)
                        animDone = True
                        progress_cb(50, "Done processing Anim Caches!")                    
            
            ## GPU CACHES
            elif item["type"] == "gpu_caches":
                if not gpuDone:
                    allItems = gpuCaches
                    cmds.select(gpuCaches, r = True)# Select the cache objects for gpu export now and replace the current selection with this list.
                    self._publish_gpu_cache_for_item(allItems, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                    gpuDone = True
                    
            ## NPARTICLE CACHES
            elif item["type"] == "nparticle_caches":
                if not npartDone:
                    allItems = npartCaches
                    print 'TRYING THE FUCKNIG NPARTICLES NOW....'
                    cmds.currentTime(1)
                    self._publish_nparticle_caches_for_item(allItems, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
                    npartDone = True
                    
            else:
                pass

        progress_cb(100)
        
        ### COPY THE CACHE FILES TO THE SERVER NOW
        ### Subprocess to copy files from the temp folder to the server
        import subprocess
        CTEMP = CONST.CTMP
        BATCHNAME = CONST.ANIMBATCHNAME
        p = subprocess.Popen(BATCHNAME, cwd=CTEMP, shell=True, bufsize=4096, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = p.communicate()
        if p.returncode == 0:
            return results
        else:
            results.append({"task":'File Copy', "errors":['Publish failed - could not copy files to the server!']})
            return results

    def _upResAssemblyRefs(self, aRef):
        if cmds.nodeType(aRef) == 'assemblyReference':
            ## Check to see what isn't loaded to full res for exporting. Those that are not turn them to full res now for cache exporting.
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
        group_name = groupName
        tank_type = 'Alembic Cache'
        publish_template = output["publish_template"]
        
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
        debug(app = None, method = 'PublishHook', message = 'publish_path: %s' % publish_path, verbose = True)
        
        tempFolder = r"C:\Temp%s" % publish_path.split("I:")[-1]
        debug(app = None, method = 'PublishHook', message = 'tempFolder: %s' % tempFolder, verbose = True)
        
        pathToVersionDir = '\\'.join(publish_path.split('\\')[0:-1])
        ## build and execute the Alembic export command for this item:
        if static:
            frame_start = 1
            frame_end = 1
        else:
            frame_start = cmds.playbackOptions(query = True, animationStartTime = True)
            frame_end = cmds.playbackOptions(query = True, animationEndTime = True)
        
        ## Exporting on selection requires the entire selection to be added with their full paths as -root flags for the export command
        ## Do this now by setting up a string and processing the selection into that string.
        rootList = ''
        for eachRoot in cmds.ls(sl= True):
            rootList = '-root %s %s' % (str(cmds.ls(eachRoot, l = True)[0]), rootList)

        ## If the publish dir doesn't exist make one now.
        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)
        ## If the temp folder doesn't exist make one now 
        if not os.path.isdir(os.path.dirname(tempFolder)):
            os.makedirs(os.path.dirname(tempFolder))
        
        ## Now build the final export command to use with the python AbcExport
        abc_export_cmd = "preRollStartFrame -15 -attr smoothed -attr dupAsset -attr mcAssArchive -ro -uvWrite -wholeFrameGeo -worldSpace -writeVisibility -fr %d %d %s -file %s" % (frame_start, frame_end, rootList, tempFolder)

        ## add to bat file
        ## Now write the bat file out since we can't use tar as a os.system command
        pathToBatFile = CONST.PATHTOANIMBAT
        if not os.path.isfile(pathToBatFile):
            outfile = open(pathToBatFile, "w")
        else:
            outfile = open(pathToBatFile, "a")
        outfile.write('copy %s %s\n' % (tempFolder, publish_path))
        outfile.close()
     
        try:
            self.parent.log_debug("Executing command: %s" % abc_export_cmd)
            print '====================='
            print 'Exporting %s to alembic cache now to %s' % (group_name, publish_path)
            cmds.AbcExport(verbose = False, j = abc_export_cmd)
        except Exception, e:
            raise TankError("Failed to export Alembic Cache!!")

        ## Finally, register this publish with Shotgun
        self._register_publish(publish_path, 
                               '%sABC' % group_name, 
                               sg_task, 
                               publish_version, 
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])
        print 'Finished alembic export...'
        print '====================='

    def _publish_gpu_cache_for_item(self, items, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        """
        group_name = 'gpuCaches'
        items = items
        tank_type = 'Alembic Cache'
        publish_template = output["publish_template"]
        
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
        #'@asset_root/publish/gpu/{name}[_{grp_name}].v{version}.abc'
        fileName = os.path.splitext(publish_path)[0].split('\\')[-1] 
        fileDir = '/'.join(publish_path.split('\\')[0:-1])
        pathToVersionDir = '\\'.join(publish_path.split('\\')[0:-1])
        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        try:
            self.parent.log_debug("Executing GPU Cache export now to: \n\t\t%s" % publish_path)
            print '====================='
            print 'Exporting gpu now to %s\%s' % (fileDir, fileName) 
            print items               
            for each in items:
                ## Now do the gpu cache export for each of the items
                try:
                    #print 'GPU STRING IS: \n%s' % 'gpuCache -startTime 1 -endTime 1 -optimize -optimizationThreshold 40000 -directory \"%s\" \"%s\";' % (fileDir, each)
                    mel.eval("gpuCache -startTime 1 -endTime 1 -optimize -optimizationThreshold 40000 -directory \"%s\" \"%s\";" % (fileDir, each))
                except:
                    #print 'GPU STRING IS: \n%s' % 'gpuCache -startTime 1 -endTime 1 -optimize -optimizationThreshold 40000 -directory \"%s\" \"%s\";' % (fileDir, each)
                    cmds.warning('FAILED TO PUBLISH GPU CACHE: %s' %  each)
                
        except Exception, e:
            raise TankError("Failed to export gpu cache file.. check for corrupt assembly references!")
         
        ## Finally, register this publish with Shotgun
        self._register_publish(publish_path, 
                               '%sGPU' % group_name, 
                               sg_task, 
                               publish_version, 
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])
        print 'Finished gpu export...'
        print '====================='
        
    def _publish_camera_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export the camera
        """
        ## Do the regular Shotgun processing now
        cam_name = item['name']
        tank_type = 'Maya Scene'
        publish_template = output["publish_template"]
        
        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn= True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        # update fields with the group name:
        fields["cam_name"] = cam_name
        ## create the publish path by applying the fields 
        ## with the publish template:
        publish_path = publish_template.apply_fields(fields)
        pathToVersionDir = '\\'.join(publish_path.split('\\')[0:-1])
        if not os.path.isdir(pathToVersionDir):
            os.mkdir(pathToVersionDir)

        cmds.select(cam_name, r = True)
        cmds.file(publish_path, options = "v=0;", typ = "mayaAscii", es = True, force= True)
        ## Finally, register this publish with Shotgun
        self._register_publish(publish_path, 
                               '%sCAM' % cam_name, 
                               sg_task, 
                               publish_version, 
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])

    def _publish_oceanPreset(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Export the Fluid Texture Caches
        """
        ## Do the regular Shotgun processing now
        group_name = item['name']
        tank_type = 'Alembic Cache'
        publish_template = output["publish_template"]
        
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
        
        #print 'CHECKING IF DIR %s EXISTS' % publish_path
        if not os.path.isdir(publish_path):
            os.mkdir(publish_path)
            
        print '====================='
        ## Now save the dispShader Preset .. this should be the exact same setup as the animation ocean shader and if it isn't shoot the animator now..
        dispShaderPreset = mel.eval("saveAttrPreset ocean_dispShader ocean_dispShader.v%s 0" %  publish_version)
        
        ## Now move this to the publish folder so we can assign it back to a new maya ocean when we setup the lighting caches..
        os.rename(dispShaderPreset, '%s/%s.v%s.mel'% (publish_path, 'ocean_dispShader', publish_version))
        
        ## Now register this with shotgun
        self._register_publish(publish_path, 
                               'ocean_dispShader_OceanPreset', 
                               sg_task, 
                               publish_version, 
                               tank_type,
                               comment,
                               thumbnail_path,
                               [primary_publish_path])
        print 'DONE exporting %s' % group_name
        print '====================='
        cmds.currentTime(1)
        
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