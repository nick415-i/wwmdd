import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys


START_SEASON = '2020-01-01'
DB_FILENAME = "nba.sqlite"

def plot2(data):
        
    _data = data.filter(['play_by_play','pts_home'])  
    _data['play_by_play'] = _data['play_by_play'].apply(
        lambda x: 15 if x.shape[0] == 0 else x.shape[0])

    #  convert the index to datetime
    #  reindex! so we get spaces on dates with no game
    _data.index = pd.DatetimeIndex(_data.index)
    _data = _data.reindex(pd.date_range(_data.index[0], _data.index[-1]), fill_value=15)
    _data.index = _data.index.strftime('%b %d')

    fig, ax = plt.subplots()    
    
    for l in _data:
        ax.bar(_data.index, list(_data[l]), label= l)  

    plt.xticks(rotation=90)
    ax.set_xticks(ax.get_xticks()[::7])
    ax.legend(loc =2, title='PBP Data',ncols=3)

    plt.show()
    return

def plot1(data):

    plus_home = ['ast_home', 'stl_home', 'blk_home', 'tov_away']
    minus_home = ['ast_away', 'stl_away', 'blk_away', 'tov_home']
    
    _mp = data.filter(minus_home + plus_home)     
    for key in _mp.keys():
        if key in minus_home:
            _mp[key] = _mp[key] * -1       

    #  convert the index to datetime
    #  reindex! so we get 0 on dates with no game
    _mp.index = pd.DatetimeIndex(_mp.index)
    _mp = _mp.reindex(pd.date_range(_mp.index[0], _mp.index[-1]), fill_value=0)
    _mp.index = _mp.index.strftime('%b-%d')
    
    ax = _mp.plot.bar(stacked=True)
    ax.set_xticks(ax.get_xticks()[::7])
    ax.set_ylabel('plus/minus')
    ax.set_title('Thunder')
    ax.legend(loc =2, title='',ncol=2)
    return
 
# NOT USED FOR NOW
def loadFromCSV():
    
    import glob
    import os

    pth = os.path.join("./csv", "*.csv")  # Replace with your directory path
    all_files = glob.glob(pth)

    dfFromCSV = {}
    for filename in all_files:
        print(filename)
        df = pd.read_csv(filename, index_col=None, header=0)
        print(df.shape)
        s = os.path.split(filename)[1].split('.')[0]
        dfFromCSV[s] = df

dfs = {}            # has everthing that was in db as dict of DateFrame by column name
gamesByTeam = {}    # reorganized game data is in gamesByTeam

def loadNBA():

    _dfs = {}
    _gamesByTeam = {}

    db_con = sqlite3.connect(DB_FILENAME)
    db_cursor = db_con.cursor()

    db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = db_cursor.fetchall()

    DoNotUseTableNames = ['play_by_play']
    table_names = [k[0] for k in table_names if k[0] not in DoNotUseTableNames]
 
    for i, table_name in enumerate(table_names):

        query = f"SELECT * FROM {table_name}"
        chunk_size = 100000
        count = 0
        chunks = []
        
        indexCol = None

        for chunk in pd.read_sql_query(query, db_con, chunksize=chunk_size,index_col= indexCol):
            chunks.append(chunk)
            print('.',end = "")
            count += chunk_size       

        _dfs[table_name] = pd.concat(chunks)
        print(table_name, _dfs[table_name].shape)

    print() 

    # strip leading digit from season, its signifies pre, post and regular season
    _dfs['game']['season_id'] = _dfs['game']['season_id'].apply(lambda x:x[1:])
    #place to save play by play dataframe
    _dfs['game']['play_by_play'] = [[pd.DataFrame([])]] * len(_dfs['game'])

    #for nickName in _dfs['team'].abbreviation:
    for nickName in ['OKC']:

        _games = getGames(_dfs['team'], _dfs['game'], nickName, 'Regular Season', START_SEASON)
        seasons = list(set(_games.season_id))
        seasons.sort()
        print(nickName, end = ' ')
        _gamesBySeason = {}
        for season in seasons:
            seasonGames = _games.query(f'season_id == "{season}"')
            
            _gamesByDate = {}
            badBunny = 0
            for index, _game in seasonGames.iterrows():
                gameDay = _game.game_date.split(' ')[0] # trims the h:m:s part off

                qs = f"select * from play_by_play where game_id == '{_game.game_id}'"
                pbps = pd.read_sql_query(qs, db_con)
                if pbps.shape[0] == 0:
                    badBunny += 1
                    if _game.play_by_play[0].shape[0] != 0:
                        print('BADBAD', _game.game_date, _game.game_id)
                    #print('BB ',gameDay,season,game.game_id)
                else:
                    _dfs['game'].loc[index, 'play_by_play'] = [pbps]
                    _game.play_by_play = [pbps]
                    #print(index,gameDay,pbps.shape)
                _gamesByDate[gameDay] = _game

            print(f' {season}:{len(_gamesByDate)}:{badBunny} ',end='')
            _gamesBySeason[season] = _gamesByDate
        print()
        
        _gamesByTeam[nickName] = _gamesBySeason      

    return _dfs, _gamesByTeam       
  
def getGames(teams, games, teamNickName, seasonType, startDate):
    teamID = teams.query(f'abbreviation == "{teamNickName}"').id.values[0] 
    return games.query(f'season_id >= "{startDate}" and season_type == "{seasonType}" and (team_id_home == "{teamID}" or team_id_away == "{teamID}")')

def filterGamesByDateRange(start, stop, games):
    return  {key: value for key, value in games.items() if start <= key <= stop}

def getTestData():

    _START_DAY = '2023-03-21'
    _STOP_DAY = '2023-03-22'
    _TEAM = 'OKC'
    _SEASON = '2022'

    results = filterGamesByDateRange( _START_DAY, _STOP_DAY, gamesByTeam[_TEAM][_SEASON])
    return results, _START_DAY, _STOP_DAY, _TEAM, _SEASON

def dump(df,keepers):
    for i in df.index:
        ts = ''
        for col in keepers:
            t =  df[col].loc[i:i].values[0]
            if t != None :
                ts += f'{t} '
        print(ts)
## firgithub
def generatePBP():

    keepers = [
        'eventmsgtype', 
        'period', 'pctimestring', 
        #'homedescription', 
        #'neutraldescription', 
        #'visitordescription', 
        
        'player1_name','player2_name','player3_name',]
    
    test_data, _start, _stop, _team, _season = getTestData()
 
    test_days = list(test_data.keys())

    for date in test_days:
        pbp_forDate = test_data[date].play_by_play[0]
        if pbp_forDate.shape[0] != 0:   

            # 8 substitution event, get our players thata are subbed IN/OUT
            pbp_subs = pbp_forDate.query('eventmsgtype == 8') 

            # player1 IN, player2 OUT 
            p1s = pbp_subs.query('player1_team_abbreviation == "OKC"')['player1_name'] 
            p2s = pbp_subs.query('player2_team_abbreviation == "OKC"')['player2_name']

            playersInGame = list(set(p1s) | set(p2s))          
             
            timeSpans = {}  # collect timespans played by this player
            for player in playersInGame:
                timeSpans[player] = []
                for x in pbp_subs.index:
                    z = pbp_subs.loc[x]
                    p1 = z['player1_name']
                    p2 = z['player2_name']
                    if (p1 == player) or (p2 == player):
                        t = 'IN' if p2 == player else "OUT"
                        timeSpans[player].append([t,z.period,z.pctimestring]) 
                        #print(date, z.period,
                        #      f'{z.pctimestring:<6}', f'{x:<5}',
                        #      ' IN:',f'{p2:<15}',' OUT:',f'{p1:<15}',
                        #      z.homedescription  ) 

            for player in list(timeSpans.keys()):
                print(player)
                for _ts in timeSpans[player]:
                    

                    sub_in = _ts[0] == 'IN'
                    period = _ts[1]
                    clock  = _ts[2]

                    print(x,_ts[0],period,clock)

    return

def main():

    global dfs 
    global gamesByTeam

    # gamesByTeam['OKC']['2022]['2023-01-03']  -- gets game via team,year,game_date

    dfs, gamesByTeam = loadNBA()


    generatePBP()

    """
    tests(test_data)
    t = pd.DataFrame(test_data[0]).T
    plot1(t)
    #input("Press Enter to continue...")
    plot2(t)
    #input("Press Enter to continue...")
    """

# TESTS TESTS TESTS TESTS TESTS TESTS TESTS TESTS
def tests(_testdata):
    
    results     = _testdata[0]
    _START_DAY  = _testdata[1]
    _STOP_DAY   = _testdata[2]
    _TEAM       = _testdata[3]
    _SEASON     = _testdata[4]

    resDates = list(results.keys())

    t =  np.array(dfs['game'].team_abbreviation_home) == _TEAM
    t |= np.array(dfs['game'].team_abbreviation_away) == _TEAM
    t &= np.array(dfs['game'].season_id) == _SEASON
    t &= ((
        np.array(dfs['game'].game_date >= resDates[0] + " 00:00:00")
        & np.array(dfs['game'].game_date <= resDates[-2] + " 00:00:00") ))

    g0 = dfs['game'][list(t)].iloc[0]
    r0 = results[resDates[0]]

    print()
    print('testing filterGamesByDateRange',_TEAM, _START_DAY, _STOP_DAY, _SEASON)
    print()

    print('g0',g0.game_date,g0.season_id,g0.matchup_away)
    print('r0',r0.game_date,r0.season_id,r0.matchup_away)

    print()
    print('data for date range',_TEAM, _START_DAY, _STOP_DAY, _SEASON)
    print()

    t_res = pd.DataFrame(results).T

    # TEST list and sum of columns that are numeric

    for colname in t_res.columns:
        firstValueOfColumn = t_res[colname][0:1].values[0]
        if type(firstValueOfColumn) in [type(1),type(1.0)]:
            tmp  = list(t_res[colname])
            print(colname, tmp, sum(tmp))
        #else:
        #    print(f'col name {colname} not numeric.')
            
    # print number of events in our pbp file        
    our_pbps = list(t_res['play_by_play'])

    def fnx(x): 
        if type(x) != pd.DataFrame: return 0
        return x.shape[0]

    pbp_steps = list(map(lambda x: fnx(x), our_pbps))

    print('play by play events', pbp_steps)

if __name__ == "__main__":
    main()


"""
play_by_play feilds

[
'game_id', 'eventnum', 

'eventmsgtype', 
'eventmsgactiontype', 

'period', 'wctimestring', 'pctimestring', 

'homedescription', 
'neutraldescription', 
'visitordescription', 

'score', 
'scoremargin', 

'person1type', 'player1_id', 'player1_name', 'player1_team_id', 'player1_team_city', 'player1_team_nickname', 'player1_team_abbreviation', 
'person2type', 'player2_id', 'player2_name', 'player2_team_id', 'player2_team_city', 'player2_team_nickname', 'player2_team_abbreviation', 
'person3type', 'player3_id', 'player3_name', 'player3_team_id', 'player3_team_city', 'player3_team_nickname', 'player3_team_abbreviation', 

'video_available_flag'
]

game feilds
[
    'season_id', 'team_id_home', 
    'team_abbreviation_home', 'team_name_home',
    'game_id', 'game_date', 'matchup_home', 'wl_home', 'min', 

    'fgm_home','fga_home', 'fg_pct_home', 'fg3m_home', 'fg3a_home', 'fg3_pct_home',
    'ftm_home', 'fta_home', 'ft_pct_home', 'oreb_home', 'dreb_home',
    'reb_home', 'ast_home', 'stl_home', 'blk_home', 'tov_home', 'pf_home',
    'pts_home', 'plus_minus_home', 
       
    'video_available_home', 
    
    'team_id_away', 'team_abbreviation_away', 'team_name_away', 'matchup_away', 'wl_away',
       
    'fgm_away', 'fga_away', 'fg_pct_away', 
    'fg3m_away', 'fg3a_away','fg3_pct_away', 
    'ftm_away', 'fta_away', 'ft_pct_away', 
    'oreb_away', dreb_away', 'reb_away', 
    'ast_away', 'stl_away', 'blk_away', 'tov_away', 'pf_away', 
       
    'pts_away', 'plus_minus_away', 
       
       'video_available_away',
       'season_type', 
       'play_by_play'

 keeps = ['Shai Gilgeous-Alexander','Jalen Williams', 'Josh Giddey', 
     'Tre Mann','Jaylin Williams', 'Dario Saric', 'Ousmane Dieng'
     'Isaiah Joe', 'Kenrich Williams',
     'Mike Muscala','Luguentz Dort','Aaron Wiggins','Jeremiah Robinson-Earl' ]
"""