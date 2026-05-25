import os
import telebot
import requests
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Tito is fully optimized and alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

USER_STATES = {}

def get_smart_prompt(user_name, mode):
    """صياغة التوجيهات لتجعل تيتو يصحح الكلمة بعينها بأسلوب تفاعلي رائع"""
    if mode == "Strict":
        return (
            f"You are Tito, a lively, encouraging, and highly interactive AI English Coach talking to {user_name}. "
            "Analyze the user's message. If there is ANY spelling, grammar, or vocabulary mistake: "
            "1. STOP the conversation immediately.\n"
            "2. Respond in a mix of English and Arabic with high energy, quoting their exact mistake. For example: "
            f"'Ooo {user_name}! I think you wanted to say \"how\" but you used \"hew\" which is wrong. 💡'\n"
            "3. Tell them strictly but cheerfully: 'هيا، أعد كتابة الجملة بشكل صحيح لأخبرك بالرد!'\n"
            "Do not answer their question until they fix it. If the message is 100% correct, reply naturally in simple English and ask a follow-up question."
        )
    else:
        # الوضع العادي
        return (
            f"You are Tito, a friendly AI English Coach talking to {user_name}. "
            "Respond naturally and beautifully to the user's text in English. "
            "At the very end of your message, if they made any mistake, add a friendly note in Arabic "
            "explaining exactly what word was wrong and how to fix it next time, starting with '💡 تلميح سريع:'."
        )

def ask_tito_brain(system_prompt, user_text):
    """الاتصال بمحرك ذكاء اصطناعي فائق السرعة ومستقر بدون حدود حظر"""
    try:
        # استخدام سيرفر نصي متطور ومفتوح ذو استجابة سريعة جداً لمنع الرسائل الصفراء
        url = "https://text.pollinations.ai/"
        full_payload = f"Instructions:\n{system_prompt}\n\nUser Input: {user_text}"
        response = requests.get(url + requests.utils.quote(full_payload), timeout=12)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = message.from_user.first_name or "My Friend"
    
    USER_STATES[user_id] = {
        "name": user_name,
        "mode": "Strict",  # جعلنا الوضع الصارم الذكي هو الافتراضي بناءً على طلبكِ
        "waiting_for_correction": False,
        "last_mistake": ""
    }
    
    welcome = (
        f"Ooo {user_name}! Welcome to Tito English Coach ⚡\n\n"
        "أنا تيتو، مدربك الذكي والتفاعلي كلياً. لقد قمت ببرمجتي لأصحح لك الكلمات بدقة بالغة!\n\n"
        "لقد قمت بتفعيل [الوضع الصارم التفاعلي 🔸] لكِ تلقائياً الآن.\n"
        "اكتبي لي أي شيء بالإنجليزية لنبدأ التحدي! 🔥"
    )
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['normal', 'strict'])
def change_mode(message):
    user_id = message.chat.id
    user_name = message.from_user.first_name or "My Friend"
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {"name": user_name, "mode": "Strict", "waiting_for_correction": False, "last_mistake": ""}
    
    mode_name = "Strict" if "strict" in message.text else "Normal"
    USER_STATES[user_id]["mode"] = mode_name
    USER_STATES[user_id]["waiting_for_correction"] = False
    bot.reply_to(message, f"🔄 تم التبديل إلى الوضع: {mode_name}")

@bot.message_handler(func=lambda message: True)
def handle_msg(message):
    user_id = message.chat.id
    user_text = message.text
    user_name = message.from_user.first_name or "My Friend"
    
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {"name": user_name, "mode": "Strict", "waiting_for_correction": False, "last_mistake": ""}
        
    state = USER_STATES[user_id]
    
    # التعامل الذكي مع إعادة المحاولة وقفل المحادثة حتى التصحيح
    if state["waiting_for_correction"]:
        check_prompt = (
            f"The user was asked to fix their previous broken English. They just wrote: '{user_text}'. "
            "Is this new text grammatically and textually 100% correct English now? Answer ONLY with 'YES' or 'NO'."
        )
        check_res = ask_tito_brain("Answer ONLY YES or NO", check_prompt)
        
        if check_res and "YES" in check_res.upper():
            state["waiting_for_correction"] = False
            bot.reply_to(message, f"Excellent, {state['name']}! ✨ الجملة الآن صحيحة 100%. دعنا نكمل المحادثة!")
            return
        else:
            bot.reply_to(message, f"❌ ما زال هناك خطأ يا {state['name']}. حاول مجدداً إعادة كتابتها بشكل سليم تماماً لأرد عليك!")
            return

    # جلب الرد التفاعلي من تيتو
    sys_instruction = get_smart_prompt(state["name"], state["mode"])
    ai_reply = ask_tito_brain(sys_instruction, user_text)
    
    if ai_reply:
        # إذا رصد تيتو خطأ وطلب إعادة الكتابة
        if state["mode"] == "Strict" and ("أعد" in ai_reply or "rewrite" in ai_reply.lower() or "correct" in ai_reply.lower()):
            state["waiting_for_correction"] = True
            state["last_mistake"] = user_text
            
        bot.reply_to(message, ai_reply)
    else:
        # رد بديل ذكي وسريع في حال حدوث ضغط على السيرفر لتفادي العبارة الصفراء
        bot.reply_to(message, f"Ooo {state['name']}! استقبلت رسالتك لكن الاتصال سريع جداً، أعد إرسالها الآن وسأجيبك فوراً!")

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    bot.polling(none_stop=True)
