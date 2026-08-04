json-config
===========

v1.0.1
------
* Fixed: LayeredConfigManager.resolve(up_to=...) raised a bare KeyError instead of ValueError (#6)
* Fixed: LayeredConfig.write_to_layer could never write to a brand-new, previously-empty layer (#6)
* Depcreated SimpleConfig and related tests
* Added support for ConfigValues categories and nesting (#6)

v1.0.0
------
* Initial release
