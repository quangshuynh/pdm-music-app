import openpyxl, sqlite3


genres = [
    'rock', 'pop', 'alternative', 'breakcore', 'blues', 'country', 'dance',
    'folk', 'ethnic', 'lo-fi', 'jazz', 'rap', 'hip hop',
    'classical', 'easy listening', 'electronic', 'soul', 'metal', 'punk'
]

genre_index = {
    'rock':1,'pop':2, 'alternative':3, 'breakcore':4, 'blues':5, 'country':6, 'dance':7,
    'folk':8, 'ethnic':9, 'lo-fi':10, 'jazz':11, 'rap':12, 'hip hop':13,
    'classical':14, 'easy listening':15, 'electronic':16, 'soul':17, 'metal':18, 'punk':19
}

con = sqlite3.connect('musicData.db')
cur_output = con.execute('SELECT * FROM song_genre')

# Getting genres_of_song for quick access
genres_of_song:dict[str,list] = {}
for row in cur_output:
    if row[0] not in genres_of_song:
        genres_of_song[row[0]] = []
    genres_of_song[row[0]].append(row[1])

# print(len(genres_of_song))

# dict which takes release year, and the number of genre releases that year
genre_releases_per_year:dict[str,list] = {}

cur_output = con.execute('SELECT song_id, release_date FROM song')
for row in cur_output:
    # making sure song has genres
    if row[0] in genres_of_song:
        release_year = row[1][0:4]
        # if release year not in genre releases add it to dict
        if release_year not in genre_releases_per_year:
            genre_releases_per_year[release_year] = [0]*(len(genres)+1)
            genre_releases_per_year[release_year][0] = int(release_year)
        
        # parsing genres of this song to add to list
        for genre in genres_of_song[row[0]]:
            genre_releases_per_year[release_year][genre_index[genre]] += 1


# Pushing to excel
wb = openpyxl.Workbook()
sheet = wb.active

# Making headers
sheet["A1"] = "Year"
sheet["B1"] = "Releases Rock"
sheet["C1"] = "Releases Pop"
sheet["D1"] = "Releases Alternative"
sheet["E1"] = "Releases Breakcore"
sheet["F1"] = "Releases Blues"
sheet["G1"] = "Releases Country"
sheet["H1"] = "Releases Dance"
sheet["I1"] = "Releases Folk"
sheet["J1"] = "Releases Ethnic"
sheet["K1"] = "Releases Lo-Fi"
sheet["L1"] = "Releases Jazz"
sheet["M1"] = "Releases Rap"
sheet["N1"] = "Releases Hip Hop"
sheet["O1"] = "Releases Classical"
sheet["P1"] = "Releases Easy Listening"
sheet["Q1"] = "Releases Electronic"
sheet["R1"] = "Releases Soul"
sheet["S1"] = "Releases Metal"
sheet["T1"] = "Releases Punk"

# getting rows to push
rows_for_excel = genre_releases_per_year.values()
index = 2
for row in rows_for_excel:
    sheet["A"+str(index)] = row[0]
    sheet["B"+str(index)] = row[1]
    sheet["C"+str(index)] = row[2]
    sheet["D"+str(index)] = row[3]
    sheet["E"+str(index)] = row[4]
    sheet["F"+str(index)] = row[5]
    sheet["G"+str(index)] = row[6]
    sheet["H"+str(index)] = row[7]
    sheet["I"+str(index)] = row[8]
    sheet["J"+str(index)] = row[9]
    sheet["K"+str(index)] = row[10]
    sheet["L"+str(index)] = row[11]
    sheet["M"+str(index)] = row[12]
    sheet["N"+str(index)] = row[13]
    sheet["O"+str(index)] = row[14]
    sheet["P"+str(index)] = row[15]
    sheet["Q"+str(index)] = row[16]
    sheet["R"+str(index)] = row[17]
    sheet["S"+str(index)] = row[18]
    sheet["T"+str(index)] = row[19]
    index+=1
    

# saving excel
wb.save("genre_over_years.xlsx")