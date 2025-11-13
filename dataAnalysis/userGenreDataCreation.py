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

# Get this sqlite by turning csvs to data via userGeneration/csvToDb
con = sqlite3.connect('musicData.db')
cur_output = con.execute('SELECT * FROM song_genre')


# Getting genre information (genre proportions)
number_of_genres:dict[str,int] = {}
proportion_of_genres:dict[str,float] = {}
max_of_genre:dict[str,float] = {}
for genre in genres:
    number_of_genres[genre] = 0
    proportion_of_genres[genre] = 0
    max_of_genre[genre] = [0,'']

genres_of_song:dict[str,list] = {}
for row in cur_output:
    number_of_genres[row[1]] += 1
    if row[0] not in genres_of_song:
        genres_of_song[row[0]] = []
    genres_of_song[row[0]].append(row[1])

total_num_genres:int = 0
for number in number_of_genres.values():
    total_num_genres += number

for genre in genres:
    proportion_of_genres[genre] = number_of_genres[genre]/total_num_genres


# print(total_num_genres)
# print(number_of_genres)
# print(proportion_of_genres)

# dict of rows, username, proportion of genre listens, metric for diff from real proportion, total # genre listens
user_song_pref_data:dict[str,list] = {}

cur_output = con.execute('SELECT listener_username, song_id FROM listen')
for row in cur_output:
    # if user not in array add user to array
    if row[0] not in user_song_pref_data:
        user_song_pref_data[row[0]] = [0]*22
        user_song_pref_data[row[0]][0] = row[0]

    # incrementing user genres with genres of this listen
    current_user = user_song_pref_data[row[0]]
    if row[1] in genres_of_song:
        for genre in genres_of_song[row[1]]:
            current_user[genre_index[genre]] += 1
            current_user[-1] += 1 # incrementing total genre listens
    
    user_song_pref_data[row[0]] = current_user

users = user_song_pref_data.keys()
for user in users:
    current_user = user_song_pref_data[user]

    # turning counts into proportions
    for genre in genres:
        current_user[genre_index[genre]] = current_user[genre_index[genre]]/current_user[-1]
        current_user[-2] += abs(current_user[genre_index[genre]]-proportion_of_genres[genre])
        if current_user[genre_index[genre]] > max_of_genre[genre][0]:
            max_of_genre[genre] = [current_user[genre_index[genre]],user]

    # dividing different proportion by amount of genres
    current_user[-2] = current_user[-2]/len(genres)

    user_song_pref_data[user] = current_user


# Pushing to excel
wb = openpyxl.Workbook()
sheet = wb.active

# Making headers
sheet["A1"] = "Username"
sheet["B1"] = "Genre Prop Rock"
sheet["C1"] = "Genre Prop Pop"
sheet["D1"] = "Genre Prop Alternative"
sheet["E1"] = "Genre Prop Breakcore"
sheet["F1"] = "Genre Prop Blues"
sheet["G1"] = "Genre Prop Country"
sheet["H1"] = "Genre Prop Dance"
sheet["I1"] = "Genre Prop Folk"
sheet["J1"] = "Genre Prop Ethnic"
sheet["K1"] = "Genre Prop Lo-Fi"
sheet["L1"] = "Genre Prop Jazz"
sheet["M1"] = "Genre Prop Rap"
sheet["N1"] = "Genre Prop Hip Hop"
sheet["O1"] = "Genre Prop Classical"
sheet["P1"] = "Genre Prop Easy Listening"
sheet["Q1"] = "Genre Prop Electronic"
sheet["R1"] = "Genre Prop Soul"
sheet["S1"] = "Genre Prop Metal"
sheet["T1"] = "Genre Prop Punk"
sheet["U1"] = "Genre Diff"
sheet["V1"] = "Total Genre Listens"

# getting rows to push
rows_for_excel = user_song_pref_data.values()
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
    sheet["U"+str(index)] = row[20]
    sheet["V"+str(index)] = row[21]
    index+=1
    

# saving excel
wb.save("user_genre_data.xlsx")