import maya_asset_lib as asset_lib
import configCONST as configCONST
from tank import TankError
import os, tank
import maya.cmds as cmds

### MODEL STUFF
def setWorkFile():
    items = []
    # get the main scene:
    scene_name = cmds.file(query=True, sn= True)
    if not scene_name:
        raise TankError("Please Save your file before Publishing")
    scene_path = os.path.abspath(scene_name)

    ## Check that we are checking into the right context!!
    srv = tank.tank_from_path(configCONST.SHOTGUN_CONFIG_PATH)
    context = srv.context_from_path(path=scene_name)
    if context.step['name'] != configCONST.MODEL_SHORTNAME:
        raise TankError("Please Save your file under the correct context before Publishing!")

    name = os.path.basename(scene_path)
    # create the primary item - this will match the primary output 'scene_item_type':
    items.append({"type": "work_file", "name": name})
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

def mdl_scan_scene(env = '', cleanup = {}):
    items = setWorkFile()
    if env == 'bld':
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

    #############################
    ## INITIAL HARD FAILS
    ## Do a quick check for geo_hrc and rig_hrc
    if not asset_lib.duplicateNameCheck():
        raise TankError("Duplicate names found please fix before publishing.\nCheck the outliner for the duplicate name set.")

    if not cmds.objExists('%s_%s' % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX)):
        raise TankError("Please Group all your geo under a %s_%s group UNDER the root _%s node." % (configCONST.GEO_SUFFIX, configCONST.GROUP_SUFFIX, configCONST.GROUP_SUFFIX))

    ## Look for a rig_hrc and fail if found.
    if asset_lib.rigGroupCheck():
        raise TankError('Rig group found!! Please use the RIG menus to publish rigs...')

    ## Incorrect Suffix check
    checkSceneGeo = asset_lib._geoSuffixCheck(items)
    if not checkSceneGeo:
        raise TankError("Incorrect Suffixes found! Fix suffixes before publishing.\nCheck the outliner for the duplicate name set.")

    ## Incorrect root name
    if not asset_lib.checkRoot_hrc_Naming(items):
        assetName = cmds.file(query=True, sn= True).split('/')[4]
        raise TankError("YOUR ASSET IS NAMED INCORRECTLY! Remember it is CASE SENSITIVE!\nIt should be %s_%s" % (assetName, configCONST.GROUP_SUFFIX))

    ## Now cleanup
    asset_lib.cleanUp(
                    items               = items,
                    checkShapes         = cleanup['checkShapes'],
                    history             = cleanup['history'],
                    pivots              = cleanup['pivots'],
                    freezeXFRM          = cleanup['freezeXFRM'],
                    smoothLvl           = cleanup['smoothLvl'],
                    tagSmoothed         = cleanup['tagSmoothed'],
                    checkVerts          = cleanup['checkVerts'],
                    renderflags         = cleanup['renderflags'],
                    deleteIntermediate  = cleanup['deleteIntermediate'],
                    turnOffOpposite     = cleanup['turnOffOpposite'],
                    instanceCheck       = cleanup['instanceCheck'],
                    shaders             = cleanup['shaders']
                    )

    ### NOW CUSTOM CONTEXT STUFF
    if env == 'env':
        ## IF Scene Assembly is being used in here switch all to the locator represenations
        getAllAssemblyReferences = cmds.ls(type = 'assemblyReference')
        if getAllAssemblyReferences:
            for eachARef in getAllAssemblyReferences:
                cmds.assembly(eachARef, edit = True, active = 'Locator')
        #if len(items) > 1:
        #    items.pop()

    elif env == 'lib':
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.LIB_SUFFIX, customTag = 'static%s' % configCONST.LIB_SUFFIX)
        if cmds.objExists('dgSHD'):
              asset_lib.tag_SHD_LIB_Geo()
        items.pop()

    elif env == 'char':
        ## Cache Tag
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.CHAR_SUFFIX, customTag = 'static%s' % configCONST.CHAR_SUFFIX)
        items = findGoZItems(items)

    elif env == 'lnd':
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.LND_SUFFIX, customTag = 'static%s' % configCONST.LND_SUFFIX)

    elif env == 'prop':
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.PROP_SUFFIX, customTag = 'static%s' % configCONST.PROP_SUFFIX)
        items = findGoZItems(items)
        items.pop()

    elif env == 'bld':
        asset_lib.assetCheckAndTag(type = '%s' % configCONST.BUILDING_SUFFIX, customTag = 'static%s' % configCONST.BUILDING_SUFFIX)
        ##Now set the auxNodes to something that won't clash during a shot build!!
        bad = ['hyperLayout', 'hyperGraphInfo', 'hyperView']
        for each in bad:
            print "CHECKING FOR ASSEMBLY DEFINITION HYPERLAYOUTS NOW"
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


def rig_scan_scene(env = '', items = [], cleanup = {}):
    pass