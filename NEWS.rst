====
News
====

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog
<https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to
`Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

[Unreleased]
============

Added
-----

- Dialog to enter name of playlist to create `#45
  <https://github.com/orontee/argos/issues/45>`_

Changed
-------

Removed
-------

[1.12.0] - 2023-05-11
=====================

Added
-----

- Playlist tracks use names set in playlists `#137
  <https://github.com/orontee/argos/issues/137>`_

- Download images for directories `#136
  <https://github.com/orontee/argos/issues/136>`_

Changed
-------

- Fix type error while sorting library `#139
  <https://github.com/orontee/argos/issues/139>`_

- Various minor fixes applied while writing automatic tests `#138
  <https://github.com/orontee/argos/issues/138>`_

Removed
-------

- Image requests aren't cached anymore since images are written to
  file system `#140 <https://github.com/orontee/argos/issues/140>`_

[1.11.0] - 2023-03-02
=====================

Added
-----

- Added Dutch translation `#135
  <https://github.com/orontee/argos/issues/135>`_

[1.10.0] - 2023-02-26
=====================

Added
-----
- Complete actions exposed through D-Bus `#134
  <https://github.com/orontee/argos/issues/134>`_
- Progress bar to track directory completion progress `#132
  <https://github.com/orontee/argos/issues/132>`_
- Choice to randomly generate a tracklist with length constraint `#131
  <https://github.com/orontee/argos/issues/131>`_
- Setting for the strategy used to select random tracks (default to random disc
  tracks) `#130 <https://github.com/orontee/argos/issues/130>`_

Changed
-------
- Avoid running concurrent tasks browsing the same directory `#133
  <https://github.com/orontee/argos/issues/133>`_
- Removing selected tracks don't remove all tracks when empty selection
  `#128 <https://github.com/orontee/argos/issues/128>`_
- Fix parse error when saving playlists that haven't been loaded `#128
  <https://github.com/orontee/argos/issues/128>`_
- Smarter dates in history playlist `#129
  <https://github.com/orontee/argos/issues/129>`_

[1.9.0] - 2023-01-30
====================

Added
-----
- Delete keys remove tracks from tracklist or playlist `#118
  <https://github.com/orontee/argos/issues/118>`_
- Browsing a directory with tracks only now displays a view with usual
  actions on tracks `#125 <https://github.com/orontee/argos/issues/125>`_
- A generic backend is added to display any directory `#123
  <https://github.com/orontee/argos/issues/123>`_

Changed
-------
- Only albums handled by Mopidy-Podcast are filtered out from random choice
  candidates `#123 <https://github.com/orontee/argos/issues/123>`_
- The Tracks directory exposed by Mopidy-Local isn't hidden anymore (better
  configure Mopidy-Local, see configuration key named `directories`) `#123
  <https://github.com/orontee/argos/issues/123>`_
- Refresh library updates visited directory `#115
  <https://github.com/orontee/argos/issues/115>`_

[1.8.0] - 2023-01-16
====================

Added
-----
- HTTP session can use a SQLite cache when library
  `aiohttp_client_cache` is installed `#111
  <https://github.com/orontee/argos/issues/111>`_
- Generic library browser supporting Mopidy-File `#110
  <https://github.com/orontee/argos/issues/110>`_
- Support for Mopidy-SomaFM `#107
  <https://github.com/orontee/argos/issues/107>`_

Changed
-------
- Library browsing execute in a task to allow other tasks to run `#57
  <https://github.com/orontee/argos/issues/57>`_
- Default is now to enable all backends `#110
  <https://github.com/orontee/argos/issues/110>`_
- Artist name is extracted from album name for Mopidy-Bandcamp albums
  `#110 <https://github.com/orontee/argos/issues/110>`_

Removed
-------
- Recent playlist has been removed since Mopidy-Local exposes
  directories for last month and last week additions `#110
  <https://github.com/orontee/argos/issues/110>`_

[1.7.0] - 2022-12-31
====================

Added
-----
- Click on a disc number separator selects the corresponding album
  tracks `#108 <https://github.com/orontee/argos/issues/108>`_
- Information service collecting abstracts of album and artist pages
  from Wikipedia `#78 <https://github.com/orontee/argos/issues/78>`_

Changed
-------
- Take user locale into account when comparing strings `#105
  <https://github.com/orontee/argos/issues/105>`_
- Display close button in titlebar when window isn't fullscreen `#104
  <https://github.com/orontee/argos/issues/104>`_

[1.6.0] - 2022-12-12
====================

Added
-----
- Support fullscreen `#102
  <https://github.com/orontee/argos/issues/102>`_
- Display album name in bottom widget  `#101
  <https://github.com/orontee/argos/issues/101>`_
- Display time position in bottom widget `#94
  <https://github.com/orontee/argos/issues/94>`_

Changed
-------
- Labels automatically elide text `#99
  <https://github.com/orontee/argos/issues/99>`_
- Fix history playlist displaying more than "history max length" tracks `#97
  <https://github.com/orontee/argos/issues/97>`_

Removed
-------
- Removed ``start-maximized`` setting (use window's menu to toggle
  window state which is automatically restored at startup or use the
  new setting ``start-fullscreen``) `#102
  <https://github.com/orontee/argos/issues/102>`_

[1.5.0] - 2022-12-05
====================

Added
-----
- Bottom widget showing playing state `#93
  <https://github.com/orontee/argos/issues/93>`_
- Preference dialog switch to activate dark theme `#89
  <https://github.com/orontee/argos/issues/89>`_
- Add button to title bar to change album sort order `#85
  <https://github.com/orontee/argos/issues/85>`_
- New "by last modified date" entry in album sort choices `#84
  <https://github.com/orontee/argos/issues/84>`_
- Display disc numbers in album track list `#82
  <https://github.com/orontee/argos/issues/82>`_
- Display date in history playlist `#81
  <https://github.com/orontee/argos/issues/81>`_
- Setting to change size of images in albums window `#77
  <https://github.com/orontee/argos/issues/77>`_

Changed
-------
- Preference dialog switch to start maximized, replace command line option `#90
  <https://github.com/orontee/argos/issues/90>`_
- Use dialog to display random chosen album before enqueuing `#88
  <https://github.com/orontee/argos/issues/88>`_
- Don't clear albums search filter when entering album details page
  (reopened) `#46 <https://github.com/orontee/argos/issues/46>`_
- Center vertically playing track image and album image `#87
  <https://github.com/orontee/argos/issues/87>`_
- Toggle visibility of title bar search and sort buttons on main page change `#85
  <https://github.com/orontee/argos/issues/85>`_
- Fix duplicated tracks for albums handled by ``MopidyPodcastBackend``
  `#83 <https://github.com/orontee/argos/issues/83>`_
- Reorganize preferences dialog `#77
  <https://github.com/orontee/argos/issues/77>`_
- History playlist can contain duplicated tracks `#80
  <https://github.com/orontee/argos/issues/80>`_

Removed
-------
- Remove "needs attention" support since playback state is now always
  visible `#93 <https://github.com/orontee/argos/issues/93>`_
- Remove album sort choice from preferences dialog `#86
  <https://github.com/orontee/argos/issues/86>`_

[1.4.0] - 2022-10-19
====================

Added
-----
- German translation `#63
  <https://github.com/orontee/argos/issues/63>`_
- Welcome dialog for users to direct users to the configuration dialog `#43
  <https://github.com/orontee/argos/issues/43>`_
- CSS identifiers to allow for style customization  `#72
  <https://github.com/orontee/argos/issues/72>`_
- Display labels with links when tracklist is empty `#71
  <https://github.com/orontee/argos/issues/71>`_
- Fix playlist widgets sensitivity in preferences dialog `#70
  <https://github.com/orontee/argos/issues/70>`_
- Display placeholder for empty tracks box of playlist `#61
  <https://github.com/orontee/argos/issues/61>`_

Changed
-------
- Simplify playlists box layout `#74
  <https://github.com/orontee/argos/issues/74>`_
- Reorganize preferences dialog to fix album sort selection `#54
  <https://github.com/orontee/argos/issues/54>`_
- "Add stream to tracklist" action replaces "play stream" action, and
  choice is given to play stream immediately or not `#68
  <https://github.com/orontee/argos/issues/68>`_
- Complete desktop and AppStream metadata file `#62
  <https://github.com/orontee/argos/issues/62>`_
- Handle tracks without name `#66
  <https://github.com/orontee/argos/issues/66>`_
- Lazy load of playlist descriptions `#61
  <https://github.com/orontee/argos/issues/61>`_

[1.3.0] - 2022-09-17
====================

Added
-----
- Restore application window state at startup `#52
  <https://github.com/orontee/argos/issues/52>`_
- Document software architecture `#51
  <https://github.com/orontee/argos/issues/51>`_
- New setting to exclude backends from random album selection `#44
  <https://github.com/orontee/argos/issues/44>`_

Changed
-------
- Fix sensitivity of play and add buttons in playlist view `#59
  <https://github.com/orontee/argos/issues/59>`_
- Force update of current tracklist track identifier to synchronize
  views `#56 <https://github.com/orontee/argos/issues/56>`_
- Don't automatically select first album track `#53
  <https://github.com/orontee/argos/issues/53>`_

[1.2.0] - 2022-08-30
====================

Added
-----
- Start documentation page `#12
  <https://github.com/orontee/argos/issues/12>`_
- Support download of images with ``http`` URI scheme `#48
  <https://github.com/orontee/argos/issues/48>`_
- Support for Mopidy-Jellyfin backend `#48
  <https://github.com/orontee/argos/issues/48>`_

Changed
-------
- Make sure descriptions of static albums are collected only once `#49
  <https://github.com/orontee/argos/issues/49>`_
- Default is now to enable backend for Mopidy-Local `#43
  <https://github.com/orontee/argos/issues/43>`_
- Limit size of request to fetch album images URIs `#48
  <https://github.com/orontee/argos/issues/48>`_

[1.1.2] - 2022-08-26
====================

Changed
-------
- Listen to key events with Mod1 and Shift modifiers `#47
  <https://github.com/orontee/argos/issues/47>`_
- Don't clear albums search filter when entering album details page `#46
  <https://github.com/orontee/argos/issues/46>`_

[1.1.1] - 2022-08-21
====================

Changed
-------
- Remove usage of stock icon for the application icon `#12
  <https://github.com/orontee/argos/issues/12>`_
- Upgrade version of Flatpak runtime version  `#12
  <https://github.com/orontee/argos/issues/12>`_

[1.1.0] - 2022-08-21
====================

Added
-----
- Add a stream URI to the tracklist `#38
  <https://github.com/orontee/argos/issues/38>`_
- Play or enqueue a track selection `#33
  <https://github.com/orontee/argos/issues/33>`_
- Option to disable/enable Mopidy backends in preference dialog `#23
  <https://github.com/orontee/argos/issues/23>`_
- Option to disable/enable history and recent additions playlists in
  preference dialog `#20
  <https://github.com/orontee/argos/issues/20>`_
- CLI argument to hide album search widget `#15
  <https://github.com/orontee/argos/issues/15>`_
- Automatically hide volume button when Mopidy mixer is disabled `#16
  <https://github.com/orontee/argos/issues/16>`_
- Virtual playlists for recently added and recently played tracks `#4
  <https://github.com/orontee/argos/issues/4>`_
- Listen to playlists related events `#1 <https://github.com/orontee/argos/issues/1>`_
- Support desktop notifications `#2
  <https://github.com/orontee/argos/issues/2>`_

Changed
-------
- Computation of album artist name `#39
  <https://github.com/orontee/argos/issues/39>`_
- Album cover don't show up for albums discovered after user clicked
  on "refresh album library" `#31
  <https://github.com/orontee/argos/issues/31>`_
- Album details page shouldn't display previously selected album
  details temporarily `#28
  <https://github.com/orontee/argos/issues/28>`_
- Window height isn't constant `#27
  <https://github.com/orontee/argos/issues/27>`_
- Entering album details page twice shows wrong album details `#26
  <https://github.com/orontee/argos/issues/26>`_
- Playlist and albums browse happen too early `#9
  <https://github.com/orontee/argos/issues/9>`_

Removed
-------
- Remove hardcoded URI from support for Mopidy-Podcast `#19
  <https://github.com/orontee/argos/issues/19>`_

[1.0.0] - 2022-05-22
====================

First version with most notable features:

- Library browser populated with albums from Mopidy-Local,
  Mopidy-Bandcamp and Mopidy-Podcast
- View of Mopidy-M3U playlists
- Playback state & tracklist view
