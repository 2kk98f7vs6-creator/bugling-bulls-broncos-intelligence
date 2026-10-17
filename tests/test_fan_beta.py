"""v0.2 test fixtures are entirely artificial and never enter the shipped app."""
from __future__ import annotations
import pandas as pd
import pytest
from analysis_engine import derive, prior_games, weekly_report, trend_signals
from data_pipeline import merge_season_safely, preserve_existing_charting, write_if_changed


def plays():
    rows=[]
    for week in [1,2,3,4,5]:
        for j in range(60):
            rows.append({
                'game_id':f'2026_{week:02d}_DEN_X', 'season':2026,'week':week,
                'play_id':100+j,'posteam':'DEN' if j%2==0 else 'LAC',
                'defteam':'LAC' if j%2==0 else 'DEN','play_type':'pass' if j%3 else 'run',
                'down':1+(j%3),'ydstogo':5,'qb_dropback':1 if j%3 else 0,
                'epa':0.05 if week<=3 else -0.6, 'success':int(j%2==0),
                'yards_gained':5,'first_down':0,'touchdown':0,
            })
    return derive(pd.DataFrame(rows))


def test_prior_games_never_looks_ahead():
    d=plays()
    early=prior_games(d,'2026_01_DEN_X')
    late=prior_games(d,'2026_04_DEN_X')
    assert early.empty
    assert set(late.week.astype(int).unique())=={1,2,3}
    assert 'previous games: N/A' in weekly_report(d,'2026_01_DEN_X')
    assert 'previous games: +0.050' in weekly_report(d,'2026_04_DEN_X')


def test_trend_flags_are_descriptive_with_supporting_samples():
    d=plays()
    result=trend_signals(d,'2026_04_DEN_X')
    assert any(x['title']=='Offense EPA/play declined' for x in result)
    assert all(x['n']>=25 for x in result)
    assert trend_signals(d,'2026_01_DEN_X')==[]


def test_regression_to_partial_feed_retains_published_year():
    old=plays()
    partial=old[old.week<4]
    result=merge_season_safely(partial,old,2026)
    assert len(result)==len(old)
    assert result.game_id.nunique()==5


def test_charting_fields_not_erased_by_optional_service_outage():
    old=plays().head(2).copy()
    old['offense_personnel']=['1 RB, 2 TE, 2 WR','1 RB, 1 TE, 3 WR']
    old['qb_location']=['S','U']
    new=old.drop(columns=['offense_personnel','qb_location']).copy()
    out=preserve_existing_charting(new,old)
    assert out.personnel_code.tolist()==['12','11']
    assert out.qb_alignment.tolist()==['Shotgun','Under center']


def test_file_only_changes_when_content_changes(tmp_path):
    p=tmp_path/'data.csv'
    assert write_if_changed(p,b'header\nvalue\n')
    first=p.stat().st_mtime_ns
    assert not write_if_changed(p,b'header\nvalue\n')
    assert p.stat().st_mtime_ns==first
    assert write_if_changed(p,b'header\nnew\n')
    assert p.read_bytes()==b'header\nnew\n'


def test_shared_app_has_no_private_notebook_code():
    from pathlib import Path
    app=(Path(__file__).parent.parent/'app.py').read_text()
    assert 'scout_notes.csv' not in app
    assert 'st.form(' not in app
    assert 'st.file_uploader(' not in app
