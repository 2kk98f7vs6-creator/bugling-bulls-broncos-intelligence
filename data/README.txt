PUBLIC fan-beta snapshot data only.

Run START_BRONCOS.ps1 locally, or GitHub Actions -> Refresh public Broncos data.
The following files will be generated:
  broncos_plays.csv        public NFL plays and derived metrics
  bo_nix_ngs_weekly.csv    optional public NGS weekly aggregates
  import_status.json       update timestamp / counts / source errors

Do NOT put scout_notes.csv or any personal/paid analysis files in this folder
when publishing the repository. The shared app is strictly read-only.
All real data comes from nflverse/nflreadpy, FTN and NFL NGS public feeds.
