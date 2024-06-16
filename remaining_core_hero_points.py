import gw2.api
import urllib.parse

def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'
    print()

    char_name = 'Welps Entrancer'

    hero_points = gw2.api.fetch_with_retries('/v2/characters/%s/heropoints' %
                urllib.parse.quote(char_name))
    
    print(hero_points)


if __name__ == '__main__':
    main()
