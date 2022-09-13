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
- New setting to exclude backends from random album selection `#44
  <https://github.com/orontee/argos/issues/44>`_

Changed
-------

Removed
-------

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
