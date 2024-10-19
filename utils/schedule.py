# Do not remove credits given in this repo.
# Importing this repo instead of forking is strictly prohibited.
# Kindly fork and edit as you wish. Feel free to give credits to the developer.

import logging
import json
from pyrogram import filters
from datetime import datetime
from aiohttp import ClientSession
from pytz import timezone
from utils.image import get_random_image
from utils.main import app, MAIN_CHANNEL, TIMEZONE, SUDO_USERS

logger = logging.getLogger(__name__)

# Global variables
current_message_id, current_sticker_id = None, None

async def fetch_schedule():
    """Fetch today's anime schedule and format the message."""
    try:
        async with ClientSession() as ses:
            schedule_url = f"https://subsplease.org/api/?f=schedule&h=true&tz={TIMEZONE}"
            res = await ses.get(schedule_url)
            if res.status != 200:
                logger.error(f"Failed to fetch schedule: {await res.text()}")
                return None

            aniContent = json.loads(await res.text()).get("schedule")
            if not aniContent:
                logger.warning("No schedule content found.")
                return None

            today_date = datetime.now(timezone(TIMEZONE))
            formatted_date = today_date.strftime("%A (%d-%m-%Y)")
            last_updated_time = today_date.strftime("%I:%M %p")

            # Calculate dynamic UTC offset
            utc_offset = today_date.utcoffset()
            offset_hours = utc_offset.total_seconds() // 3600
            offset_minutes = (utc_offset.total_seconds() % 3600) // 60
            offset_sign = '+' if offset_hours >= 0 else '-'
            offset_str = f"(UTC {offset_sign}{abs(int(offset_hours)):02d}:{abs(int(offset_minutes)):02d})"

            sch_list = "\n".join(
                f"[{datetime.strptime(i['time'], '%H:%M').strftime('%I:%M %p')}] - 📌 **{i['title']}** {'✅' if i['aired'] else ''}\n"
                for i in aniContent
            )

            text = (f"📅 **Schedule for {formatted_date}**\n\n{sch_list}\n"
                    f"🕒 __Last Updated:__ {last_updated_time} {offset_str}")
            return text
    except Exception as e:
        logger.error(f"Error fetching schedule: {str(e)}")
        return None

async def send_schedule() -> None:
    """Send the schedule post at 12:15 AM."""
    global current_message_id, current_sticker_id
    try:
        IMAGE_PATH = get_random_image()
        if IMAGE_PATH is None:
            return

        text = await fetch_schedule()
        if text is None:
            return

        # Delete the old message if it exists
        if current_message_id:
            await app.delete_messages(chat_id=MAIN_CHANNEL, message_ids=current_message_id)
        if current_sticker_id:
            await app.delete_messages(chat_id=MAIN_CHANNEL, message_ids=current_sticker_id)

        # Send the new message
        message = await app.send_photo(
            chat_id=MAIN_CHANNEL,
            photo=IMAGE_PATH,
            caption=text
        )
        await (await message.pin()).delete()
        current_message_id = message.id  # Save the message ID

        # Send the sticker and save its ID
        sticker_message = await app.send_sticker(MAIN_CHANNEL, "CAACAgUAAxkBAAELS61nD7ue7YFV0_lwebKl02ni82-nHAACFgADQ3PJEoHYvyG2hlXcNgQ")
        current_sticker_id = sticker_message.id

        logger.info("Schedule post sent successfully!")

    except Exception as err:
        logger.error(f"Error sending schedule: {str(err)}")

async def update_schedule() -> None:
    """Update the schedule post every 15 minutes."""
    global current_message_id
    try:
        if current_message_id is None:
            return  # No message to update

        text = await fetch_schedule()
        if text is None:
            return

        # Update the existing message
        await app.edit_message_caption(
            chat_id=MAIN_CHANNEL,
            message_id=current_message_id,
            caption=text
        )

        logger.info("Schedule post updated successfully!")

    except Exception as e:
        logger.error(f"Failed to update schedule: {str(e)}")

# Define the set_timezone command
@app.on_message(filters.command('set_timezone') & filters.private)
async def set_timezone(client, message):
    """Set the timezone for schedule fetching."""
    if message.from_user.id not in SUDO_USERS:
        await message.reply("🚫 **Access Denied:** You don't have permission to use this command.")
        return

    # Check if a new timezone was provided
    new_timezone = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if new_timezone:
        global TIMEZONE
        TIMEZONE = new_timezone
        await message.reply(f"🌍 **Timezone updated to:** {TIMEZONE}")
    else:
        await message.reply("❌ **Please provide a valid timezone.**")
