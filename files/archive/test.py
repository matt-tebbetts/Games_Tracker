
# set game names and prefixes
game_prefixes = ['#Worldle', '#travle', '#travle_usa', '#travle_gbr',
                 'Wordle', 'Factle.app', 'boxofficega.me',
                 'Atlantic', 'Connections', '#Emovi']
game_prefixes.sort(key=len, reverse=True)

# sample discord message
msg_txt = """#travle_usa #6 (5/9) (0 hints)
✅✅✅🟧✅
https://imois.in/games/travle/usa/
"""

# check for game score
for game_prefix in game_prefixes:

    print(f"checking for {game_prefix}...")

    # find prefix
    if str.lower(msg_txt).startswith(str.lower(game_prefix)):

        print(f"yes! prefix is {game_prefix}")

        if game_prefix in ["#travle", "#travle_usa", "#travle_gbr"]:
            game_name = game_prefix[1:]
            print(f"game_name is {game_name}")

            # find position of opening and closing parentheses
            opening_paren = msg_txt.find('(')
            closing_paren = msg_txt.find(')')

            # get substring between parentheses
            game_score = msg_txt[opening_paren+1:closing_paren]

            # set metric_02 based on first character of game_score
            metric_02 = 1 if game_score[0] != '?' else 0
        
        break
    
    else:
        print(f"prefix is not {game_prefix}")