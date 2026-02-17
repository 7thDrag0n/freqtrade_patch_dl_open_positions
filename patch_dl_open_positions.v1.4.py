import os
import shutil
import re

# git clone https://github.com/freqtrade/freqtrade.git
# Configuration for each file modification
file_modifications = [
    {
        "file_path": "freqtrade/freqai/utils.py",
        "function_name": "download_all_data_for_training",
        "insert_after_line": "all_pairs = dynamic_expand_pairlist(config, markets)",
        "code_to_insert": """\
        
    #7thDragon##########
    init_db(config["db_url"])
    trades: list[Trade] = Trade.get_open_trades()
    new_pairs_list = [trade.pair for trade in trades if trade.pair not in all_pairs]
    all_pairs += new_pairs_list
    logger.info(f"*** FreqAI needs also to train data also for opened positions pairs: {new_pairs_list}")
    #7thDragon##########""",
        "import_statement": "from freqtrade.persistence import Trade, init_db",
        "comment_lines": [],  # No lines to comment
        "applicable": "2024.5- | Fix for download data also for opened positions"
    },
    {
        "file_path": "freqtrade/data/history/history_utils.py",
        "function_name": "download_data_main",
        "insert_after_line": "expanded_pairs = dynamic_expand_pairlist(config, available_pairs)",
        "insert_before_line": "if \"timeframes\" not in config:",
        "code_to_insert": """\

    #7thDragon##########
    init_db(config["db_url"])
    trades: list[Trade] = Trade.get_open_trades()
    info_list = [trade.pair for trade in trades if trade.pair not in expanded_pairs]
    expanded_pairs += info_list
    logger.info(f"*** FreqAI needs to download data also for opened positions pairs (form DB): {info_list}")
    #7thDragon##########""",
        "import_statement": "from freqtrade.persistence import Trade, init_db",
        "comment_lines": [],  # No lines to comment
        "applicable": "2024.5-2024.12 | Fix for download data also for opened positions"
    },
    {
        "file_path": "freqtrade/data/history/history_utils.py",
        "function_name": "download_data",
        "insert_after_line": "expanded_pairs = dynamic_expand_pairlist(config, available_pairs)",
        "insert_before_line": "if \"timeframes\" not in config:",
        "code_to_insert": """\

    #7thDragon##########
    init_db(config["db_url"])
    trades: list[Trade] = Trade.get_open_trades()
    info_list = [trade.pair for trade in trades if trade.pair not in expanded_pairs]
    expanded_pairs += info_list
    logger.info(f"*** FreqAI needs to download data also for opened positions pairs (form DB): {info_list}")
    #7thDragon##########""",
        "import_statement": "from freqtrade.persistence import Trade, init_db",
        "comment_lines": [],  # No lines to comment
        "applicable": "2025.1- | Fix for download data also for opened positions"
    },
    {
        "file_path": "freqtrade/commands/data_commands.py",
        "function_name": "start_convert_trades",
        "insert_after_line": "expanded_pairs = dynamic_expand_pairlist(config, available_pairs)",
        "insert_before_line": "convert_trades_to_ohlcv(",
        "code_to_insert": """\

    #7thDragon##########
    init_db(config["db_url"])
    trades: list[Trade] = Trade.get_open_trades()
    info_list = [trade.pair for trade in trades if trade.pair not in expanded_pairs]
    expanded_pairs += info_list
    logger.info(f"*** FreqAI needs to use data also for opened positions pairs: {info_list}")
    #7thDragon##########""",
        "import_statement": "from freqtrade.persistence import Trade, init_db",
        "comment_lines": [],  # No lines to comment
        "applicable": "2024.5- | Fix for download data also for opened positions"
    },
    {
        "file_path": "freqtrade/freqai/freqai_interface.py",
        "function_name": "_set_train_queue",
        "insert_after_line": "current_pairlist = self.config.get(\"exchange\", {}).get(\"pair_whitelist\")",
        "insert_before_line": "if not self.dd.pair_dict:",
        "code_to_insert": """\
    
        #7thDragon##########
        init_db(self.config["db_url"])
        trades: list[Trade] = Trade.get_open_trades()
        current_pairlist += [trade.pair for trade in trades if trade.pair not in current_pairlist]
        #7thDragon##########""",
        "import_statement": "from freqtrade.persistence import Trade, init_db",
        "comment_lines": [],  # No lines to comment
        "applicable": "2024.5- | Fix for download data also for opened positions"
    },
    {
        "file_path": "freqtrade/freqai/freqai_interface.py",
        "function_name": "__init__",  # Assuming this is the correct function name
        "insert_after_line": "self.pair_it_train = 0",
        "code_to_insert": """\
        
        #7thDragon##########
        init_db(self.config["db_url"])
        full_pair_list = self.config.get("exchange", {}).get("pair_whitelist")
        trades: list[Trade] = Trade.get_open_trades()
        full_pair_list += [trade.pair for trade in trades if trade.pair not in full_pair_list]
        self.total_pairs = len(full_pair_list)
        #7thDragon##########""",
        "import_statement": "from freqtrade.persistence import Trade, init_db",
        "comment_lines": [
            "self.total_pairs = len(self.config.get(\"exchange\", {}).get(\"pair_whitelist\"))"
        ],
        "applicable": "2024.5- | Fix for download data also for opened positions"
    },
    {
        "file_path": "freqtrade/strategy/interface.py",
        "function_name": "advise_exit",  # Assuming this is the correct function name
        "insert_after_line": 'dataframe.loc[:,',
        "code_to_insert": """\
        #7thDragon##########
        # Create a DataFrame with the new column(s) in one step
        additional_columns = pd.DataFrame({"exit_tag": [""] * len(dataframe)}, index=dataframe.index)

        # Combine the original and new columns to avoid fragmentation
        dataframe = pd.concat([dataframe, additional_columns], axis=1)
        #7thDragon##########""",
        "import_statement": "import pandas as pd",
        "comment_lines": [
            'dataframe.loc[:, "exit_tag"] = ""'
        ],
        "applicable": "2024.5- | Fix for slow interface advise_exit"
    },
    # {
        # "file_path": "freqtrade/strategy/interface.py",
        # "function_name": "should_exit",  # Assuming this is the correct function name
        # "insert_after_line": "if roi_reached:",
        # "code_to_insert": """\
        
            # #7thDragon##########
            # trade_dur = int((current_time.timestamp() - trade.open_date_utc.timestamp()) // 60)
            # roi_minute, _ = self.min_roi_reached_entry(trade_dur)
            # exits.append(ExitCheckTuple(exit_type=ExitType.ROI, exit_reason=f"roi_{roi_minute}m"))
            # #7thDragon##########""",
        # "import_statement": "import pandas as pd",
        # "comment_lines": [
            # 'exits.append(ExitCheckTuple(exit_type=ExitType.ROI))'
        # ],
        # "applicable": "2024.5-2025.4 | ROI enrichement"
    # },
    {
        "file_path": "freqtrade/strategy/interface.py",
        "function_name": "should_exit",  # Assuming this is the correct function name
        "insert_after_line": "if roi_reached:",
        "code_to_insert": """\
        
            #7thDragon##########
            trade_dur = int((current_time.timestamp() - trade.open_date_utc.timestamp()) // 60)
            roi_minute, _ = self.min_roi_reached_entry(trade, trade_dur, current_time)
            exits.append(ExitCheckTuple(exit_type=ExitType.ROI, exit_reason=f"roi_{roi_minute}m"))
            #7thDragon##########""",
        "import_statement": "import pandas as pd",
        "comment_lines": [
            'exits.append(ExitCheckTuple(exit_type=ExitType.ROI))'
        ],
        "applicable": "2025.5- | ROI enrichement"
    }
]

def modify_file(file_info):

    print(f"")

    file_path = file_info["file_path"]
    backup_path = file_path + ".bak"

    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"File '{file_path}' not found.")
        return

    applicable = file_info.get("applicable", "N/A")
    print(f"FT versions applicable {applicable}")

    # Make a backup
    print(f"Creating backup for '{file_path}'...")
    shutil.copyfile(file_path, backup_path)

    # Read the content of the file
    with open(file_path, 'r') as file:
        content = file.read()

    # Add import if it doesn’t exist
    import_statement = file_info["import_statement"]
    if import_statement not in content:
        print(f"Adding missing import for '{file_path}'...")
        content = import_statement + "\n" + content
    else:
        print(f"Missing import for '{file_path}' already exist.")

    # Locate the function definition
    function_name = file_info["function_name"]
    function_pattern = rf"\s*def\s*{re.escape(function_name)}\("  # Function definition regex
    function_match = re.search(function_pattern, content, re.MULTILINE & re.IGNORECASE)

    if not function_match:
        print(f"Function '{function_name}' not found in '{file_path}'. Check the regex.")
        print(f"Rolling back, backup is the same as the initial file.")
        return

    # Find the body of the function
    function_body_pattern = rf"(?s)(?:\s*def\s*{function_name}\(.*?\).*?:)(.*?)(?=\n\s*def\s|\Z)"
    function_body_match = re.search(function_body_pattern, content, re.MULTILINE & re.IGNORECASE)

    if not function_body_match:
        print(f"Could not locate the body of function '{function_name}' in '{file_path}'.")
        print(f"Rolling back, backup is the same as the initial file.")                          
        return

    # Extract the function body
    function_body = function_body_match.group(0)
    body_start_index = function_body_match.start()
    body_end_index = function_body_match.end()

    # Check if the code_to_insert is already in the function body
    if file_info["code_to_insert"].strip() in function_body:
        print(f"Code to insert already exists in '{function_name}' in '{file_path}'. Skipping insertion.")
        print(f"Rolling back, backup is the same as the initial file.")
        return
        
    # Insert code after the specified line
    insert_after_line = file_info["insert_after_line"]
    after_line_regex = re.compile(rf"\s*{re.escape(insert_after_line)}.*$", re.MULTILINE)
    function_body, after_count = after_line_regex.subn(
        lambda match: match.group(0) + "\n" + file_info["code_to_insert"], function_body, count=1
    )

    if after_count == 0:
        print(f"Insertion point '{insert_after_line}' not found (case-insensitive) within '{function_name}' in '{file_path}'.")
        print(f"Rolling back, backup is the same as the initial file.")                                                                       
        return

    # Comment out specified lines in the function body
    comment_lines = file_info.get("comment_lines", [])
    for line in comment_lines:
        function_body = re.sub(rf"^(\s*)(.*{re.escape(line)})(.*$)", r"\1#\2\3", function_body, flags=re.MULTILINE)
    
    # Replace modified function body in the full content
    new_content = content[:body_start_index] + function_body + content[body_end_index:]

    # Write changes back to file
    with open(file_path, 'w') as file:
        file.write(new_content)

    print(f"Modifications to '{file_path}' are complete. Backup created at '{backup_path}'.")

print(r"_________   __  .__    ________                                          ")
print(r"\______  \_/  |_|  |__ \______ \____________     ____   ____   ____      ")
print(r"    /    /\   __\  |  \ |    |  \_  __ \__  \   / ___\ /  _ \ /    \     ")
print(r"   /    /  |  | |   Y  \|    `   \  | \// __ \_/ /_/  >  <_> )   |  \    ")
print(r"  /____/   |__| |___|  /_______  /__|  (____  /\___  / \____/|___|  /    ")
print(r"                     \/        \/           \//_____/             \/     ")
print(r"                                                                v1.4     ")
print(r"*** 1. Fix for Freqtrade/FreqAI - download data also for opened positions")
print(r"*** 2. Fix for slow interface advise_exit                                ")
print(r"*** 3. Enrich ROI (needs manual editing for different versions)          ")
print(r"*** Tested FT versions 2024.5 - 2025.5                                   ")

# Run modifications for each specified file
for file_info in file_modifications:
    modify_file(file_info)
