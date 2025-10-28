# JellyCon

JellyCon is a lightweight Kodi add-on that lets you browse and play media files directly from your Jellyfin server within the Kodi interface.  It can be thought of as a thin frontend for a Jellyfin server.

JellyCon can be used with Movie, TV Show, Music Video, and Music libraries, in addition to viewing LiveTV from the server.  It can easily switch between multiple user accounts at will.  It's easy to integrate with any customizable Kodi skin with a large collection of custom menus.  Media items are populated from the server dynamically, and menu speed will vary based on local device speed.

## 🚀 Enhanced Fork Features

This fork includes significant navigation enhancements that provide multiple intuitive ways to browse your Jellyfin media libraries:

### 🗂️ Folder Navigation System
- **File-System Style Browsing**: Navigate your media libraries like desktop file explorers with intuitive folder-based navigation
- **Parent Navigation**: Automatic ".. (Parent)" or ".. (Root)" navigation for easy backtracking through folder structures
- **Complete Library Exploration**: "All Folders" option for comprehensive library browsing
- **Performance Optimized**: Efficient API usage with proper caching for smooth navigation

### ⭐ Enhanced Favorites Organization
- **Unified Favorites View**: Single comprehensive view of all your favorited content
- **Categorized Favorites**: Organized folder view with media type categories:
  - Movies
  - TV Shows
  - Music
  - Other Media (BoxSets, MusicVideos, Photos, Books, Games)
- **Improved Discovery**: Better navigation and content discovery for your favorite items

### 🎭 Genre Browsing Integration
- **Four Genre Categories**:
  - Movie Genres
  - TV Show Genres
  - Music Genres
  - Mixed Genres (Movies & TV Shows combined)
- **Enhanced Content Discovery**: New way to explore content through genre preferences

### 🧭 Navigation Consolidation
- **Organized Library Access**: All browsing methods consolidated under "Jellyfin Libraries"
- **Cleaner Main Menu**: Reduced clutter with only essential high-level options
- **Multiple Navigation Methods**: Choose from folder browsing, favorites, or genre-based exploration

### Using Enhanced Navigation

**Folder Navigation**:
- Navigate to "Jellyfin Libraries" → "Browse Folders"
- Browse your libraries using intuitive file-system style navigation
- Use ".. (Parent)" to move up folder levels

**Organized Favorites**:
- Navigate to "Jellyfin Libraries" → "All Favorites" for a comprehensive view
- Or use "Favorites by Type" for categorized browsing

**Genre Browsing**:
- Navigate to "Jellyfin Libraries" → "Browse Genres"
- Choose from Movie, TV Show, Music, or Mixed genre categories

### Manual Building from Source

To build from source, clone this repository and switch to the `enhancements2` branch:

```bash
# Clone the repository
git clone https://github.com/bpawnzZ/jellycon.git
cd jellycon

# Switch to the enhancements2 branch (contains latest features)
git checkout enhancements2

# Build the addon ZIP files
python build.py --version py3  # For Python 3/Kodi 19+
python build.py --version py2  # For Python 2/Kodi 18 and earlier

# This creates:
# - plugin.video.jellycon+py3.zip (Python 3/Kodi 19+)
# - plugin.video.jellycon+py2.zip (Python 2/Kodi 18 and earlier)

# Install in Kodi via:
# Add-ons → Install from zip file
```

**Build Options**:
- `--version py3` (default): Build for Python 3/Kodi 19+
- `--version py2`: Build for Python 2/Kodi 18 and earlier
- `--dev`: Include development files in the build

**Note**: The build script automatically generates the addon.xml file and packages all necessary files into the ZIP archive.

----------------------------------------------------------------------------------------
EVERYTHING BELOW HERE WAS INCLUDED IN ORIGINAL README.md from upstream repo.

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
