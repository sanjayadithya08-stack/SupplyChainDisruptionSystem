# Observed freight disruption impacts

The active Analytics CSV contains **72 measured activity drops from 35 distinct disruption events** over 2019–2026, spanning 10 causes. It retains only primary event-window measurements that show a decline, are current and non-provisional, and have a source-reported or official cause attribution. Weather is the largest group; the records also include labor action, security incidents, drought restrictions, port/terminal closures, infrastructure failures, congestion, cyber incidents, collisions, and regulatory/customs action.

Each row is an event × affected port/chokepoint × activity-series observation. The measured outcomes are port calls, container calls, chokepoint transits, or related flows. They are evidence of reduced maritime activity during documented disruptions, **not individual shipment transactions or delivery-delay days**. Multiple rows can describe one incident across multiple places or measures.

Source data and reuse notes are in `disruption_dataset_sources.json`. The source snapshot is `source_snapshots/world_freight_monitor_events.json`. WFM-authored records are CC BY 4.0; measured flow data comes from IMF PortWatch, whose reuse terms and attribution requirements apply.

These records can support exploratory modeling of impact severity after a documented disruption. Because they contain only observed declines, they do not provide unaffected controls for a yes/no disruption classifier, nor do they replace actual company shipment outcomes in `company_dataset.csv`. The company model remains separate.

An older CyPort weather-only experiment and its source snapshots remain in the project files from earlier work, but they are **not read by the current Analytics endpoint or company model**.

Rebuild this snapshot from the saved WFM JSON using `python data/build_disruption_dataset.py`.
