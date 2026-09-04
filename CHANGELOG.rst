json-config
===========
v1.0.3
------
* Migrate ConfigValues from dataclasses to pydantic (#21)

v1.0.2
------
* Implement clearance of non-overrides and value revert (#16)
* Prevent ConfigValues to be nested without specifying category metadata (#15)

v1.0.1
------
* Fixed: LayeredConfigManager.resolve(up_to=...) raised a bare KeyError instead of ValueError (#6)
* Fixed: LayeredConfig.write_to_layer could never write to a brand-new, previously-empty layer (#6)
* Depcreated SimpleConfig and related tests
* Added support for ConfigValues categories and nesting (#6)

v1.0.0
------
* Initial release
