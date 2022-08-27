import json
import logging
import time

from aiogram import Bot, Dispatcher, executor, types
from utils.mq_skel_ import MqSkel, mqtt_que
from aiogram.utils import exceptions

API_TOKEN = '1891409689:AAHSrcUzUveXwpLo0irypdDmugQ5E9ZrotQ'
send_sig = False
pending = []
# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")


@dp.message_handler(regexp='(^cat[s]?$|puss)')
async def cats(message: types.Message):
    with open('data/cats.jpg', 'rb') as photo:
        '''
        # Old fashioned way:
        await bot.send_photo(
            message.chat.id,
            photo,
            caption='Cats are here 😺',
            reply_to_message_id=message.message_id,
        )
        '''

        await message.reply('I like cats ... in a gross way.')


@dp.message_handler(commands=['signals'])
async def echo(message: types.Message):
    # old style:
    # await bot.send_message(message.chat.id, message.text)
    send_sig = True
    await message.reply('Monitoring for signals ...')
    while send_sig:

        if len(mqtt_que.outgoing_msgs):
            m = mqtt_que.outgoing_msgs.pop()
            m = json.loads(m)
            if float(m['Live_score']) >= 30 and float(m['Mean_Adx']) >= 30:
                try:
                    await message.answer(m)
                except exceptions.RetryAfter:
                    mqtt_que.append(m)
                time.sleep(0.5)


if __name__ == '__main__':
    mqs = MqSkel()
    mqs.mqStart('tgbot')
    executor.start_polling(dp, skip_updates=True)
