import os
import logging
import asyncio
from telethon import Button, TelegramClient, events
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, ChannelParticipantsAdmins
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - [%(levelname)s] - %(message)s")
LOGGER = logging.getLogger(__name__)

# Bot credentials from environment variables
api_id = int(os.environ.get("APP_ID", "YOUR_API_ID")) #https://my.telegram.org/
api_hash = os.environ.get("API_HASH", "YOUR_API_HASH") #https://my.telegram.org/
bot_token = os.environ.get("TOKEN", "YOUR_BOT_TOKEN")

# Initialize Telegram client
client = TelegramClient("client", api_id, api_hash).start(bot_token=bot_token)

# List to keep track of active spam chats
spam_chats = []

async def is_user_admin(chat_id, user_id):
    """Helper function to check if a user is an admin."""
    try:
        participant = await client(GetParticipantRequest(chat_id, user_id))
        return isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except UserNotParticipantError:
        return False

def split_message(message, max_length=4096):
    """
    Splits a long message into multiple smaller messages each within the Telegram limit.
    """
    # Split the message into parts that fit within the max_length
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

@client.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    """Start command handler."""
    if not event.is_private:
        return await event.respond("Hello! This command is meant for private messages. Please send it to me directly!")

    welcome_message = (
        "👋 **Welcome to Majk Mention Bot!**\n\n"
        "I'm here to help you manage your Telegram groups more efficiently.\n"
        "With a few simple commands, you can easily mention all members or just the admins in your group, making announcements a breeze! 📢\n\n"
        "Here are some things you can do with me:\n"
        "🔹 **@everyone** - Mention all members in the group.\n"
        "🔹 **@admins** - Mention all admins in the group.\n"
        "🔹 **/cancel** - Stop any ongoing mention process.\n\n"
        "Ready to get started? Add me to your group now!\n"
    )

    await event.reply(
        welcome_message,
        link_preview=False,
        buttons=[
            [Button.url("Add me to your group", "https://t.me/mentioneer_mention_bot?startgroup=true")],
            [Button.url("Owner", "https://t.me/majikRLS")]
        ]
    )

@client.on(events.NewMessage(pattern=r"^/help(@mentioneer_mention_bot)?$"))
async def help(event):
    """Help command handler."""
    chat_id = event.chat_id
    helptext = (
        "📚 **Help Menu** 📚\n\n"
        "Here are the commands you can use with this bot:\n\n"
        "🔹 **@everyone** - Mention all members in the group.\n"
        "🔹 **@admins** - Mention all admins in the group.\n"
        "🔹 **/cancel** - Cancel the ongoing mention process.\n\n"
        "If you need more assistance or have any questions, feel free to contact [Majk](https://t.me/majikRLS).\n"
    )
    await event.reply(helptext, link_preview=False)

@client.on(events.NewMessage(pattern="^/owner$"))
async def owner(event):
    """Owner command handler."""
    if not event.is_private:
        return await event.respond("Use this command in PM")

    owner_description = (
        "👋 **Meet Majk**\n\n"
        "Majk is the creator and owner of this bot. With a passion for technology and automation, "
        "Majk has developed this bot to help streamline group management on Telegram. "
        "He is always looking to improve the bot's functionality and is open to suggestions and feedback.\n\n"
        "📬 **Contact Majk**: [Majk's Telegram](https://t.me/majikRLS)\n\n"
        "Feel free to reach out to him if you have any questions, suggestions, or just want to say hi!"
    )

    await event.reply(owner_description, link_preview=False)

@client.on(events.NewMessage(pattern=r"@everyone(?: |$)(.*)"))
async def mentionall(event):
    """Command to mention all members."""
    chat_id = event.chat_id
    
    if event.is_private:
        return await event.respond("This command can only be used in groups or channels.")

    if not await is_user_admin(chat_id, event.sender_id):
        return await event.respond("Only admins can use this command.")

    msg = event.pattern_match.group(1) or ""
    if event.is_reply and not msg:
        msg = await event.get_reply_message() or ""

    spam_chats.append(chat_id)
    mentions = ""
    async for user in client.iter_participants(chat_id):
        if chat_id not in spam_chats:
            break
        if user.bot:  # Skip bots
            continue
        mentions += f"[{user.first_name}](tg://user?id={user.id}) "

    if mentions:
        # Split the message if it's too long
        for part in split_message(f"{mentions}\n\n{msg}" if msg else mentions):
            await client.send_message(chat_id, part)

    try:
        spam_chats.remove(chat_id)
    except ValueError:
        pass

@client.on(events.NewMessage(pattern=r"^/(admins|admin)|@(admin|admins)(?: |$)(.*)"))
async def mention_admins(event):
    """Command to mention all admins."""
    chat_id = event.chat_id

    if event.is_private:
        return await event.respond("This command can only be used in groups or channels.")

    if not await is_user_admin(chat_id, event.sender_id):
        return await event.respond("Only admins can mention.")

    msg = event.pattern_match.group(3) or ""
    if event.is_reply and not msg:
        msg = await event.get_reply_message() or ""

    spam_chats.append(chat_id)
    mentions = ""
    async for user in client.iter_participants(chat_id, filter=ChannelParticipantsAdmins):
        if chat_id not in spam_chats:
            break
        if user.bot:  # Skip bots
            continue
        mentions += f"[{user.first_name}](tg://user?id={user.id}) "

    if mentions:
        # Split the message if it's too long
        for part in split_message(f"{mentions}\n\n{msg}" if msg else mentions):
            await client.send_message(chat_id, part)

    try:
        spam_chats.remove(chat_id)
    except ValueError:
        pass

@client.on(events.NewMessage(pattern="^/cancel$"))
async def cancel_spam(event):
    """Command to cancel ongoing spam process."""
    if event.chat_id not in spam_chats:
        return await event.respond("There is no ongoing process.")
    spam_chats.remove(event.chat_id)
    await event.respond("Stopped.")

print("Bot is running.")
client.run_until_disconnected()
