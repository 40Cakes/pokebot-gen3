from modules.pokemon import get_party

from tkinter import *
from modules.context import context


def get_ev_targets():
    ## Tried to use these in a similar way to ask_for_choice() in gui.multi_select_window.py
    #window = Toplevel(context.gui.window)
    #ev_goal: list[list[int]]

    # didn't know how to index on these
    #ev_names = ['hp', 'attack', 'defence', 'special_attack', 'special_defence', 'speed']

    def ev_targets(Spinboxes):
        updated_values = [[None for _ in range(6)] for _ in range(party_size)]
        for i in range(party_size):
            for j in range(6):
                updated_values[i][j] = int(Spinboxes[i][j].get())
        return updated_values

    party_size = len(get_party())
    party_evs = [[None for _ in range(6)] for _ in range(party_size)]
    for i in range(party_size):
        party_evs[i] = [get_party()[i].evs.hp, get_party()[i].evs.attack, get_party()[i].evs.defence, 
                        get_party()[i].evs.special_attack, get_party()[i].evs.special_defence, get_party()[i].evs.speed]

    window = Tk()
    window.title('EV goals')

    for i in range(party_size):
        Label(window, text=get_party()[i].name).grid(row=i+1, column=0)

    Label(window, text='HP').grid(row=0, column=1)
    Label(window, text='Atk').grid(row=0, column=2)
    Label(window, text='Def').grid(row=0, column=3)
    Label(window, text='SpA').grid(row=0, column=4)
    Label(window, text='SpD').grid(row=0, column=5)
    Label(window, text='Spe').grid(row=0, column=6)


    Spinboxes = [[None for _ in range(6)] for _ in range(party_size)]
    for i in range(party_size):
        for j in range(6):
            Spinboxes[i][j] = Spinbox(window, from_=0, to=252, increment=4, wrap=True)
            Spinboxes[i][j].delete(0, last=None)
            Spinboxes[i][j].insert(0, party_evs[i][j])
            Spinboxes[i][j].grid(row=i+1, column=j+1, padx=10, pady=3)

    def Close(): 
        ev_goal = ev_targets(Spinboxes)
        window.quit() # Want to remove the gui here. destroy() achieves this but freezes the mode
        print(ev_goal) # Testing only

    Button(window, text='EV Train', width=20, height=1, bg='lightblue', command=lambda: Close()).grid(row=7, column=3, columnspan=2, pady=15)
    
    '''    # This was an attempt to follow the approach of gui.multi_select_window.py 
    def remove_window(event=None):
        nonlocal window
        window.destroy()
        window = None

    def return_selection():
        nonlocal ev_goal
        ev_goal = ev_targets(Spinboxes)
        window.after(50, remove_window)
        print(ev_goal)


    Button(window, text='EV Train', width=20, height=1, bg='lightblue', command=lambda: return_selection()).grid(row=7, column=3, columnspan=2, pady=15)
    '''
    window.mainloop()
    
    return ev_targets(Spinboxes)