Changelog
=========

Version 2023.07.1
-----------------

- Add new POST endpoint ``/circuit/query`` to support filtering nodes by any attribute [NSETM-2210]


Version 2023.04.3
-----------------

- Generalize query function in libsonata helper [BBPP134-280]
- Support getting nodes by node_set.
- Allow node_set look ups to happen on cached files.


Version 2023.04.2
-----------------

- Cleanup cache.py and move libsonata functions.


Version 2023.04.1
-----------------

- Remove randomaccessbuffer library.


Version 2023.04.0
-----------------

- Add endpoint ``/circuit/node_sets``.
- Upgrade to python 3.10.
