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
- Add button to title bar to change album sort order `#85
  <https://github.com/orontee/argos/issues/85>`_
- New "by last modified date" entry in album sort choices `#84
  <https://github.com/orontee/argos/issues/84>`_
- Display date in history playlist `#82
  <https://github.com/orontee/argos/issues/82>`_
- Display date in history playlist `#81
  <https://github.com/orontee/argos/issues/81>`_
- Setting to change size of images in albums window `#77
  <https://github.com/orontee/argos/issues/77>`_

Changed
-------
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
