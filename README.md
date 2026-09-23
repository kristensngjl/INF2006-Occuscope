# Occuscope

**INF2006 Team Project 1 — Cloud Computing & Big Data**

A cloud-based interactive map of SIT Punggol Campus — live crowd levels and campus events, browsable from the whole campus down to one room.

## Problem statement

Before students go anywhere on campus, they have three unanswered questions: is the library crowded right now, are the discussion rooms on this floor actually free (today that means checking floor by floor), and what events are happening around campus. There's no live, browsable view of any of it.

Occuscope answers this with a map — visually modelled on SIT's own [Campus Wayfinder](https://www.singaporetech.edu.sg/campus-wayfinder) (its map, not its wayfinding/routing function) — organised hierarchically as **Campus → Building → Floor → Location**, showing a live crowd band (Quiet 0–30% / Moderate 31–70% / Crowded 71–100%) per location, plus today's events at their real locations. The crowd level shown comes from a prediction model trained on real NUS occupancy data, not an arbitrary number.

## Team

| Name | Student ID | Role |
|---|---|---|
| ZQ | | Frontend / Map — building/floor selector, crowd + event markers, Quiet/Moderate/Crowded display, frontend↔backend integration |
| Zeus | | Backend / Database — database schema (Location, Occupancy, Event), REST APIs, integration with the frontend |
| Liddy | | Data / Machine Learning — cleans ROBOD + NUS Wi-Fi datasets, EDA, feature engineering, trains/evaluates the prediction model, prediction API logic |
| Krissie (Kristen) | | Cloud / Scalability — AWS deployment (EC2, load balancer), scaling mechanism, health checks + backups, architecture diagram, resilience test |
| DJ Ryan | | Security / Monitoring / Testing — auth & IAM least privilege, secrets handling, security test, CloudWatch logging/monitoring/alerts, coordinates all 4 required tests |

## Quick start

```
# TODO: local run commands once src/ exists
```

## Architecture

Two pipelines feed the map: NUS datasets (ROBOD + NUS Wi-Fi floor counts) are cleaned and trained offline into a prediction model, while synthetic live readings and event data populate the database. The backend reads both and serves the frontend's campus → building → floor → room map.

See `evidence/architecture.png` and `report.pdf` section 2–3 for the diagram and service/deployment rationale.

## Technology

- Cloud provider: AWS — EC2 instance(s) behind a load balancer, managed relational DB (e.g. RDS)
- Datasets:
  - [ROBOD](https://github.com/ideas-lab-nus/robod) — NUS lecture rooms + library, real ground-truth occupant counts, 5-minute intervals
  - [NUS Wi-Fi floor counts](https://zenodo.org/records/17578240) — 5 floors, Wi-Fi device counts, 5-minute intervals, full year (2018)

## Known limitations

- Both datasets are real NUS data used to train the prediction model — they are not live SIT Punggol sensor feeds.
- "Current" occupancy shown on the SIT map is synthetic (generated) data standing in for a real-time feed, since no such feed exists for our campus. Stated plainly in the report.
- TODO: update as implementation progresses.
