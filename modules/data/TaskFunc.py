from enum import StrEnum  # https://docs.python.org/3/library/enum.html


class TaskFunc(StrEnum):
    LEARN_MOVE_RS = "sub_809E260"
    LEARN_MOVE_E = "Task_HandleReplaceMoveInput"
    LEARN_MOVE_FRLG = "Task_InputHandler_SelectOrForgetMove"
    START_MENU_RS = "sub_80712B4"  # whoever decided on this name is not a good person
    START_MENU_E = "Task_ShowStartMenu"
    START_MENU_FRLG = "Task_StartMenuHandleInput"
    PARTY_MENU_RS = "HandleDefaultPartyMenu"
