from datetime import datetime, timedelta

my_splits = [("0:00:00", "Preparation"),
                 ("0:03:43", "Lion's Arch"),
                 ("0:09:36", "Rata Sum"),
                 ("0:12:45", "The Grove"),
                 ("0:15:20", "Divinity's Reach"),
                 ("0:19:58", "Hoelbrak"),
                 ("0:24:40", "Black Citadel"),
                 ("0:28:40", "Jade Bot Buffs"),
                 ("0:30:36", "Metrica Province"),
                 ("0:45:10", "Brisban Wildlands"),
                 ("1:03:28", "Caledon Forest"),
                 ("1:18:47", "Queensdale"),
                 ("1:39:25", "Kessex Hills"),
                 ("1:55:53", "Gendarran Fields"),
                 ("2:09:34", "Harathi Hinterlands"),
                 ("2:25:44", "Bloodtide Coast"),
                 ("2:31:10", "Jade Bot Buffs"),
                 ("2:32:40", "Bloodtide Coast"),
                 ("2:43:19", "Sparkfly Fen"),
                 ("3:00:59", "Mount Maelstrom"),
                 ("3:17:36", "Dredgehaunt Cliffs"),
                 ("3:32:58", "Wayfarer Foothills"),
                 ("3:49:55", "Snowden Drifts"),
                 ("4:02:54", "Lornar's Pass"),
                 ("4:24:29", "Timberline Falls"),
                 ("4:42:25", "Frostgorge Sound"),
                 ("5:00:42", "Fireheart Rise"),
                 ("5:15:34", "Diessa Plateau"),
                 ("5:32:42", "Plains of Ashford"),
                 ("5:49:16", "Blazeridge Steppes"),
                 ("6:05:07", "Iron Marches"),
                 ("6:24:49", "Fields of Ruin"),
                 ("6:40:05", "Backtracking some stuff"),
                 ("6:41:03", "Straits of Devastation"),
                 ("6:48:43", "Malchor's Leap"),
                 ("6:57:06", "Cursed Shore"),
                 ("6:59:28", "End")];

current_location_found = False
current_location = "Straits of Devastation"
remaining_time = 0
remmaining_zones = 1
total_time = 0

# loop through the data and print out the time between each split
for i in range(len(my_splits)):
    if i == 0:
        continue
    previous_split_name = my_splits[i-1][1]
    split_time = datetime.strptime(my_splits[i][0], "%H:%M:%S")
    prev_split_time = datetime.strptime(my_splits[i-1][0], "%H:%M:%S")
    time_diff = split_time - prev_split_time
    time_diff_in_minutes = time_diff / timedelta(minutes=1)
    # round to 2 decimal places
    time_diff_in_minutes = round(time_diff_in_minutes, 2)
    print(f'{previous_split_name}: {time_diff_in_minutes} minutes')
    total_time += time_diff_in_minutes
    if not current_location_found:
        if previous_split_name == current_location:
            current_location_found = True
            remaining_time = time_diff_in_minutes
    else:
        remaining_time += time_diff_in_minutes
        remmaining_zones += 1
print()
print(f'Total time: {round(total_time, 2)} minutes')
print(f'Remaining zones: {remmaining_zones}')
print(f'Remaining time: {round(remaining_time, 2)} minutes')
realistic_time = remaining_time * 1.5
print(f'Realistic time: {round(realistic_time, 2)} minutes')