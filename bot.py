import os
import telebot
import requests
from flask import Flask
from threading import Thread

# 1. إعداد خادم ويب مصغر لمنصة Render لتفادي الـ Timeout
app = Flask('')

@app.route('/')
def home():
    return "Your Tito Bot is Alive and Running Natively!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. جلب توكن تيليجرام بأمان
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

USER_STATES = {}

def get_system_prompt(mode, level):
    if mode == "Strict":
        return f"You are an expert, strict AI English Coach. The user level is {level}. Analyze the input. If there's any grammar, vocabulary, or expression mistake, STOP the conversation, explain the mistake clearly in Arabic, and ask them to rewrite it correctly. If correct, reply naturally in simple English matching their level and ask a question. Respond directly without meta-commentary."
    else:
        return f"You are a friendly and encouraging AI English Coach. The user level is {level}. Respond naturally in English, and if they make any mistake, add a very short note in Arabic at the very end of your message starting with '💡 Note:'."

def ask_free_llm(system_prompt, user_text):
    """الاتصال بمحرك ذكاء اصطناعي حر ومفتوح لا يفرض حظراً جغرافياً على السيرفرات المجانية"""
    try:
        url = "https://text.pollinations.ai/"
        prompt = f"System Instruction: {system_prompt}\nUser Text: {user_text}"
        response = requests.get(url + requests.utils.quote(prompt), timeout=15)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    USER_STATES[user_id] = {"level": "A2", "mode": "Normal", "waiting_for_correction": False, "last_mistake": ""}
    welcome = (
        "Welcome to your AI English Coach! ⚡\n\n"
        "أنا Tito، مدربك الشخصي لتعليم الإنجليزية بالمحادثة.\n\n"
        "🔹 /normal - الوضع العادي\n"
        "🔸 /strict - الوضع الصارم\n\n"
        "ابدأ بالكتابة معي الآن بالإنجليزية وسأقوم بتصحيحك فوراً!"
    )
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['normal', 'strict'])
def change_mode(message):
    user_id = message.chat.id
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {"level": "A2", "mode": "Normal", "waiting_for_correction": False, "last_mistake": ""}
    
    mode_name = "Strict" if "strict" in message.text else "Normal"
    USER_STATES[user_id]["mode"] = mode_name
    USER_STATES[user_id]["waiting_for_correction"] = False
    bot.reply_to(message, f"🔄 تم التبديل إلى الوضع: {mode_name}")

@bot.message_handler(func=lambda message: True)
def handle_msg(message):
    user_id = message.chat.id
    user_text = message.text
    
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {"level": "A2", "mode": "Normal", "waiting_for_correction": False, "last_mistake": ""}
        
    state = USER_STATES[user_id]
    sys_instruction = get_system_prompt(state["mode"], state["level"])
    
    # التعامل مع إعادة المحاولة في الوضع الصارم
    if state["waiting_for_correction"]:
        check_prompt = f"The user had to correct their mistake. They just wrote: '{user_text}'. Is it grammatically 100% correct now? Answer ONLY with 'YES' or 'NO'."
        check_res = ask_free_llm("Answer ONLY YES or NO", check_prompt)
        
        if check_res and "YES" in check_res.upper():
            state["waiting_for_correction"] = False
            bot.reply_to(message, "Excellent! Corrected. ✨ Let's continue.")
            return
        else:
            bot.reply_to(message, "❌ ما زال هناك خطأ قواعدي. حاول مجدداً إعادة كتابة الجملة بشكل صحيح.")
            return

    # جلب الرد الذكي من المحرك الحر
    ai_reply = ask_free_llm(sys_instruction, user_text)
    
    if ai_reply:
        if state["mode"] == "Strict" and ("rewrite" in ai_reply.lower() or "أعد كتابة" in ai_reply):
            state["waiting_for_correction"] = True
            state["last_mistake"] = user_text
            
        bot.reply_to(message, ai_reply)
    else:
        bot.reply_to(message, "⚠️ عذراً، المحرك مشغول حالياً. جرب إرسال الرسالة مرة أخرى.")

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    bot.polling(none_stop=True)

