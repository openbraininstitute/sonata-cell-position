sonata-cell-position
====================

This service is composed by:

- ``sonata-cell-position-proxy``: reverse proxy with caching, listening on port 8040
- ``sonata-cell-position``: main service, listening on port 8050 and accessed through the proxy above

The API documentation is available at https://cells.sbo.kcp.bbp.epfl.ch/docs
