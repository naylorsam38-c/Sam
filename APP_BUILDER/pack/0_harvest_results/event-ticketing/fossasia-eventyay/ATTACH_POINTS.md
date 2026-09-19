# Attach Points

Application: fossasia/eventyay
Repository: fossasia/eventyay
Commit: 
Framework: django
Datastore: postgresql

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|
| pretix.plugin entry points | app/eventyay/config/settings.py |  | NATIVE | app/eventyay/config/settings.py line 384: 'ticket_plugins = [ep.module for ep in eps.select(group=\'pretix.plugin\') if ep.module not in EVENTYAY_PLUGINS_EXCLUDE]' -- a real, live setuptools entry-point group that third-party Python packages register plugins into; this is the exact mechanism pretix (the AGPL project eventyay forked from) uses for its own third-party plugin ecosystem, still active verbatim in eventyay's own settings.py. |

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
