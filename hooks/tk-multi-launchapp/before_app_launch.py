# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os, sys, shutil, tank
##################################################################
## EDIT BELOW TO MATCH YOUR SHOTGUN VOLUME SETUP
##################################################################
## Windows
if sys.platform == 'win32':
    SOFTWARE_ROOT = "T:/software"
## OSX
elif sys.platform == 'darwin':
    SOFTWARE_ROOT = '/volumes/development'
## Linux
else:
    SOFTWARE_ROOT = '/development'

CONFIG_NAME = 'baseConfig'
##################################################################
## FINISH EDITING HERE
##################################################################
## Now add the config root to the sys.path so we can source the base configCONST file
CONFIG_ROOT = os.path.join(SOFTWARE_ROOT, CONFIG_NAME, 'config')
if CONFIG_ROOT not in sys.path:
    sys.path.append(CONFIG_ROOT)

## Now import the base configs configCONST file
import config_constants as configCONST
sys.path.append(configCONST.TANKCORE_PYTHON_PATH)
print("configCONST LOADED!")


class BeforeAppLaunch(tank.Hook):
    """Hook to set up the system prior to app launch."""

    def execute(self, app_path, app_args, version, engine_name, software_entity=None, **kwargs):
        """
        The execute function of the hook will be called prior to starting the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.
        :param software_entity: (dict) If set, this is the Software entity that is
            associated with this launch command.
        """
        ## Remove the log for the debug module if it exists.
        pathToLog = os.path.join(configCONST.TEMP_FOLDER, configCONST.LOGFILE_NAME)
        if os.path.isfile(pathToLog):
            os.remove(pathToLog)

        ## Setup the MAYA_APP_DIR folder if it isn't there.
        if not os.path.isdir(configCONST.MAYA_APP_DIR):
            os.mkdir(configCONST.MAYA_APP_DIR)

        ## Make the user config maya folders if they don't exist in the config based maya directories
        basepaths = [configCONST.MAYA_CONFIG_SCRIPT_PATH,
                     configCONST.MAYA_CONFIG_PREFS_PATH,
                     configCONST.MAYA_CONFIG_SHELVES_PATH,
                     configCONST.MAYA_CONFIG_BASE]

        if not os.path.isdir(configCONST.MAYA_USER_APP_DIR):
            os.makedirs(configCONST.MAYA_USER_APP_DIR)
            ## Hard making some of the maya folders so we can set the userSetup.py pre load
            for eachPath in basepaths:
                if not os.path.isdir(eachPath):
                    os.makedirs(eachPath)

            ## Copy userSetup.py
            print("Copying userSetup.py from: {}".format(configCONST.MAYA_DEFAULT_USERSETUPPY))
            shutil.copy(configCONST.MAYA_DEFAULT_USERSETUPPY, configCONST.MAYA_CONFIG_SCRIPT_PATH)
        else:
            ## Check the sub dirs if they exist or not
            for eachPath in basepaths:
                if not os.path.isdir(eachPath):
                    os.makedirs(eachPath)

            ## Copy userSetup.py and bulldog shelf if the force reinstall is true in the base configCONST file
            if configCONST.FORCE_USERSETUP_REINSTALL:
                shutil.copy(configCONST.MAYA_DEFAULT_USERSETUPPY, configCONST.MAYA_CONFIG_SCRIPT_PATH)
        ##############################################################################
        ## MAYA APP DIR
        ##############################################################################
        os.environ["MAYA_APP_DIR"] = configCONST.MAYA_USER_APP_DIR
        ##############################################################################
        ## ADDITIONAL SYSTEM PATHS
        ## NOTE A BUNCH OF THESE GET USED FROM THE configCONST in the userSetup.py
        ##############################################################################
        sys_paths = []
        for eachSysPath in sys_paths:
            if eachSysPath not in sys.path:
                sys.path.append(eachSysPath)
