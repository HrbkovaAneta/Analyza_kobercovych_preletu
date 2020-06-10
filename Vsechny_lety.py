import pandas as pd
import os
import glob

#namapovani slozky v PC
os.chdir ("D:\DA\PROJEKT - kobercové přelety\Všechny lety")
extension = 'csv'
all_filenames = [i for i in glob.glob('*.{}'.format(extension))]

###Zapisujeme do souboru postupně skrze list:
li = []
for filename in all_filenames:
  df = pd.read_csv(filename, index_col=None, header=0)
  df['Name'] = filename
  df['RowID'] = df.index
  df['Name_RowID'] = df[['Name','RowID']].astype(str).apply('_'.join,1)
  coordinate = df['Position'].str.split(',', expand=True)
  df['Latitude'] = pd.to_numeric(coordinate[0]).round(6)
  df['Longitude'] = pd.to_numeric(coordinate[1]).round(6)
  UTC = df['UTC'].str.split('T', expand=True)
  df['Date'] = (UTC[0])
  df['T'] = UTC[1]
  t = df['T'].str.split('Z', expand=True)
  df['Time'] = t[0]
  df.drop('T', axis=1, inplace=True)
  li.append(df)

frame = pd.concat(li, axis=0, ignore_index=True)
frame.to_csv('Všechny lety.csv')
