import os
import functools

class Node:
    def __init__(self, p):
        self.path_ = p                # internal结点的文件夹名；跟结点是""
        self.internal_children_ = {}  # (internal)子结点列表（子结点的path_:子结点）
        self.pages_ = []              # 挂载的叶子结点列表

    # 跟结点入参例如:
    # @ p     ("a/b/c").split("/")
    # @ idx   0
    # @ pages ["[1](path_to_1.md)", "[2](path_to_2.md)"] 目录p下的所有文件
    def add_pages(self, s_p, idx, pages):
        # s_p = [""] 时 会挂载在root结点上
        if len(s_p) == 1 and s_p[0] == "":
            # print("add pages: ", pages, self.path_)
            self.pages_ = pages
            return

        if len(s_p) == idx: # 已经到最后了
            # print("add pages: ", pages, self.path_)
            self.pages_ = pages
            return
        
        if not s_p[idx] in self.internal_children_.keys():
            self.internal_children_[s_p[idx]] = Node(s_p[idx])
            # print("add node: ", s_p[idx], self.internal_children_[s_p[idx]]);
        self.internal_children_[s_p[idx]].add_pages(s_p, idx+1, pages)

sidebars_tree = Node("")
def output_sidebars(scan_dir, path, sidebars):
    global sidebars_tree
    relative_path = path[len(scan_dir)+len('/pages/'):]
    sidebars_tree.add_pages(relative_path.split("/"), 0, sidebars)

def DFS(node, level, fw):
    # print(node, node.path_, node.internal_children_)
    if node.path_ != "":
        fw.write("{}* {}\n".format("  "*(level-1), node.path_.replace("-", " ")))

    for page in node.pages_:
        fw.write("{}* {}\n".format("  "*level, page))

    for child in node.internal_children_.values():
        DFS(child, level+1, fw)

def output_to_file():
    global sidebars_tree
    with open("./_sidebar.gen.md", "w") as fw:
        # DFS打印
        DFS(sidebars_tree, 0, fw)

def cmpvalue(v1, v2):
    if v1 == v2:
        return 0
    if v1 < v2:
        return -1
    return 1

def cmp(f1, f2):
    p1 = f1.find(".")
    p2 = f2.find(".")
    # print("cmp {} ? {}, p1:{}, p2:{}".format(f1, f2, p1, p2))

    if p1 == p2 and p1 == -1:
        # 都没找到 按字符比较
        return cmpvalue(f1, f2)

    is_p1_num = False
    if p1 != -1:
        is_p1_num = f1[1:p1].isdigit()
    is_p2_num = False
    if p2 != -1:
        is_p2_num = f2[1:p2].isdigit()

    if is_p1_num and is_p2_num:
        # 都找到了 按数字比较
        return cmpvalue(int(f1[1:p1]), int(f2[1:p2]))
    elif is_p1_num:
        return 1
    elif is_p2_num:
        return -1

    return cmpvalue(f1, f2)

def get_filelist(scan_dir):
    for home, dirs, files in os.walk(scan_dir):
        # print("#### dir list ####")
        # for dir in dirs:
            # print(dir)
        # print("#### dir list ####")

        ignore_files = set(("_sidebar.md", "_footer.md", "_sidebar.gen.md", "template.md", "README.md"))
        ignore_dirs = set(("Linear-Algebra", ""))

        sidebars = []
        for filename in files:

            if not filename.endswith(".md"):
                continue

            if filename in ignore_files:
                continue

            if home.split("/")[-1] in ignore_dirs:
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
        output_sidebars(scan_dir, home, sidebars)

if __name__ == "__main__":
    get_filelist(os.getenv('WORKSPACE'))
    output_to_file();
    
