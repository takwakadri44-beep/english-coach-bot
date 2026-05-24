import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# إعداد خادم ويب وهمي لمنصة Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # جلب المنفذ الذي تحدده المنصة تلقائياً أو استخدام 8080 كافتراضي
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 1. جلب المفاتيح السرية
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

USER_STATES = {}

def get_system_prompt(mode, level):
    if mode == "Strict":
        return f"""
        You are an expert, strict AI English Coach. The user level is {level}.
        Analyze the user's input.
        1. If there is ANY mistake (Grammar, Vocabulary, Tenses, Natural Expressions):
           - STOP the conversation.
           - Explain the mistake clearly in Arabic so they learn.
           - Give the correct formula.
           - Tell them: "Now, rewrite the sentence correctly to continue."
        2. If the sentence is 100% correct:
           - Reply naturally in English (simple words matching level {level}).
           - Ask an engaging follow-up question.
        Do NOT speak any language other than English except for the error explanation.
        """
    else:
        return f"""
        You are a friendly and encouraging AI English Coach. The user level is {level}.
        Respond naturally in English to their message.
        At the end of your response, if they made any mistake, add a gentle note:
        "💡 Note: [Explain the mistake and correction briefly in Arabic]"
        Keep the conversation flowing and friendly!
        """

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    USER_STATES[user_id] = {
        "level": "A2", 
        "mode": "Normal", 
        "waiting_for_correction": False,
        "last_mistake": ""
    }
    
    welcome_text = (
        "Welcome to your AI English Coach! ⚡\n\n"
        "أنا مدربك الشخصي لتعليم الإنجليزية بالمحادثة.\n"
        "المستوى الافتراضي الآن هو: A2.\n\n"
        "التحكم بالأوضاع:\n"
        "🔹 /normal - الوضع العادي\n"
        "🔸 /strict - الوضع الصارم\n\n"
        "ابدأ بالكتابة معي الآن بالإنجليزية!"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['normal'])
def set_normal(message):
    user_id = message.chat.id
    if user_id not in USER_STATES: send_welcome(message)
    USER_STATES[user_id]["mode"] = "Normal"
    USER_STATES[user_id]["waiting_for_correction"] = False
    bot.reply_to(message, "🔄 تم التبديل إلى: الوضع العادي (Normal Mode).")

@bot.message_handler(commands=['strict'])
def set_strict(message):
    user_id = message.chat.id
    if user_id not in USER_STATES: send_welcome(message)
    USER_STATES[user_id]["mode"] = "Strict"
    bot.reply_to(message, "🔒 تم التبديل إلى: الوضع الصارم (Strict Mode). انتبه لقواعدك!")

@bot.message_handler(func=lambda message: True)
def handle_conversation(message):
    user_id = message.chat.id
    user_text = message.text
    
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {"level": "A2", "mode": "Normal", "waiting_for_correction": False, "last_mistake": ""}
        
    state = USER_STATES[user_id]
    
    if state["waiting_for_correction"]:
        check_prompt = f"The user had to correct: '{state['last_mistake']}'. They wrote: '{user_text}'. Did they write it correctly now? Answer with only 'YES' or 'NO'."
        check_response = model.generate_content(check_prompt).text.strip()
        
        if "YES" in check_response.upper():
            state["waiting_for_correction"] = False
            bot.reply_to(message, "Excellent! Corrected. ✨ Let's continue our conversation.")
        else:
            bot.reply_to(message, f"❌ ما زال هناك خطأ. حاول مجدداً إعادة كتابة الجملة بشكل صحيح:\n{state['last_mistake']}")
            return

    prompt = f"System Instruction: {get_system_prompt(state['mode'], state['level'])}\nUser says: {user_text}"
    
    try:
        ai_response = model.generate_content(prompt).text
        
        if state["mode"] == "Strict" and ("rewrite" in ai_response.lower() or "أعد كتابة" in ai_response):
            state["waiting_for_correction"] = True
            state["last_mistake"] = user_text
            
        bot.reply_to(message, ai_response)
        
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء الاتصال بالخادم الذكي، أعد المحاولة لاحقاً.")
        print(e)

# تشغيل خادم الويب والبوت معاً في مسارين منفصلين
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    bot.polling(none_stop=True)
