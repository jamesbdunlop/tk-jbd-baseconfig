"""
Created by James Dunlop

NOTES:
This config is designed to work off any custom naming you choose to use for the following base setup.
ENV     = Environment
LND     = Landscape
BLD     = Building
CHAR    = Characters
VEH     = Vehicles
PROP    = Prop
CPROP   = Character Prop
LIB     = Library Asset
SURFVAR = Surface Variables eg paint on a roof top color changes etc

Scene Assembly Notes:
Environments are made up of of landscapes(LND) and buildings(BLD) and can be used as the layout step.
How ever if you choose to model your LDN and BLD in position, you can force these to be checked for
valid transforms required for bounding boxes (maya needs the transforms to be maintained or the bbox
will be built to world-space representing the object to world x y z not object space!)
You can force a transform check for these by turning on the FORCE_TRANSFORM_CHECK by setting it to True
Note also that due to the way the assembly definitions and the scene breakdown tool work, it is necessary to alter
the base publishing approach so that scene names adopt a unified naming convention, which means that when artists
save their work with random names, these will be corrected on publish so that assemblyDefinitions work with the scenebreakdown
tool.
It is also important to note that if you have published a building assembly definition for use in an environment scene, if you
publish this again but as a RIG not a MODEL you will have to manually update the building in the environment file to the RIG Assembly
Definition path for the scene breakdown tool to start working again.

Adding Constants from this file to to tk-envReporter:
If you add constants to this and by all means do, note you may want to add these into the tk-envReporter application if you want a quick way
to print out the current settings in maya. You'll have to do this manually.

Layout:
If you use the ENV to layout your ADefs don't bother rigging just for positional changes, you can use the base transform of the ADef and this will
ensure that ALL representations will show up in the correct positions.

## Notes on various settings:
USE_BULLDOG_UI:
    Set this to True if you have downloaded and installed the Bulldog UI otherwise set this to False to avoid the userSetup.py
    from failing looking for plugins used by the UI.

USE_BONUSTOOLS:
    Is a WIP at this time, unfortunately getting the 2014 / 2015 bonus tools to sit outside their
    default locations is something I don't have the energy to work around at this time. install them clean and use em
    from their defaults for now on each operators machine. Consider this constant a place holder for now.

FORCE_USERSETUP_REINSTALL:
    This is used to force a copy of the userSetup.py into each users scripts folder. If you're updating and testing leave this set to
    True else you can stop copying this file by turing it to False and use this boolean as an `updater'

DEBUGGING:
    Used by the logger stuff to turn on the loggers verbose attr. If you want to turn off the reporting to the script editor set this
    to False and this will stop the logging from outputting.

SHOTGUN_CONFIG_NAME:
    Make sure this matches the name of the project you are working on. Or the config the project is using...

SHOTGUN_URL:
    This is used by the python-api shotgun api to instantiate a shotgun server it's the url of your website hosting the shotgun projects

SHOTGUN_TOOLKIT_NAME:
    This is the default name of the tool kit script you should already have setup on shotgun

SHOTGUN_TOOLKIT_API_KEY:
    The Toolkit api key

SAVEWRK_PREPRIMARY_PUBLISH:
    Is used if you wish to force a save of the current scene during the primary publish
    BEFORE it does the primary publish. Usually Shotgun will complain if the scene isn't saved on publish forcing the
    artist to save prior to being able to publish, but you can turn on a forced save by turning this to True.

INSIST_PREFIX_IN_ROOT:
    Used for Asset Publishing on the scan scene hooks. If your root assetName needs to contain the prefix associated with it turning this to
    True will force a check for the prefix. eg:
    CHAR_BigBill_hrc
    BigBill_hrc <-- will fail the check if this is set to True as it is missing the CHAR prefix.
    This check is performed in the assetCheckAndTag function in the defaultMayaLibrary.maya_asset_lib.py file
    It is mainly used to make sure you're trying to check in an asset into the right context, eg if you are trying to check in a BLD using the CHAR
    publishing menu it will fail because CHAR isn't in the root _hrc name.

BUILDING_SUFFIX:
    This defines a building prefix used across the config. It should match your naming convention in shotgun!!!
    Where? This is a prefix used in the actual ASSSETNAME_SUFFIX if you are not using one, set these to empty strings.
    eg: if you are calling buildings MyBuilding_BULD in shotgun change this to be BULD
    This applies to the following constants too:
    ENVIRONMENT_SUFFIX, CHAR_SUFFIX, LND_SUFFIX, PROP_SUFFIX, CPROP_SUFFIX, LIB_SUFFIX

SHOTGUN_SOFTWARE_ROOT:
    This is the install location for your shotgun stuff ie where studio sits and this config sits in relation to your studios infrastructure.

SHOTGUN_PRIMARY_DRIVE:
    The primary drive as in your project setup on the shotgun website.

SHOTGUN_SECONDARY_DRIVE:
    The secondary drive as in your project setup on the shotgun website. Note this is a multiconfig setup so you need to have this setup as well for this
    config to function correctly!

MAYA_APP_DIR_ROOT:
    The location you want to setup the projects MAYA_APP_DIR. This is the area all the artists will create their prefs into for maya when
    launching from the shotgun website.

ALL Assets are expected to follow the following setup:
    'rootName_%s' % GROUP_SUFFIX
        '%s_%s' % (GEO_SUFFIX, GROUP_SUFFIX)
        'rig_%s' % GROUP_SUFFIX
        'parts_%s' % GROUP_SUFFIX
eg:
    CHAR_MYCHARNAME_hrc
        geo_hrc
            [geo groups]
        rig_hrc
            [rig control groups]
        parts_hrc
            [rig parts groups]

Subdivision Handling:
Anything set to smoothlevelpreview 3 in the MDL or RIG steps will be tagged with a smoothed attribute. This will either be True or True depending on if it is
smoothed or not. This attr will head all the way through to lighting, where we attach the relevant subdivision nodes to those geometries set to True! So
it is VERY important to check in the MDL and RIG steps with the anticipated final smoothing | subdivision setups.
"""
## Import base python stuff
import sys, getpass

#############################################
## CONFIG CONSTANTS
#############################################
## SOME CUSTOM FLAGS FOR THINGS TO DO OR USE
USE_BULLDOG_UI                  = True
USE_BONUSTOOLS                  = True
FORCE_USERSETUP_REINSTALL       = True
DEBUGGING                       = True

## SETUP BASE CONSTANTS FOR THE CONFIG
USER_NAME                       = '%s' % getpass.getuser()
MAYA_VERSION                    = '2016'
BULLDOG_MAYA_VERSION            = '2015'
LOGFILE_NAME                    = 'tankLog'
## SHOT GUN BASE CONSTANTS
SHOTGUN_CONFIG_NAME             = 'genericconfig'
SHOTGUN_URL                     = 'https://framespersecond.shotgunstudio.com'                           #[INSERT YOUR URL HERE eg https://mystudio.shotgunstudio.com AS A STRING]
SHOTGUN_TOOLKIT_NAME            = 'Toolkit'
SHOTGUN_TOOLKIT_API_KEY         = '724eea86a7f9fe4816278f2188382eacf42834a2b5cb85f814f125e96078a3b3'    #[INSERT YOUR SHOTGUN API KEY HERE AS A STRING]

GOZ_PUBLIC_CACHEPATH            = 'C:\Users\Public\Pixologic\GoZProjects\Default'
## DEFAULT STUFF FOR THE CONFIG
## Save the maya scene before you do a primary publish?
SAVEWRK_PREPRIMARY_PUBLISH      = True
## Force a check to make sure the prefixes are in the root nodes hrc name or not
INSIST_PREFIX_IN_ROOT           = False
## Force the transform check if the buildings are to be modelled in situ
FORCE_TRANSFORM_CHECK           = False

## Shotguns default asset task short names
RIG_SHORTNAME                   = 'Rig'
MODEL_SHORTNAME                 = 'Model'
SURFACE_SHORTNAME               = 'Surface'
ART_SHORTNAME                   = 'Art'

## Shotguns default shot task short names
ANIM_SHORTNAME                  = 'Anm'
COMP_SHORTNAME                  = 'Comp'
LIGHT_SHORTNAME                 = 'Light'
LAYOUT_SHORTNAME                = 'Lay'
FX_SHORTNAME                    = 'FX'

## Define some maya prefixes for use in checks and apps across the config.
BUILDING_SUFFIX                 = 'BLD'
SG_BLD_TYPE_NAME                = 'Building'

ENVIRONMENT_SUFFIX              = 'ENV'
SG_ENV_TYPE_NAME                = 'Environment'

CHAR_SUFFIX                     = 'CHAR'
SG_CHAR_TYPE_NAME               = 'Character'

LND_SUFFIX                      = 'LND'
SG_LND_TYPE_NAME                = 'Landscape'

PROP_SUFFIX                     = 'PROP'
SG_PROP_TYPE_NAME               = 'Prop'

CPROP_SUFFIX                    = 'CPROP'

LIB_SUFFIX                      = 'LIB'

VEH_SUFFIX                      = 'VEH'
SG_VEH_TYPE_NAME                = 'Vehicle'

SURFVAR_PREFIX                  = 'SRFVar'

###################################################################################################################
## NOTE!!! If you change these you MUST MANUALLY CHANGE THEM IN THE asset_step.yml and the shot_step.yml as well!!!
ASSEMBLYDEF_SUFFIX              = 'ADEF'

###################################################################################################################

## MAYA NAMING CONVENTIONS
GROUP_SUFFIX                    = 'hrc'
GEO_SUFFIX                      = 'geo'
NURBSCRV_SUFFIX                 = 'crv'
IMPORT_SUFFIX                   = 'importDELME'
SHOTCAM_SUFFIX                  = 'shotCam'

LIGHTINGCLEANUP                 = ['parts_hrc', 'rig_hrc', '']

## Really important to note here that these are matced to the TYPE names in the tk-jbd-lighting-fetchcaches application
ANIM_CACHE                      = 'AnimationCaches'
STATIC_CACHE                    = 'StaticCaches'
CAMERA_CACHE                    = 'CameraCaches'
GPU_CACHE                       = 'GpuCaches'
FX_CACHE                        = 'FxCaches'
## Set platform dependant config constants
if sys.platform == 'win32':
    ## OS specific
    TEMP_FOLDER                 = 'C:\\Temp'
    OSTYPE                      = 'win'

    ## Shotgun specific
    SHOTGUN_SOFTWARE_ROOT       = 'T:/software'
    SHOTGUN_PRIMARY_DRIVE       = 'I:'
    SHOTGUN_SECONDARY_DRIVE     = 'K:'
    SHOTGUN_CONFIG_PATH         = '%s/%s' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME)
    SHOTGUN_ICON_PATH           = '%s/%s/config/icons' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME)
    TANKCORE_PYTHON_PATH        = '%s/studio/install/core/python' % SHOTGUN_SOFTWARE_ROOT
    SGTK_PYTHON_PATH            = '%s/python-api' % SHOTGUN_SOFTWARE_ROOT
    SHOTGUN_LIBRARY_PATH        = '%s/defaultShotgunLibrary' % SHOTGUN_SOFTWARE_ROOT
    SHOTGUN_DEVAPPS_PATH        = '%s/install/apps' % SHOTGUN_CONFIG_PATH

    ## Maya Specific
    MAYA_APP_DIR_ROOT           = 'T:'
    MAYA_APP_DIR                = '%s/%s_APPDIR' % (MAYA_APP_DIR_ROOT, SHOTGUN_CONFIG_NAME)
    MAYA_USER_APP_DIR           = '%s/%s_APPDIR/%s' % (MAYA_APP_DIR_ROOT, SHOTGUN_CONFIG_NAME, USER_NAME)
    MAYA_CONFIG_BASE            = '%s/%s' % (MAYA_USER_APP_DIR, MAYA_VERSION)
    MAYA_CONFIG_SCRIPT_PATH     = "%s/scripts" % MAYA_CONFIG_BASE
    MAYA_CONFIG_PREFS_PATH      = '%s/prefs/' % MAYA_CONFIG_BASE
    MAYA_CONFIG_SHELVES_PATH    = '%s/prefs/shelves' % MAYA_CONFIG_BASE
    MAYA_DEFAULT_ENV            = '%s/%s/mayaEnv/%s' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME, MAYA_VERSION)
    MAYA_DEFAULT_USERSETUPPY    = '%s/userSetup.py' % MAYA_DEFAULT_ENV
    MAYA_PYTHON_LIB             = '%s/defaultMayaLibrary' % SHOTGUN_SOFTWARE_ROOT
    MAYA_SCRIPT_PATHS           = []

    ## Animation publishing..
    ALEMBIC_BATCH_NAME          = '%s_animCacheExport.bat' % getpass.getuser() ## TO DO get a date time in here
    FX_BATCH_NAME               = '%s_FXCacheExport.bat' % getpass.getuser()   ## TO DO get a date time in here
    PATH_TO_ANIM_BAT            = r'%s/%s' % (TEMP_FOLDER, ALEMBIC_BATCH_NAME)
    PATH_TO_FX_BAT              = r'%s/%s' % (TEMP_FOLDER, FX_BATCH_NAME)


## OSX
elif sys.platform == 'darwin':
    ## OS specific
    TEMP_FOLDER                 = '/tmp'
    OSTYPE                      = 'osx'

    ## Shotgun specific
    SHOTGUN_SOFTWARE_ROOT       = '/volumes/development/software'
    SHOTGUN_PRIMARY_DRIVE       = '/volumes/projects'
    SHOTGUN_SECONDARY_DRIVE     = '/volumes/renders'
    SHOTGUN_CONFIG_PATH         = '%s/%s' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME)
    SHOTGUN_ICON_PATH           = '%s/%s/config/icons' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME)
    TANKCORE_PYTHON_PATH        = '%s/studio/install/core/python' % SHOTGUN_SOFTWARE_ROOT
    SGTK_PYTHON_PATH            = '%s/python-api' % SHOTGUN_SOFTWARE_ROOT
    SHOTGUN_LIBRARY_PATH        = '%s/defaultShotgunLibrary' % SHOTGUN_SOFTWARE_ROOT
    SHOTGUN_DEVAPPS_PATH        = '%s/install/apps' % SHOTGUN_CONFIG_PATH

    ## Maya Specific
    MAYA_APP_DIR_ROOT           = '/volumes/projects'
    MAYA_APP_DIR                = '%s/%s_APPDIR' % (MAYA_APP_DIR_ROOT, SHOTGUN_CONFIG_NAME)
    MAYA_USER_APP_DIR           = '%s/%s_APPDIR/%s' % (MAYA_APP_DIR_ROOT, SHOTGUN_CONFIG_NAME, USER_NAME)
    MAYA_CONFIG_BASE            = '%s/%s' % (MAYA_USER_APP_DIR, MAYA_VERSION)
    MAYA_CONFIG_SCRIPT_PATH     = "%s/scripts" % MAYA_CONFIG_BASE
    MAYA_CONFIG_PREFS_PATH      = '%s/prefs' % MAYA_CONFIG_BASE
    MAYA_CONFIG_SHELVES_PATH    = '%s/prefs/shelves' % MAYA_CONFIG_BASE
    MAYA_DEFAULT_ENV            = '%s/%s/mayaEnv/%s' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME, MAYA_VERSION)
    MAYA_DEFAULT_USERSETUPPY    = '%s/userSetup.py' % MAYA_DEFAULT_ENV
    MAYA_PYTHON_LIB             = '%s/defaultMayaLibrary' % SHOTGUN_SOFTWARE_ROOT

## LINUX
else:
    ## OS specific
    TEMP_FOLDER                 = '/tmp'
    OSTYPE                      = 'linux'

    ## Shotgun specific
    SHOTGUN_SOFTWARE_ROOT       = '/development'
    SHOTGUN_PRIMARY_DRIVE       = '/projects'
    SHOTGUN_SECONDARY_DRIVE     = '/renders'
    SHOTGUN_CONFIG_PATH         = '%s/%s' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME)
    SHOTGUN_ICON_PATH           = '%s/%s/config/icons' % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME)
    TANKCORE_PYTHON_PATH        = '%s/studio/install/core/python' % SHOTGUN_SOFTWARE_ROOT
    SGTK_PYTHON_PATH            = '%s/python-api' % SHOTGUN_SOFTWARE_ROOT
    SHOTGUN_LIBRARY_PATH        = '%s/defaultShotgunLibrary' % SHOTGUN_SOFTWARE_ROOT
    SHOTGUN_DEVAPPS_PATH        = '%s/install/apps' % SHOTGUN_CONFIG_PATH

    ## Maya Specific
    MAYA_APP_DIR_ROOT           = '/maya_appdir'
    MAYA_APP_DIR                = '%s/%s_APPDIR' % (MAYA_APP_DIR_ROOT, SHOTGUN_CONFIG_NAME)
    MAYA_USER_APP_DIR           = '%s/%s_APPDIR/%s' % (MAYA_APP_DIR_ROOT, SHOTGUN_CONFIG_NAME, USER_NAME)
    MAYA_CONFIG_BASE            = '%s/%s' % (MAYA_USER_APP_DIR, MAYA_VERSION)
    MAYA_CONFIG_SCRIPT_PATH     = "%s/scripts" % MAYA_CONFIG_BASE
    MAYA_CONFIG_PREFS_PATH      = '%s/prefs' % MAYA_CONFIG_BASE
    MAYA_CONFIG_SHELVES_PATH    = "%s/prefs/shelves" % MAYA_CONFIG_BASE
    MAYA_DEFAULT_ENV            = "%s/%s/mayaEnv/%s" % (SHOTGUN_SOFTWARE_ROOT, SHOTGUN_CONFIG_NAME, MAYA_VERSION)
    MAYA_DEFAULT_USERSETUPPY    = "%s/userSetup.py" % MAYA_DEFAULT_ENV
    MAYA_PYTHON_LIB             = "%s/defaultMayaLibrary" % SHOTGUN_SOFTWARE_ROOT

#######################
## BULLDOG UI CONSTANTS
## Note any additions to the script paths should be done AFTER these defaults as the index for these are used in the
## userSetup.py
BULLDOG_ROOT                    = '%s/bulldog' % SHOTGUN_SOFTWARE_ROOT
BULLDOG_SCRIPT_PATHS            = [
                                    '%s/bulldog/BDmaya/tools_freeMelScripts' % SHOTGUN_SOFTWARE_ROOT,
                                    '%s/bulldog/BDmaya/tools_freeMelScripts/%s' % (SHOTGUN_SOFTWARE_ROOT, BULLDOG_MAYA_VERSION)
                                    ]
BULLDOG_SYS_PATHS               = [
                                    '%s/' % SHOTGUN_SOFTWARE_ROOT,
                                    '%s/bulldog/BDmaya/tools_freeMelScripts' % SHOTGUN_SOFTWARE_ROOT,
                                    '%s/bulldog' % SHOTGUN_SOFTWARE_ROOT,
                                    ]
BULLDOG_XBM_PATHS               = [
                                    '%s/bulldog/BDmaya/tools_freeMelScripts/Icons' % SHOTGUN_SOFTWARE_ROOT,
                                    '%s/bulldog/BBicons/soup' % SHOTGUN_SOFTWARE_ROOT ]
BULLDOG_PLUGIN_PATHS            = [
                                    '%s/bulldog/BDmaya/plugins/%s/%s' % (SHOTGUN_SOFTWARE_ROOT, OSTYPE, BULLDOG_MAYA_VERSION)
                                    ]

#######################
## BASE SYS PATHS CONSTANTS
SYS_PATHS                       = [
                                    '%s/site-packages' % MAYA_DEFAULT_ENV,
                                    '%s' % SHOTGUN_LIBRARY_PATH,
                                    '%s' % TANKCORE_PYTHON_PATH,
                                    '%s' % SGTK_PYTHON_PATH,
                                    '%s' % MAYA_PYTHON_LIB,
                                    ]

MAYA_XBM_PATHS                  = []
MAYA_PLUGIN_PATHS               = []