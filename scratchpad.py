import difflib

def get_similarity_ratio(string1, string2):
    matcher = difflib.SequenceMatcher(None, string1, string2)
    return matcher.ratio()

def are_strings_similar(string1, string2, similarity_threshold=0.8):
    similarity_ratio = get_similarity_ratio(string1, string2)
    return similarity_ratio >= similarity_threshold

def find_and_add_new_lines(existing_text_lines, new_text_lines):
    existing_index = 0
    new_index = 0
    found_top = False

    # iterate through existing lines until we find the first line that matches the new line
    while existing_index < len(existing_text_lines) and new_index < len(new_text_lines):
        if are_strings_similar(existing_text_lines[existing_index], new_text_lines[new_index]):
            found_top = True
            break
        else:
            existing_index += 1

    # then iterate through both lists until we find a line that doesn't match
    if found_top:
        while existing_index < len(existing_text_lines) and new_index < len(new_text_lines):
            if are_strings_similar(existing_text_lines[existing_index], new_text_lines[new_index]):
                existing_index += 1
                new_index += 1
            else:
                break
    print("existing_index: " + str(existing_index))
    print("new_index: " + str(new_index))
    print("existing_line", existing_text_lines[existing_index])
    print("new_line", new_text_lines[new_index])
    
    # then add the rest of the new lines to the existing list
    while new_index < len(new_text_lines):
        existing_text_lines.append(new_text_lines[new_index])
        new_index += 1

    return existing_text_lines

def find_and_add_new_lines_2(existing_text_lines, new_text_lines):
    # loop backward through the new_text_lines until we find a line that matches the last line of the existing_text_lines
    existing_last_index = len(existing_text_lines) - 1
    new_index = len(new_text_lines) - 1
    found_bottom = False

    lines_to_add = []
    while new_index >= 0 and not found_bottom:
        if existing_last_index > 0 and are_strings_similar(existing_text_lines[existing_last_index], new_text_lines[new_index]):
            # check if the previous line of existing_text_lines is similar to the previous line of new_text_lines
            if existing_last_index - 1 > 0 and new_index - 1 > 0 and are_strings_similar(existing_text_lines[existing_last_index-1], new_text_lines[new_index-1]):
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


# main function
if __name__ == '__main__':
    firstlinefilepath = 'firstline.txt'
    secondlinefilepath = 'secondline.txt'

    firstLine_text = open(firstlinefilepath, 'r').read()
    secondLine_text = open(secondlinefilepath, 'r').read()

    lines = firstLine_text.splitlines()
    newlines = secondLine_text.splitlines()

    added_lines = find_and_add_new_lines_2(lines, newlines)
    
    for line in lines:
        print(line)

    # s1 = '| Commander Welps Mudlark: &&&&& START XYZ &&&&&'
    # s2 = 'Commander Welps Mudlark: &&&&& START XYZ &&&6&'
    # print(get_similarity_ratio(s1, s2))