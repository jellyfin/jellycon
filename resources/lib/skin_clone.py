
import os
import xbmc
import xbmcvfs
import xbmcgui
import xbmcvfs

from json_rpc import json_rpc
from simple_logging import SimpleLogging
from translation import string_load

log = SimpleLogging(__name__)
ver = xbmc.getInfoLabel('System.BuildVersion')[:2]

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


def get_value(name):
    result = json_rpc('Settings.getSettingValue').execute({'setting': name})
    return result['result']['value']


def set_value(name, value):
    params = {
        'setting': name,
        'value': value
    }
    result = json_rpc('Settings.setSettingValue').execute(params)
    log.debug("Save Setting : {0} : {1} : {2} : {3}", name, value, type(value), result)


def clone_skin():
    log.debug("Cloning Estuary Skin")

    response = xbmcgui.Dialog().yesno(string_load(30354), string_load(30356), string_load(30355))
    if not response:
        return

    kodi_path = xbmc.translatePath("special://xbmc")
    kodi_skin_source = os.path.join(kodi_path, "addons", "skin.estuary")
    log.debug("Kodi Skin Source: {0}", kodi_skin_source)

    pdialog = xbmcgui.DialogProgress()
    pdialog.create(string_load(30354), "")

    all_files = []
    walk_path(kodi_skin_source, "", all_files)
    for found in all_files:
        log.debug("Found Path: {0}", found)

    kodi_home_path = xbmc.translatePath("special://home")
    kodi_skin_destination = os.path.join(kodi_home_path, "addons", "skin.estuary_embycon")
    log.debug("Kodi Skin Destination: {0}", kodi_skin_destination)

    # copy all skin files (clone)
    count = 0
    total = len(all_files)
    for skin_file in all_files:
        percentage_done = int(float(count) / float(total) * 100.0)
        pdialog.update(percentage_done, "%s" % skin_file)

        source = os.path.join(kodi_skin_source, skin_file)
        destination = os.path.join(kodi_skin_destination, skin_file)
        xbmcvfs.copy(source, destination)

        count += 1

    # alter skin addon.xml
    addon_xml_path = os.path.join(kodi_skin_destination, "addon.xml")
    with open(addon_xml_path, "r") as addon_file:
        addon_xml_data = addon_file.read()

    addon_xml_data = addon_xml_data.replace("id=\"skin.estuary\"", "id=\"skin.estuary_embycon\"")
    addon_xml_data = addon_xml_data.replace("name=\"Estuary\"", "name=\"Estuary EmbyCon\"")

    #log.debug("{0}", addon_xml_data)

    # update the addon.xml
    with open(addon_xml_path, "w") as addon_file:
        addon_file.write(addon_xml_data)

    # get embycon path
    embycon_path = os.path.join(kodi_home_path, "addons", "plugin.video.embycon")

    log.debug("Major Version: {0}", ver)

    # copy the Home.xml file
    source = os.path.join(embycon_path, "resources", "skins", "skin.estuary", ver, "xml", "Home.xml")
    destination = os.path.join(kodi_skin_destination, "xml", "Home.xml")
    xbmcvfs.copy(source, destination)

    # copy the Includes_Home.xml file
    source = os.path.join(embycon_path, "resources", "skins", "skin.estuary", "xml", ver, "Includes_Home.xml")
    destination = os.path.join(kodi_skin_destination, "xml", "Includes_Home.xml")
    xbmcvfs.copy(source, destination)

    # copy the DialogVideoInfo.xml file
    source = os.path.join(embycon_path, "resources", "skins", "skin.estuary", "xml", ver, "DialogVideoInfo.xml")
    destination = os.path.join(kodi_skin_destination, "xml", "DialogVideoInfo.xml")
    xbmcvfs.copy(source, destination)

    xbmc.executebuiltin("UpdateLocalAddons")

    pdialog.close()
    del pdialog

    response = xbmcgui.Dialog().yesno(string_load(30354), string_load(30357), string_load(30358))
    if not response:
        return

    params = {
        'addonid': "skin.estuary_embycon",
        'enabled': True
    }
    result = json_rpc('Addons.SetAddonEnabled').execute(params)
    log.debug("Addons.SetAddonEnabled : {0}", result)

    log.debug("SkinCloner : Current Skin : " + get_value("lookandfeel.skin"))
    set_value("lookandfeel.skin", "skin.estuary_embycon")

