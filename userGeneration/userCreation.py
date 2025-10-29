from datetime import datetime
import random
import sqlite3 as sql
import bcrypt

# helpful variables
genres = [
    'rock', 'pop', 'alternative', 'breakcore', 'blues', 'country', 'dance',
    'folk', 'ethnic', 'lo-fi', 'jazz', 'rap', 'hip hop',
    'classical', 'easy listening', 'electronic', 'soul', 'metal', 'punk'
]
username_choices = [
    'gretta','goober','great','posom','pyro','fire','stuck','eater','poop','sparkles','coder','mario','maker','hAx0r',
    'eggbert','john','jeff','jeremy','troll','toby','fox','black','story','sans','papyrus','rudy','knight','dess','kris',
    'frisk','soul','tale','master','king','pizza','baker','improv','knife','music','liker','haver','love','level','gamer',
    'anime','watcher','afar','door','kicker','gauge','pasta','hungry','food','plsplspls','home','under','carol',
    'bruno','mars','uptown','funk','friday','night','silent','nightmare','icee'
]
first_names = [
    'Gretta','John','Jeff','Jeremy','Toby','Rudy','Sans','Kris','Frisk','Baker','Noelle','Bob','Bill','William','Gayle',
    'Kai','Quang','Uday','James','Anthony','Anna','Brett','Chris','Carol','Bella','Carl','Daren','Darling','Eddison',
    'Robert','Rachel','Truman','Tiffany','Pierre','Pablo','Paul','Paula','Odile','Scarlette','Victoria','Victor','Fred',
    'Human','Harold','Jessica','Kye','Larry','Laura','Xavier','Carlos','Mario','Luigi','Bowser','Doug','Norman','Andrew',
    'Susie','Milo','Caroline','Alexander','Ronald','Bruno'
]
last_names = [
    'Rogers','Smith','Baker','Brown','Eggbert','Bowser','Mario','Jameson','Jackson','Gaster','Sweet','Miller','Davis',
    'Kennedy','Lincoln','Trump','Washington','Lopez','Clark','King','Hall','Roberts','Collins','Cook','Ward','Watson',
    'Holmes','Wood','Gray','Henderson','Hamilton','West','McDonald','Mars'
]
emails = [
    '@gmail.com','@hotmail.com','@yahoo.com','@mail.com','@rit.edu','@bbc.uk','@gaylemail.com'
]




# Grabbing DB information from musicData
conDb:sql.Connection = sql.connect('musicData.db', detect_types=sql.PARSE_DECLTYPES)
curDb:sql.Cursor = conDb.cursor()

print("Grabbing groups and putting inside dictionary.")
group_song:dict[str,str] = {} # maps group to song
song_group:dict[str,str] = {} # maps song to group
all_songs:list[str] = []
cur_output = curDb.execute('SELECT group_id, song_id FROM song')
for row in cur_output:
    group_song[row[0]] = row[1]
    song_group[row[1]] = row[0]
    all_songs.append(row[1])
groups = list(group_song.keys())

print("Grabbing genres and putting inside dictionary.")
songs_of_genre:dict[str,list] = {}
genres_of_song:dict[str,list] = {}
for genre in genres:
    songs_of_genre[genre] = []
cur_output = curDb.execute('SELECT * FROM song_genre')
for row in cur_output:
    songs_of_genre[row[1]].append(row[0])
    if row[0] not in genres_of_song:
        genres_of_song[row[0]] = []
    genres_of_song[row[0]].append(row[1])

print("\nDoing user creation to new db for safety.")
con:sql.Connection = sql.connect('userData.db') # copy paste musicData.db and rename it to userData.db

print('Deleting previous information.')
con.execute('DELETE FROM user')
con.execute('DELETE FROM user_follow')
con.execute('DELETE FROM listen')
con.execute('DELETE FROM rating')
con.execute('DELETE FROM collection')
con.execute('DELETE FROM song_within_collection')
con.commit()




print('\nDoing user creation loop.')

# Setting up loop variables
user_genre_interests:list[str]
user_group_interests:list[str]
user_collection:list[str] = [] # Stores song ids in collection
user_collection_name:str
collection_count:int = 0
user_happiness:int # staight bump to rating
user_stingyness:float # percent songs listened from fav genre
user_activity:int # Number of songs
songs_genre:int
songs_random:int
usernames:dict[str, int] = {}
usernames_numbers:dict[str, int] = {}
user_row:dict = {
    'username':'PLACEHOLDER',
    'password':bcrypt.hashpw('password'.encode('utf-8'), bcrypt.gensalt()).decode("utf-8"),
    'first_name':'PLACEHOLDER',
    'last_name':'PLACEHOLDER',
    'email':'PLACEHOLDER',
    'display_name':'PLACEHOLDER',
    'creation_date':datetime.now(),
    'last_accessed':datetime.now()
}
listen_row:dict = {
    'listener_username':'PLACEHOLDER',
    'song_id':'PLACEHOLDER',
    'date_of_view':datetime.now()
}
rating_row:dict = {
    'rater_username':'PLACEHOLDER',
    'song_id':'PLACEHOLDER',
    'rating':0
}

for j in range(2000):
    # Reset values for new user
    user_genre_interests = []
    user_group_interests = []
    user_happiness = random.randint(0,2)
    user_stingyness = (random.random()*0.9)+0.1
    user_activity = random.randint(5,40)
    songs_genre = int(user_activity*user_stingyness)
    songs_random = user_activity-songs_genre

    # Generating user information
    username_pt1:str = username_choices[random.randint(0,len(username_choices)-1)]
    username_pt2:str = username_choices[random.randint(0,len(username_choices)-1)]
    username_tmp:str = username_pt1+username_pt2[0].upper()+username_pt2[1:]
    if username_tmp in usernames:
        usernames[username_tmp] += 1
        username_tmp += str(usernames[username_tmp])
        print(username_tmp)
    else:
        usernames[username_tmp] = 0
    usernames_numbers[username_tmp] = 1
    user_row['username'] = username_tmp
    user_row['first_name'] = first_names[random.randint(0,len(first_names)-1)]
    user_row['last_name'] = last_names[random.randint(0,len(last_names)-1)]
    user_row['email'] = username_tmp+emails[random.randint(0,len(emails)-1)]
    if random.random() > 0.5:
        user_row['display_name'] = user_row['first_name']+' '+user_row['last_name']
    else:
        user_row['display_name'] = username_tmp
    
    # Inserting user to table
    con.execute("INSERT INTO user VALUES(?,?,?,?,?,?,?,?)", tuple(user_row.values()))
    con.commit()


    # Doing listens/ratings
    listen_row['listener_username'] = username_tmp
    rating_row['rater_username'] = username_tmp

    # Filling favorite group/genre
    for i in range(10):
        user_group_interests.append(groups[random.randint(0,len(groups)-1)])
    for i in range(3):
        user_genre_interests.append(genres[random.randint(0,len(genres)-1)])
    
    # Reseting collection
    user_collection_name = username_choices[random.randint(0,len(username_choices)-1)]+' '+username_choices[random.randint(0,len(username_choices)-1)]+' '+username_choices[random.randint(0,len(username_choices)-1)] 
    user_collection = []

    # going over songs of random stuff
    songs_list = []
    # favorite genre
    for i in range(songs_genre):
        random_genre = user_genre_interests[random.randint(0,2)]
        songs_of_g = songs_of_genre[random_genre]
        songs_list.append(songs_of_g[random.randint(0,len(songs_of_g)-1)])
    # random songs
    for i in range(songs_random):
        songs_list.append(all_songs[random.randint(0,len(all_songs)-1)])
    
    # Going over songs of favorite group
    for group in user_group_interests:
        songs_list.append(group_song[group])

    for song_id in songs_list:
        # calculating rating
        has_fav_group = 0
        group = song_group[song_id]
        if group in user_group_interests:
            has_fav_group = 1
        has_fav_genre = 0
        for genre in genres_of_song:
            if genre in user_genre_interests:
                has_fav_genre = 2
                break
        rating:int = 1+random.randint(0,1)+user_happiness+has_fav_group+has_fav_genre
        
        # inserting listens
        listen_row['song_id'] = song_id
        for i in range(rating):
            listen_row['date_of_view'] = datetime.now()
            con.execute("INSERT INTO listen VALUES(?,?,?)", tuple(listen_row.values()))
            con.commit()

        # Capping rating then inserting rating
        if rating > 5:
            rating = 5
        rating_row['song_id'] = song_id
        rating_row['rating'] = rating
        con.execute("INSERT INTO rating VALUES(?,?,?)", tuple(rating_row.values()))
        con.commit()


        # Handling collection
        if random.random() < rating/5.0:
            user_collection.append(song_id)

            # checking if we are at the 'max size' of a collection
            if len(user_collection) > 5:
                collection_id = '#'+str(collection_count)
                collection_count+=1
                con.execute("INSERT INTO collection VALUES(?,?,?,?)", (collection_id,username_tmp,user_collection_name,datetime.now()))
                con.commit()
                for song in user_collection:
                    con.execute("INSERT INTO song_within_collection VALUES(?,?)",(collection_id,song))
                    con.commit()
                user_collection = []
                user_collection_name = username_choices[random.randint(0,len(username_choices)-1)]+' '+username_choices[random.randint(0,len(username_choices)-1)]+' '+username_choices[random.randint(0,len(username_choices)-1)]

    # Flushing collection
    if len(user_collection) != 0:
        collection_id = '#'+str(collection_count)
        collection_count+=1
        con.execute("INSERT INTO collection VALUES(?,?,?,?)", (collection_id,username_tmp,user_collection_name,datetime.now()))
        con.commit()
        for song in user_collection:
            con.execute("INSERT INTO song_within_collection VALUES(?,?)",(collection_id,song))
            con.commit()
        user_collection = []
        user_collection_name = 'PLACEHOLDER'




print('\nClosing all connections.')
con.close()
curDb.close()
conDb.close()