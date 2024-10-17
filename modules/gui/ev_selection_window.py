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
        updated_values = [int(Spinboxes[0].get()), int(Spinboxes[1].get()), int(Spinboxes[2].get()),
                          int(Spinboxes[3].get()), int(Spinboxes[4].get()), int(Spinboxes[5].get())]
        return updated_values
    
    party_evs = [get_party()[0].evs.hp, get_party()[0].evs.attack, get_party()[0].evs.defence, 
                        get_party()[0].evs.special_attack, get_party()[0].evs.special_defence, get_party()[0].evs.speed]

    window = Tk()
    window.title('EV goals')

    Label(window, text=get_party()[0].name).grid(row=1, column=0)

    Label(window, text='HP').grid(row=0, column=1)
    Label(window, text='Atk').grid(row=0, column=2)
    Label(window, text='Def').grid(row=0, column=3)
    Label(window, text='SpA').grid(row=0, column=4)
    Label(window, text='SpD').grid(row=0, column=5)
    Label(window, text='Spe').grid(row=0, column=6)

    Spinboxes = [0,0,0,0,0,0]
    for i in range(6):
        Spinboxes[i] = Spinbox(window, from_=0, to=252, increment=4, wrap=True, width=8)
        Spinboxes[i].delete(0, last=None)
        Spinboxes[i].insert(0, party_evs[i])
        Spinboxes[i].grid(row=1, column=i+1, padx=10, pady=3)

    def Close(): 
        ev_goal = ev_targets(Spinboxes)
        window.quit() # Want to remove the gui here. destroy() achieves this but freezes the mode

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