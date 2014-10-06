genericconfig
=============
##NOTES:
The following explains some of the constants and how they work in the config/const/configCONST.py
This config is designed to work off any custom naming you choose to use for the following base setup.

**ENV**     = Environment
**LND**     = Landscape
**BLD**     = Building
**CHAR**    = Characters
**VEH**     = Vehicles
**PROP**    = Prop
**CPROP**   = Character Prop
**LIB**     = Library Asset
**SURFVAR** = Surface Variables eg paint on a roof top color changes etc


##Scene Assembly Notes:
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
####USE_BULLDOG_UI:
Set this to True if you have downloaded and installed the Bulldog UI otherwise set this to False to avoid the userSetup.py
from failing looking for plugins used by the UI.

####USE_BONUSTOOLS:
Is a WIP at this time, unfortunately getting the 2014 / 2015 bonus tools to sit outside their
default locations is something I don't have the energy to work around at this time. install them clean and use em
from their defaults for now on each operators machine. Consider this constant a place holder for now.

####FORCE_USERSETUP_REINSTALL:
This is used to force a copy of the userSetup.py into each users scripts folder. If you're updating and testing leave this set to
True else you can stop copying this file by turing it to False and use this boolean as an `updater'

####DEBUGGING:
Used by the logger stuff to turn on the loggers verbose attr. If you want to turn off the reporting to the script editor set this
to False and this will stop the logging from outputting.

####SHOTGUN_CONFIG_NAME:
Make sure this matches the name of the project you are working on. Or the config the project is using...

####SHOTGUN_URL:
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
