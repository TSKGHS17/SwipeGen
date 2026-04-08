# ==========================================
# 1. Find Slidable Regions on the Screen (Region)
# ==========================================
REGION_TASK_PROMPT = """You are an intelligent GUI automation testing expert. This is a screenshot of a mobile application UI.
Your task is to identify **ALL** implicit or large "slidable regions" on the screen (e.g., content feeds, image waterfalls, horizontally scrollable card carousels, expandable side drawers, etc.).

Please first think privately within the <think> and </think> tags. Your thinking process should include:
1. Observe the overall layout and determine the type of the application.
2. Analyze whether the main content exceeds the screen boundaries (e.g., truncated text/images) to determine where it can be scrolled.
3. Confirm the effective bounding box (bbox) of the slidable region.

After thinking, strictly output a JSON array. 
JSON format requirements:
1. category: Must be exactly "region".
2. type: The type of the region (e.g., "feed", "carousel", "sidebar").
3. direction: The supported swipe direction ("vertical" or "horizontal").
4. bbox: Bounding box coordinates[x1, y1, x2, y2], normalized to the range of 0 to 1000.
5. command: A specific, clear natural language action instruction for this region. It MUST be an **imperative sentence** (e.g., "Swipe up on the main feed to view more posts").

STRICT REQUIREMENT: After </think>, you must output ONLY a valid JSON array. Do not include markdown tags like ```json.
"""

REGION_EXAMPLE_ASSISTANT = """<think>
This is a screenshot of a social media app's home page.
I see a large content area in the middle, and the text at the bottom is truncated, indicating this is a vertical dynamic feed.
There is a navigation bar at the top and a tab bar at the bottom, so the main area from y=150 to y=920 is a vertically slidable region.
</think>[
  {
    "category": "region",
    "type": "feed",
    "direction": "vertical",
    "bbox":[0, 150, 1000, 920],
    "command": "Swipe up on the main feed to view more posts"
  }
]"""


# ==========================================
# 2. Generate Intent Instructions for XML Components (Component)
# ==========================================
COMPONENT_TASK_PROMPT = """You are an intelligent GUI automation testing expert. This is a screenshot of a mobile application UI.
I have located a [Scrollable Component] for you via underlying code.
Its normalized bounding box (bbox) is: {}.
Its supported swipe direction is: "{}".
The text information contained within this component is: "{}".

Please first think privately within the <think> and </think> tags:
1. Locate the component in the screenshot using the provided bbox and text.
2. Observe the context of the component to infer its specific function.
3. Formulate an action instruction that matches human habits.

After thinking, return ONLY ONE specific, clear natural language action instruction. It MUST be an **imperative sentence**.
Note: After </think>, output only the plain text of this instruction, with no extra words.
"""

COMPONENT_EXAMPLE_PROMPT = COMPONENT_TASK_PROMPT.format("[0, 100, 1000, 900]", "vertical", "Settings | Network | Bluetooth | Display")

COMPONENT_EXAMPLE_ASSISTANT = """<think>
Located the component at bbox[0, 100, 1000, 900]. The internal text shows "Settings | Network | Bluetooth | Display".
This is a typical system settings list. The direction is "vertical".
If a user swipes on this component, the intent is obviously to scroll down to see other hidden setting items.
Therefore, the instruction should clearly state "Scroll down the settings list".
</think>
Scroll down the settings list to find more system options"""


# ==========================================
# 3. Generate Intent Instructions for Click (Tap) Operations
# ==========================================
CLICK_TASK_PROMPT = """You are an intelligent GUI automation testing expert. This is a screenshot of a mobile application UI.
I have located a [Clickable Component] that a user is about to tap.
Its normalized bounding box (bbox) is: {}.
The text or description of this component is: "{}".

Please first think privately within the <think> and </think> tags:
1. Locate the component in the screenshot using the provided bbox and text.
2. Observe the context (e.g., is it a tab, a back button, a profile avatar, or a list item) to infer its specific function.
3. Formulate an action instruction that matches human habits.

After thinking, return ONLY ONE specific, clear natural language action instruction. It MUST be an **imperative sentence**.
Note: After </think>, output only the plain text of this instruction, with no extra words.
"""

CLICK_EXAMPLE_PROMPT = CLICK_TASK_PROMPT.format("[850, 100, 950, 200]", "Search")

CLICK_EXAMPLE_ASSISTANT = """<think>
Located the component at bbox[850, 100, 950, 200]. It is in the top right corner of the screen, typically where a search icon is placed. The text description confirms it is "Search".
Tapping this component is intended to open the search bar or search page.
Therefore, the instruction should clearly state "Tap the search icon to find content".
</think>
Tap the search icon to find content"""