'''
    @license    : Gnu General Public License - see LICENSE.TXT

    This is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with software.  If not, see <http://www.gnu.org/licenses/>.
    
    Thanks to Hippojay for the PleXBMC plugin this is derived from
    This software is derived form the XBMB3C addon
    
'''

import os

import xbmcplugin
import xbmcgui
import xbmcaddon

__settings__ = xbmcaddon.Addon(id='plugin.video.embycon')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)

import Functions

Functions.mainEntryPoint()
    
#clear done and exit.
#sys.modules.clear()


