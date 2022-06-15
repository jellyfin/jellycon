# JellyCon

JellyCon is a lightweight Kodi add-on that lets you browse and play media files directly from your Jellyfin server within the Kodi interface. Think of it as a Thin client, compared to Jellyfin for Kodi, which integrates into Kodi itself.

JellyCon compared to the Jellyfin add-on, behaves more like a standard Kodi streaming add-on. Media is accessed primarily by going through the Add-ons -> JellyCon menu, however depending on what skin is being used custom shortcuts and widgets can be added to the home menu. It also allows easier switching between multiple Jellyfin servers or users since it doesn't have to rely on syncing all the metadata down. By not having metadata synced, it has to request info from the server which can take a bit more time when you're browsing, but you don't have to wait for the database to sync or keep it up to date. It's also compatible with other media sources and can be used with other add-ons without issue.


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
- A "Quick Connect" code will be displayed. Which can be used to Login without the need of credentials, once you enter it on your Jellyfin server under "User Settings" -> "Quick Connect"
- Alternatively you can select "Manual Login" to select a user from the list, or Manual Login using your username and password


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
