"""Build a source-attributed, PUBLIC, Broncos-only play snapshot.

Runs outside the viewer: locally or in scheduled GitHub Actions. A page visit
never fetches the NFL data and never modifies the snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from analysis_engine import derive

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data'
PBP_FIELDS = [
    'game_id','play_id','season','week','season_type','game_date',
    'posteam','defteam','home_team','away_team','play_type','desc',
    'down','ydstogo','yardline_100','qtr','time','epa','success','first_down',
    'touchdown','yards_gained','air_yards','qb_dropback','qb_scramble',
    'shotgun','no_huddle','pass','rush','interception','sack',
]
FTN_FIELDS = [
    'nflverse_game_id','nflverse_play_id','qb_location','n_offense_backfield',
    'n_defense_box','is_motion','is_no_huddle','is_play_action',
    'is_screen_pass','is_rpo','n_blitzers','n_pass_rushers','read_thrown',
    'is_qb_fault_sack','is_drop','is_throw_away','date_pulled',
]
PART_FIELDS = [
    'nflverse_game_id','play_id','offense_formation','offense_personnel',
    'defense_personnel','defenders_in_box','defense_man_zone_type',
    'defense_coverage_type','time_to_throw','route','was_pressure',
]
NGS_FIELDS = [
    'season','week','season_type','player_display_name','team_abbr',
    'attempts','avg_time_to_throw','avg_intended_air_yards',
    'avg_air_yards_to_sticks','completion_percentage',
    'expected_completion_percentage','completion_percentage_above_expectation',
    'aggressiveness','pass_yards',
]
CHART_FIELDS = [x for x in FTN_FIELDS if x not in {'nflverse_game_id','nflverse_play_id','date_pulled'}] + [x for x in PART_FIELDS if x not in {'nflverse_game_id','play_id'}]


def selected(df, names):
    return df.select([x for x in names if x in df.columns])


def unique_chart(frame, keys, label):
    if frame.empty:
        return frame
    n = int(frame.duplicated(keys).sum())
    if n:
        print(f'  {label}: {n} duplicate join keys; choosing latest charted record')
        if 'date_pulled' in frame.columns:
            frame = frame.sort_values('date_pulled', kind='stable')
        frame = frame.drop_duplicates(keys, keep='last')
    return frame


def merge_chart(pbp, chart, left, right, label):
    if chart.empty:
        return pbp
    chart = chart.copy()
    chart[left[0]] = chart[right[0]].astype(str)
    chart[left[1]] = pd.to_numeric(chart[right[1]], errors='coerce').astype('Int64')
    chart = chart.drop(columns=[x for x in right if x not in left], errors='ignore')
    chart = unique_chart(chart, left, label)
    keep = [x for x in chart.columns if x in left or x not in pbp.columns]
    result = pbp.merge(chart[keep], on=left, how='left', validate='many_to_one')
    if len(result) != len(pbp):
        raise ValueError(f'{label}: source join unexpectedly changed the play row count')
    return result


def load_season(nfl, pl, season: int, want_participation=True):
    print(f'Loading {season} play-by-play...')
    raw = nfl.load_pbp(season)
    required = {'game_id','play_id','posteam','defteam','play_type','season','week'}
    if not required.issubset(raw.columns):
        raise ValueError('Play-by-play missing essential fields: '+repr(sorted(required-set(raw.columns))))
    mask = ((pl.col('posteam') == 'DEN') | (pl.col('defteam') == 'DEN')) & pl.col('play_type').is_in(['run','pass'])
    if 'season_type' in raw.columns:
        mask &= pl.col('season_type') == 'REG'
    pbp = pd.DataFrame(selected(raw.filter(mask),PBP_FIELDS).to_dicts())
    if pbp.empty:
        return pbp
    pbp['game_id'] = pbp.game_id.astype(str)
    pbp['play_id'] = pd.to_numeric(pbp.play_id,errors='coerce').astype('Int64')
    game_ids = pbp.game_id.unique().tolist()
    try:
        ftn = nfl.load_ftn_charting(season)
        if {'nflverse_game_id','nflverse_play_id'}.issubset(ftn.columns):
            ftn = selected(ftn.filter(pl.col('nflverse_game_id').is_in(game_ids)), FTN_FIELDS)
            pbp = merge_chart(pbp,pd.DataFrame(ftn.to_dicts()),['game_id','play_id'],['nflverse_game_id','nflverse_play_id'],'FTN')
        else:
            print('  FTN join keys missing; charting fields remain blank')
    except Exception as exc:
        print(f'  Optional FTN charting unavailable: {type(exc).__name__}: {exc}')
    if want_participation:
        try:
            part = nfl.load_participation(season)
            if {'nflverse_game_id','play_id'}.issubset(part.columns):
                part = selected(part.filter(pl.col('nflverse_game_id').is_in(game_ids)),PART_FIELDS)
                pbp = merge_chart(pbp,pd.DataFrame(part.to_dicts()),['game_id','play_id'],['nflverse_game_id','play_id'],'Participation')
            else:
                print('  Participation join keys missing; leaving personnel uncharted')
        except Exception as exc:
            print(f'  Optional participation unavailable: {type(exc).__name__}: {exc}')
    return derive(pbp)


def load_nix_ngs(nfl, pl, seasons):
    raw = nfl.load_nextgen_stats(seasons=seasons,stat_type='passing')
    if not {'player_display_name','season','week'}.issubset(raw.columns):
        return pd.DataFrame()
    mask = (pl.col('player_display_name') == 'Bo Nix') & pl.col('week').is_between(1,18)
    if 'season_type' in raw.columns:
        mask &= pl.col('season_type') == 'REG'
    if 'team_abbr' in raw.columns:
        mask &= pl.col('team_abbr') == 'DEN'
    return pd.DataFrame(selected(raw.filter(mask),NGS_FIELDS).to_dicts())


def preserve_existing_charting(fresh:pd.DataFrame, old:pd.DataFrame)->pd.DataFrame:
    """Do not erase charting when optional services temporarily omit it."""
    if fresh.empty or old.empty:
        return fresh
    keys=['game_id','play_id']
    oldcols=[c for c in CHART_FIELDS if c in old.columns]
    if not oldcols:
        return fresh
    saved=old[keys+oldcols].drop_duplicates(keys,keep='last').set_index(keys)
    result=fresh.set_index(keys)
    for c in oldcols:
        if c not in result:
            result[c]=pd.NA
        result[c]=result[c].combine_first(saved[c])
    return derive(result.reset_index())


def merge_season_safely(new:pd.DataFrame, existing:pd.DataFrame, season:int)->pd.DataFrame:
    """Protect a published full season from a partial or failed upstream refresh."""
    old=existing.loc[pd.to_numeric(existing.get('season'), errors='coerce').eq(season)].copy() if not existing.empty else pd.DataFrame()
    if new.empty:
        if old.empty:
            return new
        print(f'  {season}: no new data; retaining {len(old):,} previously published plays')
        return old
    if old.empty:
        return new
    previous_games=int(old.game_id.nunique())
    fresh_games=int(new.game_id.nunique())
    if fresh_games < previous_games or len(new) < len(old)*0.90:
        print(f'  {season}: upstream regression ({fresh_games}/{previous_games} games); retaining prior data')
        return old
    return preserve_existing_charting(new,old)


def write_if_changed(path:Path, data:bytes)->bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(data)
    os.replace(temp,path)
    return True


def run(seasons):
    import nflreadpy as nfl
    import polars as pl
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'broncos_plays.csv'
    old = pd.read_csv(path,low_memory=False) if path.exists() else pd.DataFrame()
    if not old.empty and {'game_id','play_id','season'}.difference(old.columns):
        raise ValueError('Existing public dataset is missing required keys; refusing overwrite.')
    all_seasons=sorted(set(seasons) | set(pd.to_numeric(old.get('season',pd.Series(dtype=float)),errors='coerce').dropna().astype(int)))
    tables=[]; errors=[]
    now_year=datetime.now(timezone.utc).year
    for season in all_seasons:
        try:
            fresh=load_season(nfl,pl,season,want_participation=(season<now_year)) if season in seasons else pd.DataFrame()
        except Exception as exc:
            message=f'{season}: {type(exc).__name__}: {exc}'
            print('  Import failed; retaining old season if possible:',message)
            errors.append(message)
            fresh=pd.DataFrame()
        merged=merge_season_safely(fresh,old,season)
        if not merged.empty:
            tables.append(merged)
    if not tables:
        raise RuntimeError('No Broncos data available. The public dataset was NOT overwritten. ' + '; '.join(errors))
    df=pd.concat(tables,ignore_index=True).drop_duplicates(['game_id','play_id'],keep='last')
    df=df.sort_values(['season','week','game_id','play_id']).reset_index(drop=True)
    # Reorder columns deterministically to avoid noisy commits on each schedule run.
    front=[c for c in PBP_FIELDS if c in df.columns]
    rest=sorted(c for c in df.columns if c not in front)
    df=df[front+rest]
    new_bytes=df.to_csv(index=False,float_format='%.9g').encode('utf-8')
    changed=write_if_changed(path,new_bytes)
    print(f'{"Updated" if changed else "Unchanged"}: {len(df):,} plays, {df.game_id.nunique()} games')
    ngs_path=OUT/'bo_nix_ngs_weekly.csv'
    ngs_changed=False
    try:
        nix=load_nix_ngs(nfl,pl,seasons)
        if not nix.empty:
            nix=nix.sort_values(['season','week']).drop_duplicates(['season','week'],keep='last')
            nbytes=nix.to_csv(index=False,float_format='%.9g').encode('utf-8')
            ngs_changed=write_if_changed(ngs_path,nbytes)
            print(f'NGS: {len(nix)} weeks')
    except Exception as exc:
        errors.append(f'NGS optional: {type(exc).__name__}: {exc}')
        print('  Retaining old NGS snapshot:',exc)
    status=OUT/'import_status.json'
    if changed or ngs_changed or not status.exists():
        meta={
            'updated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'seasons':sorted(int(v) for v in df.season.dropna().unique()),
            'games':int(df.game_id.nunique()),'plays':int(len(df)),
            'offensive_personnel_plays':int(df.personnel_code.notna().sum()) if 'personnel_code' in df else 0,
            'defensive_personnel_plays':int(df.defensive_package.notna().sum()) if 'defensive_package' in df else 0,
            'source_errors':errors,
            'data_sha256':hashlib.sha256(new_bytes).hexdigest(),
        }
        write_if_changed(status,json.dumps(meta,indent=2,sort_keys=True).encode('utf-8'))
    if errors:
        print('Nonfatal source errors in this run:', ' | '.join(errors))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Refresh public Broncos Intelligence data without exposing fan notebooks')
    parser.add_argument('--seasons',nargs='+',type=int,default=[2024,2025,2026])
    args=parser.parse_args()
    run(args.seasons)
