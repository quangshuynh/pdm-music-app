import random
import sqlite3 as sql

# Setting up variables
print("Grabbing user information.")
con:sql.Connection = sql.connect('userData.db', detect_types=sql.PARSE_DECLTYPES)
db_output = con.execute("SELECT username FROM user;")
user_followers = [] # format [# followers, user followed]
usernames = []
for username in db_output:
    usernames.append(username[0])
    user_followers.append([1,username[0]])

# Deleting previous 
print("\nDeleting previous followers.")
con.execute('DELETE FROM user_follow')
con.commit()

# Creating follows
print("\nDoing follower loop.")
follow_count = len(usernames)-1
random.seed(121839597132894)
for username in usernames:
    followed_so_far = []

    # Following users
    for followNum in range(10):
        # Getting the 'index' of the user we wish to follow
        random_user_value = random.randint(0,follow_count)
        current_value = 0
        index = 0
        follow_count += 1

        # Finding the user we're following
        while True:
            current_value += user_followers[index][0]
            # we are at the user
            if random_user_value <= current_value:
                # If we already followed, or we are the user move to the next index, if at end of list previous index
                if user_followers[index][1] in followed_so_far or user_followers[index][1] == username:
                    if index == len(user_followers)-1:
                        index-=1
                    else:
                        index+=1
                followed_so_far.append(user_followers[index][1])
                con.execute("INSERT INTO user_follow VALUES(?,?);", (username, user_followers[index][1]))
                user_followers[index][0] += 1
                break
            index += 1
        con.commit()