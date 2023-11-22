Changelog
=========

Version 2023.11.2
-----------------

- Added new endpoints: /circuit/attribute_names, /circuit/attribute_dtypes, /circuit/attribute_values
- Changed /circuit/downsample from GET to POST.
- Fix json serialization in case of validation error with pydantic v2.
- Move query parameters to arguments.


Version 2023.11.1
-----------------

- Upgrade to Pydantic v2.
- Upgrade requirements.txt.
- Forbid extra attributes in POST endpoints, to prevent potential mistakes in query parameters.
- The endpoint ``/circuit/count`` now accepts only 0 (all) or 1 node populations, for consistency with other endpoints.
- Explicitly require libsonata>=0.1.24 where toJSON() correctly serializes node_sets with node_id.
- Raise the error "nodesets with `node_id` aren't currently supported" only when it's specified a node_set referencing node_id, directly or in a compound expression.


Version 2023.08.1
-----------------

- Improve error handling.


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
