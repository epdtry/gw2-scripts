import itertools
import os
import numpy as np
import cv2
import time

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

_FOUND = None
def found(pos, size):
    if _FOUND is not None:
        if hasattr(size, 'shape'):
            shape = size.shape
            size = (shape[1], shape[0])
        _FOUND.append((pos, size))

def find_template(gray_img, template_name, threshold = 0.85):
    template = asset(template_name, gray=True)
    res = cv2.matchTemplate(gray_img, template, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(res >= threshold)
    assert len(xs) == len(ys) and len(xs) <= 1, 'weird np.where result: %r, %r' % (xs, ys)
    if len(xs) == 0:
        return None
    elif len(xs) == 1:
        pos = (xs[0], ys[0])
        found(pos, template)
        return pos
    else:
        assert False, 'unreachable'

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
    global _FOUND
    h, w, depth = img.shape
    _FOUND = []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Check if trading post is open
    bltc_pos = find_bltc(gray)

    if bltc_pos is not None:
        mode = detect_bltc_mode(gray, bltc_pos)

        if mode == 'tp':
            tab = detect_tp_tab(gray, bltc_pos)
        else:
            tab = None
        print(bltc_pos, mode, tab)

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
        pass

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
