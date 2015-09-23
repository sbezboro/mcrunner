Running MCRunner
================

If running for the first time, rename the sample configuration file::

   mv /etc/mcrunner/mcrunner.sample.conf /etc/mcrunner/mcrunner.conf

In it you will find some basic configuration required for running Minecraft server instances.

The configuration file can contain multiple named 'server' sections that define the path and other data required for each server.

.. code-block:: ini

   [server:survival]
   path=/path/to/server
   jar=spigot.jar
   opts=-Xms1G -Xmx2G

More documentation about possible configuration values and their purpose can be found in :doc:`configuration`

mcrunnerd
---------

`mcrunnerd` is the daemon process that controls the server instances directly. To start it, simply type::

   mcrunnerd start

mcrunner
--------

`mcrunner` is a client used to interface with the `mcrunnerd` daemon server process. You can use it to start servers, stop servers, and send commands to server::

   mcrunner start survival

This will attempt to start the "survival" server defined in the configuration if it exists. Otherwise an error will be shown.
