import itertools
import json
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

def vmul(xs, c):
    return tuple(x * c for x in xs)


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

def find_first_price(gray, tab, price_pos):
    return find_first_price_with_template(gray, tab, price_pos, 'coin-copper.png')

def find_first_price_with_template(gray, tab, price_pos, template_name):
    template = asset(template_name)
    x1 = 75 - (17 if tab == 'buy' else 0)
    x0 = x1 - template.shape[1]
    y0 = 20
    y1 = y0 + ROW_HEIGHT + template.shape[0] + 0
    px, py = price_pos
    region = gray[py + y0 : py + y1, px + x0 : px + x1]
    base = vadd(price_pos, (x0, y0))
    found((px + x0, py + y0), (1, 1))
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

NAME_OFFSET0 = (-570, -3)
NAME_OFFSET1 = (-152, 10)
NAME_HEIGHT = NAME_OFFSET1[1] - NAME_OFFSET0[1]
# Offset of the start of the price column on the buy tab, relative to its
# position on the sell and transaction tabs
BUY_PRICE_OFFSET_X = 63 + 17

def extract_name(image, tab, coin_pos):
    x0, y0 = vadd(coin_pos, NAME_OFFSET0)
    x1, y1 = vadd(coin_pos, NAME_OFFSET1)

    if tab == 'buy':
        # On the buy tab, the presence of the Favorite column shifts the price
        # column to the left and reduces the width available for the name.
        x0 += BUY_PRICE_OFFSET_X

    found((x0, y0), (x1 - x0, y1 - y0))
    return (image[y0:y1, x0:x1], (x0, y0))

def trim_name(image):
    assert len(image.shape) == 2
    col_max = np.max(image, axis = 0)
    col_min = np.min(image, axis = 0)
    col_range = col_max - col_min
    window_range = np.max(np.lib.stride_tricks.sliding_window_view(
        col_range, window_shape = 7), axis = 1)
    width = np.argmax(window_range < 30)
    sy, sx = image.shape
    return image[:, 0:width]


def get_mtime(path):
    if not os.path.exists(path):
        return None
    return os.stat(path).st_mtime

INPUT_PATH = 'input.txt'
_LAST_INPUT_MTIME = get_mtime(INPUT_PATH)
_LAST_INPUT_STAT = time.time()

def input_changed():
    global _LAST_INPUT_MTIME, _LAST_INPUT_STAT
    now = time.time()
    if now < _LAST_INPUT_STAT + 1:
        return False
    mtime = get_mtime(INPUT_PATH)
    if mtime != _LAST_INPUT_MTIME:
        _LAST_INPUT_MTIME = mtime
        _LAST_INPUT_STAT = now
        return True
    return False


class NameCache:
    def __init__(self, path):
        os.makedirs(path, exist_ok = True)
        self.path = path
        # Cache contents.  Map from image width to a pair of (image data,
        # name list).  To add an entry, we look up the image and names for its
        # width, add a new row (consisting of the image data flattened out to
        # 1px high) to the image, and add the name to the name list.  To do a
        # lookup, we find the matching row and return the corresponding name.
        self.dct = {}
        # We store the first unknown image we see each frame.  The user can
        # input a translation to add an entry to the cache.
        self.unknown_image = None

    def _load(self, width):
        img_path = os.path.join(self.path, '%d.bin' % width)
        names_path = os.path.join(self.path, '%d.json' % width)
        if not os.path.exists(img_path) or not os.path.exists(names_path):
            names = []
            img = np.ndarray((0, width * NAME_HEIGHT), dtype = 'uint8')
        else:
            names = json.load(open(names_path))
            count = len(names)
            img = np.ndarray((count, width * NAME_HEIGHT), dtype = 'uint8',
                    buffer = open(img_path, 'rb').read())
        self.dct[width] = (img, names)
        return (img, names)

    def _save(self, width):
        (img, names) = self.dct[width]
        img_path = os.path.join(self.path, '%d.bin' % width)
        names_path = os.path.join(self.path, '%d.json' % width)
        count = len(names)
        with open(img_path, 'wb') as f:
            f.write(bytes(img.reshape(count * width * NAME_HEIGHT)))
        with open(names_path, 'w') as f:
            json.dump(names, f)

    def _get_info(self, width):
        info = self.dct.get(width)
        if info is not None:
            return info
        info = self._load(width)
        if info is not None:
            self.dct[width] = info
        return info

    def lookup(self, text_image):
        sy, sx = text_image.shape
        width = sx
        n = sy * sx
        row = text_image.reshape((1, n))

        img, names = self._get_info(width)

        if len(names) == 0:
            index = None
            strength = 0
        else:
            res = cv2.matchTemplate(img, row, cv2.TM_CCOEFF_NORMED)
            index = np.argmax(res)
            strength = res[index, 0]

        if strength < 0.95:
            if self.unknown_image is None:
                self.unknown_image = text_image
            return None

        return names[index]

    def insert(self, text_image, text):
        sy, sx = text_image.shape
        width = sx
        n = sy * sx
        row = text_image.reshape((1, n))

        img, names = self._get_info(width)
        img = np.append(img, row, axis = 0)
        names.append(text)
        self.dct[width] = (img, names)
        self._save(width)

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

NAME_CACHE = NameCache('storage/cv_tp_name_cache')

def process(img):
    global _FOUND, _TEXT
    h, w, depth = img.shape
    _FOUND = []
    _TEXT = []
    NAME_CACHE.unknown_image = None

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
            first_price_pos = find_first_price(gray, tab, price_header_pos)
            print(first_price_pos)
            if first_price_pos is not None:
                prices = []
                for row in range(10):
                    coin_pos = (first_price_pos[0], first_price_pos[1] + row * ROW_HEIGHT)
                    if not check_template(gray, coin_pos, 'coin-copper.png', threshold = 0.95):
                        continue
                    price = read_price(gray, coin_pos)
                    prices.append(price)

                    (name_img, name_pos) = extract_name(gray, tab, coin_pos)
                    name_img = trim_name(name_img)
                    text = NAME_CACHE.lookup(name_img)
                    if text is not None:
                        sx, sy = asset_size('coin-copper.png')
                        show_text(vadd(name_pos, (0, sy)), text)
                    print(text, price)


        print(bltc_pos, mode, tab, price_header_pos)

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
        cv2.rectangle(thumb, (x0, y0), (x1, y1), vmul(color, 0.5), 1)

    for (pos, s) in _TEXT:
        x, y = pos
        x = round(x * ratio)
        y = round(y * ratio)
        cv2.putText(thumb, s, (x, y), cv2.FONT_HERSHEY_PLAIN, 0.6,
                (255, 0, 255), 1, cv2.LINE_AA)

    # Copy unknown_image into place, if needed
    if NAME_CACHE.unknown_image is not None:
        unk_img = NAME_CACHE.unknown_image
        sy, sx = unk_img.shape
        sx = min(sx, thumb_w)
        sy = min(sy, thumb_h)
        thumb[0:sy, 0:sx, 2] = 255 - unk_img[0:sy, 0:sx]
        thumb[0:sy, 0:sx, 1] = 0
        thumb[0:sy, 0:sx, 0] = 0

        if input_changed():
            name = open(INPUT_PATH).read().strip()
            NAME_CACHE.insert(NAME_CACHE.unknown_image, name)

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
