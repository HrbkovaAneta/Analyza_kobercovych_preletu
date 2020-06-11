import pandas as pd
import geopy.distance
from geopy.distance import geodesic
import numpy as np
import os
import glob
from datetime import datetime

WINDOW_SIZE = 15
ROUND_BASE = 10
DIRECTION_LO_BOUND = 70

###Funkce, na zobrazení času ze stringu '2020-04-01T11:26:34Z' na string '11:26:34'
def convertTime(d):
    new_time = datetime.strptime(d,"%Y-%m-%dT%H:%M:%SZ")
    return new_time.time()

###Mapovaní složky v PC
os.chdir ("D:\DA\PROJEKT - kobercové přelety\Všechny lety")
extension = 'csv'
all_filenames = [i for i in glob.glob('*.{}'.format(extension))]

###Zapisujeme postupně do souboru:
source = open('Tabulka - lety.csv', 'w', encoding='utf-8')
source.write("Název letu, Datum, Čas startu, Část dne, Trvání, Vzdálenost prvního a posledního bodu, Celková vzdálenost, Počet bodů, Počet bodů na km, Počet otáček, Počet přímek, Detekce letu\n")

for name in all_filenames:
  df = pd.read_csv(name)
  coordinate = df['Position'].str.split(',', expand=True)
  df['Latitude'] = pd.to_numeric(coordinate[0]).round(6)
  df['Longitude'] = pd.to_numeric(coordinate[1]).round(6)
  df['Latitude_shift'] = df['Latitude'].shift(1)
  df['Longitude_shift'] = df['Longitude'].shift(1)

  ###Převod na radiány
  df['Lat1'] = np.radians(df['Latitude'])
  df['Lat2'] = np.radians(df['Latitude_shift'])
  df['Lon1'] = np.radians(df['Longitude'])
  df['Lon2'] = np.radians(df['Longitude_shift'])

  ###Výpočet vzdálenosti přes Haversinův vzorec
  df['Dif_Lon'] = df['Lon2'] - df['Lon1']
  df['Dif_Lat'] = df['Lat2'] - df['Lat1']
  df['a'] = np.sin(df['Dif_Lat']/2)**2 + np.cos(df['Lat1']) * np.cos(df['Lat2']) * np.sin(df['Dif_Lon']/2)**2
  df['c'] = 2 * np.arcsin(np.sqrt(df['a'])) 
  df['km'] = 6372.795 * df['c']
  Total_distance = df['km'].sum()

  ###Vzdálenost mezi prvním a posledním bodem
  origin = (df['Latitude'].iloc[0], df['Longitude'].iloc[0])
  df['Distance_First_and_Last'] = df.apply(lambda x: geopy.distance.geodesic(origin,(x['Latitude'],x['Longitude'])).km, axis=1)
  Distance_F_a_L = df['Distance_First_and_Last'].iloc[-1]

  ###Vzdálenost mezi prvním(new_origin) a ostatními body
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

  ###Filtrace 180 stupnu nám uvede přímky 
  lines = lines[lines["Difference"]==180]
  
  ###Postupně otevřu soubory csv
  file = open(name)
  input_number = [number.strip() for number in file]
  file.close()

  ###Pracujeme bez hlavičky souboru
  input_number = input_number[1:]
  input_number = [number.replace('"','') for number in input_number]
  input_number = [number.split(',') for number in input_number]

  ###Vytvorim si list s časy
  times = [time[1] for time in input_number]

  ###Vytvořím list hodin, kterou upravím funkcí converTime 
  hours =[]
  for time in times:
    new_time =str(convertTime(time))
    hours.append(new_time)
    
  ###Delta posledního času a prvního v seznamu
  Duration = datetime.strptime(hours[-1], '%H:%M:%S') - datetime.strptime(hours[0], '%H:%M:%S')

  ###Atributy
  Linie = len(lines)
  Points = (len(coordinate))
  Turn = (df["TurnPointIndicator"]).sum()
  Points_km = Points/Total_distance

  ###Podmínky detekce letu
  for Detection in df:
    if Turn >= 4 and Linie >= 2:
      Detection = 'Koberec'
    else:
      Detection = 'Primka'
  
  ###Úprava času a datu
  UTC = df['UTC'].str.split('T', expand=True)
  Date = (UTC[0]).iloc[0]

  df['Time'] = (UTC[1])
  df['Time'] = df['Time'].str.split('Z', expand=True)
  Start_time = df['Time'].iloc[0]

  if Start_time > '04:00:00' and Start_time < '12:00:00':
    Part_of_day = 'Morning'
  elif Start_time > '12:00:00' and Start_time < '18:00:00':
    Part_of_day = 'Afternoon'
  elif Start_time > '18:00:00' and Start_time < '21:00:00':
    Part_of_day = 'Evening'
  else:
    Part_of_day = 'Night'

###Zapíšem všechny hodnoty do souboru
  source.write(name + "," + str(Date) + "," + str(Start_time) + "," + str(Part_of_day) + "," + str(Duration) + "," + str(Distance_F_a_L) + "," + str(Total_distance) + "," + str(Points) + "," + str(Points_km) + "," + str(Turn) + "," + str(Linie) + "," + str(Detection) + "\n")

###Ukončím zápis do souboru:
source.close()
