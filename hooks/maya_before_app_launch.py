# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
# maya pyqt windows binaries http://www.robg3d.com/maya-windows-binaries/

"""
Before App Launch Hook

This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""
import os, sys, shutil, tank
from tank.platform.qt import QtCore, QtGui
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

CONFIG_NAME = 'genericconfig'
##################################################################
## FINISH EDITING HERE
##################################################################
## Now add the config root to the sys.path so we can source the base configCONST file
CONFIG_ROOT = '{}/{}/config/const'.format((SOFTWARE_ROOT, CONFIG_NAME))
if CONFIG_ROOT not in sys.path:
    sys.path.append(CONFIG_ROOT)

## Now import the base configs configCONST file
try:
    import config_constants as configCONST
    print('configCONST imported successfully...')
except ImportError:
    print('configCONST NOT FOUND! Please make sure the CONFIG_NAME and the CONFIG_ROOT constants in the \
          maya_before_app_launch.py are set correctly!')
sys.path.append(configCONST.TANKCORE_PYTHON_PATH)



class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """
    def execute(self, **kwargs):
        """
        The execute function of the hook will be called to start the required application        
        """
        ## Remove the log for the debug module if it exists.
        pathToLog = "{}/{}".format((configCONST.TEMP_FOLDER, configCONST.LOGFILE_NAME))
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
            ##Hard making some of the maya folders so we can set the userSetup.py pre load
            for eachPath in basepaths:
                if not os.path.isdir(eachPath):
                    os.makedirs(eachPath)

            ## Copy userSetup.py
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

        for path in sys.path:
            print(path)