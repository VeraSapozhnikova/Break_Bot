import logging
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Create a bot instance
bot = telegram.Bot(token='6333040173:AAHeiZdftbgLXnGbf8xcJwSgpg_KomF-Yqc')

# Create an Updater with the bot instance
updater = Updater(bot.token, request_kwargs={'read_timeout': 10})

# Get the dispatcher to register handlers
dispatcher = updater.dispatcher

# Keyboard for bot responses
keyboard = [['/break'], ['/endbreak']]

# Dictionary to store the state of breaks
breaks = {}

# List to store the queue of users
queue = []

# Set to store registered operators
operators = set()

# Command handler for /start
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Привет! Я бот для управления перерывами. Нажми кнопку, чтобы начать перерыв.",
                             reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

# Command handler for /break
def break_handler(update, context):
    chat_id = update.effective_chat.id
    
    # Check if there is already an active break for this chat
    if chat_id in breaks:
        context.bot.send_message(chat_id=chat_id, text="У вас уже идет перерыв.")
        return
    
    # Determine the number of operators to send on break
    num_breaks = 4 if is_line_busy() else 3
    
    # Check if there are enough operators in the queue to send on break
    if len(queue) >= num_breaks:
        # Extract operators from the queue
        operators_on_break = [queue.pop(0) for _ in range(num_breaks)]
        
        # Send break start message to operators
        for operator in operators_on_break:
            context.bot.send_message(chat_id=operator, text="Перерыв начался.")
        
        # Add operator chats to the active breaks dictionary
        breaks.update({operator: num_breaks for operator in operators_on_break})
        
        context.bot.send_message(chat_id=chat_id, text=f"Перерыв начался. Вам на перерыве нужно быть {num_breaks} человек(а).")
    else:
        context.bot.send_message(chat_id=chat_id, text="Недостаточно операторов в очереди для отправки на перерыв.")

# Command handler for /endbreak
def end_break(update, context):
    chat_id = update.effective_chat.id
    
    # Check if there is an active break for this chat
    if chat_id not in breaks:
        context.bot.send_message(chat_id=chat_id, text="У вас нет активного перерыва.")
        return
    
    # Determine the number of operators on break
    num_breaks = breaks[chat_id]
    
    # Remove operator chats from the active breaks dictionary
    del breaks[chat_id]
    
    # Add operators back to the queue
    queue.extend([chat_id] * num_breaks)
    
    context.bot.send_message(chat_id=chat_id, text="Перерыв окончен.")

# Message handler
def message_handler(update, context):
    chat_id = update.effective_chat.id
    message_text = update.message.text
    
    if message_text == "#смена":
        # Check if the user is already in the operators set or queue
        if chat_id in operators:
            context.bot.send_message(chat_id=chat_id, text="Вы уже зарегистрированы и находитесь в очереди.")
        else:
            operators.add(chat_id)
            queue.append(chat_id)
            context.bot.send_message(chat_id=chat_id, text="Вы зарегистрированы и добавлены в очередь.")
    
    elif message_text == "#конец":
        if chat_id in operators:
            operators.remove(chat_id)
            if chat_id in queue:
                queue.remove(chat_id)
            context.bot.send_message(chat_id=chat_id, text="Вы вышли из очереди и завершили смену.")
        else:
            context.bot.send_message(chat_id=chat_id, text="Вы не зарегистрированы и не находитесь в очереди.")
    
    elif message_text.startswith("#перерыв"):
        # Check if the user is already in the queue
        if chat_id in queue:
            context.bot.send_message(chat_id=chat_id, text="Вы уже находитесь в очереди на перерыв.")
        else:
            # Split the message into the command and number of minutes
            command, minutes = message_text.split()
            
            # Check if the number of minutes is a valid integer
            if not minutes.isdigit():
                context.bot.send_message(chat_id=chat_id, text="Неверный формат команды. Используйте #перерыв <количество минут>.")
                return
            
            # Convert minutes to an integer
            minutes = int(minutes)
            
            # Add the user to the queue
            queue.append(chat_id)
            
            # Determine the number of operators in the queue
            num_operators = len(queue)
            
            # Determine the number of breaks happening simultaneously
            num_breaks = 4 if is_line_busy() else 3
            
            # Calculate the estimated wait time for the user
            wait_time = num_operators * minutes // num_breaks
            
            # Get the user's information (first name and username)
            user_info = update.effective_user
            user_name = user_info.first_name
            username = user_info.username
            
            # Compose the response message
            response_message = f"[По {num_breaks}] {user_name} (@{username}) добавлен(а) в очередь. " \
                               f"На данный момент в очереди {num_operators} оператора.\n" \
                               f"Ты сможешь пойти на перерыв примерно через {wait_time} мин."
            
            context.bot.send_message(chat_id=chat_id, text=response_message)
    
    elif message_text.startswith("#налинии"):
        # Remove the user from the queue if present
        if chat_id in queue:
            queue.remove(chat_id)
            context.bot.send_message(chat_id=chat_id, text="Вы удалены из очереди.")
        else:
            context.bot.send_message(chat_id=chat_id, text="Вы не находитесь в очереди на перерыв.")
    
    else:
        context.bot.send_message(chat_id=chat_id, text="Неизвестная команда.")

# Helper function to check line occupancy
def is_line_busy():
    total_operators = len(operators)  # Total number of operators
    busy_operators = len(queue)  # Number of operators in the queue
    
    occupancy_ratio = busy_operators / total_operators  # Ratio of operators in the queue to total operators
    
    if occupancy_ratio >= 0.7:
        return True  # Line is busy if 70% or more operators are busy
    else:
        return False

# Register command handlers
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

break_handler = CommandHandler('break', break_handler)
dispatcher.add_handler(break_handler)

end_break_handler = CommandHandler('endbreak', end_break)
dispatcher.add_handler(end_break_handler)

# Register message handler
message_handler = MessageHandler(Filters.text, message_handler)
dispatcher.add_handler(message_handler)

# Start the bot
updater.start_polling()
