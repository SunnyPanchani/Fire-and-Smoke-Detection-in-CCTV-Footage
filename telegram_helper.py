# telegram_helper.py - Helper functions for multiple Telegram chat IDs

import requests
import time
from typing import List, Tuple, Optional

def send_telegram_message_multiple(bot_token: str, chat_ids: List[int], message: str, 
                                 parse_mode: str = "Markdown", max_retries: int = 3, 
                                 silent_fail: bool = False) -> dict:
    """
    Send a message to multiple Telegram chat IDs
    
    Args:
        bot_token: Telegram bot token
        chat_ids: List of chat IDs to send to
        message: Message text to send
        parse_mode: Telegram parse mode (default: Markdown)
        max_retries: Maximum number of retries per chat ID
        silent_fail: If True, don't print errors (useful for shutdown)
    
    Returns:
        Dictionary with success status and results
    """
    results = {
        'total_chats': len(chat_ids),
        'successful_sends': 0,
        'failed_sends': 0,
        'results': []
    }
    
    if not silent_fail:
        print(f"📤 Sending Telegram message to {len(chat_ids)} chat(s): {chat_ids}")
    
    for chat_id in chat_ids:
        success = False
        error_msg = None
        
        if not silent_fail:
            print(f"📱 Attempting to send to chat ID: {chat_id}")
        
        for attempt in range(max_retries):
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': parse_mode
                }
                
                response = requests.post(url, json=payload, timeout=15)
                
                if response.status_code == 200:
                    success = True
                    results['successful_sends'] += 1
                    if not silent_fail:
                        print(f"✅ Message sent successfully to chat ID: {chat_id}")
                    break
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if not silent_fail:
                        print(f"❌ HTTP Error for chat ID {chat_id}: {error_msg}")
                    
            except requests.exceptions.Timeout:
                error_msg = "Request timeout"
                if not silent_fail:
                    print(f"⏰ Timeout sending to chat ID {chat_id} (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                error_msg = "Connection error"
                if not silent_fail:
                    print(f"🔌 Connection error for chat ID {chat_id} (attempt {attempt + 1})")
            except requests.exceptions.SSLError:
                error_msg = "SSL error"
                if not silent_fail:
                    print(f"🔐 SSL error for chat ID {chat_id} (attempt {attempt + 1})")
            except Exception as e:
                error_msg = str(e)
                if not silent_fail:
                    print(f"❓ Unexpected error for chat ID {chat_id}: {error_msg}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                time.sleep(2)
        
        if not success:
            results['failed_sends'] += 1
            if not silent_fail:
                print(f"⚠️ Failed to send message to chat ID {chat_id} after {max_retries} attempts: {error_msg}")
        
        results['results'].append({
            'chat_id': chat_id,
            'success': success,
            'error': error_msg if not success else None
        })
        
        # Small delay between sends to avoid rate limiting
        time.sleep(0.5)
    
    if not silent_fail:
        print(f"📊 Telegram send summary: {results['successful_sends']}/{results['total_chats']} successful")
    
    return results

def send_telegram_photo_multiple(bot_token: str, chat_ids: List[int], photo_path: str, 
                                caption: str = "", max_retries: int = 3, silent_fail: bool = False) -> dict:
    """
    Send a photo to multiple Telegram chat IDs
    
    Args:
        bot_token: Telegram bot token
        chat_ids: List of chat IDs to send to
        photo_path: Path to the photo file
        caption: Photo caption
        max_retries: Maximum number of retries per chat ID
        silent_fail: If True, don't print errors
    
    Returns:
        Dictionary with success status and results
    """
    results = {
        'total_chats': len(chat_ids),
        'successful_sends': 0,
        'failed_sends': 0,
        'results': []
    }
    
    try:
        with open(photo_path, 'rb') as photo_file:
            photo_data = photo_file.read()
    except Exception as e:
        if not silent_fail:
            print(f"⚠️ Error reading photo file {photo_path}: {e}")
        results['failed_sends'] = len(chat_ids)
        for chat_id in chat_ids:
            results['results'].append({
                'chat_id': chat_id,
                'success': False,
                'error': f"Could not read photo file: {e}"
            })
        return results
    
    if not silent_fail:
        print(f"📤 Sending photo to {len(chat_ids)} chat(s): {chat_ids}")
    
    for chat_id in chat_ids:
        success = False
        error_msg = None
        
        if not silent_fail:
            print(f"📱 Attempting to send photo to chat ID: {chat_id}")
        
        for attempt in range(max_retries):
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                
                files = {'photo': ('photo.jpg', photo_data, 'image/jpeg')}
                data = {
                    'chat_id': chat_id,
                    'caption': caption
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    success = True
                    results['successful_sends'] += 1
                    if not silent_fail:
                        print(f"✅ Photo sent successfully to chat ID: {chat_id}")
                    break
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if not silent_fail:
                        print(f"❌ HTTP Error for chat ID {chat_id}: {error_msg}")
                    
            except requests.exceptions.Timeout:
                error_msg = "Request timeout"
                if not silent_fail:
                    print(f"⏰ Timeout sending photo to chat ID {chat_id} (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                error_msg = "Connection error"
                if not silent_fail:
                    print(f"🔌 Connection error for chat ID {chat_id} (attempt {attempt + 1})")
            except requests.exceptions.SSLError:
                error_msg = "SSL error"
                if not silent_fail:
                    print(f"🔐 SSL error for chat ID {chat_id} (attempt {attempt + 1})")
            except Exception as e:
                error_msg = str(e)
                if not silent_fail:
                    print(f"❓ Unexpected error for chat ID {chat_id}: {error_msg}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                time.sleep(2)
        
        if not success:
            results['failed_sends'] += 1
            if not silent_fail:
                print(f"⚠️ Failed to send photo to chat ID {chat_id} after {max_retries} attempts: {error_msg}")
        
        results['results'].append({
            'chat_id': chat_id,
            'success': success,
            'error': error_msg if not success else None
        })
        
        # Small delay between sends to avoid rate limiting
        time.sleep(0.5)
    
    if not silent_fail:
        print(f"📊 Telegram photo send summary: {results['successful_sends']}/{results['total_chats']} successful")
    
    return results

def format_telegram_config_for_legacy_compatibility(bot_token: str, chat_ids: List[int]) -> Tuple[str, int]:
    """
    Format new telegram config for legacy code compatibility
    Returns the first chat ID for backward compatibility
    
    Args:
        bot_token: Telegram bot token
        chat_ids: List of chat IDs
    
    Returns:
        Tuple of (bot_token, first_chat_id)
    """
    if not chat_ids:
        return bot_token, None
    
    return bot_token, chat_ids[0]

def is_multiple_chat_config(telegram_config) -> bool:
    """
    Check if telegram_config contains multiple chat IDs
    
    Args:
        telegram_config: Tuple of (bot_token, chat_ids)
    
    Returns:
        True if chat_ids is a list with multiple IDs, False otherwise
    """
    if not telegram_config or len(telegram_config) != 2:
        return False
    
    bot_token, chat_ids = telegram_config
    return isinstance(chat_ids, list) and len(chat_ids) > 1