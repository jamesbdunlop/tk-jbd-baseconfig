import tank, logging
logger = logging.getLogger(__name__)

def _register_publish(path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths = None, parent = None):
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
    logger.info('args: {}'.format(args))
    # register publish;
    sg_data = tank.util.register_publish(**args)
    return sg_data