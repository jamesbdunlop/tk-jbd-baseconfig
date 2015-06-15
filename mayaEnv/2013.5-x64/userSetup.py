import sys, os
import maya.cmds as cmds
import maya.utils as mu
import maya.mel as mel

##################################################################
## EDIT BELOW TO MATCH YOUR SHOTGUN VOLUME SETUP
##################################################################
## Windows
if sys.platform == 'win32':
    SOFTWARE_ROOT = "T:/software"
## OSX
elif sys.platform == 'darwin':
    SOFTWARE_ROOT = '/volumes/development/software'
## Linux
else:
    SOFTWARE_ROOT = '/development/software'

CONFIG_NAME = 'default'
##################################################################
## FINISH EDITING HERE
##################################################################
## Now add the config root to the sys.path so we can source the base configCONST file
CONFIG_ROOT = '%s/%s/config/const' % (SOFTWARE_ROOT, CONFIG_NAME)
if CONFIG_ROOT not in sys.path:
    sys.path.append(CONFIG_ROOT)
## Now import the base configs configCONST file
import configCONST as configCONST
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
            os.environ[envName] = '%s%s%s'% (listEnv, ';', envPath)
            print 'Added %s to env %s' % (envPath, envName)
    else:
        os.environ[envName] = '%s%s%s'% (listEnv, ';', envPath)
        print 'Added %s to env %s' % (envPath, envName)

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
## BULLDOG ENV STUFF
##############################################################################
if configCONST.USE_BULLDOG_UI:
    ## MAYA_SCRIPT_PATH
    for eachPath in configCONST.BULLDOG_SCRIPT_PATHS:
        _setup_env('MAYA_SCRIPT_PATH', eachPath)

    ## SYS.PATH
    for eachSysPath in configCONST.BULLDOG_SYS_PATHS:
        if eachSysPath not in sys.path:
            sys.path.append(eachSysPath)

    ## XBM.PATH
    for eachPath in configCONST.BULLDOG_XBM_PATHS:
        _setup_env('XBMLANGPATH', eachPath)

    ## PLUGIN PATHS
    for eachPath in configCONST.BULLDOG_PLUGIN_PATHS:
        _setup_env('MAYA_PLUGIN_PATH', eachPath)

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
    mu.executeDeferred('mentalcore.startup()')
    print 'mentalcore.startup() forced to load successfully...'

##################################################################
#### IS THE BULLDOG UI BEING USED BY THIS CONFIG?
if configCONST.USE_BULLDOG_UI:
    ## Now load the plugins from the bulldDog directory
    def loadPlugins():
        for eachPluginPath in configCONST.BULLDOG_PLUGIN_PATHS:
            listDir = os.listdir(eachPluginPath)
            if listDir:
                for eachPlugin in listDir:
                    ## MLL LOAD
                    if eachPlugin.endswith('.mll'):
                        try:
                            print 'Loading %s/%s... ' % (eachPluginPath, eachPlugin)
                            cmds.loadPlugin('%s/%s' % (eachPluginPath, eachPlugin))
                        except RuntimeError:
                            cmds.warning('%s plugin failed to load...' % eachPlugin)
                    ## PY LOAD
                    elif eachPlugin.endswith('.py'):
                        try:
                            print 'Loading %s/%s... ' % (eachPluginPath, eachPlugin)
                            cmds.loadPlugin('%s/%s.py' % (eachPluginPath, eachPlugin))
                        except RuntimeError:
                            cmds.warning('%s failed to load...' % eachPlugin)
                    else:
                        pass

    ## LOAD PLUGINS NOW
    loadPlugins()

    #############################################################
    ## LOAD MAYA 2013 DEFAULT MEL SCRIPTS NOW FROM THE UI FOLDERS
    if '2013' in configCONST.MAYA_VERSION:
        DEFAULT_MEL_SCRIPTS = ['sz_RenderView.mel', 'mayaPreviewRender.mel', 'mentalrayPreviewRender.mel', 'renderWindowPanel.mel']
        for eachMel in DEFAULT_MEL_SCRIPTS:
            try:
                mel.eval("source \"%s/%s\"" % (configCONST.BULLDOG_SCRIPT_PATHS[1], eachMel))
                print 'source \"%s/%s\"' % (configCONST.BULLDOG_SCRIPT_PATHS[1], eachMel)
            except RuntimeError:
                print 'MEL LOAD FAILED: %s failed to load...' % eachMel

    #############################################################
    ## LOAD MAYA 2013 DEFAULT MEL SCRIPTS NOW FROM THE UI FOLDERS
    if '2015' in configCONST.MAYA_VERSION:
        DEFAULT_MEL_SCRIPTS = []
        for eachMel in DEFAULT_MEL_SCRIPTS:
            try:
                mel.eval("source \"%s/%s\"" % (configCONST.BULLDOG_SCRIPT_PATHS[1], eachMel))
                print 'source \"%s/%s\"' % (configCONST.BULLDOG_SCRIPT_PATHS[1], eachMel)
            except RuntimeError:
                print 'MEL LOAD FAILED: %s failed to load...' % eachMel