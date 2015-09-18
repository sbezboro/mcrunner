Configuration
=============

By default `mcrunnerd` and `mcrunner` look at /etc/mcrunner/mcrunner.conf for configuration.

The configuration file contains three different sections, `[mcrunnerd]`, `[mcrunner]` and `[server:<name>]`.

``[mcrunnerd]`` section
-----------------------

This section contains properties used by the daemon process.

``logfile``

  Filepath to the log file used for `mcrunnerd`.

  *Default*: ``/var/log/mcrunner/mcrunnerd.log``

  *Required*: yes

``user``

  UNIX username used to setuid on startup.

  *Default*: none

  *Required*: no

``[mcrunner]`` section
----------------------

This section contains properties used by the client process.

``url``

  Path to a UNIX socket used for communication between `mcrunnerd` and `mcrunner`

  *Default*: ``/tmp/mcrunner.sock``

  *Required*: yes

``[server:<name>]`` section
---------------------------

This section contains properties for a Minecraft server that MCRunner should manage.
This section can appear multiple times as long as the server names are unique.
The name is used when interfacing with the `mcrunner` command line.

``path``

  Path to a Minecraft server root directory containing the main jar and other data.

  *Default*: none

  *Required*: yes

``jar``

  Filename of the main jar used to start the Minecraft server. Example: `spigot.jar`.

  *Default*: none

  *Required*: yes

``opts``

  Additional options passed to the java invocation of the server. Example: `-Xms1G -Xmx2G`.

  *Default*: none

  *Required*: no
