import cv2
import numpy as np
import os
from PIL import Image
import pytesseract
import sys
import difflib

CHATBOX_LINE_DELIMETER_PATH = "images\\ChatBoxLineDelimeter.png"

# function that takes an opencv image and crops it
def crop_image(image, start_x, start_y, end_x, end_y):
    # crop image
    crop_img = image[start_y:end_y, start_x:end_x]

    cv2.imwrite("temp_image\\croppedImageTest.png", crop_img)
    return crop_img

# function that takes an opencv image and uses pytesseract to extract text
def extract_text(image):
    # extract text from image
    text = pytesseract.image_to_string(image, lang='eng')
    return text

def extract_text_lines_from_chat_image(image):
    # read in line delimeter image
    line_delimeter_image = cv2.imread(CHATBOX_LINE_DELIMETER_PATH)
    w, h = line_delimeter_image.shape[:-1]

    # convert images to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_line_delimeter = cv2.cvtColor(line_delimeter_image, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(gray_image, gray_line_delimeter, cv2.TM_CCOEFF_NORMED)
    threshold = 0.85
    loc = np.where(res >= threshold)

    # find the most occuring height between the tops of the line delimeters
    height_dict = []
    for i in range(0, len(loc[0])-1):
        top_of_loc = loc[0][i] - h
        top_of_next_loc = loc[0][i+1] - h
        height_diff = top_of_next_loc - top_of_loc
        height_dict.append(height_diff)
    # find the mode height
    line_height = max(set(height_dict), key=height_dict.count)

    # find the top most point the delimeters
    TWEAK_Y = 2 # tweak for the fact that the line delimeter is not perfectly aligned with the chatbox
    top_most_point = (loc[1][0], loc[0][0] - TWEAK_Y)
    bottom_most_point = (loc[1][0] + w, loc[0][len(loc[0]) - 1])
    height_diff = bottom_most_point[1] - top_most_point[1]
    num_of_lines = int(height_diff / line_height)+1

    # draw vertical lines across the whole width of the image starting from the top most point
    text_lines = []
    for i in range(0, num_of_lines):
        start_x = 0
        start_y = top_most_point[1] + (i * line_height)
        end_x = image.shape[1] + line_height
        end_y = top_most_point[1] + (i * line_height) + line_height
        cropped_image = crop_image(image, start_x, start_y, end_x, end_y)
        text = extract_text(cropped_image)
        text = text.replace("\n", "")
        text_lines.append(text)
        # cv2.line(image, (start_x, start_y), (end_x, start_y), (0, 0, 255), 1)

    # write the image to disk
    # cv2.imwrite("temp_image\\lineDelimeters2.png", image)

    return text_lines

TEST_IMAGE_PATH = "temp_image\\testCroppedImage.png"

if not os.path.isfile(TEST_IMAGE_PATH):
    print("Error: test image does not exist")
    sys.exit()

image = cv2.imread(TEST_IMAGE_PATH)

text_lines = extract_text_lines_from_chat_image(image)

# print text_lines
for line in text_lines:
    print(line)