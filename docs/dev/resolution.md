# Resolution and saving

## Ordering

`topological_sort_layers` uses `graphlib.TopologicalSorter` on the `depends_on` graph,
so dependencies come first. It checks that every dependency is registered
(`ValueError`) and lets `graphlib.CycleError` through for cycles.

`sorted_names(up_to=name)` first collects the layers reachable from `name` through
`depends_on` (`_reachable_subgraph`), then sorts only those. That is how `layer_filter`
hides layers above the chosen one: they are not reachable from it.

The order among layers that don't depend on each other is whatever
`TopologicalSorter` yields. Nothing in the library should rely on it.

## Merging

`manager.resolve(up_to)` folds `deep_merge_dicts` over the sorted layers' data, starting
from `{}`.

- Dicts merge recursively.
- Everything else, **lists included**, is replaced by the later layer's value.
- A dict replaces a non-dict, and the other way around.

`resolve_many(*names)` resolves each name with its own dependencies, then merges the
results left to right. `write_to_layer` uses it to build the baseline for a layer with
several dependencies.

## Saving

`LayeredConfig.save()`:

1. `layer_manager.seed_root_layers(values.get_defaults())`: every root layer gets the
   defaults it lacks, and a root layer with a `file_path` and no file is written.
2. `write_to_layer(current_layer)`:
    1. `baseline = manager.resolve_many(*layer.depends_on)`: what would be inherited
       without this layer.
    2. `current = values.to_dict()`: runs `pre_serialize` and `post_serialize`.
    3. `diff = deep_diff_dicts(current, baseline)`: keeps what differs, recursing into
       dicts that exist on both sides and dropping nested keys that match.
    4. `layer.replace_data(diff)`: the layer's data is **replaced**, not updated.
3. `manager.save(layer)` writes the file.

Consequences worth remembering:

- Replacing the data means keys in a layer file that `to_dict()` doesn't produce are
  dropped on save. Unknown keys survive loading but not saving.
- For a root layer the baseline is `{}`, and step 1 has seeded it with defaults, so a
  root layer ends up holding the full values, not a diff.
- A value equal to the baseline is removed from the file. If a lower layer later
  changes, the upper layer follows it. That is the point of saving only overrides, but
  it also means you can't pin a value by setting it to what is currently inherited.

## Reverting

`revert_value(path)` resolves a field name or dotted path to a key tuple (top-level
names go through `_field_key`, dotted paths are used as given), then:

1. `layer.unset_path(path)` removes the key from the layer's data. `pop_nested` also
   removes parents that become empty.
2. The inherited value comes from `get_nested(baseline, path)`, falling back to
   `get_nested(get_defaults(), path)` when no dependency has it.
3. The in-memory `values` is updated with `replace(nest_value(path, value))`, so only
   that leaf changes.

If neither the baseline nor the defaults have the path (a field without a default),
`values` is left as it is.
