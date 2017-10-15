import sys, os
import maya.utils as mu

##################################################################
## EDIT BELOW TO MATCH YOUR SHOTGUN VOLUME SETUP
##################################################################
CONFIG_NAME = 'genericconfig'
## Windows
if sys.platform == 'win32':
    SOFTWARE_ROOT = "T:/software"
## OSX
elif sys.platform == 'darwin':
    SOFTWARE_ROOT = '/volumes/development'
## Linux
else:
    SOFTWARE_ROOT = '/development'
##################################################################
## FINISH EDITING HERE
##################################################################
## Now add the config root to the sys.path so we can source the base config_constants file
CONFIG_ROOT = os.path.join(SOFTWARE_ROOT, CONFIG_NAME, 'config')
if CONFIG_ROOT not in sys.path:
    sys.path.append(CONFIG_ROOT)
## Now import the base configs configCONST file
import config_constants as configCONST
print('IMPORTED config successfully!')
##################################################################

def _setup_env(envName, envPath):
    """
    Function to setup default environment variables.
    :param envName: The Name of the environment var to set
    :param envPath: The path you want to add to this environment var
    :return:
    """
    listEnv = os.getenv(envName)
    if listEnv:
        if envPath not in listEnv:
            os.environ[envName] = '%s%s%s' % (listEnv, ';', envPath)
            print('Added %s to env %s' % (envPath, envName))
    else:
        os.environ[envName] = '%s%s%s' % (listEnv, ';', envPath)
        print('Added %s to env %s' % (envPath, envName))

##################################################################
## START USER SETUP NOW
##################################################################
## Look for the MENTALCORE render engine
MENTALCORE = False
try:
    import mentalcore
    MENTALCORE = True
except ImportError:
    pass

##############################################################################
## SYS PATHS
##############################################################################
for eachSysPath in configCONST.SYS_PATHS:
    if eachSysPath not in sys.path:
        sys.path.append(eachSysPath)

##############################################################################
## MAYA_SCRIPT_PATH
##############################################################################
for eachPath in configCONST.MAYA_SCRIPT_PATHS:
    _setup_env('MAYA_SCRIPT_PATH', eachPath)

##############################################################################
## XBMLANGPATH
##############################################################################
for eachPath in configCONST.MAYA_XBM_PATHS:
    _setup_env('XBMLANGPATH', eachPath)

##############################################################################
#### MAYA PLUGIN PATH
##############################################################################
for eachPath in configCONST.MAYA_PLUGIN_PATHS:
    _setup_env('MAYA_PLUGIN_PATH', eachPath)

##################################################################
## SET FINAL CONFIGURATIONS
## MENTALCORE STARTUP
if MENTALCORE:
    ## Try and force a mentalcore load if it is installed...
    ## ---- MENTALCORE STARTUP
    try:
        mu.executeDeferred('mentalcore.startup()')
        print('mentalcore.startup() forced to load successfully...')
    except NameError:
        print('No Mentalcore found... skipping load...')