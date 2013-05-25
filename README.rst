This repository houses code for running `Brass`_. `SchizoidPy`_ is required.

``task.py``
    Task code for the initial, in-laboratory testing session in which subjects make commitments and complete pretests. Some information is sent to the server for the benefit of ``checkin.pl`` and ``notifier.pl``.

``commitments.py``
    A library for ``task.py``.

``receiver.pl``
    A CGI program that receives messages from ``task.py`` and updates the database accordingly.

``checkin.pl``
    A CGI program subjects use to check in each day.

``notifier.pl``
    A program that should be run on the server once per day (although it's idempotent: it will only send one message per subject per day) at 9 PM local time.

``schema.sql``
    A schema for the server's SQLite database.

License
============================================================

This program is copyright 2013 Kodi Arfer.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the `GNU General Public License`_ for more details.

.. _Brass: http://arfer.net/projects/brass
.. _SchizoidPy: https://github.com/Kodiologist/SchizoidPy
.. _`GNU General Public License`: http://www.gnu.org/licenses/
