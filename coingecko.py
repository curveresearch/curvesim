import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from itertools import combinations
from time import sleep

def get(id, vs_currency, days):
    url = 'https://api.coingecko.com/api/v3/coins/'+id+'/market_chart'
    p = {'vs_currency': vs_currency, 'days': days}
    
    getData = True
    while getData:
        r = requests.get(url, params=p)
        if r.status_code == 200:
            getData = False
        else:
            print(str(r.status_code))
            sleep(.1)
    
    data = pd.DataFrame(r.json()['prices'], columns=['timestamp', 'prices'])
    data = data.merge(pd.DataFrame(r.json()['total_volumes'], columns=['timestamp', 'volumes']))
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms', utc='True')
    data = data.set_index('timestamp')
    
    return data
    
def poolprices(coins, vs_currency, days):
    #Times to reindex to hourly intervals starting on half hour mark
    t_end = datetime.utcnow() - timedelta(days = 1)
    t_end = t_end.replace(hour=23, minute=30, second=0, microsecond=0)
    t_start = t_end - timedelta(days = days+1)
    t_samples = pd.date_range(start=t_start, end=t_end, freq='60T', tz=timezone.utc)
    
    #Get data from API
    qprices = []
    qvolumes = []
    for coin in coins:
        curr_data = get(coin, vs_currency, days+3)
        curr_data.drop(curr_data.tail(1).index,inplace=True) #remove last row
        curr_data = curr_data.reindex(t_samples, method = 'ffill')
        qprices.append(curr_data['prices'])
        qvolumes.append(curr_data['volumes'])
    
    qprices = pd.concat(qprices,axis=1)
    qvolumes = pd.concat(qvolumes,axis=1)
    
    #Compute prices by coin pairs
    combos = list(combinations(range(len(coins)),2))
    prices = []
    volumes = []
        
    for pair in combos:
        prices.append(qprices.iloc[:,pair[0]]/qprices.iloc[:,pair[1]]) #divide prices
        volumes.append(qvolumes.iloc[:,pair[0]]+qvolumes.iloc[:,pair[1]]) #sum volumes
        
    prices = pd.concat(prices,axis=1)
    volumes = pd.concat(volumes,axis=1)
    
        
    return prices, volumes


