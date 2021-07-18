import os
import functools

path_to_sidebars = {"": []}

def output_sidebars(path, sidebars):
    global path_to_sidebars
    short_path = ""
    if len(path) > 39:
        short_path = path[39:]

    formated_sbs = ""
    for sidebar in sidebars:
        cnt = sidebar.count("/") - 1
        formated_sbs = formated_sbs + "{}* {}\n".format("  "*cnt, sidebar)

    if short_path in path_to_sidebars:
        path_to_sidebars[short_path].append(formated_sbs)
    else:
        path_to_sidebars[short_path] = [formated_sbs]

output = ""
def output_to_file():
    global path_to_sidebars
    global output
    with open("./_sidebar.gen.md", "w") as fw:
        for item in path_to_sidebars:
            if len(item) != 0:
                fw.write("* {}\n".format(item))
            for sidebar in path_to_sidebars[item]:
                fw.write(sidebar)

def cmpvalue(v1, v2):
    if v1 == v2:
        return 0
    if v1 < v2:
        return -1
    return 1

def cmp(f1, f2):
    p1 = f1[:-4].rfind(".")
    p2 = f2[:-4].rfind(".")
    # print("cmp {} ? {}, p1:{}, p2:{}".format(f1, f2, p1, p2))

    if p1 == p2 and p1 == -1:
        return cmpvalue(f1, f2)
    elif p1 == p2 and p1 != -1:
        return cmpvalue(f1[1:p1], f2[1:p2])
    elif p1 != p2 and p1 == -1:
        return -1
    elif p1 != p2 and p2 == -1:
        return 1
    else:
        return cmpvalue(int(f1[1:p1]), int(f2[1:p2]))

def get_filelist(scan_dir):
    for home, dirs, files in os.walk(scan_dir):
        # print("#### dir list ####")
        # for dir in dirs:
            # print(dir)
        # print("#### dir list ####")

        ignore_files = set(("_sidebar.md", "_footer.md", "_sidebar.gen.md", "template.md"))

        sidebars = []
        for filename in files:
            if not filename.endswith(".md"):
                continue
            if filename in ignore_files:
                continue
            fullname = os.path.join(home, filename)
            f = open(fullname, mode='r')
            file_title = f.readline()[1:].strip()
            sidebar = "[{}]({})".format(file_title, fullname[len(scan_dir):])
            if len(file_title) != 0:
                sidebars.append(sidebar)
        sidebars = sorted(sidebars, key=functools.cmp_to_key(cmp))

        if len(sidebars) == 0:
            continue
        # print("sidebars: ", sidebars)
        output_sidebars(home, sidebars)

if __name__ == "__main__":
    get_filelist("/home/ubuntu/work/engineers_cool/")
    output_to_file();
