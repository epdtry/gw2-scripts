import cv2
import numpy as np
import os
from PIL import Image
import pytesseract
import sys
import difflib
from skimage.metrics import structural_similarity as compare_ssim

# global variables
IMAGES_PATH = "images\\"
OUTPUT_PATH = "temp_image\\"

CHATBOX_UPPERRIGHT_ICON_PATH = "images\\ChatBoxUpperRightIcon.png"
CHATBOX_BOTTOMLEFT_ICON_PATH = "images\\ChatBoxBottomLeftIcon.png"
CHATBOX_LINE_DELIMETER_PATH = "images\\ChatBoxLineDelimeter.png"

FRAME_PROCESS_RATE = 10 # process every FRAME_PROCESS_RATEth frame

# function that takes a file path and returns a video capture object
def get_video_capture(video_file_path):
    # Check if file exists
    if not os.path.isfile(video_file_path):
        print("File does not exist")
        sys.exit()

    # Extract screenshot
    vidcap = cv2.VideoCapture(video_file_path)
    return vidcap

# function that takes a video capture object and returns the total number of frames
def count_frames(vidcap):
    total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    return total_frames

# function that takes a video capture object and returns the frames per second
def count_frames_per_second(vidcap):
    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    return fps

def extract_next_Nth_frame(vidcap, N):
    last_image = None
    for i in range(N):
        success, image = vidcap.read()
        if success:
            last_image = image
        else:
            print('Nonsuccess extracting frames')
            # write image to disk
            #cv2.imwrite("temp_image\\lastImage.png", last_image)
            return None
    return last_image

def locate_top_right_of_chatbox_icon(image):
    # read in chatbox icon
    chatbox_icon = cv2.imread(CHATBOX_UPPERRIGHT_ICON_PATH)
    w, h = chatbox_icon.shape[:-1]

    # convert images to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_chatbox_icon = cv2.cvtColor(chatbox_icon, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(gray_image, gray_chatbox_icon, cv2.TM_CCOEFF_NORMED)
    threshold = 0.85
    loc = np.where(res >= threshold)
    ADJUST_Y = 4 # adjust for the fact that the chatbox icon is not perfectly aligned with the chatbox
    top_right_pt = (loc[1][0], loc[0][0] + h + ADJUST_Y)
    return top_right_pt

def locate_bottom_left_of_chatbox(image):
    # read in chatbox icon
    chatbox_icon = cv2.imread(CHATBOX_BOTTOMLEFT_ICON_PATH)
    w, h = chatbox_icon.shape[:-1]

    # convert images to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_chatbox_icon = cv2.cvtColor(chatbox_icon, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(gray_image, gray_chatbox_icon, cv2.TM_CCOEFF_NORMED)
    threshold = 0.85
    loc = np.where(res >= threshold)
    ADJUST_X = -10 # adjust for the fact that the chatbox icon is not perfectly aligned with the chatbox
    bottom_left_pt = (loc[1][0] + w + ADJUST_X, loc[0][0])
    return bottom_left_pt

# function that takes an opencv image and crops it
def crop_image(image, start_x, start_y, end_x, end_y):
    # crop image
    crop_img = image[start_y:end_y, start_x:end_x]
    # cv2.imwrite("temp_image\\croppedImage.png", crop_img)
    return crop_img

# function that takes an opencv image and uses pytesseract to extract text
def extract_text(image):
    # extract text from image
    imageObject = Image.fromarray(image)
    text = pytesseract.image_to_string(imageObject, lang='eng', config='--psm 7')
    return text

def image_similarity(image1, image2):
    if image1 is None or image2 is None:
        return 0
    if image1.shape != image2.shape:
        return 0

    # convert images to grayscale
    gray_image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray_image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

    # compare the images
    (score, diff) = compare_ssim(gray_image1, gray_image2, full=True)
    return score

def are_images_similar(image1, image2, similarity_threshold=0.985):
    if image1 is None or image2 is None:
        return False
    similarity = image_similarity(image1, image2)
    return similarity >= similarity_threshold

def are_strings_similar(string1, string2, similarity_threshold=0.8):
    matcher = difflib.SequenceMatcher(None, string1, string2)
    similarity_ratio = matcher.ratio()
    return similarity_ratio >= similarity_threshold

def extract_chatbox_from_image(image):
    cropped_image = None
    try:
        top_right_chatbox_pt = locate_top_right_of_chatbox_icon(image)
        bottom_left_chatbox_pt = locate_bottom_left_of_chatbox(image)
        middle_y = int((top_right_chatbox_pt[1] + bottom_left_chatbox_pt[1]) / 2)
        cropped_image = crop_image(image, bottom_left_chatbox_pt[0], middle_y, top_right_chatbox_pt[0], bottom_left_chatbox_pt[1])
        # cropped_image = crop_image(image, bottom_left_chatbox_pt[0], top_right_chatbox_pt[1], top_right_chatbox_pt[0], bottom_left_chatbox_pt[1])
    except:
        print('Error extracting chatbox from image, skipping frame')
        pass
    return cropped_image

def extract_text_lines_from_chatbox_image(image):
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
        cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((1, 1), np.uint8)
        cropped_image = cv2.dilate(cropped_image, kernel, iterations=1)
        cropped_image = cv2.erode(cropped_image, kernel, iterations=1)
        text = extract_text(cropped_image)
        text = text.replace("\n", "")
        # if text == '':
        #     # try to extract with grayscale
        #     cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
        #     text = extract_text(cropped_image)
        #     text = text.replace("\n", "")
        if text != '':
            text_lines.append(text)
        # cv2.line(image, (start_x, start_y), (end_x, start_y), (0, 0, 255), 1)

    # write the image to disk
    # cv2.imwrite("temp_image\\lineDelimeters2.png", image)

    return text_lines

def do_previous_N_lines_match(existing_text_lines, new_text_lines, current_new_text_lines_index, N):
    existing_last_index = len(existing_text_lines) - 1
    new_index = current_new_text_lines_index
    print("current matching strings: ", existing_text_lines[existing_last_index], new_text_lines[new_index])

    # check if the ending N lines of existing_text_lines are similar to the previous N lines of 
    # new_text_lines starting from current_new_text_lines_index
    for i in range(1, N+1):
        if existing_last_index - i < 0:
            print("THIS SHOULD ONLY HAPPEN ONCE")
            return True
            
        if new_index - i < 0:
            return True
        
        print('Comparing these strings: ', existing_text_lines[existing_last_index-i], new_text_lines[new_index-i])

        if not are_strings_similar(existing_text_lines[existing_last_index-i], new_text_lines[new_index-i]):
            print('previous N lines do not match')
            return False
    print('All lines matched!')
    return True

def find_and_add_new_lines(existing_text_lines, new_text_lines):
    # loop backward through the new_text_lines until we find a line that matches the last line of the existing_text_lines
    existing_last_index = len(existing_text_lines) - 1
    new_index = len(new_text_lines) - 1
    found_bottom = False

    lines_to_add = []
    while new_index >= 0 and not found_bottom:
        if existing_last_index > 0 and are_strings_similar(existing_text_lines[existing_last_index], new_text_lines[new_index]):
            # check if the previous ending lines of existing_text_lines are similar to the previous lines of new_text_lines
            if do_previous_N_lines_match(existing_text_lines, new_text_lines, new_index, 3):
                # the current line and the previous line are similar, so we can stop
                found_bottom = True
            else:
                # the current line is similar, but the previous line is not, so we need to add the current line
                lines_to_add.append(new_text_lines[new_index])
                new_index -= 1
        else:
            lines_to_add.append(new_text_lines[new_index])
            new_index -= 1

    # reverse the list of lines to add
    lines_to_add.reverse()

    # append the lines to add to the existing text lines
    for line in lines_to_add:
        existing_text_lines.append(line)
    
    return existing_text_lines

def extract_text_from_video(video_file_path):
    video_cap = get_video_capture(video_file_path)
    total_frames = count_frames(video_cap)
    fps = count_frames_per_second(video_cap)
    print('Total frames: ' + str(total_frames))
    print('Frames per second: ' + str(fps))
    print('Frame process rate: ' + str(FRAME_PROCESS_RATE))

    previous_cropped_image = None
    processed_frames = 0

    # a list to store the text extracted from each frame
    video_chat_text = []
    report_interval_percentage = 0

    # skip 500 frames
    # for i in range(500):
    #     video_cap.read()
    #     processed_frames += 1

    for i in range(total_frames):
        report_interval_percentage = int(processed_frames / total_frames * 100)
        print('Processed ' + str(report_interval_percentage) + '% of frames')
        processed_frames += FRAME_PROCESS_RATE
            
        image = None
        try:
            image = extract_next_Nth_frame(video_cap, FRAME_PROCESS_RATE)
        except:
            pass
        if image is None:
            print('Finished extracting frames')
            break
        height, width, channels = image.shape

        chatbox_image = extract_chatbox_from_image(image)
        if chatbox_image is None:
            continue
        if previous_cropped_image is not None and are_images_similar(chatbox_image, previous_cropped_image):
                continue
        else:
            previous_cropped_image = chatbox_image
        # chatbox_file_name = OUTPUT_PATH + 'cropped_chatbox' + str(i) + '.png'
        # cv2.imwrite(chatbox_file_name, chatbox_image)

        lines = extract_text_lines_from_chatbox_image(chatbox_image)

        # for line in lines:
        #     print(line)
        # print('-----------------', ' num lines: ', len(lines))
        
        find_and_add_new_lines(video_chat_text, lines)
    
    return video_chat_text


if __name__ == '__main__':
    # mkv_file = 'C:\\Users\\jake\\Videos\\2023-04-28 22-21-27.mkv'
    mkv_file = 'C:\\Users\\jake\\Videos\\2023-04-28 22-20-43.mkv'
    flv_file = 'C:\\Users\\jake\\Videos\\STU 2023-05-13_19-48-44.flv'
    
    #video_chat_text = extract_text_from_video(mkv_file)
    video_chat_text = extract_text_from_video(flv_file)
    
    # prints the list of text extracted from each frame
    print('-----------------**************')
    for line in video_chat_text:
        print(line)