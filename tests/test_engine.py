import math
import pandas as pd
import pytest
from analysis_engine import derive, normalize_personnel, metric_summary, group_performance, data_coverage, weekly_report
from data_pipeline import merge_chart


def fixture():
    return pd.DataFrame([
        {'game_id':'2024_01_DEN_SEA','play_id':1,'season':2024,'week':1,'posteam':'DEN','defteam':'SEA','play_type':'pass',
         'qb_dropback':1,'down':1,'ydstogo':10,'epa':0.7,'success':1,'yards_gained':22,'first_down':1,'touchdown':0,
         'offense_personnel':'1 RB, 2 TE, 2 WR','offense_formation':'SHOTGUN','defense_personnel':'4 DL, 2 LB, 5 DB',
         'qb_location':'S'},
        {'game_id':'2024_01_DEN_SEA','play_id':2,'season':2024,'week':1,'posteam':'DEN','defteam':'SEA','play_type':'run',
         'qb_dropback':0,'down':3,'ydstogo':2,'epa':-0.1,'success':0,'yards_gained':1,'first_down':0,'touchdown':0,
         'offense_personnel':'1 RB, 1 TE, 3 WR','qb_location':'U'},
        {'game_id':'2024_01_DEN_SEA','play_id':3,'season':2024,'week':1,'posteam':'SEA','defteam':'DEN','play_type':'pass',
         'qb_dropback':1,'down':3,'ydstogo':6,'epa':-1.3,'success':0,'yards_gained':-5,'first_down':0,'touchdown':0,
         'defense_personnel':'4 DL, 2 LB, 5 DB'},
        {'game_id':'2026_05_DEN_LAC','play_id':4,'season':2026,'week':5,'posteam':'DEN','defteam':'LAC','play_type':'run',
         'qb_dropback':1,'qb_scramble':1,'down':3,'ydstogo':5,'epa':0.2,'success':1,'yards_gained':8,'first_down':1,'touchdown':0},
        {'game_id':'2026_05_DEN_LAC','play_id':5,'season':2026,'week':5,'posteam':'LAC','defteam':'DEN','play_type':'run',
         'qb_dropback':0,'down':1,'ydstogo':10,'epa':0.4,'success':1,'yards_gained':7,'first_down':0,'touchdown':0},
        {'game_id':'2026_05_DEN_LAC','play_id':6,'season':2026,'week':5,'posteam':'DEN','defteam':'LAC','play_type':'kickoff',
         'qb_dropback':None,'down':0,'ydstogo':0,'epa':0.6,'success':1,'yards_gained':20,'first_down':0,'touchdown':0},
    ])


def test_personnel_verified():
    assert normalize_personnel('1 RB, 2 TE, 2 WR') == '12'
    assert normalize_personnel('1 RB 1 FB 1 TE 2 WR') == '21'
    assert normalize_personnel('2 RB, 1 TE, 2 WR') == '21'
    assert normalize_personnel('1 RB, 1 TE') is None
    assert normalize_personnel(None) is None


def test_defense_epa_not_reversed():
    z=derive(fixture())
    assert len(z)==5  # kickoff excluded
    a=metric_summary(z,'Offense')
    d=metric_summary(z,'Defense')
    assert a['plays']==3 and d['plays']==2
    assert d['epa']==pytest.approx((-1.3+0.4)/2)
    assert d['success']==pytest.approx(0.5)
    assert a['epa']==pytest.approx((0.7-0.1+0.2)/3)
    assert a['explosive']==pytest.approx(1/3)


def test_scramble_is_dropback_and_caller_switched():
    z=derive(fixture())
    scr=z[z.play_id.eq(4)].iloc[0]
    assert scr.play_call=='Pass / dropback'
    assert scr.play_caller=='Sean Payton'
    assert z[z.play_id.eq(1)].iloc[0].play_caller=='Sean Payton'
    assert z[z.play_id.eq(3)].iloc[0].play_caller=='Vance Joseph (DC)'


def test_unreported_fields_are_null():
    z=derive(fixture())
    scr=z[z.play_id.eq(4)].iloc[0]
    assert pd.isna(scr.personnel_code)
    assert pd.isna(scr.qb_alignment)
    coverage=data_coverage(z)
    row=coverage.set_index('Field').loc['Offensive personnel']
    assert row['Coverage %']==40.0


def test_group_and_third_down_conversion():
    z=derive(fixture())
    off=metric_summary(z,'Offense')
    assert off['third_down_conversion']==pytest.approx(0.5)
    groups=group_performance(z,'play_call','Offense')
    assert groups.Plays.sum()==3
    assert 'Sample' in groups
    assert 'Game:' in weekly_report(z,'2024_01_DEN_SEA')


def test_chart_join_one_record_per_play():
    pbp=pd.DataFrame([{'game_id':'2024_01_DEN_SEA','play_id':1,'epa':0.5},{'game_id':'2024_01_DEN_SEA','play_id':2,'epa':-0.1}])
    chart=pd.DataFrame([
        {'nflverse_game_id':'2024_01_DEN_SEA','nflverse_play_id':1,'qb_location':'S'},
        {'nflverse_game_id':'2024_01_DEN_SEA','nflverse_play_id':1,'qb_location':'U'},
    ])
    x=merge_chart(pbp,chart,['game_id','play_id'],['nflverse_game_id','nflverse_play_id'],'FTN')
    assert len(x)==2
    assert x.iloc[0].qb_location=='U'
    assert math.isnan(x.iloc[1].qb_location) if isinstance(x.iloc[1].qb_location,float) else pd.isna(x.iloc[1].qb_location)


def test_missing_core_columns_raise():
    with pytest.raises(ValueError):derive(pd.DataFrame([{'x':1}]))
