# JellyCon

JellyCon is a lightweight Kodi add-on that lets you browse and play media files directly from your Jellyfin server within the Kodi interface.  It can be thought of as a thin frontend for a Jellyfin server.

JellyCon can be used with Movie, TV Show, Music Video, and Music libraries, in addition to viewing LiveTV from the server.  It can easily switch between multiple user accounts at will.  It's easy to integrate with any customizable Kodi skin with a large collection of custom menus.  Media items are populated from the server dynamically, and menu speed will vary based on local device speed.


## Installation

#### 1. Adding the Jellyfin repository

https://jellyfin.org/docs/general/clients/kodi.html#install-add-on-repository

#### 2. Install JellyCon Add-on

- From within Kodi, navigate to "Add-on Browser"
- Select "Install from Repository"
- Choose "Kodi Jellyfin Add-ons", followed by "Video Add-ons"
- Select the JellyCon add-on and choose install

#### 3. Login

- Within a few seconds after the installation you should be prompted for your server details.
- If a Jellyfin server is detected on your local network, it will displayed in a dialog. Otherwise, you will be prompted to enter the URL of your Jellyfin server
- If Quick Connect is enabled in the server, a code will be displayed that you can use to log in via Quick Connect in the web UI or a mobile app.
- If Quick Connect is not enabled, or if you select the "Manual Login" button, you will be able to select a user from the list, or manually login using your username and password.


## Configuration

#### Configuring Home

Many Kodi skins allow for customizing of the home menu with custom nodes and widgets. However, all of these use slightly different layouts and terminology. Rather than a step by step guide, this section serves as an barebones introduction to customizing a skin.
Examples

If you would like a link on the home screen to open a library in your Jellyfin server called "Kid's Movies", you would point the menu item to the path: Add-On -> Video Add-On -> JellyCon -> Jellyfin Libraries -> Kid's Movies -> Create menu item to here.

Beyond just modifying where the home menu headers go, many skins also allow you to use widgets. Widgets help populate the home screen with data, often the posters of media in the selected image. If you would like to display the most recent movies across all of your Jellyfin libraries on the home screen, the path would be: Add-On -> Video Add-On -> JellyCon -> Global Lists -> Movies -> Movies - Recently Added (20) -> Use as widget

Another common use case of widgets would be to display the next available episodes of shows that you may be watching. As above, this can be done both with individual libraries or with all libraries combined:

    Add-On -> Video Add-On -> JellyCon -> Jellyfin Libraries -> Anime -> Anime - Next Up (20) -> Use as widget
    Add-On -> Video Add-On -> JellyCon -> Global Lists -> TV Shows -> TV Shows - Next Up (20) -> Use as widget


## License

JellyCon is licensed under the terms of the [GPLv2](LICENSE.txt).
