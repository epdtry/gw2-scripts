import gw2.api
import gw2.character


def main():
    discipline_levels = gw2.character.get_max_of_each_discipline()
    print(discipline_levels)

if __name__ == '__main__':
    main()