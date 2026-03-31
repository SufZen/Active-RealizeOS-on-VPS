"""
Telegram channel adapter for RealizeOS.

Wraps python-telegram-bot to receive and send messages via Telegram.
This is an optional channel — requires a bot token.

Supports: text messages, documents (PDF), photos, and voice notes.
"""

import asyncio
import io
import logging

from realize_core.channels.base import BaseChannel, IncomingMessage, OutgoingMessage
from realize_core.utils.message_utils import split_message

logger = logging.getLogger(__name__)


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from a PDF file. Returns extracted text or error message."""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"[Page {i}]\n{text}")
            return "\n\n".join(pages) if pages else "[PDF contained no extractable text]"
    except ImportError:
        logger.warning("pdfplumber not installed — PDF text extraction unavailable")
        return "[PDF received but pdfplumber is not installed for text extraction]"
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"[PDF extraction failed: {e}]"


async def _transcribe_voice(file_bytes: bytes, file_path: str = "") -> str:
    """Transcribe a voice message using the configured LLM (Gemini Flash supports audio)."""
    try:
        # Gemini natively supports audio input — send as inline data
        import google.genai as genai

        client = genai.Client()
        audio_part = genai.types.Part.from_bytes(
            data=file_bytes,
            mime_type="audio/ogg",
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                audio_part,
                "Transcribe this voice message exactly. Return only the transcription, nothing else.",
            ],
        )
        return response.text.strip() if response.text else "[Could not transcribe voice message]"
    except ImportError:
        logger.warning("google-genai not available for voice transcription")
        return "[Voice message received but transcription is not available]"
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        return f"[Voice transcription failed: {e}]"


class TelegramChannel(BaseChannel):
    """
    Telegram bot channel using python-telegram-bot library.

    Supports text, documents (PDF), photos, and voice messages.
    All non-text content is extracted/transcribed to text before processing.

    Modes:
    - "single": Routes all messages to a fixed system_key (default).
    - "super_agent": Multi-system routing via smart keyword matching,
      /system command overrides, and optional topic-to-system mapping.
    """

    def __init__(
        self,
        bot_token: str,
        system_key: str = "",
        authorized_users: set = None,
        mode: str = "single",
        name: str = "",
        topic_routing: dict = None,
    ):
        super().__init__("telegram")
        self.bot_token = bot_token
        self.system_key = system_key
        self.authorized_users = authorized_users or set()
        self.mode = mode
        self.bot_name = name
        self.topic_routing = topic_routing or {}
        self._application = None
        # Per-user system overrides (set via /system command)
        self._user_system_overrides: dict[str, str] = {}
        # Topic discovery: thread_id → first message text (for mapping)
        self._discovered_topics: dict[int, str] = {}

    async def start(self):
        """Start the Telegram bot in polling mode."""
        try:
            from telegram import BotCommand
            from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

            self._application = ApplicationBuilder().token(self.bot_token).build()

            # Command handlers
            self._application.add_handler(CommandHandler("brief", self._handle_brief))
            self._application.add_handler(CommandHandler("done", self._handle_done))
            self._application.add_handler(CommandHandler("research", self._handle_research))
            self._application.add_handler(CommandHandler("reset", self._handle_reset))
            self._application.add_handler(CommandHandler("remember", self._handle_remember))
            # Tool shortcut commands
            self._application.add_handler(CommandHandler("inbox", self._handle_inbox))
            self._application.add_handler(CommandHandler("calendar", self._handle_calendar))
            self._application.add_handler(CommandHandler("search", self._handle_search))
            self._application.add_handler(CommandHandler("email", self._handle_email))
            self._application.add_handler(CommandHandler("drive", self._handle_drive))
            if self.mode == "super_agent":
                self._application.add_handler(CommandHandler("system", self._handle_system))
                self._application.add_handler(CommandHandler("maptopics", self._handle_maptopics))

            # Text messages (excludes commands)
            self._application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
            )
            # Documents (PDF, etc.)
            self._application.add_handler(
                MessageHandler(filters.Document.ALL, self._handle_document)
            )
            # Photos
            self._application.add_handler(
                MessageHandler(filters.PHOTO, self._handle_photo)
            )
            # Voice messages
            self._application.add_handler(
                MessageHandler(filters.VOICE | filters.AUDIO, self._handle_voice)
            )

            self.logger.info("Telegram channel starting (polling mode)")
            await self._application.initialize()
            await self._application.start()
            await self._application.updater.start_polling()

            # Register command menu in Telegram (visible in chat input)
            try:
                commands = [
                    BotCommand("brief", "Start a new request"),
                    BotCommand("done", "Mark task as completed"),
                    BotCommand("inbox", "Check recent emails"),
                    BotCommand("calendar", "View upcoming events"),
                    BotCommand("search", "Search the web"),
                    BotCommand("email", "Draft an email"),
                    BotCommand("drive", "Search Google Drive"),
                    BotCommand("research", "Deep research on a topic"),
                    BotCommand("reset", "Clear conversation history"),
                    BotCommand("remember", "Save to persistent memory"),
                ]
                if self.mode == "super_agent":
                    commands.append(BotCommand("system", "Switch system context"))
                await self._application.bot.set_my_commands(commands)
                bot_label = self.bot_name or "telegram"
                self.logger.info(f"Telegram command menu registered for '{bot_label}' (mode={self.mode})")
            except Exception as e:
                self.logger.warning(f"Failed to register command menu: {e}")

        except ImportError:
            self.logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")

    async def stop(self):
        """Stop the Telegram bot."""
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            self.logger.info("Telegram channel stopped")

    async def send_message(self, message: OutgoingMessage):
        """Send a message back via Telegram with smart splitting and error recovery."""
        if self._application and message.metadata.get("chat_id"):
            chat_id = message.metadata["chat_id"]
            for chunk in split_message(message.text or ""):
                await self._send_chunk(chat_id, chunk)

    def format_instructions(self) -> str:
        """Telegram-specific formatting rules."""
        return (
            "Format your response for Telegram messaging. Keep it conversational. "
            "Use short paragraphs. Avoid markdown headers (# ##). "
            "Use *bold* and _italic_ sparingly. "
            "Use bullet points (- ) for lists. Keep responses under 4000 characters."
        )

    def _check_auth(self, user_id: str) -> bool:
        """Check if user is authorized. Returns True if authorized or no restrictions set."""
        if not self.authorized_users:
            return True
        return int(user_id) in self.authorized_users

    async def _handle_text(self, update, context):
        """Handle a plain text message."""
        if not update.message or not update.message.text:
            return

        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            await update.message.reply_text("Unauthorized. Contact the system administrator.")
            return

        text = update.message.text
        topic_id = str(update.message.message_thread_id or "")
        chat_id = update.message.chat_id

        # Log topic discovery for forum groups (negative chat_id = group)
        if topic_id and chat_id < 0:
            thread_id = update.message.message_thread_id
            if thread_id and thread_id not in self._discovered_topics:
                self._discovered_topics[thread_id] = text[:80]
            self.logger.info(f"[TOPIC] chat={chat_id} thread_id={thread_id} text='{text[:60]}'")

        # Resolve system_key: fixed in single mode, dynamic in super_agent mode
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, text, topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=text,
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )

        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_document(self, update, context):
        """Handle a document attachment (PDF, images, etc.)."""
        if not update.message or not update.message.document:
            return

        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            await update.message.reply_text("Unauthorized.")
            return

        doc = update.message.document
        file_name = doc.file_name or "document"
        caption = update.message.caption or ""
        mime_type = doc.mime_type or ""

        self.logger.info(f"Document received: {file_name} ({mime_type}, {doc.file_size} bytes)")

        # Download the file
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        # Extract content based on type
        if mime_type == "application/pdf" or file_name.lower().endswith(".pdf"):
            await update.message.reply_text(f"Reading PDF: {file_name}...")
            extracted = _extract_pdf_text(bytes(file_bytes))
            text = f"[Document: {file_name}]\n{extracted}"
            if caption:
                text = f"{caption}\n\n{text}"
            else:
                # Check if there's conversation context — if so, don't override with standalone instructions
                from realize_core.memory.conversation import get_history
                history = get_history(self.system_key, user_id)
                if history:
                    text = f"Here is the document I mentioned.\n\n{text}"
                else:
                    text = f"I'm sending you this document to review. Please summarize the key points and suggest next steps.\n\n{text}"
        elif mime_type and mime_type.startswith("image/"):
            # Image sent as document — use Gemini vision to extract content
            try:
                from realize_core.llm.gemini_client import call_gemini_vision

                vision_prompt = (
                    "Extract all text, numbers, and visual content from this image. "
                    "Be precise with numbers, dates, and amounts."
                )
                extracted = await call_gemini_vision(
                    system_prompt="You are a document and image reader. Extract all text and content precisely.",
                    messages=[{"role": "user", "content": vision_prompt}],
                    image_data=bytes(file_bytes),
                    media_type=mime_type,
                )
                text = f"[Image: {file_name}]\n{extracted}"
                if caption:
                    text = f"{caption}\n\n{text}"
            except Exception as e:
                self.logger.error(f"Image vision failed: {e}")
                text = caption or f"I sent you an image file: {file_name}. Please analyze it."
                text += "\n\n[Image received but vision extraction failed]"
        else:
            # Other file types — try to read as text
            try:
                content = bytes(file_bytes).decode("utf-8", errors="replace")
                text = f"[File: {file_name}]\n{content[:10000]}"
                if caption:
                    text = f"{caption}\n\n{text}"
            except Exception:
                text = f"[File received: {file_name} ({mime_type}) — unable to extract text content]"
                if caption:
                    text = f"{caption}\n\n{text}"

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, text, topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=text,
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )

        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_photo(self, update, context):
        """Handle a photo message — extract text/content via Gemini vision, then process."""
        if not update.message or not update.message.photo:
            return

        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            await update.message.reply_text("Unauthorized.")
            return

        caption = update.message.caption or ""

        # Download highest-resolution photo
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        self.logger.info(f"Photo received: {photo.width}x{photo.height}, {len(file_bytes)} bytes, caption='{caption}'")

        # Use Gemini vision to extract text/content from the image
        extracted = None
        try:
            from realize_core.llm.gemini_client import call_gemini_vision

            vision_prompt = (
                "Extract all text, numbers, and visual content from this image. "
                "Be precise with numbers, dates, and amounts. "
                "Return the extracted content clearly."
            )
            result = await call_gemini_vision(
                system_prompt="You are a document and image reader. Extract all text and content precisely.",
                messages=[{"role": "user", "content": vision_prompt}],
                image_data=bytes(file_bytes),
                media_type="image/jpeg",
            )
            # call_gemini_vision may return error strings instead of raising
            if result and "error occurred" not in result.lower():
                extracted = result
            else:
                self.logger.warning(f"Vision extraction returned error: {result}")

        except Exception as e:
            self.logger.error(f"Vision extraction failed: {e}")

        # Build the message text
        if extracted:
            if caption:
                text = f"{caption}\n\n[Image content]: {extracted}"
            else:
                text = f"[Image content]: {extracted}"
        elif caption:
            # Vision failed but we have a caption — process it with conversation context
            text = f"{caption}\n\n[A photo was attached but could not be read]"
        else:
            # No caption, no extraction — ask user to describe
            text = "I received a photo but couldn't extract its content. Could you describe what's in it or type the information?"

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, text, topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=text,
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )

        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_voice(self, update, context):
        """Handle a voice message — transcribe and process as text."""
        voice = update.message.voice or update.message.audio
        if not update.message or not voice:
            return

        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            await update.message.reply_text("Unauthorized.")
            return

        self.logger.info(f"Voice message received: {voice.duration}s, {voice.file_size} bytes")
        await update.message.reply_text("Transcribing voice message...")

        # Download and transcribe
        tg_file = await voice.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        transcription = await _transcribe_voice(bytes(file_bytes))

        text = f"[Voice message transcription]: {transcription}"
        caption = update.message.caption or ""
        if caption:
            text = f"{caption}\n\n{text}"

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, text, topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=text,
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )

        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    # ── System Routing (super_agent mode) ─────────────────────

    def _resolve_system_key(self, user_id: str, text: str, topic_id: str = "") -> str:
        """
        Resolve the system_key for a message. Used in super_agent mode.

        Priority:
        1. Topic routing (if message is in a forum topic with a mapping)
        2. User override (set via /system command)
        3. Smart routing (keyword scoring against all systems)
        """
        # 1. Topic routing (highest priority — forum topic → system)
        if topic_id and self.topic_routing:
            mapped = self.topic_routing.get(topic_id) or self.topic_routing.get(int(topic_id) if topic_id.isdigit() else topic_id)
            if mapped:
                self.logger.info(f"[ROUTE] Topic routing: thread_id={topic_id} → {mapped}")
                return mapped

        # 2. User override (set via /system command)
        override = self._user_system_overrides.get(user_id)
        if override:
            self.logger.info(f"[ROUTE] User override: user={user_id} → {override}")
            return override

        # 3. Smart routing
        try:
            from realize_core.config import build_systems_dict, load_config
            from realize_core.engine import route_to_system

            config = load_config()
            from realize_core.config import KB_PATH
            kb_path = config.get("kb_path", KB_PATH)
            from pathlib import Path
            systems = build_systems_dict(config, kb_path=Path(kb_path).resolve())
            return route_to_system(text, systems)
        except Exception as e:
            self.logger.error(f"Smart routing failed: {e}")
            return "personal"  # Safe fallback

    # ── Telegram Command Handlers ──────────────────────────────

    async def _handle_system(self, update, context):
        """Switch system context. Usage: /system [key|auto]"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        args = context.args or []

        if not args:
            # Show current system and list all available
            current = self._user_system_overrides.get(user_id, "auto (smart routing)")
            try:
                from pathlib import Path

                from realize_core.config import KB_PATH, build_systems_dict, load_config
                config = load_config()
                systems = build_systems_dict(config, kb_path=Path(config.get("kb_path", KB_PATH)).resolve())
                system_list = "\n".join(f"  - {k} ({v.get('name', k)})" for k, v in systems.items())
            except Exception:
                system_list = "  (could not load systems)"

            await update.message.reply_text(
                f"Current system: {current}\n\n"
                f"Available systems:\n{system_list}\n\n"
                f"Usage:\n"
                f"/system <key> — switch to a system\n"
                f"/system auto — return to smart routing"
            )
            return

        target = args[0].lower().strip()

        if target == "auto":
            self._user_system_overrides.pop(user_id, None)
            await update.message.reply_text("Switched to auto mode (smart routing). I'll detect the right system from your messages.")
            return

        # Validate the system key exists
        try:
            from pathlib import Path

            from realize_core.config import KB_PATH, build_systems_dict, load_config
            config = load_config()
            systems = build_systems_dict(config, kb_path=Path(config.get("kb_path", KB_PATH)).resolve())
        except Exception:
            systems = {}

        if target not in systems:
            available = ", ".join(sorted(systems.keys())) if systems else "none loaded"
            await update.message.reply_text(f"System '{target}' not found.\nAvailable: {available}")
            return

        self._user_system_overrides[user_id] = target
        sys_name = systems[target].get("name", target)
        await update.message.reply_text(f"Switched to: {sys_name} ({target})\nAll messages will route here until you /system auto")

    async def _handle_maptopics(self, update, context):
        """Show discovered forum topic thread IDs. Usage: /maptopics [set <thread_id> <system_key>]"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        args = context.args or []

        if not args:
            # Show all discovered topics
            if not self._discovered_topics:
                return await update.message.reply_text(
                    "No topics discovered yet.\n"
                    "Send a message in each forum topic, then run /maptopics again."
                )
            lines = ["Discovered forum topics:\n"]
            for tid, text in sorted(self._discovered_topics.items()):
                lines.append(f"  thread_id={tid} → \"{text}\"")
            lines.append(f"\nTotal: {len(self._discovered_topics)} topics")
            lines.append("\nCopy these thread_ids into realize-os.yaml topic_routing config.")
            return await update.message.reply_text("\n".join(lines))

        # /maptopics clear — reset discovered topics
        if args[0] == "clear":
            self._discovered_topics.clear()
            return await update.message.reply_text("Topic discovery cache cleared.")

        # /maptopics yaml — dump as YAML-ready config
        if args[0] == "yaml":
            if not self._discovered_topics:
                return await update.message.reply_text("No topics discovered yet.")
            lines = ["topic_routing:"]
            for tid, text in sorted(self._discovered_topics.items()):
                # suggest a system_key from the text
                lines.append(f'  "{tid}": "TODO"  # {text}')
            return await update.message.reply_text("\n".join(lines))

        await update.message.reply_text(
            "Usage:\n"
            "/maptopics — show discovered topic thread IDs\n"
            "/maptopics yaml — dump as YAML config template\n"
            "/maptopics clear — reset discovery cache"
        )

    async def _handle_brief(self, update, context):
        """Start a new request — clear context and ask structured questions."""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        from realize_core.memory.conversation import clear_history

        topic_id = str(update.message.message_thread_id or "")
        system_key = (
            self._resolve_system_key(user_id, "brief", topic_id)
            if self.mode == "super_agent"
            else self.system_key
        )
        clear_history(system_key, user_id)
        await update.message.reply_text(
            "Starting a new request. Tell me:\n\n"
            "1. What do you need?\n"
            "2. Any specific entity or contact involved?\n"
            "3. Deadline or urgency?"
        )

    async def _handle_done(self, update, context):
        """Mark current task as completed."""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        from realize_core.memory.conversation import clear_history

        topic_id = str(update.message.message_thread_id or "")
        system_key = (
            self._resolve_system_key(user_id, "done", topic_id)
            if self.mode == "super_agent"
            else self.system_key
        )
        clear_history(system_key, user_id)
        await update.message.reply_text("Task marked as done. Context cleared. What's next?")

    async def _handle_research(self, update, context):
        """Trigger online research. Usage: /research <query>"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        query = " ".join(context.args) if context.args else ""
        if not query:
            return await update.message.reply_text("Usage: /research <what to search for>")

        await update.message.reply_text(f"Researching: {query}...")
        message = IncomingMessage(
            user_id=user_id,
            text=f"Research and find: {query}",
            system_key=self.system_key,
            channel="telegram",
            topic_id=str(update.message.message_thread_id or ""),
            metadata={"chat_id": update.message.chat_id},
        )
        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_reset(self, update, context):
        """Clear conversation history."""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        from realize_core.memory.conversation import clear_history

        topic_id = str(update.message.message_thread_id or "")
        system_key = (
            self._resolve_system_key(user_id, "reset", topic_id)
            if self.mode == "super_agent"
            else self.system_key
        )
        clear_history(system_key, user_id)
        await update.message.reply_text("Conversation cleared. Fresh start!")

    async def _handle_remember(self, update, context):
        """Save a note to persistent memory. Usage: /remember <text>"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        note = " ".join(context.args) if context.args else ""
        if not note:
            return await update.message.reply_text("Usage: /remember <what to remember>")

        from datetime import datetime

        from realize_core.config import KB_PATH

        memory_file = KB_PATH / "systems" / "personal" / "I-insights" / "paulo-memory.md"
        memory_file.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n- [{timestamp}] {note}\n"

        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(entry)

        await update.message.reply_text(f"Remembered: {note}")

    # ── Tool Shortcut Commands ────────────────────────────────

    async def _handle_inbox(self, update, context):
        """Check recent emails. Usage: /inbox [query]"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        query = " ".join(context.args) if context.args else "is:unread"
        await update.message.reply_text(f"Checking emails: {query}...")

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, f"email inbox {query}", topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=f"Check my email inbox. Search for: {query}. Show me the most recent messages with sender, subject, and a brief snippet.",
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )
        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_calendar(self, update, context):
        """View upcoming calendar events. Usage: /calendar [days]"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        args = context.args or []
        days = "7"
        for arg in args:
            if arg.isdigit():
                days = arg
                break

        await update.message.reply_text(f"Checking calendar for the next {days} days...")

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, "calendar events schedule", topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=f"Show my calendar events for the next {days} days. Include time, title, and any attendees.",
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )
        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_search(self, update, context):
        """Search the web. Usage: /search <query>"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        query = " ".join(context.args) if context.args else ""
        if not query:
            return await update.message.reply_text("Usage: /search <what to search for>")

        await update.message.reply_text(f"Searching: {query}...")

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, query, topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=f"Search the web for: {query}. Summarize the top results with key findings.",
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )
        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_email(self, update, context):
        """Draft or send an email. Usage: /email <to> <subject> or /email <instructions>"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        text = " ".join(context.args) if context.args else ""
        if not text:
            return await update.message.reply_text(
                "Usage:\n"
                "/email Draft an email to john@example.com about the project update\n"
                "/email Reply to the last email from Maria about the contract"
            )

        await update.message.reply_text("Composing email...")

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, f"email draft {text}", topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=f"Help me with this email task: {text}. Create a draft email unless I explicitly ask to send it.",
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )
        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    async def _handle_drive(self, update, context):
        """Search Google Drive. Usage: /drive <query>"""
        user_id = str(update.message.from_user.id)
        if not self._check_auth(user_id):
            return await update.message.reply_text("Unauthorized.")

        query = " ".join(context.args) if context.args else ""
        if not query:
            return await update.message.reply_text("Usage: /drive <what to search for>")

        await update.message.reply_text(f"Searching Drive: {query}...")

        topic_id = str(update.message.message_thread_id or "")
        if self.mode == "super_agent":
            system_key = self._resolve_system_key(user_id, f"google drive search {query}", topic_id)
        else:
            system_key = self.system_key

        message = IncomingMessage(
            user_id=user_id,
            text=f"Search my Google Drive for: {query}. Show file names, types, and links.",
            system_key=system_key,
            channel="telegram",
            topic_id=topic_id,
            metadata={"chat_id": update.message.chat_id},
        )
        response = await self.handle_incoming(message)
        await self._send_response(update, response.text)

    # ── Response Helpers ─────────────────────────────────────

    async def _send_chunk(self, chat_id: int, text: str):
        """Send a single text chunk with retry on transient failure."""
        try:
            await self._application.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            self.logger.error(f"Telegram send failed: {e}")
            try:
                await asyncio.sleep(1)
                await self._application.bot.send_message(chat_id=chat_id, text=text)
            except Exception as retry_err:
                self.logger.error(f"Telegram send retry failed: {retry_err}")

    async def _send_response(self, update, text: str):
        """Send a response, splitting into chunks with smart boundaries."""
        if not text:
            text = "I received your message but couldn't generate a response."
        chat_id = update.message.chat_id
        for chunk in split_message(text):
            await self._send_chunk(chat_id, chunk)
