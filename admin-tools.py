#  This file is for ADMIN AND DEVELOPERS ONLY!
#  It is heavily unrecomended to use any of this functions
# in telegram directly.
#  You can view help with `python admin-tools.py -h`

import argparse
import sqlite3
import json
import math
import sys

argaction = ["add-class", "interactive", "i"]

# Adding parsers for console usage
parser = argparse.ArgumentParser(prog="admin-tools")
parser.add_argument('-a', '--all-options', action="store_true",
                    help="prints all possible actions")
parser.add_argument("action", help="""executes functon(for getting
                   all possible functions run with --all-actions)""",
                   type=str, metavar="action", nargs="*",
                   action="append")

pyargs = parser.parse_args()
if pyargs.all_options == True:
    print("""All arguments:
  add-class [name [teacher [students]]] adds class using arguments or
                                  runs a dialog
  interactive, i                  runs an interactive administrator
                                  shell""")
    sys.exit()
if pyargs.action == [[]]:
    parser.print_help()
    sys.exit()
if pyargs.action[0][0] not in argaction:
    parser.error("first action should be from --all-options list")

def adapt_list_to_JSON(lst):
    return json.dumps(lst).encode('utf8')
def convert_JSON_to_list(data):
    return json.loads(data.decode('utf8'))
sqlite3.register_adapter(list, adapt_list_to_JSON)
sqlite3.register_converter("JSON", convert_JSON_to_list)
db = sqlite3.connect("user_data.db",
                     detect_types=sqlite3.PARSE_DECLTYPES)
cur = db.cursor()

# Getting list of empty classes IDs
fetch = cur.execute("""
    SELECT testID
    FROM tests_table
    ORDER BY testID ASC""").fetchall()
if fetch == []:
    max_class_id = 2
    empty_class_ids = [0, 1]
else:
    max_class_id = 2**math.ceil(math.log2(fetch[-1][0]))
    empty_class_ids = list(set(range(max_class_id)) -
                           set(i[0] for i in fetch))

def dialog(questions, valid_answ, conditions) -> ["answer1",...]:
    a = None
    answers = []
    for i in range(len(questions)):
        a = input(f"{questions[i]}\n>({', '.join(valid_answ[i])}) "
                  ).strip()
        while not conditions[i](a):
            a =input(f"{questions[i]}\n>({', '.join(valid_answ[i])}) "
                     ).strip()
        answers.append(a)
    return answers


def add_class(*args) -> None:
    name = ""
    teacher_id = -1
    students_ids = []

    # Getting values from `args`
    if len(args) >=1 and args[0][-1].isalpha() and args[0][:-1].isdigit():
        name = args[0][:-1] + args[0][-1].upper()
    elif len(args) >= 1:
        name = dialog([" Unrecognized argument `name`. It should \
contain numbers and one symbol after."], [["str"]],
                  [lambda a: a[-1].isalpha() and a[:-1].isdigit()])[0]

    if len(args) >= 2 and args[1].isdigit():
        teacher_id = args[1]
    elif len(args) >= 2 and args[1].isidentifier():
        pass
    elif len(args) >= 2:
        teacher_id = dialog([" Unrecognized argument `teacher`. It \
should be a valid teacher id or handle of a teacher"], [["int/str"]],
                        [lambda a: a.isdigit()or a.isidentifier()])[0]

    if len(args) >= 3:
        for i in args[2:]:
            if i.isdigit():
                students_ids.append(i)
            elif dialog([f" Unrecognized argument `student` by \
id `{i}`. Is the list {students_ids} valid?"], [["y", "n"]],
                        [lambda a: a in["y", "n"]])==["y"]:
                break
            else:
                students_ids = []
                break

    # Getting values that wasn't in `args`
    questions = []
    answers = []
    conditions = []
    if name == "":
        questions.append(" Argument `name` is unbounded. Name should \
contain any amount of numbers and one symbol next")
        answers.append(["str"])
        conditions +=[lambda a: a[-1].isalpha() and a[:-1].isdigit()]
    if teacher_id == -1:
        questions.append(" Argument `teacher` is unbounded. It should\
 contain teacher handle(teacher must start bot first) or id.")
        answers.append(["int, str"])
        conditions.append(lambda a: a.isdigit() or a.isidentifier())
    if students_ids == []:
        questions.append(" Argument `students` is unbounded. It \
should contain multiple student ids")
        answers.append(["(int, ...)"])
        conditions +=[lambda a:False not in map(lambda x:x.isdigit(),
                                                a.split(", "))]

    answ = dialog(questions, answers, conditions)

    if name == "":
        name = answ[0][:-1] + answ[0][-1].upper()
        teacher_id = answ[1]
    elif teacher_id == -1:
        teacher_id = answ[0]
    if students_ids == []:
        students_ids = answ[-1].split(", ")

    if dialog([f"You shure you want to make class with properties \
name={name}, teacher_id={teacher_id}, student_ids={students_ids}?"],
              [["y", "n"]], [lambda a: a in ["y", "n"]]) == ["n"]:
        return

    cur.execute("""INSERT INTO classes_table
                VALUES (:teacherid, :studentsids, :classid, :name)""",
                {"teacherid":teacher_id, "studentsids":students_ids,
                 "classid":empty_class_ids.pop(), "name":name})


def interactive(*args):
    print(" Info: you can use `python -m sqlite3 user_data.db` to \
login into interactive sqlite3 shell")
    print("  Write `exit` or press ^D to exit")
    prompt = input("> ")
    while prompt not in ["exit", ""]:
        try:
            exec(prompt)
        except:
            print("// Caught error while processing")
        prompt = input("> ")


if pyargs.action[0][0] == "add-class":
    add_class(*pyargs.action[0][1:])
if pyargs.action[0][0] in ["interactive", "i"]:
    interactive(*pyargs.action[0][1:])


