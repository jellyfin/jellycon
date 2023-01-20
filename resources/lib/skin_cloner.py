from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import os
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui
import xbmcvfs

from .jsonrpc import JsonRpc, get_value, set_value
from .lazylogger import LazyLogger
from .utils import translate_path, kodi_version

log = LazyLogger(__name__)


def clone_default_skin():
    xbmc.executebuiltin("Dialog.Close(all,true)")
    xbmc.executebuiltin("ActivateWindow(Home)")

    response = xbmcgui.Dialog().yesno(
        "JellyCon Skin Cloner",
        ("This will clone the default Estuary Kodi skin and"
         "add JellyCon functionality to it."),
        "Do you want to continue?")
    if not response:
        return

    clone_skin()
    set_skin_settings()
    update_kodi_settings()


def walk_path(root_path, relative_path, all_files):
    files = xbmcvfs.listdir(root_path)
    found_paths = files[0]
    found_files = files[1]

    for item in found_files:
        rel_path = os.path.join(relative_path, item)
        all_files.append(rel_path)

    for item in found_paths:
        new_path = os.path.join(root_path, item)
        rel_path = os.path.join(relative_path, item)
        all_files.append(rel_path)
        walk_path(new_path, rel_path, all_files)


def clone_skin():
    log.debug("Cloning Estuary Skin")

    kodi_path = translate_path("special://xbmc")
    kodi_skin_source = os.path.join(kodi_path, "addons", "skin.estuary")
    log.debug("Kodi Skin Source: {0}".format(kodi_skin_source))

    pdialog = xbmcgui.DialogProgress()
    pdialog.create("JellyCon Skin Cloner", "")

    all_files = []
    walk_path(kodi_skin_source, "", all_files)
    for found in all_files:
        log.debug("Found Path: {0}".format(found))

    kodi_home_path = translate_path("special://home")
    kodi_skin_destination = os.path.join(
        kodi_home_path, "addons", "skin.estuary_jellycon"
    )
    log.debug("Kodi Skin Destination: {0}".format(kodi_skin_destination))

    # copy all skin files (clone)
    count = 0
    total = len(all_files)
    for skin_file in all_files:
        percentage_done = int(float(count) / float(total) * 100.0)
        pdialog.update(percentage_done, skin_file)

        source = os.path.join(kodi_skin_source, skin_file)
        destination = os.path.join(kodi_skin_destination, skin_file)
        xbmcvfs.copy(source, destination)

        count += 1

    # alter skin addon.xml
    addon_xml_path = os.path.join(kodi_skin_destination, "addon.xml")
    addon_tree = ET.parse(addon_xml_path)
    addon_root = addon_tree.getroot()

    addon_root.attrib['id'] = 'skin.estuary_jellycon'
    addon_root.attrib['name'] = 'Estuary JellyCon'

    addon_tree.write(addon_xml_path)

    # get jellycon path
    jellycon_path = os.path.join(
        kodi_home_path, "addons", "plugin.video.jellycon"
    )

    log.debug("Major Version: {0}".format(kodi_version()))

    file_list = ["Home.xml",
                 "Includes_Home.xml",
                 "DialogVideoInfo.xml",
                 "DialogSeekBar.xml",
                 "VideoOSD.xml"]

    # Copy customized skin files from our addon into cloned skin
    for file_name in file_list:
        source = os.path.join(
            jellycon_path, "resources", "skins", "skin.estuary",
            str(kodi_version), "xml", file_name
        )
        destination = os.path.join(kodi_skin_destination, "xml", file_name)
        xbmcvfs.copy(source, destination)

    xbmc.executebuiltin("UpdateLocalAddons")

    pdialog.close()
    del pdialog

    response = xbmcgui.Dialog().yesno(
        "JellyCon Skin Cloner",
        "Do you want to switch to the new cloned skin?"
    )
    if not response:
        return

    params = {
        'addonid': "skin.estuary_jellycon",
        'enabled': True
    }
    result = JsonRpc('Addons.SetAddonEnabled').execute(params)
    log.debug("Addons.SetAddonEnabled : {0}".format(result))

    log.debug("SkinCloner : Current Skin : {}".format(
        get_value("lookandfeel.skin"))
    )
    set_result = set_value("lookandfeel.skin", "skin.estuary_jellycon")
    log.debug("Save Setting : lookandfeel.skin : {0}".format(set_result))
    log.debug("SkinCloner : Current Skin : {}".format(
        get_value("lookandfeel.skin"))
    )


def update_kodi_settings():
    log.debug("Settings Kodi Settings")

    set_value("videoplayer.seekdelay", 0)
    set_value("filelists.showparentdiritems", False)
    set_value("filelists.showaddsourcebuttons", False)
    set_value("myvideos.extractchapterthumbs", False)
    set_value("myvideos.extractflags", False)
    set_value("myvideos.selectaction", 3)
    set_value("myvideos.extractthumb", False)


def set_skin_settings():
    log.debug("Settings Skin Settings")

    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoPicturesButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoMusicButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoVideosButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoFavButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoTVButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoWeatherButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoMusicVideoButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoRadioButton)")
    xbmc.executebuiltin("Skin.SetBool(no_slide_animations)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoMovieButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoTVShowButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoGamesButton)")
    xbmc.executebuiltin("Skin.Reset(HomeMenuNoProgramsButton)")
