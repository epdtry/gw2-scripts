import sys
import gw2.api
import gw2.character
import gw2.items
import bookkeeper


def main():
    with open('api_key.txt') as f:
        gw2.api.API_KEY = f.read().strip()
    gw2.api.CACHE_DIR = 'cache'

    # 1 Stabilizing Matrix = 1 Fractal Encryption Key
    # 1 Fractal Encryption + 1 Fractal Encryption Key = 1 Cracked Fractal Encryption
    # 1 Fractal Encryption + 1 Stabilizing Matrix = 1 Cracked Fractal Encryption
    # Get .1 Fractal Encryption Key per Cracked Fractal Encryption, so you need 0.9 Stabilizing Matrix for each Fractal Encryption 
    # 0.2 Fractal Relics per Cracked Fractal Encryption
    # 1 Spirit Shard = 35 Fractal Relics
    # Gen 3 legendary needs 325 Spirit Shards
    # How many Cracked Fractal Encryptions do you need to get 325 Spirit Shards?
    FRACTAL_RELICS_PER_SPIRIT_SHARD = 35
    FRACTAL_RELICS_PER_CRACKED_FRACTAL_ENCRYPTION = 0.19
    discount_per_box = 4000

    # get base costs from trading post
    stabalizing_matrix_item = gw2.items.search_name('Stabilizing Matrix')
    fractal_encryption_item = gw2.items.search_name('Fractal Encryption')
    buy_prices, sell_prices = bookkeeper.get_prices([stabalizing_matrix_item, fractal_encryption_item])
    stabalizing_matrix_cost = buy_prices[stabalizing_matrix_item]
    fractal_encryption_cost = buy_prices[fractal_encryption_item]
    print('')
    print('Stabalizing Matrix Cost: {}'.format(stabalizing_matrix_cost))
    print('Fractal Encryption Cost: {}'.format(fractal_encryption_cost))
    print('')
    
    # Calculate cost of num_cracked_fractal_encryptions cracked fractal encryptions, given each cracked gives 1 fractal encryption key
    num_cracked_fractal_encryptions = 250
    cracked_fractal_encryption_stack_cost = num_cracked_fractal_encryptions * stabalizing_matrix_cost * .9 + num_cracked_fractal_encryptions * fractal_encryption_cost
    fractal_relics_received_per_stack = num_cracked_fractal_encryptions * FRACTAL_RELICS_PER_CRACKED_FRACTAL_ENCRYPTION
    spirit_shards_received_per_stack = fractal_relics_received_per_stack / FRACTAL_RELICS_PER_SPIRIT_SHARD
    print('stack Cracked Fractal Encryption Cost: {}'.format(cracked_fractal_encryption_stack_cost))
    print('stack Cracked Fractal Encryption Fractal Relics Received: {}'.format(fractal_relics_received_per_stack))
    print('stack Cracked Fractal Encryption Spirit Shards Received: {}'.format(spirit_shards_received_per_stack))
    cost_per_spirit_shard = cracked_fractal_encryption_stack_cost / spirit_shards_received_per_stack
    cost_per_cracked_fractal_encryption = cracked_fractal_encryption_stack_cost / num_cracked_fractal_encryptions
    actual_cost_per_encryption = cost_per_cracked_fractal_encryption - discount_per_box
    print('Cost per Spirit Shard: {}'.format(cost_per_spirit_shard))
    print('Cost per Cracked Fractal Encryption: {}'.format(cost_per_cracked_fractal_encryption))
    print('Actual Cost per Cracked Fractal Encryption (after discount): {}'.format(actual_cost_per_encryption))
    print('')
    

    spirit_shards_needed_for_gen_3_legendary = 325
    fractal_relics_needed_for_gen_3_legendary = spirit_shards_needed_for_gen_3_legendary * FRACTAL_RELICS_PER_SPIRIT_SHARD
    cracked_fractal_encryption_needed_for_gen_3_legendary = int((fractal_relics_needed_for_gen_3_legendary / FRACTAL_RELICS_PER_CRACKED_FRACTAL_ENCRYPTION) + 0.5)
    cracked_fractal_encryption_cost_for_gen_3_legendary = cracked_fractal_encryption_needed_for_gen_3_legendary * actual_cost_per_encryption
    print('Cracked Fractal Encryption Needed for Gen 3 Legendary: {}'.format(cracked_fractal_encryption_needed_for_gen_3_legendary))
    print('Cracked Fractal Encryption Fractal Relics Needed for Gen 3 Legendary: {}'.format(fractal_relics_needed_for_gen_3_legendary))
    print('Cracked Fractal Encryption Cost for Gen 3 Legendary: {}'.format(bookkeeper.format_price(cracked_fractal_encryption_cost_for_gen_3_legendary)))
    print('')

if __name__ == '__main__':
    main()
