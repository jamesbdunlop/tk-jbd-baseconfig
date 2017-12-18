import os, tank, logging
import maya.cmds as cmds
from tank import TankError
import config_constants as configCONST
import shotgun.sg_asset_lib as asset_lib
logger = logging.getLogger(__name__)

def _do_maya_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb, tank, parent):
    """
    Publish the main Maya scene
    """
    ## Save the current working file just in case
    cmds.file(save=True, force=True)
    logger.info('Scene Saved.')
    ## Get scene path
    scene_path = os.path.abspath(cmds.file(query=True, sn=True))
    logger.info('Scene Path: {}'.format(scene_path))
    ## Test if it's a valid scene path
    if not work_template.validate(scene_path):
        raise TankError("File {} is not a valid work path, unable to publish!".format(scene_path))
    ## Turn off the model editors for the new bake
    asset_lib.turnOffModelEditors()
    ## Use templates to convert to publish path:
    output = task["output"]
    fields = work_template.get_fields(scene_path)
    fields["TankType"] = output["tank_type"]
    ## Now update the name to be the actual assetName from shotgun and remove the for saving
    fields['name'] = fields['Shot'].replace('_', '')
    publish_template = output["publish_template"]
    publish_path = publish_template.apply_fields(fields)

    logger.info('publish_path: {}'.format(publish_path))
    logger.info('publishing Maya scene file now..')
    publishMayaSceneFile(task, publish_path, publish_template, output, fields, progress_cb, tank, comment, thumbnail_path, sg_task, parent)
    return publish_path

def publishMayaSceneFile(task, publish_path, publish_template, output, fields, progress_cb, tank, comment, thumbnail_path, sg_task, parent):
    progress_cb(0.0, "Finding scene dependencies", task)
    dependencies = _maya_find_additional_scene_dependencies(parent)
    logger.info('Versioning scene file for publish now...')
    publish_path = _versionFile(publish_path, publish_template, fields, progress_cb, parent)

    logger.info('Version finished. Getting publish name')
    publish_name = _get_publish_name(publish_path, publish_template, fields)
    logger.info('publish_name: {}'.format(publish_name))

    ## Now rename and save the working file with the new version number for the publish
    ## Change the file type to mb for publish
    progress_cb(50.0, "Publishing the file to publish area")
    try:
        ## Now rename the file to the correct name and version number...
        cmds.file(rename='{}.v{}{}.mb'.format(publish_name, _padding(fields), fields['version']))
        logger.info('Successfully renamed scenefile.')
        ## Now save the file
        cmds.file(save=True, force=True, type='mayaBinary')
        logger.info('Successfully saved scenefile.')
        ## Now put the published file into the publish folder
        publish_folder = os.path.dirname(publish_path)
        ## Make sure the folder exists
        parent.ensure_folder_exists(publish_folder)

        ## Find current scene path and rename the saved file using os.rename to move it into the publish folder
        getCurrentScenePath = os.path.abspath(cmds.file(query=True, sn=True))
        os.rename(getCurrentScenePath, publish_path)

        parent.log_debug("Publishing {} --> {}...".format(getCurrentScenePath, publish_path))
        progress_cb(65.0, "Moved the publish")
    except Exception as e:
        raise TankError("Failed to working file to publish folder.... please contact a TD about this: {}".format(e))

    progress_cb(100)
    ## Now put it back to Ascii
    cmds.file(rename='{}.v{}{}.ma'.format(publish_name, _padding(fields), fields['version']))
    cmds.file(save=True, force=True, type='mayaAscii')

    # finally, register the publish:
    progress_cb(75.0, "Registering the publish")

    publish_name = '{}_{}'.format(publish_name, configCONST.ANIM_SHORTNAME)

    _register_publish(publish_path,
                       publish_name,
                       sg_task,
                       fields["version"],
                       output["tank_type"],
                       comment,
                       thumbnail_path,
                       dependencies,
                       parent)

    return publish_path

def _padding(fields):
    ##Padding because fields is a single int without padding
    version = fields['version']
    logger.info('version: {}'.format(version))
    if version < 10:
        padding = '00'
    elif version < 100:
        padding = '0'
    else:
        padding = ''
    logger.info('padding: {}'.format(padding))
    return padding

def _versionFile(publish_path, publish_template, fields, progress_cb, parent):
    if os.path.exists(publish_path):
        ## If it already exists version up one.
        ## We should never fail a publish just because a published asset already exists
        logger.info('Found existing publish_path: {}'.format(publish_path))
        logger.info('Adjusting publish_path now...')
        path = '\\'.join(publish_path.split('\\')[0:-1])
        getfiles = os.listdir(path)
        if 'Keyboard' in getfiles:
           getfiles.remove('Keyboard')

        ## Get the max of the list
        highestVersFile = max(getfiles).split('.')[1].split('v')[-1]
        newVersNum = int(highestVersFile) + 1

        fields["version"] = newVersNum
        ## Apply the fields to the templates paths..
        publish_path = publish_template.apply_fields(fields)
        ## Output the new publish path to the scripteditor
        logger.info('NewPublishPath: {}'.format(publish_path))
        return publish_path
    else:
        return publish_path

def _maya_find_additional_scene_dependencies(parent):
    """
    Find additional dependencies from the scene
    """
    # default implementation looks for references and
    # textures (file nodes) and returns any paths that
    # match a template defined in the configuration
    ref_paths = set()

    # first let's look at maya references
    ref_nodes = cmds.ls(references=True)
    for ref_node in ref_nodes:
        print('Checking ref node {}'.format(ref_node))
        try:
            ref_path = cmds.referenceQuery(ref_node, filename=True)
            # make it platform dependent
            # (maya uses C:/style/paths)
            ref_path = ref_path.replace("/", os.path.sep)
            if ref_path:
                ref_paths.add(ref_path)
        except RuntimeError:
            cmds.warning('This file is broken removing: {}'.format(ref_node))
            cmds.lockNode(ref_node, lock=False)
            cmds.delete(ref_node)

    # now look at file texture nodes
    for file_node in cmds.ls(l=True, type="file"):
        # ensure this is actually part of this scene and not referenced
        if cmds.referenceQuery(file_node, isNodeReferenced=True):
            # this is embedded in another reference, so don't include it in the
            # breakdown
            continue

        # get path and make it platform dependent
        # (maya uses C:/style/paths)
        texture_path = cmds.getAttr("{}.fileTextureName".format(file_node).replace("/", os.path.sep))
        if texture_path:
            ref_paths.add(texture_path)

    # now, for each reference found, build a list of the ones
    # that resolve against a template:
    dependency_paths = []
    for ref_path in ref_paths:
        # see if there is a template that is valid for this path:
        for template in parent.tank.templates.values():
            if template.validate(ref_path):
                dependency_paths.append(ref_path)
                break

    return dependency_paths

def _get_publish_name(path, template, fields=None):
    """
    Return the 'name' to be used for the file - if possible
    this will return a 'versionless' name
    """
    # first, extract the fields from the path using the template:
    fields = fields.copy() if fields else template.get_fields(path)
    if "name" in fields and fields["name"]:
        # well, that was easy!
        name = fields["name"]
    else:
        # find out if version is used in the file name:
        template_name, _ = os.path.splitext(os.path.basename(template.definition))
        version_in_name = "{version}" in template_name

        # extract the file name from the path:
        name, _ = os.path.splitext(os.path.basename(path))
        delims_str = "_-. "
        if version_in_name:
            # looks like version is part of the file name so we
            # need to isolate it so that we can remove it safely.
            # First, find a dummy version whose string representation
            # doesn't exist in the name string
            version_key = template.keys["version"]
            dummy_version = 9876
            while True:
                test_str = version_key.str_from_value(dummy_version)
                if test_str not in name:
                    break
                dummy_version += 1

            # now use this dummy version and rebuild the path
            fields["version"] = dummy_version
            path = template.apply_fields(fields)
            name, _ = os.path.splitext(os.path.basename(path))

            # we can now locate the version in the name and remove it
            dummy_version_str = version_key.str_from_value(dummy_version)

            v_pos = name.find(dummy_version_str)
            # remove any preceeding 'v'
            pre_v_str = name[:v_pos].rstrip("v")
            post_v_str = name[v_pos + len(dummy_version_str):]

            if (pre_v_str and post_v_str
                and pre_v_str[-1] in delims_str
                and post_v_str[0] in delims_str):
                # only want one delimiter - strip the second one:
                post_v_str = post_v_str.lstrip(delims_str)

            versionless_name = pre_v_str + post_v_str
            versionless_name = versionless_name.strip(delims_str)

            if versionless_name:
                # great - lets use this!
                name = versionless_name
            else:
                # likely that version is only thing in the name so
                # instead, replace the dummy version with #'s:
                zero_version_str = version_key.str_from_value(0)
                new_version_str = "#" * len(zero_version_str)
                name = name.replace(dummy_version_str, new_version_str)
    logger.info('name: {}'.format(name))
    return name

def _register_publish(path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths, parent):
    """
    Helper method to register publish using the
    specified publish info.
    """
    # construct args:
    args = {
        "tk": parent.tank,
        "context": parent.context,
        "comment": comment,
        "path": path,
        "name": name,
        "version_number": publish_version,
        "thumbnail_path": thumbnail_path,
        "task": sg_task,
        "dependency_paths": dependency_paths,
        "published_file_type":tank_type,
    }

    parent.log_debug("Register publish in shotgun: {}".format(str(args)))

    # register publish;
    sg_data = tank.util.register_publish(**args)

    return sg_data