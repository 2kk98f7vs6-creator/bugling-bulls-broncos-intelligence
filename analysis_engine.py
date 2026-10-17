"""Reproducible football calculations for Bugling Bulls fan beta v0.2.

No metrics are inferred when source values are absent. Offensive EPA is from
possession team's perspective; defensive EPA allowed is also possession-team EPA
(negative means effective Denver defense).
"""
from __future__ import annotations
import re
import pandas as pd
import numpy as np

TEAM = 'DEN'


def safe_number(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        return pd.Series(float('nan'), index=frame.index, dtype='float64')
    return pd.to_numeric(frame[name], errors='coerce')


def available_str(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame:
        return pd.Series(pd.NA, index=frame.index, dtype='string')
    return frame[name].astype('string').str.strip().replace({'':pd.NA, 'nan':pd.NA, 'None':pd.NA})


def normalize_personnel(raw: object) -> str | None:
    """Convert e.g. '1 RB, 2 TE, 2 WR' to '12' if five eligibles verified."""
    if raw is None or pd.isna(raw):
        return None
    s = str(raw).upper().strip()
    if re.fullmatch(r'(?:0|1|2|3|4|5){2}', s):
        return s
    pieces = re.findall(r'(\d+)\s*(RB|TE|WR|FB)', s)
    if not pieces:
        return None
    counts = {'RB':0, 'FB':0, 'TE':0, 'WR':0}
    for n, p in pieces:
        counts[p] += int(n)
    rb = counts['RB'] + counts['FB']
    te = counts['TE']
    if rb + te + counts['WR'] != 5 or rb > 5 or te > 5:
        return None
    return f'{rb}{te}'


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Adds side, call classification, coach periods, and validated rate fields."""
    if df.empty:
        return df.copy()
    z = df.copy()
    required = ['game_id','play_id','posteam','defteam','season','week','play_type']
    missing = [k for k in required if k not in z]
    if missing:
        raise ValueError('Missing essential play fields: ' + ', '.join(missing))
    z['season'] = safe_number(z,'season').astype('Int64')
    z['week'] = safe_number(z,'week').astype('Int64')
    z['play_id'] = safe_number(z,'play_id').astype('Int64')
    z = z.loc[(z.posteam == TEAM) | (z.defteam == TEAM)].copy()
    z = z.loc[z.play_type.isin(['run','pass'])].copy()
    z['side'] = np.where(z.posteam == TEAM, 'Offense', 'Defense')
    z['opponent'] = np.where(z.posteam == TEAM, z.defteam, z.posteam)
    dropback = safe_number(z,'qb_dropback')
    z['play_call'] = np.where(dropback.eq(1) | (dropback.isna() & z.play_type.eq('pass')),'Pass / dropback','Designed run')
    z['epa'] = safe_number(z,'epa')
    z['yards_gained'] = safe_number(z,'yards_gained')
    z['ydstogo'] = safe_number(z,'ydstogo')
    z['down'] = safe_number(z,'down').astype('Int64')
    z['success'] = safe_number(z,'success')
    z['first_down'] = safe_number(z,'first_down')
    z['touchdown'] = safe_number(z,'touchdown')
    z['defense_success_allowed'] = z['success']
    z['explosive'] = np.where(z.yards_gained.notna(),z.yards_gained.ge(20).astype(float),np.nan)
    z['converted'] = np.where(
        z.first_down.eq(1) | z.touchdown.eq(1) |
        ((z.ydstogo > 0) & z.yards_gained.ge(z.ydstogo)), 1.0,
        np.where(z.ydstogo.notna() & z.yards_gained.notna(),0.0,np.nan)
    )
    z['formation_name'] = available_str(z,'offense_formation')
    z['personnel_code'] = available_str(z,'offense_personnel').map(normalize_personnel)
    qb = available_str(z,'qb_location')
    z['qb_alignment'] = qb.str.upper().map({'U':'Under center','S':'Shotgun','P':'Pistol'})
    z['defensive_package'] = available_str(z,'defense_personnel')
    year = z.season.fillna(0).astype(int)
    week = z.week.fillna(0).astype(int)
    z['play_caller'] = np.where((year==2026)&(week<=4),'Davis Webb', 'Sean Payton')
    z['play_caller'] = np.where(z.side.eq('Defense'),'Vance Joseph (DC)',z.play_caller)
    z['distance_band'] = pd.cut(z['ydstogo'],bins=[-0.01,2,6,10,float('inf')],labels=['1–2','3–6','7–10','11+'])
    return z


def metric_summary(df: pd.DataFrame, side: str) -> dict:
    z = df.loc[df.side == side] if 'side' in df else pd.DataFrame()
    if z.empty:
        return {'plays':0,'epa':float('nan'),'success':float('nan'),'explosive':float('nan'),'pass_rate':float('nan'),'third_down_conversion':float('nan')}
    third = z.loc[safe_number(z,'down').eq(3)]
    epa = safe_number(z,'epa')
    return {
        'plays':int(len(z)),
        'epa':float(epa.mean()),
        'success':float(safe_number(z,'success').mean()),
        'explosive':float(safe_number(z,'explosive').mean()),
        'pass_rate':float((z.play_call=='Pass / dropback').mean()),
        'third_down_conversion':float(safe_number(third,'converted').mean()) if len(third) else float('nan'),
    }


def group_performance(df: pd.DataFrame, group_by: str, side: str, min_plays: int=1) -> pd.DataFrame:
    z = df.loc[df.side == side].copy() if 'side' in df else pd.DataFrame()
    if z.empty or group_by not in z:
        return pd.DataFrame(columns=[group_by,'Plays','EPA/play','Success %','Explosive %','Pass rate %','Sample'])
    z = z.loc[z[group_by].notna() & z[group_by].astype(str).ne('')].copy()
    if z.empty:
        return pd.DataFrame(columns=[group_by,'Plays','EPA/play','Success %','Explosive %','Pass rate %','Sample'])
    grouped = z.groupby(group_by,observed=True,dropna=True).agg(
        Plays=('play_id','size'),
        **{'EPA/play':('epa','mean'), 'Success %':('success','mean'),
           'Explosive %':('explosive','mean')}
    ).reset_index()
    grouped['Pass rate %'] = z.assign(pass_rate=z.play_call.eq('Pass / dropback').astype(float)).groupby(group_by,observed=True)['pass_rate'].mean().reindex(grouped[group_by]).to_numpy()*100
    for c in ('Success %','Explosive %'):
        grouped[c] *= 100
    grouped = grouped.loc[grouped.Plays >= min_plays].sort_values('Plays',ascending=False).reset_index(drop=True)
    grouped['Sample'] = grouped.Plays.map(lambda n:'Exploratory (<15)' if n<15 else ('Directional (15–39)' if n<40 else 'Larger sample (40+)'))
    return grouped


def data_coverage(df: pd.DataFrame) -> pd.DataFrame:
    fields = [
        ('EPA', 'epa','nflverse play-by-play'),
        ('FTN QB alignment', 'qb_alignment','FTN weekly charting'),
        ('FTN motion', 'is_motion','FTN weekly charting'),
        ('FTN pass rushers', 'n_pass_rushers','FTN weekly charting'),
        ('Offensive personnel', 'personnel_code','Participation (historical)'),
        ('Offensive formation', 'formation_name','Participation (historical)'),
        ('Defensive personnel', 'defensive_package','Participation (historical)'),
    ]
    out = []
    for label,field,source in fields:
        seen = int(df[field].notna().sum()) if field in df else 0
        total = len(df)
        out.append({'Field':label,'Coverage':f'{seen:,}/{total:,}', 'Coverage %':round(100*seen/total,1) if total else 0,'Source':source})
    return pd.DataFrame(out)


def weekly_report(df: pd.DataFrame, game_id: str) -> str:
    game = df.loc[df.game_id.eq(game_id)]
    if game.empty:
        return '# No game data found\n'
    row=game.iloc[0]
    off = metric_summary(game,'Offense')
    deff = metric_summary(game,'Defense')
    # Historical means games BEFORE the chosen game, never future games.
    earlier = (safe_number(df,'season') < int(row.season)) | (
        safe_number(df,'season').eq(int(row.season)) & safe_number(df,'week').lt(int(row.week)))
    hist = df.loc[earlier].copy()
    historical_off = metric_summary(hist,'Offense')
    historical_def = metric_summary(hist,'Defense')
    def num(value, digits=3): return 'N/A' if pd.isna(value) else f'{value:+.{digits}f}'
    def pct(value):return 'N/A' if pd.isna(value) else f'{value*100:.1f}%'
    lines = [
        '# Bugling Bulls — Broncos Weekly Play-Calling Report',
        f'Game: {row.game_id} | {row.season} Week {row.week} | Opponent: {row.opponent}',
        '\n## Offensive scorecard',
        f'- Scrimmage plays: {off["plays"]}',
        f'- EPA/play: {num(off["epa"])} (previous games: {num(historical_off["epa"])})',
        f'- Success rate: {pct(off["success"])}',
        f'- Pass/dropback selection: {pct(off["pass_rate"])}',
        f'- Third-down conversion (tracked scrimmage plays): {pct(off["third_down_conversion"])}',
        '\n## Defensive scorecard',
        f'- Scrimmage plays defended: {deff["plays"]}',
        f'- EPA allowed/play: {num(deff["epa"])} (previous games: {num(historical_def["epa"])})',
        f'- Opponent offensive success rate: {pct(deff["success"])}',
        f'- Opponent explosive-play rate: {pct(deff["explosive"])}',
        '\n## Analytical limitations',
        '- Results are descriptive; this build does not attribute causes to a coach or player.',
        '- EPA is measured from the possession team perspective. Negative defensive EPA allowed is favorable.',
        '- Historical comparison combines other selected Broncos games; it is not yet opponent-adjusted.',
        '- Scrimmage run/pass filter excludes penalties that negated plays, kick plays, spikes and kneels.',
        '- Formation/personnel, rush and motion fields are displayed only when the relevant charting source supplies them.',
        '\nSources: nflverse play-by-play; FTN charting/participation when available. Analysis generated from saved local play records.',
    ]
    return '\n'.join(lines)+'\n'


def prior_games(df:pd.DataFrame, game_id:str, count:int=3)->pd.DataFrame:
    """Return prior Denver games only. Prevents future-game information leakage."""
    g=df.loc[df.game_id.eq(game_id)]
    if g.empty:
        return df.iloc[0:0].copy()
    row=g.iloc[0]
    games=(df[['game_id','season','week']].drop_duplicates()
           .sort_values(['season','week','game_id']))
    earlier=games.loc[(games.season < row.season) |
                      ((games.season == row.season)&(games.week < row.week))]
    ids=earlier.tail(count).game_id.tolist()
    return df.loc[df.game_id.isin(ids)].copy()


def trend_signals(df:pd.DataFrame, game_id:str)->list[dict]:
    """Descriptive postgame deviations from *previous* three games only.

    No causal interpretations or statistical-significance claims.
    """
    game=df.loc[df.game_id.eq(game_id)]
    prior=prior_games(df,game_id,3)
    if game.empty or prior.game_id.nunique()<2:
        return []
    results=[]
    for side in ('Offense','Defense'):
        cur=metric_summary(game,side);base=metric_summary(prior,side)
        if cur['plays']>=25 and base['plays']>=60:
            delta=cur['epa']-base['epa']
            if pd.notna(delta) and abs(delta)>=0.075:
                favor=delta if side=='Offense' else -delta
                trend='improved' if favor>0 else 'declined'
                results.append({
                    'title':f'{side} EPA/play {trend}',
                    'detail':f'{cur["epa"]:+.3f} in this game versus {base["epa"]:+.3f} across {prior.game_id.nunique()} previous games (difference {delta:+.3f}).',
                    'n':cur['plays'], 'field':'epa', 'side':side,
                })
        if side=='Offense' and cur['plays']>=25 and base['plays']>=60:
            delta=cur['pass_rate']-base['pass_rate']
            if pd.notna(delta) and abs(delta)>=0.09:
                results.append({
                    'title':'Dropback selection increased' if delta>0 else 'Dropback selection decreased',
                    'detail':f'{cur["pass_rate"]:.1%} this game vs {base["pass_rate"]:.1%} over the previous {prior.game_id.nunique()} games.',
                    'n':cur['plays'], 'field':'play_call', 'side':side,
                })
    return results[:5]
