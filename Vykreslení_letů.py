import pandas as pd
import geopy.distance
from geopy.distance import geodesic
import numpy as np
import os
import glob
from datetime import datetime
import matplotlib.pyplot as plt

WINDOW_SIZE = 15
ROUND_BASE = 10
DIRECTION_LO_BOUND = 70

###Mapovaní složky v PC
os.chdir ("D:\DA\PROJEKT - kobercové přelety\Všechny lety")
extension = 'csv'
all_filenames = [i for i in glob.glob('*.{}'.format(extension))]

for name in all_filenames:
  df = pd.read_csv(name)
  coordinate = df['Position'].str.split(',', expand=True)
  df['Latitude'] = pd.to_numeric(coordinate[0]).round(6)
  df['Longitude'] = pd.to_numeric(coordinate[1]).round(6)
  
  ###Vzdálenost mezi prvním a posledním bodem
  origin = (df['Latitude'].iloc[0], df['Longitude'].iloc[0])
  df['Distance_First_and_Last'] = df.apply(lambda x: geopy.distance.geodesic(origin,(x['Latitude'],x['Longitude'])).km, axis=1)
  Distance_F_a_L = df['Distance_First_and_Last'].iloc[-1]

  ###Vzdálenost mezi prvním(origin) a ostatními body
  new_origin = (df["Latitude"].min()-0.1,df["Longitude"].max()+0.1)
  df['Distance_From_First'] = df.apply(lambda x: geopy.distance.geodesic(new_origin,(x['Latitude'],x['Longitude'])).km, axis=1)

  ###Průměr vzdálenost od prvního bodu(origin)
  df['Average_D_Distance'] = df['Distance_From_First'].rolling(window=WINDOW_SIZE,center=True).mean()

  ###Doplní se jedničky - pokud dojde ke změně směru k prvnímu bodu dojde ke změně znamínka
  df['Average_D_Distance_Diff'] =  np.sign(df['Average_D_Distance'].diff())
  df['Shift_Distance'] = df['Average_D_Distance_Diff'].shift(1)

  ####Směr - rozdíl
  df['Delta_Direction'] = df['Direction'].diff()

  ###Funkce, která nám změní hodnoty, pokud překročíme 360 stupňů
  def greater_180(df):
    result = df['Delta_Direction']
    if (abs(df['Delta_Direction']) > 180):
      result = df['Delta_Direction'] - np.sign(df['Delta_Direction']) * 360
      return result
    else:
      return result

  df['Greater_360'] = df.apply(greater_180,axis=1)
  df['Sum_D_Direction'] = df['Greater_360'].rolling(window=WINDOW_SIZE,center=True).sum()
  df['Sum_D_Direction_Abs'] = (df['Greater_360'].rolling(window=WINDOW_SIZE,center=True).sum()).abs()

  df["TurnPointIndicator"] = df.apply(
          lambda row:
              1 if np.sign(row.Average_D_Distance_Diff) != np.sign(row.Shift_Distance)
              and row.Sum_D_Direction_Abs >= DIRECTION_LO_BOUND
              else 0,
          axis=1)

  ####Zaokrouhlení na 10
  df["RoundDirection"] = df.apply(
          lambda row: ROUND_BASE * round(row.Direction/ROUND_BASE) if ROUND_BASE * round(row.Direction/ROUND_BASE) != 360 else 0
          ,axis = 1
      )

  ####Zgrupuje se to podle definovaných bodů a podle zaokrouhlené direction
  df["TurnGroup"] = df["TurnPointIndicator"].cumsum()
  lines = df.groupby(["TurnGroup","RoundDirection"]).agg(
      cnt = ('TurnGroup', 'count')
  )
  ###Převod do tabulky a reset indexů 
  lines = lines.reset_index()

  ###Označení největšího počtu bodů (cnt = udává počet) v rámci skupiny jedničkou
  lines['RN'] = lines.sort_values(['cnt'], ascending=[False]) \
            .groupby(['TurnGroup']) \
            .cumcount() + 1 

  ###Výběr linií pro každou skupinou s největším počtem bodů 
  lines = lines[lines.RN==1]

  ###Výpočet rozdílu kurzu mezi liniemi
  lines["Difference"]= (lines["RoundDirection"].diff()).abs()

  ###vybere latitude a longitude, kde je definovaná hodnota 1 
  data = df[df['TurnPointIndicator'] == True]

  ###vykreslení
  plt.plot(df['Latitude'],df['Longitude'])
  plt.plot(data['Latitude'],data['Longitude'],'o', color='red')
  plt.show()

  ###ukládání letů do složky
  #plt.savefig(name + '.png')
  #plt.close()