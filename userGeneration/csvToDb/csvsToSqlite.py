import sqlite3
import pandas as pd
import os

con = sqlite3.connect('musicData.db')

files = os.listdir()
for file in files:
    if file[-4:] != '.csv':
        continue
    filename = file.split('.')[0]
    print(filename,file)
    data = pd.read_csv(file)
    data.to_sql(filename, con, if_exists='replace', index=False)
    con.commit()
con.close()