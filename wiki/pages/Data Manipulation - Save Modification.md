# 💾 Save Modification

> ⚠️ **Warning**: This feature is only available using debug mode (use `--debug` option when running the bot)

The **Save Modification** feature allows users to export and import event flags and variables for the emulator. 

Below is a detailed guide to use this feature.

---

## ❓ Why Is This Useful?

This feature is particularly useful to transfer event flags and variables across different save files. For example:
- If you are playing a **US or European save file** and want to switch to a **Japanese ROM**, you cannot directly load the save file due to incompatibilities. However, with this feature, you can:
    - Export event flags and variables from your non-Japanese save.
    - Start the bot on your Japanese ROM save.
    - Import the event flags and variables into the new save to recreate progress from your previous game.

### ⚠️ Warnings and Potential Issues
1. **Limited Data Transfer**:
    - The feature only copies **event flags** and **variables**. It does **NOT** transfer:
        - Pokémon party
        - Items, Pokémons in inventory or storage
        - TMs, HMs, or Pokéballs
    - As a result, some progress may be incomplete or inconsistent in the new save.

2. **Soft Lock Risks**:
    - Using this feature in a **fresh save** with **endgame flags and variables** may result in a **soft lock**.  
      Example: Unlocking endgame content without having any HMs or Pokémon in your party may prevent progress as the game will consider you already chose a starter and received all the TMs.

3. **Manual Editing**:
    - The generated files (`event_flags.txt` and `event_vars.txt`) can be manually edited if necessary.
    - This allows for fine-tuning the game state to help avoiding soft locks.

4. **Editing for Fresh Saves**:
    - If you wish to start from a fresh save and use endgame flags and variables, you may need to edit your save to inject:
        - Items (e.g., HMs, Poké Balls)
        - Pokémon in your party or storage
        - Other essentials required for progress (Bikes, Rod...).
    
---

## 🚀 Features and Functionality

### Export Events and Variables
- **Description**: Exports the current event flags and variables from the emulator to text files.
- **How to Use**:
    1. Open the **Data Manipulation** menu in the application.
    2. Select the **Export events and ears** option.
    3. The event flags and variables will be saved to the paths specified above.

### Import Events and Variables
- **Description**: Imports event flags and variables from the saved text files into the emulator.
- **How to Use**:
    1. Open the **Data Manipulation** menu in the application.
    2. Select the **Import events and vars** option.
    3. The emulator will load the data from the files and apply the changes.
    4. Save your game.
    5. Reset the game in **Emulator** -> **Reset** or restart the bot.

---

## 📂 Files Generated

When you use the **Save Modification** feature, the following files are created or used:

1. **Event Flags File**
    - **Path**: `profiles/event_flags.txt`
    - **Purpose**: Stores event flag data as key-value pairs in the format:
      ```
      flag_name = 1  # Enabled
      flag_name = 0  # Disabled
      ```

2. **Event Variables File**
    - **Path**: `profiles/event_vars.txt`
    - **Purpose**: Stores event variable data as key-value pairs in the format:
      ```
      var_name = <value>
      ```

---

## 🛠️ Developer Use Cases

This feature is also valuable for developers and testers. By exporting and importing flags and variables, you can:

1. **Generate Specific Game States**:
    - Create custom states to simulate particular moments in the game.

2. **Efficient Debugging**:
    - Quickly toggle event flags or variables to isolate and test specific features.

3. **Cross-Save Compatibility Testing**:
    - Test the bot’s behavior across different save files, regions, or ROM versions