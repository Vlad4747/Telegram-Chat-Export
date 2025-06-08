import re
from pyrogram import Client
from pyrogram.enums import ChatType, ChatMemberStatus
from dotenv import load_dotenv
import os
import html
import cv2
import uuid

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHAT_ID = os.getenv("CHAT_ID")
MESSAGE_LIMIT = int(os.getenv("MESSAGE_LIMIT", 20))

os.makedirs("downloads", exist_ok=True)
os.makedirs("downloaded_emojis", exist_ok=True)

def linkify(text):
    url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
    return re.sub(url_pattern, r'<a href="\g<0>" target="_blank">\g<0></a>', text)

def check_can_send_messages(app, chat_id):
    try:
        chat = app.get_chat(chat_id)
        
        if chat.type == ChatType.PRIVATE:
            try:
                return True, "Личные сообщения доступны"
            except Exception as e:
                if "blocked" in str(e).lower():
                    return False, "Вы заблокированы пользователем"
                return False, f"Ошибка доступа к ЛС: {str(e)}"
        
        elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                member = app.get_chat_member(chat_id, "me")
                
                if member.status == ChatMemberStatus.BANNED:
                    return False, "Вы забанены в этой группе"
                
                if member.status == ChatMemberStatus.LEFT:
                    return False, "Вы не состоите в этой группе"
                
                if member.status == ChatMemberStatus.RESTRICTED:
                    if hasattr(member, 'can_send_messages') and not member.can_send_messages:
                        return False, "У вас мут в этой группе"
                    
                if hasattr(chat, 'permissions'):
                    if not chat.permissions.can_send_messages:
                        return False, "Отправка сообщений запрещена в этой группе"
                
                return True, "Отправка сообщений разрешена"
                
            except Exception as e:
                return False, f"Ошибка проверки группы: {str(e)}"
        
        elif chat.type == ChatType.CHANNEL:
            try:
                member = app.get_chat_member(chat_id, "me")
                
                if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                    if hasattr(member, 'can_post_messages') and member.can_post_messages:
                        return True, "Вы администратор с правами на публикацию"
                    elif member.status == ChatMemberStatus.OWNER:
                        return True, "Вы владелец канала"
                    else:
                        return False, "У вас нет прав на публикацию в канале"
                else:
                    return False, "Только администраторы могут писать в канале"
                    
            except Exception as e:
                return False, f"Ошибка проверки канала: {str(e)}"
        
        else:
            return False, "Неизвестный тип чата"
            
    except Exception as e:
        return False, f"Общая ошибка: {str(e)}"

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Chat</title>
    <style>
        @font-face {{
            font-family: 'Roboto-Regular-Emoji';
            src: url('Roboto-Regular-Emoji.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        body {{
            background-image: url('wp1.jpeg');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        a {{
            color: #00B7EB;
            text-decoration: underline;
        }}
        .chat-container {{
            max-width: 800px;
            margin: 0 auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .chat-header {{
            background-color: #212121;
            padding: 10px;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 10px;
            border-bottom: 1px solid #333;
        }}
        .chat-icon {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            object-fit: cover;
        }}
        .messages {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            scrollbar-width: none;
        }}
        .messages::-webkit-scrollbar {{
            display: none;
        }}
        .message {{
            max-width: 70%;
            padding: 10px;
            border-radius: 10px;
            line-height: 1.4;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }}
        .message-content {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .message-info {{
            font-size: 12px;
            color: #aaaaaa;
            text-align: right;
            margin-top: 5px;
            margin-left: 8px;
        }}
        .message-details {{
            display: flex;
            flex-direction: column;
        }}
        .message-time {{
            margin-left: 8px;
        }}
        .sent {{
            background-color: #005c4b;
            margin-left: auto;
            margin-right: 10px;
        }}
        .received {{
            background-color: #2a2a2a;
            margin-right: auto;
            margin-left: 10px;
        }}
        .message-time {{
            font-size: 12px;
            color: #aaaaaa;
            text-align: right;
            margin-top: 5px;
            padding: 0 10px;
        }}
        .reply-preview {{
            background-color: rgba(255, 255, 255, 0.1);
            border-left: 3px solid #4a90e2;
            padding: 8px;
            margin-bottom: 8px;
            border-radius: 5px;
            font-size: 14px;
            color: #cccccc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .forwarded-from {{
            background-color: rgba(255, 255, 255, 0.1);
            border-left: 3px solid #4a90e2;
            padding: 8px;
            margin-bottom: 8px;
            border-radius: 5px;
            font-size: 14px;
            color: #cccccc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .message-photo {{
            max-width: 100%;
            border-radius: 10px;
            margin-bottom: 8px;
            display: block;
        }}
        .inline-keyboard {{
            display: grid;
            gap: 5px;
            margin-top: 10px;
            padding: 0 1px;
        }}
        .inline-keyboard > div {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
            gap: 5px;
        }}
        .inline-button {{
            background-color: #3f3f3f;
            padding: 8px 12px;
            border-radius: 5px;
            text-align: center;
            cursor: pointer;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .reply-keyboard {{
            display: grid;
            gap: 5px;
            padding: 10px;
            background-color: #212121;
            border-top: 1px solid #333;
            box-sizing: border-box;
            width: 100%;
        }}
        .reply-keyboard > div {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
            gap: 5px;
        }}
        .reply-button {{
            background-color: #3f3f3f;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            cursor: pointer;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .input-container {{
            display: flex;
            align-items: center;
            padding: 10px;
            background-color: #212121;
            border-top: 1px solid #333;
            width: 100%;
            box-sizing: border-box;
        }}
        .centered-text {{
            display: flex;
            justify-content: center;
        }}
        .input-container > div {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }}
        .emoji-icon {{
            flex: 0 0 auto;
            font-family: 'Roboto-Regular-Emoji';
        }}
        .message-placeholder {{
            flex: 1;
            background-color: #2a2a2a;
            padding: 8px 12px;
            border-radius: 20px;
            text-align: left;
            color: #aaaaaa;
        }}
        .right-icons {{
            flex: 0 0 auto;
            display: flex;
            gap: 10px;
        }}
        .right-icons span {{
            font-family: 'Roboto-Regular-Emoji';
        }}
        .reactions {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .reaction {{
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 2px 5px;
            margin: 0 2px;
        }}
    </style>
</head>
<body>
    <div class="chat-container">
        {chat_header}
        <div class="messages">
            {messages}
        </div>
        {input_container}
        {reply_keyboard}
    </div>
</body>
</html>
"""

app = Client(
    name="usr",
    api_id=API_ID,
    api_hash=API_HASH,
)

emoji_img = {
    "❤": "imgs/emoji_7.webp_0_2.png",
    "❤‍🔥": "imgs/emoji_7.webp_12_2.png"
}

with app:
    chat_title = "Chat"
    chat_icon_path = "downloads/chat_icon.jpg"
    messages_html = ""
    reply_keyboard_html = ""
    chat_members_count_html = ""
    can_send_messages = False

    try:
        chat = app.get_chat(CHAT_ID)
        chat_title = chat.title or chat.first_name or "Chat"

        can_send_messages = check_can_send_messages(app, CHAT_ID)

        if chat.photo:
            try:
                chat_icon_path = app.download_media(
                    chat.photo.big_file_id,
                    file_name="downloads/chat_icon.jpg"
                )
            except Exception:
                pass

        if chat.type in ("group", "supergroup", "channel"):
            try:
                member_count = app.get_chat_members_count(CHAT_ID)
                chat_members_count_html = f'<div style="font-size: 12px; display: block;">{member_count} подписчиков</div>'
            except Exception:
                chat_members_count_html = ""

        header_html = f"""
            <div class="chat-header">
                <span>←</span>
                <img src="downloads/chat_icon.jpg" class="chat-icon" onerror="this.style.display='none'">
                <span>{html.escape(chat_title)}</span>
                {chat_members_count_html}
            </div>
        """

        input_container_html = """
            <div class="input-container">
                <div>
                    <span class="emoji-icon">😊</span>
                    <span class="message-placeholder">Сообщение</span>
                    <div class="right-icons">
                        <span>📎</span>
                        <span>🎤</span>
                    </div>
                </div>
            </div>
        """
        if not can_send_messages:
            input_container_html = """
                <div class="input-container">
                    <div style="width: 100%; display: flex; justify-content: center;">
                        <div class="centered-text" style="font-size: larger; color: #00B7EB;">ВКЛ. ЗВУК</div>
                    </div>
                </div>
            """

        for m in reversed(list(app.get_chat_history(CHAT_ID, limit=MESSAGE_LIMIT))):
            text = linkify(html.escape(m.caption or m.text or "")).replace('\n', '<br>')
            message_class = "sent" if m.from_user and m.from_user.is_self else "received"
            time_str = m.date.strftime("%H:%M")

            forwarded_from_html = ""
            if m.forward_from or m.forward_from_chat:
                if m.forward_from:
                    forward_name = m.forward_from.first_name or "Unknown User"
                elif m.forward_from_chat:
                    forward_name = m.forward_from_chat.title or "Unknown Chat"
                forwarded_from_html = f'<div class="forwarded-from">Переслано от {html.escape(forward_name)}</div>'

            photo_html = ""
            if m.photo:
                try:
                    photo_path = app.download_media(
                        m.photo,
                        file_name=f"downloads/photo_{m.id}.jpg"
                    )
                    photo_html = f'<img src="downloads/photo_{m.id}.jpg" class="message-photo">'
                except Exception:
                    photo_html = '<div>Не удалось загрузить фото</div>'
            elif m.video:
                try:
                    video_path = app.download_media(
                        m.video,
                        file_name=f"downloads/video_{m.id}.mp4"
                    )
                    video = cv2.VideoCapture(video_path)
                    success, image = video.read()
                    if success:
                        frame_path = f"downloads/video_frame_{m.id}.jpg"
                        cv2.imwrite(frame_path, image)
                        photo_html = f'<img src="{frame_path}" class="message-photo">'
                    else:
                        photo_html = '<div>Не удалось извлечь кадр из видео</div>'
                    video.release()
                    os.remove(video_path)
                except Exception as e:
                    print(f"Error processing video: {e}")
                    photo_html = '<div>Не удалось загрузить видео</div>'

            reply_preview_html = ""
            if m.reply_to_message_id:
                try:
                    replied_msg = app.get_messages(CHAT_ID, m.reply_to_message_id)
                    replied_text = replied_msg.caption or replied_msg.text or "Нет текста"
                    first_line = html.escape(replied_text.split('\n')[0])
                    reply_preview_html = f'<div class="reply-preview">{first_line}</div>'
                except Exception:
                    reply_preview_html = '<div class="reply-preview">Не удалось загрузить сообщение</div>'

            inline_keyboard_html = ""
            if m.reply_markup and hasattr(m.reply_markup, 'inline_keyboard'):
                inline_keyboard_html += '<div class="inline-keyboard">'
                for row in m.reply_markup.inline_keyboard:
                    inline_keyboard_html += '<div>'
                    for button in row:
                        button_text = html.escape(button.text)
                        inline_keyboard_html += f'<span class="inline-button">{button_text}</span>'
                    inline_keyboard_html += '</div>'
                inline_keyboard_html += '</div>'

            if m.reply_markup and hasattr(m.reply_markup, 'keyboard'):
                reply_keyboard_html = '<div class="reply-keyboard">'
                for row in m.reply_markup.keyboard:
                    reply_keyboard_html += '<div>'
                    for button in row:
                        button_text = html.escape(button.text)
                        reply_keyboard_html += f'<span class="reply-button">{button_text}</span>'
                    reply_keyboard_html += '</div>'
                reply_keyboard_html += '</div>'

            reactions_html = ""
            if m.reactions and hasattr(m.reactions, 'reactions'):
                reactions_html += '<div class="reactions">'
                for reaction in m.reactions.reactions:
                    if hasattr(reaction, 'custom_emoji_id') and reaction.custom_emoji_id:
                        emoji_path = os.path.join("downloaded_emojis", f"emoji_{reaction.custom_emoji_id}.tgs")
                        if not os.path.exists(emoji_path):
                            try:
                                sticker_set = app.get_sticker_set(str(reaction.custom_emoji_id))
                                if sticker_set and sticker_set.stickers:
                                    file_path = app.download_media(
                                        sticker_set.stickers[0],
                                        file_name=emoji_path
                                    )
                            except Exception as e:
                                print(f"Error downloading custom emoji: {e}")
                                emoji_path = None
                        if emoji_path:
                            reactions_html += f'<span class="reaction"><img src="{emoji_path}" height="20"> {reaction.count}</span>'
                        else:
                            reactions_html += f'<span class="reaction">{reaction.emoji or '❓'} {reaction.count}</span>'
                    elif hasattr(reaction, 'is_paid') and reaction.is_paid:
                        reactions_html += f'<span class="reaction"><img src="imgs/star.png" height="20"> {reaction.count}</span>'
                    else:
                        emoji_path = emoji_img.get(reaction.emoji)
                        if emoji_path:
                            reactions_html += f'<span class="reaction"><img src="{emoji_path}" height="20"> {reaction.count}</span>'
                        else:
                            reactions_html += f'<span class="reaction">{reaction.emoji or '❓'} {reaction.count}</span>'
                reactions_html += '</div>'

            view_count = m.views if m.views else 0
            view_count_str = f"{view_count / 1000:.1f}K" if view_count > 1000 else str(view_count)
            messages_html += f"""
                <div class="message {message_class}">
                    {forwarded_from_html}
                    {reply_preview_html}
                    {photo_html}
                    <div class="message-content">
                        <div class="message-details">{text}</div>
{'<span class="message-info">👁 {view_count_str}  {time_str}</span>' if chat.type in ("group", "supergroup", "channel") else f'<span class="message-info">{time_str}</span>'}
                    </div>
                    {inline_keyboard_html}
                    {reactions_html}
                </div>
            """

        final_html = html_template.format(
            chat_header=header_html,
            messages=messages_html,
            input_container=input_container_html,
            reply_keyboard=reply_keyboard_html
        )

        with open("telegram_chat.html", "w", encoding="utf-8") as file:
            file.write(final_html)

    except Exception as e:
        print(f"Error: {e}")