import os
import telebot
import google.generativeai as genai

# 1. جلب المفاتيح السرية من بيئة التشغيل بأمان
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# إعداد البوت والذكاء الاصطناعي
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# استخدام نموذج جيمني السريع والمجاني
model = genai.GenerativeModel('gemini-1.5-flash')

# ذاكرة مؤقتة بسيطة لحفظ وضع المستخدم ومستواه (بديل مؤقت لقاعدة البيانات لتبسيط التشغيل على الهاتف)
# في تطبيق حقيقي يتم حفظها في ملف أو قاعدة بيانات، لكن هذه الذاكرة تكفي ما دام البوت يعمل.
USER_STATES = {}

# التوجيهات الأساسية للبوت حسب الوضع
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
    else: # الوضع العادي
        return f"""
        You are a friendly and encouraging AI English Coach. The user level is {level}.
        Respond naturally in English to their message.
        At the end of your response, if they made any mistake, add a gentle note:
        "💡 Note: [Explain the mistake and correction briefly in Arabic]"
        Keep the conversation flowing and friendly!
        """

# أمر البداية /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    # إعداد افتراضي للمستخدم الجديد
    USER_STATES[user_id] = {
        "level": "A2", 
        "mode": "Normal", 
        "waiting_for_correction": False,
        "last_mistake": ""
    }
    
    welcome_text = (
        "Welcome to your AI English Coach! ⚡\n\n"
        "أنا مدربك الشخصي لتعليم الإنجليزية بالمحادثة.\n"
        "المستوى الافتراضي الآن هو: A2 (يمكنك تعديله لاحقاً).\n\n"
        "التحكم بالأوضاع:\n"
        "🔹 /normal - الوضع العادي (محادثة مرنة مع تصحيح لطيف)\n"
        "🔸 /strict - الوضع الصارم (لن ننتقل لرد جديد حتى تصحح خطأك)\n\n"
        "ابدأ بالكتابة معي الآن بالإنجليزية!"
    )
    bot.reply_to(message, welcome_text)

# التبديل إلى الوضع العادي
@bot.message_handler(commands=['normal'])
def set_normal(message):
    user_id = message.chat.id
    if user_id not in USER_STATES: send_welcome(message)
    USER_STATES[user_id]["mode"] = "Normal"
    USER_STATES[user_id]["waiting_for_correction"] = False
    bot.reply_to(message, "🔄 تم التبديل إلى: الوضع العادي (Normal Mode).")

# Tالتبديل إلى الوضع الصارم
@bot.message_handler(commands=['strict'])
def set_strict(message):
    user_id = message.chat.id
    if user_id not in USER_STATES: send_welcome(message)
    USER_STATES[user_id]["mode"] = "Strict"
    bot.reply_to(message, "🔒 تم التبديل إلى: الوضع الصارم (Strict Mode). انتبه لقواعدك!")

# معالجة الرسائل والمحادثة
@bot.message_handler(func=lambda message: True)
def handle_conversation(message):
    user_id = message.chat.id
    user_text = message.text
    
    # التأكد من وجود بيانات للمستخدم
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {"level": "A2", "mode": "Normal", "waiting_for_correction": False, "last_mistake": ""}
        
    state = USER_STATES[user_id]
    
    # إذا كنا ننتظر من المستخدم تصحيح جملة في الوضع الصارم
    if state["waiting_for_correction"]:
        check_prompt = f"The user had to correct: '{state['last_mistake']}'. They wrote: '{user_text}'. Did they write it correctly now? Answer with only 'YES' or 'NO'."
        check_response = model.generate_content(check_prompt).text.strip()
        
        if "YES" in check_response.upper():
            state["waiting_for_correction"] = False
            bot.reply_to(message, "Excellent! Corrected. ✨ Let's continue our conversation.")
            # الآن نترك البرنامج يكمل ليولد رداً عادياً للمحادثة
        else:
            bot.reply_to(message, f"❌ ما زال هناك خطأ. حاول مجدداً إعادة كتابة الجملة بشكل صحيح:\n{state['last_mistake']}")
            return

    # صياغة الطلب للذكاء الاصطناعي بناء على الوضع والمستوى
    prompt = f"System Instruction: {get_system_prompt(state['mode'], state['level'])}\nUser says: {user_text}"
    
    try:
        # إرسال النص لـ Gemini
        ai_response = model.generate_content(prompt).text
        
        # إذا كنا في الوضع الصارم والبوت وجد خطأ (سنعرف هذا برمجياً إذا طلب البوت إعادة الكتابة)
        if state["mode"] == "Strict" and ("rewrite" in ai_response.lower() or "أعد كتابة" in ai_response):
            state["waiting_for_correction"] = True
            state["last_mistake"] = user_text
            
        bot.reply_to(message, ai_response)
        
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء الاتصال بالخادم الذكي، أعد المحاولة لاحقاً.")
        print(e)

# تشغيل البوت
bot.polling(none_stop=True)
