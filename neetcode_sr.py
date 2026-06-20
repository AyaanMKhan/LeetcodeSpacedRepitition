#!/usr/bin/env python3
"""
Neetcode 150 — Spaced Repetition Daily Reviewer
Uses the SM-2 algorithm. History stored in neetcode_sr.json (same folder as this script).
"""

"""
python3 neetcode_sr.py        # start your session
python3 neetcode_sr.py --list-due      # just peek at today's problems
python3 neetcode_sr.py --list-tomorrow # preview tomorrow's problems
python3 neetcode_sr.py --stats      # see your progress
python3 neetcode_sr.py --config     # change problems per day (2-10)
python3 neetcode_sr.py --reset      # wipe history and start fresh

"""

import json
import os
import shutil
import sys
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
DATA_FILE   = _SCRIPT_DIR / "neetcode_sr.json"
_LEGACY_DATA_FILE = Path.home() / ".neetcode_sr.json"
PROBLEMS_PER_DAY = 5       # default; overridable in saved settings
MIN_EASINESS = 1.3
DEFAULT_EASINESS = 2.5
SELECTION_VERSION = 2      # bump when daily selection logic changes
CARD_FORMAT_VERSION = 2    # cards keyed by name with topic + difficulty + recall_ratings

# ── ANSI colors ───────────────────────────────────────────────────────────────
def supports_color():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = supports_color()

def c(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def bold(t):    return c(t, "1")
def dim(t):     return c(t, "2")
def green(t):   return c(t, "32")
def yellow(t):  return c(t, "33")
def red(t):     return c(t, "31")
def cyan(t):    return c(t, "36")
def magenta(t): return c(t, "35")
def blue(t):    return c(t, "34")

DIFF_COLOR = {"Easy": green, "Medium": yellow, "Hard": red}

# ── Active problem pool (comment out sections to exclude until ready) ─────────
PROBLEMS = [
    # Arrays & Hashing
    (1,   "Contains Duplicate",                  "Arrays & Hashing", "Easy",   217),
    (2,   "Valid Anagram",                        "Arrays & Hashing", "Easy",   242),
    (3,   "Two Sum",                              "Arrays & Hashing", "Easy",   1),
    (4,   "Group Anagrams",                       "Arrays & Hashing", "Medium", 49),
    (5,   "Top K Frequent Elements",              "Arrays & Hashing", "Medium", 347),
    (6,   "Product of Array Except Self",         "Arrays & Hashing", "Medium", 238),
    (7,   "Valid Sudoku",                         "Arrays & Hashing", "Medium", 36),
    (8,   "Encode and Decode Strings",            "Arrays & Hashing", "Medium", 271),
    (9,   "Longest Consecutive Sequence",         "Arrays & Hashing", "Medium", 128),
    # Two Pointers
    (10,  "Valid Palindrome",                     "Two Pointers",     "Easy",   125),
    (11,  "Two Sum II",                           "Two Pointers",     "Medium", 167),
    (12,  "3Sum",                                 "Two Pointers",     "Medium", 15),
    (13,  "Container With Most Water",            "Two Pointers",     "Medium", 11),
    (14,  "Trapping Rain Water",                  "Two Pointers",     "Hard",   42),
    # Sliding Window
    (15,  "Best Time to Buy and Sell Stock",      "Sliding Window",   "Easy",   121),
    (16,  "Longest Substring Without Repeating",  "Sliding Window",   "Medium", 3),
    (17,  "Longest Repeating Char Replacement",   "Sliding Window",   "Medium", 424),
    (18,  "Permutation in String",                "Sliding Window",   "Medium", 567),
    (19,  "Minimum Window Substring",             "Sliding Window",   "Hard",   76),
    (20,  "Sliding Window Maximum",               "Sliding Window",   "Hard",   239),
    # Stack
    (21,  "Valid Parentheses",                    "Stack",            "Easy",   20),
    (22,  "Min Stack",                            "Stack",            "Medium", 155),
    (23,  "Evaluate Reverse Polish Notation",     "Stack",            "Medium", 150),
    (24,  "Generate Parentheses",                 "Stack",            "Medium", 22),
    (25,  "Daily Temperatures",                   "Stack",            "Medium", 739),
    (26,  "Car Fleet",                            "Stack",            "Medium", 853),
    (27,  "Implement Queue using Stacks",         "Stack",            "Easy",   232),
    (28,  "Largest Rectangle in Histogram",       "Stack",            "Hard",   84),
    # Binary Search
    (29,  "Binary Search",                        "Binary Search",    "Easy",   704),
    (30,  "Search a 2D Matrix",                   "Binary Search",    "Medium", 74),
    (31,  "Koko Eating Bananas",                  "Binary Search",    "Medium", 875),
    (32,  "Find Min in Rotated Sorted Array",     "Binary Search",    "Medium", 153),
    (33,  "Search in Rotated Sorted Array",       "Binary Search",    "Medium", 33),
    (34,  "Time Based Key-Value Store",           "Binary Search",    "Medium", 981),
    (35,  "Median of Two Sorted Arrays",          "Binary Search",    "Hard",   4),
    # Linked List
    (36,  "Reverse Linked List",                  "Linked List",      "Easy",   206),
    (37,  "Merge Two Sorted Lists",               "Linked List",      "Easy",   21),
    (38,  "Reorder List",                         "Linked List",      "Medium", 143),
    (39,  "Remove Nth Node From End",             "Linked List",      "Medium", 19),
    (40,  "Copy List with Random Pointer",        "Linked List",      "Medium", 138),
    (41,  "Add Two Numbers",                      "Linked List",      "Medium", 2),
    (42,  "LRU Cache",                            "Linked List",      "Medium", 146),
    (43,  "Merge K Sorted Lists",                 "Linked List",      "Hard",   23),
    (44,  "Reverse Nodes in k-Group",             "Linked List",      "Hard",   25),
    # Trees
    (45,  "Invert Binary Tree",                   "Trees",            "Easy",   226),
    (46,  "Maximum Depth of Binary Tree",         "Trees",            "Easy",   104),
    (47,  "Diameter of Binary Tree",              "Trees",            "Easy",   543),
    (48,  "Balanced Binary Tree",                 "Trees",            "Easy",   110),
    (49,  "Same Tree",                            "Trees",            "Easy",   100),
    (50,  "Subtree of Another Tree",              "Trees",            "Easy",   572),
    (51,  "Lowest Common Ancestor of BST",        "Trees",            "Medium", 235),
    (52,  "Binary Tree Level Order Traversal",    "Trees",            "Medium", 102),
    (53,  "Binary Tree Right Side View",          "Trees",            "Medium", 199),
    (54,  "Count Good Nodes in Binary Tree",      "Trees",            "Medium", 1448),
    (55,  "Validate Binary Search Tree",          "Trees",            "Medium", 98),
    (56,  "Kth Smallest Element in BST",          "Trees",            "Medium", 230),
    (57,  "Construct Binary Tree from Preorder",  "Trees",            "Medium", 105),
    (58,  "Binary Tree Max Path Sum",             "Trees",            "Hard",   124),
    (59,  "Serialize and Deserialize Binary Tree","Trees",            "Hard",   297),
    (60,  "Binary Search Tree Iterator",          "Trees",            "Medium", 173),
    # Tries
    (61,  "Implement Trie (Prefix Tree)",         "Tries",            "Medium", 208),
    (62,  "Design Add and Search Words",          "Tries",            "Medium", 211),
    (63,  "Word Search II",                       "Tries",            "Hard",   212),
    # Heap / Priority Queue
    (64,  "Kth Largest Element in a Stream",      "Heap",             "Easy",   703),
    (65,  "Last Stone Weight",                    "Heap",             "Easy",   1046),
    (66,  "K Closest Points to Origin",           "Heap",             "Medium", 973),
    (67,  "Kth Largest Element in an Array",      "Heap",             "Medium", 215),
    (68,  "Task Scheduler",                       "Heap",             "Medium", 621),
    (69,  "Design Twitter",                       "Heap",             "Medium", 355),
    (70,  "Find Median from Data Stream",         "Heap",             "Hard",   295),
    # Backtracking
    (71,  "Subsets",                              "Backtracking",     "Medium", 78),
    (72,  "Combination Sum",                      "Backtracking",     "Medium", 39),
    (73,  "Permutations",                         "Backtracking",     "Medium", 46),
    (74,  "Subsets II",                           "Backtracking",     "Medium", 90),
    (75,  "Combination Sum II",                   "Backtracking",     "Medium", 40),
    (76,  "Word Search",                          "Backtracking",     "Medium", 79),
    (77,  "Palindrome Partitioning",              "Backtracking",     "Medium", 131),
    (78,  "Letter Combinations Phone Number",     "Backtracking",     "Medium", 17),
    (79,  "N-Queens",                             "Backtracking",     "Hard",   51),
    # Graphs
    (80,  "Number of Islands",                    "Graphs",           "Medium", 200),
    (81,  "Max Area of Island",                   "Graphs",           "Medium", 695),
    (82,  "Clone Graph",                          "Graphs",           "Medium", 133),
    (83,  "Walls and Gates",                      "Graphs",           "Medium", 286),
    (84,  "Rotting Oranges",                      "Graphs",           "Medium", 994),
    (85,  "Pacific Atlantic Water Flow",          "Graphs",           "Medium", 417),
    (86,  "Surrounded Regions",                   "Graphs",           "Medium", 130),
    (87,  "Course Schedule",                      "Graphs",           "Medium", 207),
    (88,  "Course Schedule II",                   "Graphs",           "Medium", 210),
    (89,  "Graph Valid Tree",                     "Graphs",           "Medium", 261),
    (90,  "Number of Connected Components",       "Graphs",           "Medium", 323),
    (91,  "Redundant Connection",                 "Graphs",           "Medium", 684),
    # Advanced Graphs (disabled — uncomment when ready)
    (92,  "Word Ladder",                          "Graphs",           "Hard",   127),
    (93,  "Reconstruct Itinerary",                "Graphs",           "Hard",   332),
    (94,  "Min Cost to Connect All Points",       "Graphs",           "Medium", 1584),
    (95,  "Network Delay Time",                   "Graphs",           "Medium", 743),
    (96,  "Swim in Rising Water",                 "Graphs",           "Hard",   778),
    (97,  "Alien Dictionary",                     "Graphs",           "Hard",   269),
    (98,  "Cheapest Flights Within K Stops",      "Graphs",           "Medium", 787),
    # 1-D Dynamic Programming
    (99,  "Climbing Stairs",                      "1D DP",            "Easy",   70),
    (100, "Min Cost Climbing Stairs",             "1D DP",            "Easy",   746),
    (101, "House Robber",                         "1D DP",            "Medium", 198),
    (102, "House Robber II",                      "1D DP",            "Medium", 213),
    (103, "Longest Palindromic Substring",        "1D DP",            "Medium", 5),
    (104, "Palindromic Substrings",               "1D DP",            "Medium", 647),
    (105, "Decode Ways",                          "1D DP",            "Medium", 91),
    (106, "Coin Change",                          "1D DP",            "Medium", 322),
    (107, "Maximum Product Subarray",             "1D DP",            "Medium", 152),
    (108, "Word Break",                           "1D DP",            "Medium", 139),
    (109, "Longest Increasing Subsequence",       "1D DP",            "Medium", 300),
    (110, "Partition Equal Subset Sum",           "1D DP",            "Medium", 416),
    # 2-D Dynamic Programming (disabled — uncomment when ready)
    # (111, "Unique Paths",                         "2D DP",            "Medium", 62),
    # (112, "Longest Common Subsequence",           "2D DP",            "Medium", 1143),
    # (113, "Best Time to Buy Stock w/ Cooldown",   "2D DP",            "Medium", 309),
    # (114, "Coin Change II",                       "2D DP",            "Medium", 518),
    # (115, "Target Sum",                           "2D DP",            "Medium", 494),
    # (116, "Interleaving String",                  "2D DP",            "Medium", 97),
    # (117, "Longest Increasing Path in Matrix",    "2D DP",            "Hard",   329),
    # (118, "Distinct Subsequences",                "2D DP",            "Hard",   115),
    # (119, "Edit Distance",                        "2D DP",            "Medium", 72),
    # (120, "Burst Balloons",                       "2D DP",            "Hard",   312),
    # (121, "Regular Expression Matching",          "2D DP",            "Hard",   10),
    # Greedy
    (122, "Maximum Subarray",                     "Greedy",           "Medium", 53),
    (123, "Jump Game",                            "Greedy",           "Medium", 55),
    (124, "Jump Game II",                         "Greedy",           "Medium", 45),
    (125, "Gas Station",                          "Greedy",           "Medium", 134),
    (126, "Hand of Straights",                    "Greedy",           "Medium", 846),
    (127, "Merge Triplets to Form Target",        "Greedy",           "Medium", 1899),
    (128, "Partition Labels",                     "Greedy",           "Medium", 763),
    (129, "Valid Parenthesis String",             "Greedy",           "Medium", 678),
    # Intervals
    (130, "Insert Interval",                      "Intervals",        "Medium", 57),
    (131, "Merge Intervals",                      "Intervals",        "Medium", 56),
    (132, "Non-overlapping Intervals",            "Intervals",        "Medium", 435),
    (133, "Meeting Rooms",                        "Intervals",        "Easy",   252),
    (134, "Meeting Rooms II",                     "Intervals",        "Medium", 253),
    (135, "Minimum Interval to Include Query",    "Intervals",        "Hard",   1851),
    # Math & Geometry (disabled — uncomment when ready)
    # (136, "Rotate Image",                         "Math & Geometry",  "Medium", 48),
    # (137, "Spiral Matrix",                        "Math & Geometry",  "Medium", 54),
    # (138, "Set Matrix Zeroes",                    "Math & Geometry",  "Medium", 73),
    # (139, "Happy Number",                         "Math & Geometry",  "Easy",   202),
    # (140, "Plus One",                             "Math & Geometry",  "Easy",   66),
    # (141, "Pow(x, n)",                            "Math & Geometry",  "Medium", 50),
    # (142, "Multiply Strings",                     "Math & Geometry",  "Medium", 43),
    # (143, "Detect Squares",                       "Math & Geometry",  "Medium", 2013),
    # Bit Manipulation (disabled — uncomment when ready)
    # (144, "Single Number",                        "Bit Manipulation", "Easy",   136),
    # (145, "Number of 1 Bits",                     "Bit Manipulation", "Easy",   191),
    # (146, "Counting Bits",                        "Bit Manipulation", "Easy",   338),
    # (147, "Reverse Bits",                         "Bit Manipulation", "Easy",   190),
    # (148, "Missing Number",                       "Bit Manipulation", "Easy",   268),
    # (149, "Sum of Two Integers",                  "Bit Manipulation", "Medium", 371),
    # (150, "Reverse Integer",                      "Bit Manipulation", "Medium", 7),
]

PROBLEMS_BY_ID = {p[0]: p for p in PROBLEMS}
PROBLEMS_BY_NAME = {p[1]: p for p in PROBLEMS}
ACTIVE_IDS = {p[0] for p in PROBLEMS}

# ── SM-2 helpers ──────────────────────────────────────────────────────────────
# card schema: {easiness, difficulty, topic, interval, repetitions,
#               next_review, last_review, recall_ratings}

def sm2_new(topic, difficulty):
    return {
        "easiness":       DEFAULT_EASINESS,
        "difficulty":     difficulty,
        "topic":          topic,
        "interval":       1,
        "repetitions":    0,
        "next_review":    str(date.today()),
        "last_review":    None,
        "recall_ratings": [],
    }

def normalize_card(card, topic, difficulty):
    ratings = card.get("recall_ratings", [])
    if not isinstance(ratings, list):
        ratings = []
    return {
        "easiness":       round(card.get("easiness", DEFAULT_EASINESS), 2),
        "difficulty":     difficulty,
        "topic":          topic,
        "interval":       card.get("interval", 1),
        "repetitions":    card.get("repetitions", 0),
        "next_review":    card.get("next_review", str(date.today())),
        "last_review":    card.get("last_review"),
        "recall_ratings": [int(r) for r in ratings if isinstance(r, (int, float))],
    }

def sm2_update(card, quality):
    """
    quality: 0-5
      5 = perfect recall
      4 = correct with slight hesitation
      3 = correct with difficulty
      2 = wrong but remembered once shown
      1 = wrong, hint barely helped
      0 = total blank
    """
    if quality < 3:
        card["repetitions"] = 0
        card["interval"]    = 1
    else:
        if card["repetitions"] == 0:
            card["interval"] = 1
        elif card["repetitions"] == 1:
            card["interval"] = 6
        else:
            card["interval"] = math.ceil(card["interval"] * card["easiness"])
        card["repetitions"] += 1

    card["easiness"] = round(max(
        MIN_EASINESS,
        card["easiness"] + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    ), 2)

    card["last_review"] = str(date.today())
    next_dt = date.today() + timedelta(days=card["interval"])
    card["next_review"] = str(next_dt)
    return card

def is_due(card, as_of=None):
    as_of = as_of or date.today()
    if card["next_review"] is None:
        return True
    return date.fromisoformat(card["next_review"]) <= as_of

def last_recall_rating(card):
    ratings = card.get("recall_ratings", [])
    return ratings[-1] if ratings else None

def struggled_recently(card):
    rating = last_recall_rating(card)
    return rating is not None and rating <= 2

# ── Persistence ───────────────────────────────────────────────────────────────

def migrate_cards_format(data):
    """Convert ID-keyed cards to name-keyed cards with topic and difficulty."""
    cards = data.get("cards", {})
    if not cards:
        return False

    new_cards = {}
    changed = False

    for key, card in cards.items():
        if str(key).isdigit():
            prob = PROBLEMS_BY_ID.get(int(key))
            if not prob:
                continue
            _, name, topic, diff, _ = prob
            changed = True
        elif key in PROBLEMS_BY_NAME:
            prob = PROBLEMS_BY_NAME[key]
            _, name, topic, diff, _ = prob
            if not card.get("topic") or not card.get("difficulty"):
                changed = True
        else:
            new_cards[key] = card
            continue

        new_cards[name] = normalize_card(dict(card), topic, diff)

    if set(new_cards) != set(cards) or any(
        k.isdigit() for k in cards
    ):
        changed = True

    data["cards"] = new_cards
    return changed

def load_data():
    if not DATA_FILE.exists() and _LEGACY_DATA_FILE.exists():
        try:
            shutil.copy2(_LEGACY_DATA_FILE, DATA_FILE)
        except OSError:
            pass

    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
            settings = data.setdefault("settings", {})
            if settings.get("selection_version") != SELECTION_VERSION:
                settings["selection_version"] = SELECTION_VERSION
                data["today_date"] = None
                data["today_list"] = []
                data["today_done"] = []
            if settings.get("card_format_version") != CARD_FORMAT_VERSION:
                migrate_cards_format(data)
                settings["card_format_version"] = CARD_FORMAT_VERSION
                save_data(data)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "cards":      {},   # problem name -> card
        "settings":   {
            "problems_per_day": PROBLEMS_PER_DAY,
            "selection_version": SELECTION_VERSION,
            "card_format_version": CARD_FORMAT_VERSION,
        },
        "streak":     0,
        "last_session": None,
        "today_list": [],   # list of problem IDs for today
        "today_date": None,
        "today_done": [],   # IDs completed today
    }

def save_data(data):
    for name, card in list(data.get("cards", {}).items()):
        if name in PROBLEMS_BY_NAME:
            p = PROBLEMS_BY_NAME[name]
            data["cards"][name] = normalize_card(card, p[2], p[3])
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── Problem selection ─────────────────────────────────────────────────────────

def get_card(data, pid):
    _, name, topic, diff, _ = PROBLEMS_BY_ID[pid]
    if name not in data["cards"]:
        data["cards"][name] = sm2_new(topic, diff)
    return data["cards"][name]

def _urgency_key(p, data, as_of=None):
    """Lower = more urgent (due sooner / fewer successful reps)."""
    card = get_card(data, p[0])
    due = 0 if is_due(card, as_of) else 1
    struggle = 0 if struggled_recently(card) else 1
    return (
        due,
        struggle,
        card.get("repetitions", 0),
        card.get("next_review", "9999-99-99"),
    )


def pick_diverse_random(pool, n, data, as_of=None):
    """
    Pick up to n problems with random topic order (round-robin across topics).
    Within each topic, prefer the most urgent due cards first.
    """
    if not pool or n <= 0:
        return []

    by_topic = defaultdict(list)
    for p in pool:
        by_topic[p[2]].append(p)

    for topic in by_topic:
        by_topic[topic].sort(key=lambda p: _urgency_key(p, data, as_of))

    topics = list(by_topic.keys())
    random.shuffle(topics)

    selected = []
    while len(selected) < n and topics:
        progressed = False
        for topic in list(topics):
            if len(selected) >= n:
                break
            bucket = by_topic[topic]
            if not bucket:
                topics.remove(topic)
                continue
            selected.append(bucket.pop(0)[0])
            progressed = True
        if not progressed:
            break
        random.shuffle(topics)

    return selected[:n]


def pick_for_date(data, as_of=None, *, save=False, use_cache=True):
    as_of = as_of or date.today()
    n = data["settings"].get("problems_per_day", PROBLEMS_PER_DAY)
    day_str = str(as_of)

    if save and use_cache and data.get("today_date") == day_str and data.get("today_list"):
        cached = [pid for pid in data["today_list"] if pid in ACTIVE_IDS]
        if len(cached) == len(data["today_list"]):
            return cached
        data["today_list"] = []
        data["today_date"] = None

    rng_state = random.getstate()
    random.seed(day_str)
    try:
        due = [p for p in PROBLEMS if is_due(get_card(data, p[0]), as_of)]
        due_struggled = [p for p in due if struggled_recently(get_card(data, p[0]))]
        due_ids = {p[0] for p in due}
        not_due = [p for p in PROBLEMS if p[0] not in due_ids]

        # Always include all due problems you recently struggled with (rating <= 2),
        # even if this exceeds the daily cap.
        selected = pick_diverse_random(due_struggled, len(due_struggled), data, as_of)
        selected_ids = set(selected)
        remaining_due = [p for p in due if p[0] not in selected_ids]
        target_total = max(n, len(selected))
        if len(selected) < target_total:
            selected.extend(
                pick_diverse_random(remaining_due, target_total - len(selected), data, as_of)
            )
        if len(selected) < target_total:
            selected.extend(
                pick_diverse_random(not_due, target_total - len(selected), data, as_of)
            )
    finally:
        random.setstate(rng_state)

    if save:
        data["today_list"] = selected
        data["today_date"] = day_str
        data["today_done"] = []
        save_data(data)
    return selected


def pick_today(data):
    return pick_for_date(data, date.today(), save=True, use_cache=True)


def pick_tomorrow(data):
    return pick_for_date(data, date.today() + timedelta(days=1), save=False, use_cache=False)

# ── Display helpers ───────────────────────────────────────────────────────────

def lc_url(lc_num, name):
    slug = name.lower()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = "-".join(slug.split())
    return f"https://leetcode.com/problems/{slug}/"

def print_header(data, when=None):
    when = when or date.today()
    day_str = when.strftime("%A, %B %d %Y")
    streak = data.get("streak", 0)
    streak_txt = f"  🔥 {streak} day streak" if streak and when == date.today() else ""
    print()
    print(bold(cyan("╔══════════════════════════════════════════════════════╗")))
    print(bold(cyan("║")) + bold("   Neetcode 150 — Spaced Repetition Review         ") + bold(cyan("║")))
    print(bold(cyan("╚══════════════════════════════════════════════════════╝")))
    print(f"  {dim(day_str)}{yellow(streak_txt)}")
    print()


def print_problem_list(data, problem_ids, *, when=None, done_set=None):
    when = when or date.today()
    done_set = done_set or set()
    print_header(data, when=when)
    total = len(problem_ids)
    n = data["settings"].get("problems_per_day", PROBLEMS_PER_DAY)
    if total > n:
        print(f"  {bold(str(total))} problems scheduled  "
              f"{dim('(includes all due struggles above your ' + str(n) + '/day cap)')}")
    else:
        print(f"  {bold(str(total))} problems scheduled")
    print()
    for idx, pid in enumerate(problem_ids, 1):
        print_problem(idx, total, pid, done=pid in done_set)
    print()

def print_problem(idx, total, pid, done=False):
    prob = PROBLEMS_BY_ID[pid]
    _, name, topic, diff, lc_num = prob
    diff_fn = DIFF_COLOR.get(diff, lambda x: x)
    status = green("✓") if done else dim("○")
    url = lc_url(lc_num, name)
    print(f"  {status}  {bold(str(idx))}/{total}  {bold(name)}")
    print(f"      {diff_fn(diff)}  ·  {dim(topic)}  ·  LC #{lc_num}")
    print(f"      {blue(url)}")

def print_separator():
    print(dim("  " + "─" * 52))

# ── Interactive session ───────────────────────────────────────────────────────

QUALITY_LABELS = {
    "5": ("5", "Perfect recall"),
    "4": ("4", "Hesitated slightly"),
    "3": ("3", "Correct but hard"),
    "2": ("2", "Wrong, remembered after"),
    "1": ("1", "Wrong, hint barely helped"),
    "0": ("0", "Total blank"),
}

def ask_quality():
    print()
    print("  " + bold("How well did you recall this?"))
    for k, (num, label) in QUALITY_LABELS.items():
        bar = "█" * (int(k) + 1)
        q_fn = [red, red, yellow, yellow, green, green][int(k)]
        print(f"    {q_fn(num)} — {label}")
    print()
    while True:
        try:
            ans = input("  Enter rating (0-5): ").strip()
            if ans in QUALITY_LABELS:
                return int(ans)
            print("  Please enter a number from 0 to 5.")
        except (KeyboardInterrupt, EOFError):
            print()
            return None

def run_session(data):
    today_ids = pick_today(data)
    done_set  = set(data.get("today_done", []))
    total     = len(today_ids)

    print_header(data)

    # Summary line
    reviewed = sum(1 for pid in today_ids if pid in done_set)
    print(f"  {bold(str(total))} problems today  ·  {green(str(reviewed))} completed")
    print()

    for idx, pid in enumerate(today_ids, 1):
        done = pid in done_set
        print_problem(idx, total, pid, done=done)

    print_separator()
    print()

    # Prompt
    pending = [pid for pid in today_ids if pid not in done_set]
    if not pending:
        print(green("  All done for today! Great work. 🎉"))
        update_streak(data)
        save_data(data)
        print_stats(data, today_ids)
        return

    print("  Commands: " +
          bold("[1-%d]" % total) + " review a problem  " +
          bold("[a]") + " review all  " +
          bold("[s]") + " stats  " +
          bold("[q]") + " quit")
    print()

    while True:
        try:
            cmd = input("  > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            print(dim("  Session saved. See you tomorrow!"))
            save_data(data)
            return

        if cmd == "q":
            print(dim("  Session saved. See you tomorrow!"))
            save_data(data)
            return

        elif cmd == "s":
            print_stats(data, today_ids)

        elif cmd == "a":
            for pid in list(pending):
                review_one(data, pid, today_ids, done_set)
                pending_now = [p for p in today_ids if p not in done_set]
                if not pending_now:
                    break
            done_set = set(data.get("today_done", []))
            if all(pid in done_set for pid in today_ids):
                print()
                print(green("  All done for today! Great work. 🎉"))
                update_streak(data)
                save_data(data)
                print_stats(data, today_ids)
                return
            save_data(data)

        elif cmd.isdigit():
            num = int(cmd)
            if 1 <= num <= total:
                pid = today_ids[num - 1]
                review_one(data, pid, today_ids, done_set)
                done_set = set(data.get("today_done", []))
                if all(pid in done_set for pid in today_ids):
                    print()
                    print(green("  All done for today! Great work. 🎉"))
                    update_streak(data)
                    save_data(data)
                    print_stats(data, today_ids)
                    return
                save_data(data)
            else:
                print(f"  Enter a number between 1 and {total}.")

        else:
            print("  Unknown command. Try a number, 'a', 's', or 'q'.")

def review_one(data, pid, today_ids, done_set):
    prob = PROBLEMS_BY_ID[pid]
    _, name, topic, diff, lc_num = prob
    diff_fn = DIFF_COLOR.get(diff, lambda x: x)

    print()
    print_separator()
    print(f"  {bold(name)}")
    print(f"  {diff_fn(diff)}  ·  {dim(topic)}  ·  LC #{lc_num}")
    print(f"  {blue(lc_url(lc_num, name))}")
    print()
    print(dim("  Open the link, solve or trace through the problem, then rate yourself."))

    card = get_card(data, pid)
    print(f"  {dim('Interval: ' + str(card['interval']) + ' day(s)  |  Easiness: ' + str(round(card['easiness'], 2)))}")
    history = card.get("recall_ratings", [])
    if history:
        print(f"  {dim('Past recall (oldest → newest): ' + ' → '.join(str(r) for r in history))}")

    quality = ask_quality()
    if quality is None:
        return

    sm2_update(card, quality)
    card.setdefault("recall_ratings", []).append(quality)
    data["cards"][name] = card

    if pid not in done_set:
        data["today_done"].append(pid)
        done_set.add(pid)

    next_dt = date.fromisoformat(card["next_review"])
    days_until = (next_dt - date.today()).days
    if days_until <= 0:
        when = "tomorrow"
    elif days_until == 1:
        when = "in 1 day"
    else:
        when = f"in {days_until} days"

    print()
    print(f"  {green('✓')} Logged! Next review: {bold(when)} ({card['next_review']})")
    print_separator()

def update_streak(data):
    today = str(date.today())
    last  = data.get("last_session")
    if last is None:
        data["streak"] = 1
    else:
        last_dt  = date.fromisoformat(last)
        today_dt = date.today()
        delta    = (today_dt - last_dt).days
        if delta == 1:
            data["streak"] = data.get("streak", 0) + 1
        elif delta == 0:
            pass  # already counted today
        else:
            data["streak"] = 1
    data["last_session"] = today

def print_stats(data, today_ids):
    print()
    print(bold("  ── Stats ──────────────────────────────"))

    cards = data.get("cards", {})
    total_reviewed = sum(1 for c in cards.values() if c.get("repetitions", 0) > 0)

    done_today = len(data.get("today_done", []))
    streak     = data.get("streak", 0)

    # Due this week
    week_ahead = date.today() + timedelta(days=7)
    due_week   = sum(
        1 for p in PROBLEMS
        if p[1] in cards and
           date.fromisoformat(cards[p[1]]["next_review"]) <= week_ahead
    )

    # By difficulty
    by_diff = {"Easy": 0, "Medium": 0, "Hard": 0}
    for p in PROBLEMS:
        c = cards.get(p[1])
        if c and c.get("repetitions", 0) > 0:
            diff = c.get("difficulty", p[3])
            by_diff[diff] = by_diff.get(diff, 0) + 1

    print(f"  Total problems reviewed : {bold(str(total_reviewed))} / {len(PROBLEMS)}")
    print(f"  Completed today         : {green(str(done_today))} / {len(today_ids)}")
    print(f"  Current streak          : {yellow('🔥 ' + str(streak) + ' day(s)')}")
    print(f"  Due within 7 days       : {str(due_week)}")
    print(f"  Easy / Medium / Hard    : {green(str(by_diff['Easy']))} / {yellow(str(by_diff['Medium']))} / {red(str(by_diff['Hard']))}")
    print()

# ── Settings ──────────────────────────────────────────────────────────────────

def configure(data):
    print()
    print(bold("  Settings"))
    current = data["settings"].get("problems_per_day", PROBLEMS_PER_DAY)
    print(f"  Problems per day (current: {current})")
    try:
        val = input("  New value (2-10, enter to keep): ").strip()
        if val:
            n = int(val)
            if 2 <= n <= 10:
                data["settings"]["problems_per_day"] = n
                # reset today so new count applies
                data["today_date"] = None
                data["today_list"] = []
                save_data(data)
                print(green(f"  Saved! Problems per day set to {n}."))
            else:
                print(red("  Must be between 2 and 10."))
    except (ValueError, KeyboardInterrupt, EOFError):
        print(dim("  Unchanged."))

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Neetcode 150 Spaced Repetition Reviewer")
    parser.add_argument("--stats",    action="store_true", help="Show stats and exit")
    parser.add_argument("--config",   action="store_true", help="Change settings")
    parser.add_argument("--reset",    action="store_true", help="Reset all history (dangerous!)")
    parser.add_argument("--list-due", action="store_true", help="List today's problems and exit")
    parser.add_argument("--list-tomorrow", action="store_true", help="Preview tomorrow's problems and exit")
    args = parser.parse_args()

    data = load_data()

    if args.reset:
        confirm = input("Reset ALL review history? This cannot be undone. Type YES: ").strip()
        if confirm == "YES":
            DATA_FILE.unlink(missing_ok=True)
            print(green("History cleared."))
        else:
            print(dim("Cancelled."))
        return

    if args.config:
        configure(data)
        return

    if args.stats:
        today_ids = pick_today(data)
        print_stats(data, today_ids)
        return

    if args.list_due:
        today_ids = pick_today(data)
        print_problem_list(
            data,
            today_ids,
            when=date.today(),
            done_set=set(data.get("today_done", [])),
        )
        return

    if args.list_tomorrow:
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_ids = pick_tomorrow(data)
        print_problem_list(data, tomorrow_ids, when=tomorrow)
        print(dim("  Preview based on current schedule. Finishing today's reviews may change this."))
        print()
        return

    run_session(data)

if __name__ == "__main__":
    main()
