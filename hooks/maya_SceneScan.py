import os, tank, time
from tank import TankError
import configCONST as configCONST
reload(configCONST)
import maya_asset_lib as asset_lib
reload(asset_lib)
import maya_shd_lib as shd_lib
reload(shd_lib)
import maya.cmds as cmds
import maya.mel as mel
import logging
logger = logging.getLogger(__name__)


def mdl_scan_scene(env = '', sanityChecks = {}):
    ## Look for a rig_hrc and fail if found.
    if asset_lib.rigGroupCheck():
        raise TankError('Rig group found!! Please use the RIG menus to publish rigs...')

    items = setWorkFile(configCONST.MODEL_SHORTNAME)
    items = mdl_getMeshGroup(items)

    if env != configCONST.ENVIRONMENT_SUFFIX:
        mdl_genericHardFails(items)
        doSanityChecks(sanityChecks, items)

    ### NOW CUSTOM CONTEXT STUFF
    if env == configCONST.ENVIRONMENT_SUFFIX:
        ## Note no cache tages necessary here for using ADefs as those will be nested inside defintions themselves as previously published.
        getAllAssemblyReferences = cmds.ls(type = 'assemblyReference')
        if getAllAssemblyReferences:
            for eachARef in getAllAssemblyReferences:
                ## IF Scene Assembly is being used in here switch all to the locator represenations
                cmds.assembly(eachARef, edit = True, active = 'Locator')

    elif env == configCONST.LIB_SUFFIX:
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.LIB_SUFFIX, customTag = 'static%s' % configCONST.LIB_SUFFIX)
        if cmds.objExists('dgSHD'):
              asset_lib.tag_SHD_LIB_Geo()
        items.pop()

    elif env == configCONST.CHAR_SUFFIX:
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.CHAR_SUFFIX, customTag = 'static%s' % configCONST.CHAR_SUFFIX)
        items = findGoZItems(items)

    elif env == configCONST.LND_SUFFIX:
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.LND_SUFFIX, customTag = 'static%s' % configCONST.LND_SUFFIX)

    elif env == configCONST.PROP_SUFFIX:
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.PROP_SUFFIX, customTag = 'static%s' % configCONST.PROP_SUFFIX)
        items = findGoZItems(items)
        items.pop()

    elif env == configCONST.BUILDING_SUFFIX:
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.BUILDING_SUFFIX, customTag = 'static%s' % configCONST.BUILDING_SUFFIX)

        bad = ['hyperLayout', 'hyperGraphInfo', 'hyperView']
        for each in bad:
            logger.info( "CHECKING FOR ASSEMBLY DEFINITION HYPERLAYOUTS NOW")
            for eachNaughty in cmds.ls(type = each):
                try:
                    getAdef = cmds.listConnections(eachNaughty)
                    if getAdef:
                        if '_ADEF' in getAdef[0]:
                            print 'Renamed %s to %s' % (eachNaughty, '%s_%s' % (getAdef[0], each))
                            cmds.rename(eachNaughty, '%s_%s' % (getAdef[0], each))
                except TypeError:
                    pass
    return items

def rig_scan_scene(env = '', static = False, sanityChecks =  {}):
    ## Look for a rig_hrc and fail if not found.
    if not asset_lib.rigGroupCheck():
        raise TankError('No rig group found!! Please make sure your animation controls are under rig_%s.' % configCONST.GROUP_PREFIX)

    items = setWorkFile(configCONST.RIG_SHORTNAME)
    items = mdl_getMeshGroup(items)
    mdl_genericHardFails(items)
    doSanityChecks(sanityChecks, items)

    ### NOW CUSTOM CONTEXT STUFF
    if env == configCONST.BUILDING_SUFFIX:
        asset_lib.setRiggedSmoothPreviews()
        if static: ## Because some buildings may be background assets with no anim export necessary except 1 frame
            asset_lib.assetCheckAndTag(type = '%s' % configCONST.BUILDING_SUFFIX, customTag = 'static%s' % configCONST.BUILDING_SUFFIX)
        else:
            asset_lib.assetCheckAndTag(type = '%s' % configCONST.BUILDING_SUFFIX, customTag = 'snim%s' % configCONST.BUILDING_SUFFIX)

    elif env == configCONST.CHAR_SUFFIX:
        ## Cache tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.CHAR_SUFFIX, customTag = 'anim%s' % configCONST.CHAR_SUFFIX)
        items.pop()

    elif env == configCONST.LIB_SUFFIX:
        items.pop()
    elif env == configCONST.PROP_SUFFIX:
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.PROP_SUFFIX, customTag = 'anim%s' % configCONST.PROP_SUFFIX)
        items.pop()

    ## Global shader cleanup
    if not cmds.objExists('dgSHD'):
        asset_lib.cleanUpShaders()
    else:
        try:
            cmds.delete(cmds.ls(type = 'core_material'))
            mel.eval("MLdeleteUnused();")
        except:
            pass
    return items

def anim_scan_Scene(env = '', sanityChecks = {}):
    """
    :param env: layout, animation as appears in the configCONST file for shotNames
    :param cleanup: for animation scene cleanup
    :return:
    """
    items = setWorkFile(configCONST.ANIM_SHORTNAME)
    if env == configCONST.LAYOUT_SHORTNAME:
        ## set scene for ma export only
        items = anim_getAssemblyReference(items, True)

    elif env == configCONST.ANIM_SHORTNAME:
        logger.info('Animation context found... processing items now...')
        if cmds.objExists('BAKE_CAM_hrc'):
            logger.info('BAKE_CAM_hrc removed sucessfully.')
            cmds.delete('BAKE_CAM_hrc')

        ##Prep for full cache export
        items = anim_getCacheTypes(items)
        logger.info('anim_scan_Scene anim_getCacheTypes: %s' % items)

        items = anim_getAssemblyReference(items, False)
        logger.info('anim_scan_Scene anim_getAssemblyReference: %s' % items)

        ## NOW ADD THE TAGS FOR CREASES TO BE EXPORTED CORRECTLY
        ## NEED TO DO THIS LONG WAY IN CASE THE ATTR ALREADY EXISTS AND FAILS>.
        for each in cmds.ls(type = 'mesh', l = True):
            if not cmds.objExists('%s.SubDivisionMesh' % each):
                try:
                    cmds.addAttr('%s' % each, ln = 'SubDivisionMesh', at = 'bool')
                    cmds.setAttr("%s.SubDivisionMesh" % each, 1)
                except:
                    pass
    asset_lib.cleanupUnknown()
    logger.info('anim_scan_Scene items: %s' % items)
    return items

def shd_scan_Scene(sanityChecks = {}):
    items = setWorkFile(configCONST.SURFACE_SHORTNAME)
    items = mdl_getMeshGroup(items)
    mdl_genericHardFails(items)
    doSanityChecks(sanityChecks, items)

    ## Now do the smartConn
    start = time.time()
    shd_lib.smartConn()
    logger.info('Total time to %s: %s' % ('shd_lib.smartConn()', time.time()-start))

    ## Fix remap and ramps color entry plugs and any incorrect ordering
    ## Leads to bad plugs being inserted when the XML recreates all the values. Querying also creates which makes black colour entry plugs.
    start = time.time()
    shd_lib.fixRamps(cmds.ls(type = 'remapValue'))
    shd_lib.fixRamps(cmds.ls(type = 'ramp'))
    logger.info('Total time to %s: %s' % ('shd_lib.fixRamps()', time.time()-start))

    ## Removed duplicate dgSHD nodes...
    shd_lib.deleteDGSHD()

    ## Delete empty UV Sets
    start = time.time()
    asset_lib.deleteEmptyUVSets()
    logger.info('Total time to %s: %s' % ('asset_lib.deleteEmptyUVSets()', time.time() - start))
    return items

########################################################################################################################
###############
### MODEL STUFF
def setWorkFile(contextName):
    items = []
    # get the main scene:
    scene_name = cmds.file(query=True, sn= True)
    if not scene_name:
        raise TankError("Please Save your file before Publishing")
    scene_path = os.path.abspath(scene_name)

    ## Check that we are checking into the right context!!
    srv = tank.tank_from_path(configCONST.SHOTGUN_CONFIG_PATH)
    context = srv.context_from_path(path=scene_name)
    if context.step['name'] != contextName:
        raise TankError("Please Save your file under the correct context before Publishing!")

    name = os.path.basename(scene_path)
    # create the primary item - this will match the primary output 'scene_item_type':
    items.append({"type": "work_file", "name": name})
    logger.info('setWorkFile success!')
    return items

def findGoZItems(items):
    scene_name = cmds.file(query=True, sn= True)
    if asset_lib.goZScanScene():
        for eachGoZ in cmds.ls(type = 'transform'):
            if cmds.objExists('%s.GoZBrushID' % eachGoZ):
                items.append({"type": "goZ_group", "name": cmds.getAttr('%s.GoZBrushID' % eachGoZ)})

        ## Scan the zbrush folder if it exists
        zbrushdir   = '%s/%s' % ('/'.join(scene_name.split("/")[0:-2]), 'zbrush')
        ZBrushFiles = []
        if os.path.isdir(zbrushdir):
            getZbrushFiles = os.listdir(zbrushdir)
            if getZbrushFiles:
                for eachZbrushFile in os.listdir(zbrushdir):
                    if eachZbrushFile.endswith('.ZTL'):
                        timeStamp = os.path.getmtime('%s/%s' % (zbrushdir, eachZbrushFile))
                        ZBrushFiles.append([eachZbrushFile, timeStamp])
        if ZBrushFiles:
            ZBrushFiles = sorted(ZBrushFiles[-3:])
            for eachZbrushFile in ZBrushFiles:
                items.append({"type": "zbrush_group", "name": eachZbrushFile[0]})

    return items

def mdl_getMeshGroup(items, env = ''):
    if env == configCONST.BUILDING_SUFFIX:
        for grp in cmds.ls(assemblies=True, long= True):
            if cmds.ls(grp, dag=True, type="mesh"):
                if configCONST.FORCE_TRANSFORM_CHECK:
                    if asset_lib.BLDTransformCheck(grp): ## Check for BLD step only to make sure the transforms are not frozen on the BLD grps
                            items.append({"type": "mesh_group", "name": grp})
                else:
                    items.append({"type": "mesh_group", "name": grp})
    else:
        ## Find the mesh group
        for grp in cmds.ls(assemblies = True, long = True):
            if cmds.ls(grp, dag=True, type="mesh"):
                items.append({"type": "mesh_group", "name": grp})
    return items

def mdl_genericHardFails(items):
    #############################
    ## INITIAL HARD FAILS
    ## Do a quick check for geo_hrc and rig_hrc
    if not asset_lib.duplicateNameCheck():
        raise TankError("Duplicate names found please fix before publishing.\nCheck the outliner for the duplicate name set.")

    if not cmds.objExists('%s_%s' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX)):
        raise TankError("Please Group all your geo under a %s_%s group UNDER the root _%s node." % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX, configCONST.GROUP_SUFFIX))

    ## Incorrect Suffix check
    checkSceneGeo = asset_lib._geoSuffixCheck(items)
    if not checkSceneGeo:
        raise TankError("Incorrect Suffixes found! Fix suffixes before publishing.\nCheck the outliner for the duplicate name set.")

    ## Incorrect root name
    if not asset_lib.checkRoot_hrc_Naming(items):
        assetName = cmds.file(query=True, sn= True).split('/')[4]
        raise TankError("YOUR ASSET IS NAMED INCORRECTLY! Remember it is CASE SENSITIVE!\nIt should be %s_%s" % (assetName, configCONST.GROUP_SUFFIX))

def doSanityChecks(sanityChecks, items):
    asset_lib.sanityChecks(
                            items               = items,
                            checkShapes         = sanityChecks['checkShapes'],
                            history             = sanityChecks['history'],
                            pivots              = sanityChecks['pivots'],
                            freezeXFRM          = sanityChecks['freezeXFRM'],
                            smoothLvl           = sanityChecks['smoothLvl'],
                            tagSmoothed         = sanityChecks['tagSmoothed'],
                            checkVerts          = sanityChecks['checkVerts'],
                            renderflags         = sanityChecks['renderflags'],
                            deleteIntermediate  = sanityChecks['deleteIntermediate'],
                            turnOffOpposite     = sanityChecks['turnOffOpposite'],
                            instanceCheck       = sanityChecks['instanceCheck'],
                            shaders             = sanityChecks['shaders'],
                            lightingCleanup     = sanityChecks['lightingCleanup']
                            )

###############
### ANIM STUFF
def anim_getAssemblyReference(items = [], gpuRes = True):
    scene_name = cmds.file(query=True, sn= True)
    CACHETAGS = configCONST.CACHETAGS
    for eachTransform in cmds.ls(transforms = True):
        if cmds.nodeType(eachTransform) == 'assemblyReference':
            ## FIRST Check to see what the active state is of the assembly reference node
            ## If it is still on GPU add this for gpu rendering
            ## Else look for what type of building it is for the alembic caching
            if cmds.assembly(eachTransform, query = True, active = True) == 'gpuCache':
                if gpuRes:## Maintain the adef as a gpu cache
                    items.append({"type":configCONST.GPU_CACHE, "name":eachTransform})
                else: ## Set to full res
                    if configCONST.ANIM_SHORTNAME in scene_name.split('/'):
                        cmds.assembly(eachTransform, edit = True, active = 'full')
                        items.append({"type":configCONST.STATIC_CACHE, "name":eachTransform})

            else:
                getChildren = cmds.listRelatives(eachTransform, children = True)
                if getChildren:
                    for eachChild in getChildren:
                        if cmds.objExists('%s.type' % eachChild):
                            cacheType = cmds.getAttr('%s.type' % eachChild)
                            items.append({"type":CACHETAGS[cacheType], "name":eachTransform})
        return items

def anim_getCacheTypes(items):
    """
    Scan the scene for cache type attribs and process accordingly
    :param items: The items list to append to
    :return:
    """
    CACHETAGS = configCONST.CACHETAGS
    for eachTransform in cmds.ls(transforms = True):
        if cmds.objExists('%s.type' % eachTransform) and eachTransform != 'camGate':
            cacheType = cmds.getAttr('%s.type' % eachTransform)
            items.append({"type": CACHETAGS[cacheType], "name":eachTransform})

    ## NPARTICLES
    for eachNpart in cmds.ls(type = 'nParticle'):
        ## Now put the fx nodes to be cached into items, remember the type is set to match the shot_step.yml secondary output type!
        items.append({"type":"nparticle_caches", "name":eachNpart})

    ## ANIM CURVES
    items.append({"type":configCONST.ATOM_CACHE, "name":"Animation Curves"})
    return items