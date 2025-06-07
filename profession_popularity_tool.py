import requests

def previousPatchName(htmlText, currentPatch):
    patchInListFormat = "\',\'" + currentPatch + "\'"
    spotInListIndex = htmlText.find(patchInListFormat)
    if spotInListIndex == -1:
        print('Error, patch name not found in list: ' + patchInListFormat)
        return None
    # find the last single quote before this index, this is our beginning quote
    beginningQuoteIndex = htmlText.rfind("'", 0, spotInListIndex)
    if beginningQuoteIndex == -1:
        print('Error: beginning quote not found')
        return None
    # take the string between begginning quote and spotInListIndex
    previousPatch = htmlText[beginningQuoteIndex + 1 : spotInListIndex]
    print(previousPatch)
    return previousPatch

def main():
    currentRelease = 'Janthir Wilds Release August 2024'
    # patchPrefaceString = 'Janthir Wilds Release August 2024<br>'
    patchPrefaceString = currentRelease + '<br>'
    popularityUrl = 'https://gw2wingman.nevermindcreations.de/contentPopularity'
    professionList = ['Guardian', 'Dragonhunter', 'Firebrand', 'Willbender', 'Revenant', 'Herald', 'Renegade', 'Vindicator', 'Warrior', 'Berserker', 'Spellbreaker', 'Bladesworn', 'Engineer', 'Scrapper', 'Holosmith', 'Mechanist', 'Ranger', 'Druid', 'Soulbeast', 'Untamed', 'Thief', 'Daredevil', 'Deadeye', 'Specter', 'Elementalist', 'Tempest', 'Weaver', 'Catalyst', 'Mesmer', 'Chronomancer', 'Mirage', 'Virtuoso', 'Necromancer', 'Reaper', 'Scourge', 'Harbinger']

    # check if we have a cached version of the popularity data
    try:
        with open('popularity.data', 'r') as f:
            popularityData = f.read()
            print("Loaded cached popularity data")
    except:
        popularityData = None
        print("No cached popularity data found")
    
    if (popularityData != None):
        print("Using cached data")
        htmlText = popularityData
    else:
        print("Fetching data from the web")
        response = requests.get(popularityUrl) # returns html
    
        if (response.status_code == 200):
            print("Success")
            # write text to file for caching
            with open('popularity.data', 'w') as f:
                f.write(response.text)
        else:
            print(response.status_code)
            print("Failed")

        # get the html text
        htmlText = response.text

    professionPopularitySet = set()
    previousPatchNameRes = previousPatchName(htmlText, currentRelease)

    # loop through the profession list
    for profession in professionList:
        targetSearchString = patchPrefaceString+profession+': '
        patchPrefaceIndex = htmlText.find(targetSearchString)
        if (patchPrefaceIndex == -1):
            print("Patch preface string not found")
            return
        else:
            # print 20 characters after the patch preface string
            prefaceStringLength = len(targetSearchString)
            popularityRawString = htmlText[patchPrefaceIndex:patchPrefaceIndex+prefaceStringLength+6]
            # print(popularityRawString)
            processedString = popularityRawString.replace(targetSearchString, '').split('%')[0]
            # convert string to float
            popularity = float(processedString)
            # print(profession + ': ' + str(popularity))
            professionPopularitySet.add((profession, popularity))

    # sort the set by popularity
    sortedProfessionPopularitySet = sorted(professionPopularitySet, key=lambda x: x[1], reverse=True)
    totalPopularity = 0
    for professionPopularity in sortedProfessionPopularitySet:
        totalPopularity += professionPopularity[1]
        print(professionPopularity[0] + ': ' + str(professionPopularity[1]) + '%')
    print("Total Popularity: " + str(totalPopularity) + '%')

if __name__ == '__main__':
    main()
