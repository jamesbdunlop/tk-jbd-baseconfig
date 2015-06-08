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
## Now import the base configs configCONSTant file
import configCONST as configCONST
##################################################################


##################################################################
## START USER SETUP NOW
##################################################################
## Look for the MENTALCORE render engine
MENTALCORE = False
try:
    import mentalcore
    MENTALCORE = True
except:
    pass

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
        for eachPlugin in os.listdir(configCONST.BULLDOG_PLUGIN_PATH):
            ## MLL LOAD
            if eachPlugin.endswith('.mll'):
                try:
                    print 'Loading %s/%s... ' % (configCONST.BULLDOG_PLUGIN_PATH, eachPlugin)
                    cmds.loadPlugin('%s/%s' % (configCONST.BULLDOG_PLUGIN_PATH, eachPlugin))
                except RuntimeError:
                    cmds.warning('%s plugin failed to load...' % eachPlugin)
            ## PY LOAD
            elif eachPlugin.endswith('.py'):
                try:
                    print 'Loading %s/%s... ' % (configCONST.BULLDOG_PLUGIN_PATH, eachPlugin)
                    cmds.loadPlugin('%s/%s.py' % (configCONST.BULLDOG_PLUGIN_PATH, eachPlugin))
                except RuntimeError:
                    cmds.warning('%s failed to load...' % eachPlugin)
            else:
                pass

    ## LOAD PLUGINS NOW
    loadPlugins()

    ## LOAD MAYA 2013 DEFAULT MEL SCRIPTS NOW FROM THE UI FOLDERS
    if '2013' in configCONST.MAYA_VERSION:
        DEFAULT_MEL_SCRIPTS = ['sz_RenderView.mel', 'mayaPreviewRender.mel', 'mentalrayPreviewRender.mel', 'renderWindowPanel.mel']
        for eachMel in DEFAULT_MEL_SCRIPTS:
            try:
                mel.eval("source \"%s/%s/%s.mel\"" % (eachMel, configCONST.BULLDOG_SCRIPT_PATH, configCONST.BULLDOG_MAYA_VERSION))
                print '%s sourced successfully...\n' % eachMel
            except RuntimeError:
                print 'MEL LOAD FAILED: %s failed to load...' % eachMel