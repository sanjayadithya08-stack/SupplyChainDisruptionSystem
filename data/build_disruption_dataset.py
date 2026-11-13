from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SOURCE = DATA / 'source_snapshots' / 'world_freight_monitor_events.json'
OUTPUT = DATA / 'disruption_analytics_events.csv'
MANIFEST = DATA / 'disruption_dataset_sources.json'


def collect():
    payload = json.loads(SOURCE.read_text(encoding='utf-8'))
    rows = []
    for event in payload.get('events', []):
        cause = event.get('cause') or {}
        cause_status = cause.get('status', '')
        if cause_status not in ('official', 'reported'):
            continue
        entities = event.get('entities') or {}
        affected_places = [place for key in ('ports', 'chokepoints', 'lanes', 'countries') for place in entities.get(key, [])]
        source_refs = [item.get('url', '') for item in event.get('sources', []) if item.get('url')]
        for effect in event.get('measured_effect') or []:
            try:
                change_pct = float(effect.get('delta_pct'))
            except (TypeError, ValueError):
                continue
            if (effect.get('comparison') != 'primary' or change_pct >= 0
                    or effect.get('superseded_by') or effect.get('provisional')):
                continue
            entity_id = effect.get('entity_id', '')
            key = '|'.join((event.get('id', ''), entity_id, effect.get('series_id', ''),
                            effect.get('window_start', ''), effect.get('window_end', '')))
            rows.append({
                'record_id': key,
                'event_id': event.get('id', ''),
                'event_date': event.get('start_date', ''),
                'event_end_date': event.get('end_date', ''),
                'impact_window_start': effect.get('window_start', ''),
                'impact_window_end': effect.get('window_end', ''),
                'event_type': event.get('event_type', ''),
                'event_title': event.get('title', ''),
                'severity_level': event.get('severity', ''),
                'affected_entity': entity_id,
                'affected_places': '; '.join(affected_places),
                'measurement_series': effect.get('series_id', ''),
                'measurement_unit': effect.get('unit', ''),
                'baseline_start': effect.get('baseline_start', ''),
                'baseline_end': effect.get('baseline_end', ''),
                'baseline_days': effect.get('baseline_days', ''),
                'observed_window_days': effect.get('window_days', ''),
                'baseline_value': effect.get('baseline_value', ''),
                'observed_value': effect.get('observed_value', ''),
                'absolute_change': effect.get('abs_change', ''),
                'change_pct': change_pct,
                'z_score': effect.get('z_score', ''),
                'cause': cause.get('text', ''),
                'cause_attribution_status': cause_status,
                'cause_attributed_by': cause.get('attributed_by', ''),
                'confidence': (event.get('confidence') or {}).get('level', ''),
                'confidence_note': (event.get('confidence') or {}).get('reason', ''),
                'summary': event.get('summary', ''),
                'source_event_url': event.get('url', ''),
                'source_references': '; '.join(source_refs),
                'measurement_source': 'World Freight Monitor measured effect; underlying activity series from IMF PortWatch',
                'data_license': 'CC BY 4.0 for WFM-authored fields; upstream PortWatch terms apply to flow measurements',
                'selection_rule': 'Primary event window; negative change; non-provisional; current revision; source cause status official/reported',
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT, index=False, encoding='utf-8')
    event_dates = pd.to_datetime(df['event_date'], errors='coerce')
    manifest = {
        'retrieved_on': '2026-11-13',
        'source_snapshot_date': payload.get('generated_from_data_through'),
        'record_count': int(len(df)),
        'unique_disruption_events': int(df['event_id'].nunique()),
        'cause_type_count': int(df['event_type'].nunique()),
        'date_from': event_dates.min().strftime('%Y-%m-%d'),
        'date_to': event_dates.max().strftime('%Y-%m-%d'),
        'counts_by_event_type': {str(k): int(v) for k, v in df['event_type'].value_counts().items()},
        'counts_by_measurement_series': {str(k): int(v) for k, v in df['measurement_series'].value_counts().items()},
        'row_grain': 'One measured event × affected port/chokepoint × activity-series observation. Multiple rows may describe one disruption event; these are not shipment transactions or delay-day labels.',
        'selection_rule': 'Only primary event-window decreases with official/reported cause attribution, non-provisional measurements, and no superseding revision.',
        'sources': [
            {'name': 'World Freight Monitor event archive', 'url': 'https://worldfreightmonitor.com/data/events.json', 'license': 'CC BY 4.0 for WFM-authored records; upstream terms apply', 'note': 'Cause text, cause attribution status, confidence, severity, and original source references are retained.'},
            {'name': 'IMF PortWatch', 'url': 'https://portwatch.imf.org/', 'license': 'IMF terms; attribution required; permissions may be required for systematic or commercial reuse', 'note': 'Underlying port-call, container-call, and chokepoint-flow measurements are included in the WFM event records.'},
        ],
        'training_guidance': 'Useful as an exploratory measured maritime-flow impact dataset. It does not contain individual shipment IDs or actual shipment delay days and should not be appended to the company shipment labels.',
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote {len(df)} measured impact rows across {manifest['unique_disruption_events']} events and {manifest['cause_type_count']} cause types.")


if __name__ == '__main__':
    collect()
