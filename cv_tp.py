import itertools
import os
import numpy as np
import cv2
import time


def vadd(xs, ys):
    assert len(xs) == len(ys)
    return tuple(x + y for x, y in zip(xs, ys))

def vsub(xs, ys):
    assert len(xs) == len(ys)
    return tuple(x - y for x, y in zip(xs, ys))


BASE_DIR = os.path.dirname(__file__)

_ASSETS = {}
def asset(name, gray=False):
    key = (name, gray)
    x = _ASSETS.get(key)
    if x is not None:
        return x

    if gray:
        orig = asset(name, gray=False)
        img = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    else:
        img = cv2.imread(os.path.join(BASE_DIR, 'cv_assets', name))
    _ASSETS[key] = img
    return img

def asset_size(name):
    shape = asset(name).shape
    return shape[1], shape[0]


_FOUND = None
def found(pos, size):
    if _FOUND is not None:
        if hasattr(size, 'shape'):
            shape = size.shape
            size = (shape[1], shape[0])
        _FOUND.append((pos, size))

_TEXT = None
def show_text(pos, s):
    if _TEXT is not None:
        _TEXT.append((pos, s))


def find_template(gray_img, template_name, threshold = 0.85, multi = False,
        best_match = False, base = None):
    template = asset(template_name, gray=True)
    res = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)

    if best_match:
        index = np.argmax(res)
        y, x = np.unravel_index(index, res.shape)
        if res[y, x] < threshold:
            return None
        pos = (x, y)
        if base is None:
            found(pos, template)
        else:
            found(vadd(pos, base), template)
        return pos

    ys, xs = np.where(res >= threshold)
    assert len(xs) == len(ys), 'weird np.where result: %r, %r' % (xs, ys)
    if multi:
        ps = list(zip(xs, ys))
        for p in ps:
            if base is None:
                found(p, template)
            else:
                found(vadd(p, base), template)
        return ps
    else:
        if len(xs) == 0:
            return None
        elif len(xs) == 1:
            pos = (xs[0], ys[0])
            if base is None:
                found(pos, template)
            else:
                found(vadd(pos, base), template)
            return pos
        else:
            raise ValueError('got %d positions, but expected at most 1' % len(xs))

def check_template(gray_img, pos, template_name, threshold = 0.85):
    '''Compare the portion of `gray_img` at `pos` to the template image loaded
    from `template_name`.  Returns `true` if the similarity measure is at least
    `threshold` and false otherwise'''
    x, y = pos
    template = asset(template_name, gray=True)
    sy, sx = template.shape
    region = gray_img[y : y + sy, x : x + sx]
    res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
    matches = res[0][0] >= threshold
    if matches:
        found(pos, (sx, sy))
    return matches

def best_template(gray_img, templates, threshold = 0.85, record_found = True):
    '''Given several `(template_name, pos)` pairs, check each template against
    the region of `gray_img` at `pos`, and return the index of the strongest
    match.  If no match had a strength exceeding `threshold`, this function
    returns `None`.
    '''
    best_index = None
    best_strength = 0
    for index, (template_name, (x, y)) in enumerate(templates):
        template = asset(template_name, gray=True)
        sy, sx = template.shape
        region = gray_img[y : y + sy, x : x + sx]
        res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        strength = res[0,0]
        if strength > best_strength:
            best_strength = strength
            best_index = index

    if best_strength < threshold:
        return None

    if record_found:
        name, pos = templates[best_index]
        found(pos, asset(name))

    return best_index


def detect_bltc_mode(gray, win_pos):
    win_x, win_y = win_pos
    mode_x = win_x + 420
    mode_y = win_y + 6
    mode_pos = (mode_x, mode_y)

    gemstore = check_template(gray, mode_pos, 'bltc-header-gemstore.png')
    currency = check_template(gray, mode_pos, 'bltc-header-currency.png')
    tp = check_template(gray, mode_pos, 'bltc-header-tp.png')

    if sum((gemstore, currency, tp)) != 1:
        return None
    elif gemstore:
        return 'gemstore'
    elif currency:
        return 'currency'
    elif tp:
        return 'tp'

def detect_tp_tab(gray, win_pos):
    win_x, win_y = win_pos
    tab_x = win_x + 315
    tab_y = win_y + 107
    tab_pos = (tab_x, tab_y)

    home = check_template(gray, tab_pos, 'tp-tab-home.png')
    buy = check_template(gray, tab_pos, 'tp-tab-buy.png')
    sell = check_template(gray, tab_pos, 'tp-tab-sell.png')
    transactions = check_template(gray, tab_pos, 'tp-tab-transactions.png')

    if sum((home, buy, sell, transactions)) != 1:
        return None
    elif home:
        return 'home'
    elif buy:
        return 'buy'
    elif sell:
        return 'sell'
    elif transactions:
        return 'transactions'

_LAST_BLTC_POS = None
def find_bltc(gray):
    global _LAST_BLTC_POS
    # Fast path: check if the window is in the same place it was previously
    if _LAST_BLTC_POS is not None:
        if check_template(gray, _LAST_BLTC_POS, 'bltc-header.png'):
            return _LAST_BLTC_POS
    bltc_pos = find_template(gray, 'bltc-header.png')
    _LAST_BLTC_POS = bltc_pos
    return bltc_pos

PRICE_OFFSETS_BUY = [(830, 186), (830, 150), (830, 222)]
PRICE_OFFSETS_SELL = [(893, 150), (893, 186)]

def find_price_header(gray, tab, win_pos):
    if tab == 'buy':
        offsets = PRICE_OFFSETS_BUY
    elif tab == 'sell':
        offsets = PRICE_OFFSETS_SELL
    else:
        return None

    for off in offsets:
        pos = vadd(win_pos, off)
        if check_template(gray, pos, 'tp-price.png'):
            return pos
    return None

# Height of the rows in the buy/sell tabs
ROW_HEIGHT = 61

def find_first_price(gray, price_pos):
    return find_first_price_with_template(gray, price_pos, 'coin-copper.png')

def find_first_price_with_template(gray, price_pos, template_name):
    template = asset(template_name)
    x1 = 75
    x0 = x1 - template.shape[1]
    y0 = 20
    y1 = y0 + ROW_HEIGHT + template.shape[0] + 0
    px, py = price_pos
    region = gray[py + y0 : py + y1, px + x0 : px + x1]
    base = vadd(price_pos, (x0, y0))
    pos = find_template(region, template_name, best_match = True, base = base)
    if pos is None:
        return None
    return vadd(base, pos)

COIN_TIERS = [
        'coin-copper.png',
        'coin-silver.png',
        'coin-gold.png',
        ]

DIGIT_WIDTH = 8
# Offset of digit templates above the top of the coin template.
DIGIT_Y_OFFSET = 2

def read_price(gray, coin_pos):
    '''Given the position of the last coin icon, extract the full price.
    Returns the total price in copper.'''
    if coin_pos is None:
        return None
    price = 0
    next_tier = 1
    tier_mult = 1
    digit_mult = 1
    x, y = coin_pos
    digits = []
    value = 0
    while True:
        candidates = [('digit-%d.png' % i, (x - DIGIT_WIDTH, y - DIGIT_Y_OFFSET))
                for i in range(10)]
        if next_tier < len(COIN_TIERS):
            coin = COIN_TIERS[next_tier]
            coin_sx, coin_sy = asset_size(coin)
            candidates.append((coin, (x - coin_sx, y)))

        index = best_template(gray, candidates, record_found = False)
        if index is None:
            break

        if index < 10:
            digits.append(index)
            x -= DIGIT_WIDTH
            value += index * digit_mult
            digit_mult *= 10
        else:
            digits.append(None)
            x -= coin_sx
            next_tier += 1
            tier_mult *= 100
            digit_mult = tier_mult

    sx, sy = asset_size('coin-copper.png')
    found((x, y), (coin_pos[0] + sx - x, sy))
    show_text(vadd(coin_pos, (10 + sx, sy)), str(value))

    return value


FOUND_COLORS = [
        (0, 0, 255),
        (0, 128, 255),
        (0, 255, 255),
        (0, 255, 0),
        (255, 128, 0),
        (255, 0, 0),
        (255, 0, 128),
        (255, 0, 255),
        ]

def process(img):
    global _FOUND, _TEXT
    h, w, depth = img.shape
    _FOUND = []
    _TEXT = []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Check if trading post is open
    bltc_pos = find_bltc(gray)

    if bltc_pos is not None:
        mode = detect_bltc_mode(gray, bltc_pos)

        tab = None
        if mode == 'tp':
            tab = detect_tp_tab(gray, bltc_pos)

        price_header_pos = None
        if tab in ('buy', 'sell'):
            price_header_pos = find_price_header(gray, tab, bltc_pos)

        if price_header_pos is not None:
            first_price_pos = find_first_price(gray, price_header_pos)
            if first_price_pos is not None:
                prices = []
                for row in range(10):
                    coin_pos = (first_price_pos[0], first_price_pos[1] + row * ROW_HEIGHT)
                    if not check_template(gray, coin_pos, 'coin-copper.png', threshold = 0.95):
                        break
                    price = read_price(gray, coin_pos)
                    prices.append(price)
                print('prices', prices)


        #print(bltc_pos, mode, tab)

    thumb_w = 300
    ratio = thumb_w / w
    thumb_h = round(h * ratio)
    thumb = cv2.resize(gray, (thumb_w, thumb_h), cv2.INTER_LINEAR)
    thumb = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)

    for ((x, y), (sx, sy)), color in zip(_FOUND, itertools.cycle(FOUND_COLORS)):
        x0 = round(x * ratio)
        y0 = round(y * ratio)
        x1 = round((x + sx) * ratio)
        y1 = round((y + sy) * ratio)
        cv2.rectangle(thumb, (x0, y0), (x1, y1), color, 1)

    for (pos, s) in _TEXT:
        x, y = pos
        x = round(x * ratio)
        y = round(y * ratio)
        print('put %s at %d,%d' % (s, x, y))
        cv2.putText(thumb, s, (x, y), cv2.FONT_HERSHEY_PLAIN, 0.6, (255, 0, 255))

    return thumb

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    cv2.namedWindow('frame', flags=cv2.WINDOW_GUI_NORMAL)
    cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        # if frame is read correctly ret is True
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break

        display = process(frame)

        cv2.imshow('frame', display)
        cv2.moveWindow('frame', 1920 - 300, 0)
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite(time.strftime('out-%Y%m%d-%H%M%S.png'), frame)
    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
